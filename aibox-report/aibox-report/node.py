import copy
from datetime import datetime
import math
import os
import json
import time
import base64
import shutil
from typing import Dict, List, Union
from collections import deque

import cv2
import numpy as np
from loguru import logger
from filterpy.kalman import KalmanFilter
from coral import (
    CoralNode,
    BaseParamsModel,
    NodeType,
    ObjectPayload,
    RTManager,
    RawPayload,
    PTManager,
    ReturnPayloadWithTS,
)
from coral.constants import MOUNT_PATH
from coral.metrics import init_mqtt, mqtt
from pydantic import Field

import web
from algrothms import report
from algrothms.event import EventRecord
from algrothms.gpio import GpioControl


MOUNT_NODE_PATH = os.path.join(MOUNT_PATH, "aibox")
os.makedirs(MOUNT_NODE_PATH, exist_ok=True)


class InvalidPersonCount(Exception):
    pass


class MQTTParamsModel(BaseParamsModel):
    broker: str = Field(
        default_factory=lambda: os.environ.get("MQTT_BROKER", "127.0.0.1")
    )
    port: int = Field(default_factory=lambda: int(os.environ.get("MQTT_PORT", 1883)))
    username: str = Field(
        default_factory=lambda: os.environ.get("MQTT_USERNAME", "admin")
    )
    password: str = Field(
        default_factory=lambda: os.environ.get("MQTT_PASSWORD", "admin")
    )


class GpioParamsModel(BaseParamsModel):
    enable: bool = True
    pins: list = [7, 29, 31]
    interval: float = Field(default=3, description="触发gpio on的间隔时间")


@PTManager.register()
class AIboxReportParamsModel(BaseParamsModel):
    mqtt: MQTTParamsModel = MQTTParamsModel()
    gpio: GpioParamsModel = GpioParamsModel()
    windows_interval: int = Field(
        default=5, description="预测值人数窗口最大间隔时间，在这时间内的才做统计"
    )
    report_image: bool = False
    report_url: str = Field(
        default="https://iot.lhehs.com/iot-api/resource/uploadNoAuthor",
        description="图片上报地址",
    )
    report_scene: float = Field(
        default=0.5,
        description="上报场景, 越小表示场景遮挡越多，越相信历史数据",
        ge=0,
        le=1,
    )
    max_camera_invalid_stats: int = Field(
        default=300, description="最大摄像头无效统计次数, 触发预警"
    )
    base_dir_name: str = Field(default="report", description="事件保存路径")

    @property
    def base_dir(self):
        _dir = os.path.join(MOUNT_NODE_PATH, self.base_dir_name)
        os.makedirs(_dir, exist_ok=True)
        return _dir

    @property
    def kf_Q(self):
        return 0.0001 * pow(100, self.report_scene)

    @property
    def kf_R(self):
        return 100 / pow(100, self.report_scene)

    @property
    def predict_threshold(self):
        """基于此值来判定人数是否向上还是向下取整"""
        return 0.7 - self.report_scene * 0.4


@RTManager.register()
class AIboxReportRTModel(ReturnPayloadWithTS):
    person_count: int
    objects_count: int


class AIboxReport(CoralNode):

    # 配置文件，默认文件config.json, 可通过环境变量 CORAL_NODE_CONFIG_PATH 覆盖
    node_name = "上报节点"
    node_desc = "功能，上报当前信息"
    config_path = "config.json"
    node_type = NodeType.trigger

    web.check_config_fp_or_set_default(CoralNode.get_config()[0])

    def __init__(self):
        super().__init__()
        # 摄像头人数
        self.cameras_frame_data: Dict[str, RawPayload] = {}
        # 摄像头最后一次接收时间
        self.cameras_last_capture_time: Dict[str, float] = {}
        # 摄像头能合并一起计算的最大间隔时间
        self.concat_max_interval = self.params.windows_interval
        # 近几次上报的观察人数列表
        self.observations = deque(maxlen=15)
        # kalman滤波器
        self.kf = self.init_kalman_filter()
        # 初始化事件类
        self.event = EventRecord(event_dir=self.params.base_dir)
        web.async_run(self.config.node_id, self.params.base_dir)
        # 持久化数据
        web.durable_config(self.params.model_dump())
        # 上报图片数据
        report_images_dir = os.path.join(self.params.base_dir, "images")
        os.makedirs(report_images_dir, exist_ok=True)
        self.image_report_thread = report.ImageSnapshotReport(
            url=self.params.report_url, report_image_dir=report_images_dir
        )
        self.image_report_thread.start()
        # 无效统计次数统计
        self.camera_invalid_stats = 0

    def init(self, index: int, context: dict):
        """
        初始化参数，可传递到sender方法中

        :param context: 上下文参数
        """
        data = self.params.model_dump()
        gpio_cfg = data["gpio"]

        try:
            mqtt_client = init_mqtt(data["mqtt"])
        except Exception as e:
            logger.error(f"mqtt init error: {e}")
            mqtt_client = None

        gpio_client = GpioControl(
            gpio_cfg["pins"], gpio_cfg["enable"], gpio_cfg["interval"]
        )
        context["mqtt"] = mqtt_client
        context["gpio"] = gpio_client
        context["event"] = self.event

        web.contexts[index] = {
            "context": context,
            "params": self.params,
            "kf": self.kf,
            "image_report_thread": self.image_report_thread,
        }

    @property
    def topic(self):
        return f"aibox/inference/{self.mac_addr}/{self.config.node_id}"

    @property
    def camera_droped_topic(self):
        return f"aibox/camera_droped/{self.mac_addr}"

    def init_kalman_filter(self):
        kf = KalmanFilter(dim_x=2, dim_z=1)

        # 定义状态转移矩阵和观测矩阵
        kf.F = np.array([[1, 1], [0, 1]])  # 状态转移矩阵
        kf.H = np.array([[1, 0]])  # 观测矩阵

        # 定义过程噪声协方差和观测噪声协方差
        kf.Q = np.eye(2) * self.params.kf_Q  # 过程噪声协方差
        kf.R = np.array([[self.params.kf_R]])  # 观测噪声协方差

        logger.info(f"init kalman filter: {self.params.kf_Q}, {self.params.kf_R}")

        # 初始化状态和协方差矩阵
        kf.x = np.array([0, 0])  # 初始状态
        kf.P = np.eye(2)  # 初始协方差矩阵
        return kf

    def prepare_objects(self, objects: List[ObjectPayload]):
        detects = []
        for obj in objects:
            detect = {
                # 表示人脸识别结果
                "id": obj.objects[0].label if obj.objects else None,
                # 表示目标检测结果
                "label": obj.label,
                # 表示目标检测概率
                "prob": obj.prob,
                # 表示目标检测框坐标
                "positions": [obj.box.x1, obj.box.y1, obj.box.x2, obj.box.y2],
                # 表示人脸检测概率
                "face_prop": obj.objects[0].prob if obj.objects else None,
            }
            detects.append(detect)
        return detects

    def encode_frame(self, frame: np.ndarray):
        is_ok, _frame = cv2.imencode(".jpg", frame)
        if not is_ok:
            raise ValueError("无法编码视频帧!")
        b64_frame = base64.b64encode(_frame).decode()
        return b64_frame

    def process_person_count(self, camera_ids: str):
        _valid_camera_ids = []
        _valid_person_count = 0
        for camera_id in self.cameras_frame_data:
            # 过滤掉最近concat_max_interval时间段内没更新的摄像头数据
            # 这类可能会存在摄像头不稳定的情况，camera_id中的数据不一定是最新的，因此过滤掉
            if (
                time.time() - self.cameras_last_capture_time[camera_id]
                > self.concat_max_interval
            ):
                continue
            _valid_camera_ids.append(camera_id)
            _valid_person_count += len(self.cameras_frame_data[camera_id].objects or [])

        # 验证此次统计的有效性
        # ! 这种模式会存在如果有1/2的摄像头出现问题，则会一直无法正确统计的情况, 后续需要以某种方式通知摄像头问题
        if (
            set(_valid_camera_ids) != set(camera_ids)
            and len(set(_valid_camera_ids)) / len(camera_ids) >= 0.5
        ):
            self.camera_invalid_stats += 1
            raise InvalidPersonCount(
                f"无效的摄像头: {set(camera_ids) - set(_valid_camera_ids)}"
            )
        else:
            # 有一次正常则清零
            self.camera_invalid_stats = 0
            self.observations.append(_valid_person_count)

        # 滤波统计
        pre_state_count = []
        for obs in self.observations:
            self.kf.predict()
            self.kf.update(obs)
            pre_state_count.append(self.kf.x[0])
        count = (
            math.ceil(self.kf.x[0])
            if self.kf.x[0] - math.floor(self.kf.x[0]) > self.params.predict_threshold
            else math.floor(self.kf.x[0])
        )
        logger.debug(
            f"预测值窗口中每一帧人数：{pre_state_count}, 最终人数：[ {count} ]"
        )
        # 向上取整返回最终的人数
        return count

    def sender(self, payload: RawPayload, context: Dict) -> AIboxReportRTModel:
        """
        数据发送函数

        :param payload: receiver的数据
        :param context: 上下文参数
        :return: 数据
        """
        # objects = self.prepare_objects(payload.objects or [])
        # 记录每个摄像头的人数
        self.cameras_last_capture_time[payload.source_id] = time.time()
        self.cameras_frame_data[payload.source_id] = payload.model_copy(deep=True)

        mqtt_client: Union[mqtt.Client, None] = context["mqtt"]
        gpio_client: GpioControl = context["gpio"]
        pre_camera_count = [
            len(camera_payload.objects or [])
            for camera_payload in self.cameras_frame_data.values()
        ]
        try:
            # 根据有效的统计人数来做反馈，若人数统计无效，则抛出异常，此次不做上报
            person_count = self.process_person_count(payload.raw_params["camera_ids"])
        except InvalidPersonCount as e:
            logger.warning(f"{e}")
            person_count = -1
            web.person_count = None
            # !无效统计次数比较，判断是否触发警报，若警报表示摄像头可能存在问题，或者上层节点通信存在问题
            if self.camera_invalid_stats >= self.params.max_camera_invalid_stats:
                if mqtt_client:
                    mqtt_client.publish(
                        self.camera_droped_topic, json.dumps({"msg": f"{e}"})
                    )
                logger.error(f"严重错误，上游节点错误或者摄像头掉线, {e}")
        else:
            report_msg = {
                "uuid": payload.raw_id,
                "source": payload.source_id,
                # !docker部署需要设置 network=host模式
                "mac_address": self.mac_addr,
                # ! 人数采用滤波过滤方式检测人数, 因此人数可能会与objects中的数量不符
                # ! 人数建议采用person_count给出的数值
                "person_count": person_count,
                # 处理时间，取当前帧的处理时间数据
                "duration": int(payload.nodes_cost * 1000),
                # 上报时间
                "report_time": int(time.time() * 1000),
                "extras": {},
            }

            if mqtt_client:
                if person_count and person_count > 0:
                    # 发布消息
                    mqtt_client.publish(self.topic, json.dumps(report_msg))

                    if self.params.report_image and self.cameras_frame_data:
                        # 图片上报信息加入队列
                        report.report_queue.append(
                            (
                                payload.raw_id,
                                person_count,
                                self.cameras_frame_data,
                            )
                        )
            else:
                logger.warning("mqtt client not init, report not send!!!")

            # 触发信号, 开
            if person_count and person_count != -1:
                with gpio_client:
                    gpio_client.trigger_on()

                self.event.add_event(
                    {
                        # 取时间: 年-月-日 时:分:秒.毫秒
                        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                        "person_count": person_count,
                        "objects_count": sum(pre_camera_count),
                        "pre_camera_count": pre_camera_count,
                    }
                )

            # 更新人数
            web.person_count = person_count

        return AIboxReportRTModel(
            person_count=person_count, objects_count=sum(pre_camera_count)
        )


if __name__ == "__main__":
    AIboxReport().run()
