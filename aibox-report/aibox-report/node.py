import math
import os
import json
import time
import base64
import shutil
from typing import Dict, List
from collections import defaultdict, deque

import cv2
import numpy as np
from loguru import logger
from filterpy.kalman import KalmanFilter
from coral import (
    CoralNode,
    BaseParamsModel,
    NodeType,
    ObjectPayload,
    RawPayload,
    PTManager,
)
from coral.metrics import init_mqtt, mqtt
from pydantic import Field

from algrothms.gpio import GpioControl


class MQTTParamsModel(BaseParamsModel):
    broker: str = "127.0.0.1"
    port: int = 1883
    username: str = "admin"
    password: str = "admin"


class GpioParamsModel(BaseParamsModel):
    enable: bool = True
    pins: list = [7, 29, 31]
    interval: float = Field(default=1, description="触发gpio on的间隔时间")


@PTManager.register()
class AIboxReportParamsModel(BaseParamsModel):
    mqtt: MQTTParamsModel = MQTTParamsModel()
    gpio: GpioParamsModel = GpioParamsModel()
    windows_interval: int = Field(
        default=1, description="预测值人数窗口最大间隔时间，在这时间内的才做统计"
    )
    report_image: bool = True


def check_config_fp_or_set_default(config_fp: str, default_config_fp: str):
    """
    校验配置文件是否存在，不存在则拷贝

    :param config_fp: 环境变量配置文件路径
    :param default_config_fp: 默认本地项目的配置文件路径
    """
    config_dir = os.path.split(config_fp)[0]
    if config_dir:
        os.makedirs(config_dir, exist_ok=True)
    if not os.path.exists(config_fp):
        logger.warning(f"{config_fp} not exists, copy from {default_config_fp}!")
        shutil.copyfile(default_config_fp, config_fp)
    if config_fp == default_config_fp:
        logger.warning(f"config_fp is default {default_config_fp}!")


class AIboxReport(CoralNode):

    # 配置文件，默认文件config.json, 可通过环境变量 CORAL_NODE_CONFIG_PATH 覆盖
    node_name = "上报节点"
    node_desc = "功能，上报当前信息"
    config_path = "config.json"
    node_type = NodeType.trigger

    check_config_fp_or_set_default(CoralNode.get_config()[0], "config.json")

    def __init__(self):
        super().__init__()
        self.cameras_person_count_windows: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=5)
        )
        self.cameras_last_capture_time: Dict[str, float] = {}
        self.windows_interval = 1
        self.kf = self.init_kalman_filter()

    def init(self, index: int, context: dict):
        """
        初始化参数，可传递到sender方法中

        :param context: 上下文参数
        """
        data = self.params.model_dump()
        gpio_cfg = data["gpio"]

        mqtt_client = init_mqtt(data["mqtt"])
        gpio_client = GpioControl(
            gpio_cfg["pins"], gpio_cfg["enable"], gpio_cfg["interval"]
        )
        context["mqtt"] = mqtt_client
        context["gpio"] = gpio_client

    @property
    def topic(self):
        return f"aibox/inference/{self.mac_addr}/{self.config.node_id}"

    def init_kalman_filter(self):
        kf = KalmanFilter(dim_x=2, dim_z=1)

        # 定义状态转移矩阵和观测矩阵
        kf.F = np.array([[1, 1], [0, 1]])  # 状态转移矩阵
        kf.H = np.array([[1, 0]])  # 观测矩阵

        # 定义过程噪声协方差和观测噪声协方差
        kf.Q = np.eye(2) * 0.01  # 过程噪声协方差
        kf.R = np.array([[1]])  # 观测噪声协方差

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

    def process_person_count(self):
        observations = []
        for (
            camera_id,
            window_person_count_buffer,
        ) in self.cameras_person_count_windows.items():
            # 过滤掉最近windows_interval时间段内没更新的摄像头数据
            # 这类可能会存在摄像头不稳定的情况，window中的数据不一定是最新的，因此过滤掉
            if (
                time.time() - self.cameras_last_capture_time[camera_id]
                > self.windows_interval
            ):
                continue
            observations.extend(list(window_person_count_buffer))
        pre_state_count = []
        for obs in observations:
            self.kf.predict()
            self.kf.update(obs)
            pre_state_count.append(self.kf.x[0])
        logger.debug(f"预测值窗口中每一帧人数：{pre_state_count}")
        # 向上取整返回最终的人数
        return math.ceil(self.kf.x[0])

    def sender(self, payload: RawPayload, context: Dict):
        """
        数据发送函数

        :param payload: receiver的数据
        :param context: 上下文参数
        :return: 数据
        """
        # 记录每个摄像头的人数
        self.cameras_last_capture_time[payload.source_id] = time.time()
        self.cameras_person_count_windows[payload.source_id].append(
            len(payload.objects or [])
        )

        mqtt_client: mqtt.Client = context["mqtt"]
        gpio_client: GpioControl = context["gpio"]
        frame_msg = {
            "uuid": payload.raw_id,
            "source": payload.source_id,
            # !docker部署需要设置 network=host模式
            "mac_address": self.mac_addr,
            # ! 人数采用滤波过滤方式检测widows_interval秒内的人数, 因此人数可能会与objects中的数量不符
            # ! 人数建议采用person_count给出的数值
            "person_count": self.process_person_count(),
            "objects": self.prepare_objects(payload.objects or []),
            # 单位: ms
            "duration": payload.nodes_cost * 1000,
            # 图片数据按base64编码传输
            "image": (
                self.encode_frame(payload.raw) if self.params.report_image else None
            ),
        }

        mqtt_client.publish(self.topic, json.dumps(frame_msg))

        # 触发信号, 开
        if payload.objects:
            with gpio_client:
                gpio_client.trigger_on()

        return None


if __name__ == "__main__":
    AIboxReport().run()
