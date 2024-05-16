import os
import time
from typing import Dict

import cv2
from pydantic import Field
from coral import (
    CoralNode,
    BaseParamsModel,
    NodeType,
    RawPayload,
    PTManager,
)
from threading import Lock
from coral.constants import MOUNT_PATH

import web
from algrothms.recorder import Recorder


MOUNT_NODE_PATH = os.path.join(MOUNT_PATH, "aibox")
os.makedirs(MOUNT_NODE_PATH, exist_ok=True)


@PTManager.register()
class AIboxRecordParamsModel(BaseParamsModel):
    base_dir_name: str = Field(default="record", description="保存路径")
    recycle_interval: int = Field(default=300, description="自动清理间隔时间")
    interval: int = Field(default=600, description="间隔时间")
    enable: bool = Field(default=True, description="是否开启")
    max_gb: int = Field(default=5, description="最大存储空间")

    @property
    def base_dir(self):
        _dir = os.path.join(MOUNT_NODE_PATH, self.base_dir_name)
        os.makedirs(_dir, exist_ok=True)
        return _dir


class AIboxRecord(CoralNode):

    # 配置文件，默认文件config.json, 可通过环境变量 CORAL_NODE_CONFIG_PATH 覆盖
    node_name = "记录节点"
    node_desc = "记录画面内容"
    config_path = "config.json"
    node_type = NodeType.trigger

    web.check_config_fp_or_set_default(CoralNode.get_config()[0])

    def __init__(self):
        super().__init__()
        self.recorders = {}
        # 自动清理磁盘
        self.bg_tasks.add_job(
            Recorder.auto_recycle,
            trigger="interval",
            args=(self.params.base_dir, self.params.max_gb),
            seconds=self.params.recycle_interval,
        )
        self.lock = Lock()
        web.async_run(self.config.node_id, self.params.base_dir)

    def init(self, index: int, context: dict):
        """
        初始化参数，可传递到sender方法中

        :param context: 上下文参数
        """

        web.contexts[index] = {"context": context, "params": self.params}

    def sender(self, payload: RawPayload, context: Dict):
        """
        数据发送函数

        :param payload: receiver的数据
        :param context: 上下文参数
        :return: 数据
        """
        # 加锁确保同一时间只有一个节点写入
        with self.lock:
            if self.recorders.get(payload.source_id) is None:
                recorder = Recorder(
                    base_dir=self.params.base_dir,
                    record_interval=self.params.interval,
                    auto_recycle_threshold=self.params.max_gb,
                    enable=self.params.enable,
                )
                self.recorders[payload.source_id] = recorder
            else:
                recorder: Recorder = self.recorders[payload.source_id]

        # 获取运行时插入图片的帧率, 程序运行300s后代表帧率基本稳定,
        # 因为插入是每个摄像头，当前fps计算是总的fps，因此需要除以摄像头数量
        dynamic_fps = (
            int(self.sender_fps / len(payload.raw_params["camera_ids"]))
            if time.time() - self.run_time > 300
            else 5
        )

        # 作为最后一个节点，为了节省内存，则直接用原numpy画图
        frame = payload.raw
        # 修改分辨率
        camera_height = payload.raw_params.get("camera_height") or 360
        if camera_height:
            oh, ow = frame.shape[:2]
            scale = camera_height / oh
            frame = cv2.resize(frame, (int(ow * scale), int(camera_height)))

        report_data = payload.metas.get(self.meta.receivers[0].node_id)
        recorder.write(
            frame,
            payload.objects,
            crt_fps=dynamic_fps,
            report_timestamp=report_data["timestamp"],
            person_count=report_data["person_count"],
            target_dir_name=payload.source_id,
            points=payload.raw_params["points"],
        )
        return None


if __name__ == "__main__":
    AIboxRecord().run()
