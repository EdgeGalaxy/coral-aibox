from typing import Dict, List

import cv2
from coral import (
    CoralNode,
    BaseParamsModel,
    FirstPayload,
    RawPayload,
    PTManager,
    NodeType,
)

from .schema import CameraParamsModel
from .web import WebBackGroundTask


@PTManager.register()
class AIboxCameraParamsModel(BaseParamsModel):
    cameras: List[CameraParamsModel]
    port: int = 8010


class AIboxCamera(CoralNode):

    # 配置文件，默认文件config.json, 可通过环境变量 CORAL_NODE_CONFIG_PATH 覆盖
    node_name = "aibox摄像头节点"
    node_desc = "获取摄像头信息并做简单处理"
    config_path = "config.json"
    node_type = NodeType.input

    def __init__(self):
        super().__init__()
        self.contexts = {}
        # 启动web服务
        web_task = WebBackGroundTask(
            self.config.node_id, self.contexts, self.params.port
        )
        web_task.start()

    def init(self, index: int, context: dict):
        """
        初始化参数，可传递到sender方法中

        :param context: 上下文参数
        """
        cameras = self.params.model_dump()["cameras"]
        if not cameras:
            raise ValueError("未配置摄像头")
        if not self.process.enable_parallel:
            raise ValueError(
                "当前摄像头只支持并行模式, 设置 process -> enable_parallel 为 true"
            )

        if self.process.count != len(cameras):
            raise ValueError(
                f"摄像头数量与启动线程数不匹配, 设置 process -> count 为 {len(cameras)}"
            )

        camera = cameras[index]
        url = camera["url"]
        if url.isdigit():
            camera["url"] = int(url)
        vc = cv2.VideoCapture(camera["url"])
        context["vc"] = vc
        context["name"] = camera["name"]
        context["params"] = camera["params"]
        self.contexts[camera["name"]] = context

    def sender(self, payload: RawPayload, context: Dict) -> FirstPayload:
        """
        数据发送函数

        :param payload: receiver的数据
        :param context: 上下文参数
        :return: 数据
        """
        vc: cv2.VideoCapture = context["vc"]
        ret, frame = vc.read()
        if not ret:
            raise ValueError("摄像头读取失败")

        return FirstPayload(
            source_id=context["name"], raw=frame, raw_params=context["params"]
        )


if __name__ == "__main__":
    # 脚本入口，包括注册和启动
    import os

    run_type = os.getenv("CORAL_NODE_RUN_TYPE", "run")
    if run_type == "register":
        AIboxCamera.node_register()
    else:
        AIboxCamera().run()
