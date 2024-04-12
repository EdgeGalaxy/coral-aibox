import time

from typing import Dict

from pydantic import Field
from coral import CoralNode, BaseParamsModel, NodeType, ReturnPayloadWithTS, RawPayload,  RTManager, PTManager

from algrothms.core import AIboxRecordCore
@RTManager.register()
class AIboxRecordReturnPayload(ReturnPayloadWithTS):
    pass


@PTManager.register()
class AIboxRecordParamsModel(BaseParamsModel):
    # 可更改的参数，遵循pydantic的格式
    timestamp: float = Field(default_factory=lambda: time.time())


class AIboxRecord(CoralNode):

    # 配置文件，默认文件config.json, 可通过环境变量 CORAL_NODE_CONFIG_PATH 覆盖
    node_name = '记录节点'
    node_desc = '记录画面内容'
    config_path = 'config.json'
    node_type = NodeType.trigger

    def init(self, index: int, context: dict):
        """
        初始化参数，可传递到sender方法中

        :param context: 上下文参数
        """
        # 获取入参
        print(self.params.timestamp)
        context['timestamp'] = time.time()
    def sender(self, payload: RawPayload, context: Dict) -> AIboxRecordReturnPayload:
        """
        数据发送函数

        :param payload: receiver的数据
        :param context: 上下文参数
        :return: 数据
        """
        print(context['timestamp'])
        return AIboxRecordReturnPayload()



if __name__ == '__main__':
    # 脚本入口，包括注册和启动
    import os
    run_type = os.getenv("CORAL_NODE_RUN_TYPE", "run")
    if run_type == 'register':
        AIboxRecord.node_register()
    else:
        AIboxRecord().run()