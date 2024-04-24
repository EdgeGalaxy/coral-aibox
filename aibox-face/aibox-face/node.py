import math
from typing import Dict, List, Any

from coral import (
    CoralNode,
    PTManager,
    ObjectsPayload,
    InterfaceMode,
    NodeType,
    RawPayload,
    ObjectPayload,
)

import web
from algrothms.gossip import GossipCommunicate
from algrothms.featuredb import FeatureDB
from algrothms.inference import Inference
from algrothms.utils import INTERNAL_IP
from schema import AIboxFaceParamsModel


# 注册PT
PTManager.register()(AIboxFaceParamsModel)


class AIboxFace(CoralNode):

    # 配置文件，默认文件config.json, 可通过环境变量 CORAL_NODE_CONFIG_PATH 覆盖
    node_name = "人脸识别"
    node_desc = "识别检测出的人物的人脸信息"
    config_path = "config.json"
    node_type = NodeType.interface

    web.check_config_fp_or_set_default(CoralNode.get_config()[0], "config.json")

    def __init__(self):
        super().__init__()
        # 更新node_id变量，并启动web服务
        web.node_id = self.config.node_id
        web.async_run(self.config.node_id, self.params.featuredb.db_path)

    def init(self, index: int, context: dict):
        """
        初始化参数，可传递到sender方法中

        :param context: 上下文参数
        """
        data = self.params.model_dump()
        featuredb = FeatureDB(**data["featuredb"])
        inference = Inference(featuredb=featuredb, **data["detection"])
        context["model"] = inference
        # 系统内传播的Gossip
        gossip_enable = True if self.metrics.enable and INTERNAL_IP else False
        gossip = GossipCommunicate(
            self.metrics.mqtt_client,
            featuredb=featuredb,
            mac_addr=self.mac_addr,
            enable=gossip_enable,
        )
        context["gossip"] = gossip
        # 更新contexts
        web.contexts[index] = {"context": context, "params": self.params}

    @classmethod
    def get_max_face(cls, objects: List[Dict[str, Any]]):
        if len(objects) == 0:
            return None

        max_area, max_index = 0, 0
        for idx, object in enumerate(objects):
            box = object["box"]
            x1, y1, x2, y2 = box["x1"], box["y1"], box["x2"], box["y2"]
            if (x2 - x1 + 1) * (y2 - y1 + 1) > max_area:
                max_area = (x2 - x1 + 1) * (y2 - y1 + 1)
                max_index = idx

        return objects[max_index]

    def sender(self, payload: RawPayload, context: Dict) -> ObjectsPayload:
        """
        数据发送函数

        :param payload: receiver的数据
        :param context: 上下文参数
        :return: 数据
        """
        if self.params.is_open:
            raw = payload.raw
            model: Inference = context["model"]
            for object in payload.objects:
                box = object.box
                face_raw = raw[box.x1 : box.x2 + 1, box.y1 : box.y2 + 1, :]
                face_objects = model.predict(face_raw, box, self.params.is_record)
                similar_face_object = self.get_max_face(face_objects)
                if similar_face_object:
                    object.objects = [ObjectPayload(**similar_face_object)]

        # 传输当前RawPayload的复制对象到frames_queue中，供web页面展示
        web.append_payload_to_web_queue(
            payload.model_copy(deep=True), math.ceil(self.sender_fps)
        )

        return ObjectsPayload(objects=payload.objects, mode=InterfaceMode.OVERWRITE)


if __name__ == "__main__":
    AIboxFace().run()
