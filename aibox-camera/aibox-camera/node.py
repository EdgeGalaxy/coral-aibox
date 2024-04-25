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

import web
from schema import CameraParamsModel
from algrothms.streamer import VideoStreamer


@PTManager.register()
class AIboxCameraParamsModel(BaseParamsModel):
    cameras: List[CameraParamsModel]


class AIboxCamera(CoralNode):

    # 配置文件，默认文件config.json, 可通过环境变量 CORAL_NODE_CONFIG_PATH 覆盖
    node_name = "aibox摄像头节点"
    node_desc = "获取摄像头信息并做简单处理"
    config_path = "config.json"
    node_type = NodeType.input

    web.check_config_fp_or_set_default(CoralNode.get_config()[0], "config.json")

    def __init__(self):
        super().__init__()
        # 更新node_id变量，并启动web服务
        web.node_id = self.config.node_id
        web.async_run(self.config.node_id)

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
        url: str = camera["url"]
        vc = VideoStreamer(url, width=camera["width"], height=camera["height"])
        context["vc"] = vc
        context.update(camera)
        # 写入所有摄像头ID到每一帧画面中
        context["params"]["camera_ids"] = [_cam["name"] for _cam in cameras]
        # 更新web的全局变量
        web.contexts[camera["name"]] = context

    @classmethod
    def restart_program(cls):
        """重启当前程序。"""
        import os
        import sys
        import subprocess

        python = sys.executable
        # 如果你的脚本接受命令行参数，可以通过sys.argv传递
        args = sys.argv[:]
        # 也可以在这里修改sys.argv中的元素，如果你想改变重启时的命令行参数
        # args[1:] = ['arg1', 'arg2']

        # 下面的命令会启动一个新的Python进程，使用相同的参数运行本脚本
        subprocess.Popen([python] + args)

        # 退出当前进程, 运行两次，冷退出,
        # ! 确保图片内存缓存记录落盘
        os.kill(os.getpid(), 2)
        os.kill(os.getpid(), 9)

    def sender(self, payload: RawPayload, context: Dict) -> FirstPayload:
        """
        数据发送函数

        :param payload: receiver的数据
        :param context: 上下文参数
        :return: 数据
        """
        # 此处控制线程退出
        if web.restart:
            web.restart = False
            self.shutdown()
            self.restart_program()

        vc: VideoStreamer = context["vc"]
        ret, frame = vc.read()
        if not ret:
            raise ValueError("摄像头读取失败")

        return FirstPayload(
            source_id=context["name"], raw=frame, raw_params=context["params"]
        )


if __name__ == "__main__":
    AIboxCamera().run()
