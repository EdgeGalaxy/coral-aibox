import os
import time
import json
import shutil

from typing import Dict

from loguru import logger
from coral import CoralNode, BaseParamsModel, NodeType, RawPayload, PTManager
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
        return f"aibox/{self.mac_addr}/{self.config.node_id}"

    def sender(self, payload: RawPayload, context: Dict):
        """
        数据发送函数

        :param payload: receiver的数据
        :param context: 上下文参数
        :return: 数据
        """
        mqtt_client: mqtt.Client = context["mqtt"]
        gpio_client: GpioControl = context["gpio"]
        data = payload.model_dump()
        frame_msg = {
            "uuid": payload.raw_id,
            "source": payload.source_id,
            # !docker部署需要设置 network=host模式
            "mac_address": self.mac_addr,
            "objects": data["objects"],
            # 单位: ms
            "duration": payload.nodes_cost * 1000,
            "image": payload.raw if self.params.report_image else None,
        }

        mqtt_client.publish(self.topic, json.dumps(frame_msg))

        # 触发信号, 开
        if payload.objects:
            with gpio_client:
                gpio_client.trigger_on()

        return None


if __name__ == "__main__":
    AIboxReport().run()
