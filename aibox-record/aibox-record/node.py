import os
import shutil
from typing import Dict

from pydantic import Field, field_validator
from coral import (
    CoralNode,
    BaseParamsModel,
    NodeType,
    RawPayload,
    PTManager,
)
from loguru import logger
from coral.constants import MOUNT_PATH

import web
from algrothms.recorder import Recorder


MOUNT_NODE_PATH = os.path.join(MOUNT_PATH, "aibox")
os.makedirs(MOUNT_NODE_PATH, exist_ok=True)


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


@PTManager.register()
class AIboxRecordParamsModel(BaseParamsModel):
    base_dir_name: str = Field(default="record", description="保存路径")
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

    check_config_fp_or_set_default(
        CoralNode.get_config()[0], CoralNode.default_config_fp()
    )

    def __init__(self):
        super().__init__()
        web.async_run(self.config.node_id, self.params.base_dir)

    def init(self, index: int, context: dict):
        """
        初始化参数，可传递到sender方法中

        :param context: 上下文参数
        """
        # 获取入参
        recorder = Recorder(
            base_dir=self.params.base_dir,
            record_interval=self.params.interval,
            auto_recycle_threshold=self.params.max_gb,
            enable=self.params.enable,
        )
        context["recorder"] = recorder

        web.contexts[index] = {"context": context, "params": self.params}

    def sender(self, payload: RawPayload, context: Dict):
        """
        数据发送函数

        :param payload: receiver的数据
        :param context: 上下文参数
        :return: 数据
        """
        recorder: Recorder = context["recorder"]
        image = payload.raw.copy()
        recorder.write(
            image,
            payload.objects,
            target_dir_name=payload.source_id,
            points=payload.raw_params["points"],
        )
        return None


if __name__ == "__main__":
    AIboxRecord().run()
