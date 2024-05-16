import sys
import time
import signal
from typing import Dict, List

from coral import (
    CoralNode,
    BaseParamsModel,
    FirstPayload,
    RawPayload,
    PTManager,
    NodeType,
)
from loguru import logger
from coral.sched import SharedMemoryIDManager
from coral.exception import CoralSenderIgnoreException

import web
from schema import CameraParamsModel
from algrothms.streamer import VideoStreamer


def signal_restart(signal, frame):
    logger.info("receive signal: {}".format(signal))
    SharedMemoryIDManager.clear_all_memory()
    web.stop_main_thread()
    sys.exit(0)


# 注册信号触发
signal.signal(signal.SIGTERM, signal_restart)
# 清除共享内存
SharedMemoryIDManager.clear_all_memory()


@PTManager.register()
class AIboxCameraParamsModel(BaseParamsModel):
    cameras: List[CameraParamsModel] = [CameraParamsModel()]
    resolution: str = "low"


class AIboxCamera(CoralNode):

    # 配置文件，默认文件config.json, 可通过环境变量 CORAL_NODE_CONFIG_PATH 覆盖
    node_name = "aibox摄像头节点"
    node_desc = "获取摄像头信息并做简单处理"
    config_path = "config.json"
    node_type = NodeType.input

    # 初始化web服务
    web.check_config_fp_or_set_default(CoralNode.get_config()[0])

    def __init__(self):
        super().__init__()
        self.logger_fps_time = time.time()
        # 更新node_id变量，并启动web服务
        web.node_id = self.config.node_id
        web.is_actived = self.is_active
        web.async_run(self.config.node_id)

    def init(self, index: int, context: dict):
        """
        初始化参数，可传递到sender方法中

        :param context: 上下文参数
        """
        cameras = self.params.model_dump()["cameras"]
        # if not cameras:
        #     raise ValueError("未配置摄像头")
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
        vc = VideoStreamer(url)
        context["vc"] = vc
        context.update(camera)
        # 写入所有摄像头ID到每一帧画面中
        # context["params"]["camera_ids"] = [_cam["name"] for _cam in cameras]
        context["resolution"] = self.params.resolution
        # 更新web的全局变量
        web.contexts[camera["name"]] = context

    def sender(self, payload: RawPayload, context: Dict) -> FirstPayload:
        """
        数据发送函数

        :param payload: receiver的数据
        :param context: 上下文参数
        :return: 数据
        """
        vc: VideoStreamer = context["vc"]
        ret, frame = vc.read()
        if not ret:
            raise CoralSenderIgnoreException("读取频率过高, 队列为空")

        # 将摄像头拷贝数据web读取写入队列
        web.cameras_queue[context["name"]].append(frame.copy())

        raw_params = {
            **context["params"],
            "camera_height": web.resolution_height_mapper(context["resolution"]),
            "camera_ids": [cam.name for cam in self.params.cameras],
        }

        return FirstPayload(source_id=context["name"], raw=frame, raw_params=raw_params)

    def logger_fps(self):
        # 每3秒打印一次FPS
        if time.time() - self.logger_fps_time > 3:
            super().logger_fps()
            self.logger_fps_time = time.time()


if __name__ == "__main__":
    AIboxCamera().run()
