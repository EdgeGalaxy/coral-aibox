import json

from typing import Dict

from coral import CoralNode, BaseParamsModel, NodeType, RawPayload, PTManager
from coral.metrics import init_mqtt, mqtt

from algrothms.gpio import GPIOSignal


class MQTTParamsModel(BaseParamsModel):
    broker: str = '127.0.0.1'
    port: int = 1883
    username: str = 'admin'
    password: str = 'admin'


class GpioParamsModel(BaseParamsModel):
    enable: bool = True
    on_signal_duration: int = 3


@PTManager.register()
class AIboxReportParamsModel(BaseParamsModel):
    mqtt: MQTTParamsModel = MQTTParamsModel()
    gpio: GpioParamsModel = GpioParamsModel()
    report_image: bool = True


class AIboxReport(CoralNode):

    # 配置文件，默认文件config.json, 可通过环境变量 CORAL_NODE_CONFIG_PATH 覆盖
    node_name = '上报节点'
    node_desc = '功能，上报当前信息'
    config_path = 'config.json'
    node_type = NodeType.trigger

    def init(self, index: int, context: dict):
        """
        初始化参数，可传递到sender方法中

        :param context: 上下文参数
        """
        data = self.params.model_dump()
        gpio_trigger = GPIOSignal(**data['gpio'])
        mqtt_client = init_mqtt(data['mqtt'])
        context['mqtt'] = mqtt_client
        context['gpio'] = gpio_trigger
    
    @property
    def topic(self):
        return f'aibox/{self.mac_addr}/{self.config.node_id}'

    def sender(self, payload: RawPayload, context: Dict):
        """
        数据发送函数

        :param payload: receiver的数据
        :param context: 上下文参数
        :return: 数据
        """
        mqtt_client: mqtt.Client = context['mqtt']
        gpio_trigger: GPIOSignal = context['gpio']
        data = payload.model_dump()
        frame_msg = {
            'uuid': payload.raw_id,
            'source': payload.source_id,
            # docker部署需要设置 network=host模式
            'mac_address': self.mac_addr,
            'objects': data['objects'],
            # 单位: ms
            'duration': payload.nodes_cost * 1000,
            'image': payload.raw if self.params.report_image else None
        }
        
        mqtt_client.publish(self.topic, json.dumps(frame_msg))

        # 触发信号, 关或开
        if payload.objects:
            gpio_trigger.gpio_on()
        gpio_trigger.trigger()
        return None


if __name__ == '__main__':
    # 脚本入口，包括注册和启动
    import os
    run_type = os.getenv("CORAL_NODE_RUN_TYPE", "run")
    if run_type == 'register':
        AIboxReport.node_register()
    else:
        AIboxReport().run()