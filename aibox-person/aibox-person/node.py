import os
from typing import Dict, List, Any

import cv2
import numpy as np
from pydantic import Field
from coral import (
    CoralNode,
    BaseParamsModel,
    ObjectPayload,
    PTManager,
    ObjectsPayload,
    InterfaceMode,
    NodeType,
    RawPayload,
)

import web
from algrothms.featuredb import FeatureDB
from algrothms.inference import Inference
from schema import DetectionParamsModel, FeatureDBParamsModel


@PTManager.register()
class AIboxPersonParamsModel(BaseParamsModel):
    detection: DetectionParamsModel
    featuredb: FeatureDBParamsModel
    is_record: bool = Field(
        default=False, description="是否记录当前获取的图像信息和特征"
    )


class AIboxPerson(CoralNode):

    # 配置文件，默认文件config.json, 可通过环境变量 CORAL_NODE_CONFIG_PATH 覆盖
    node_name = "人物识别"
    node_desc = "识别物体是否是人类"
    config_path = "config.json"
    node_type = NodeType.interface

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
        data = self.params.model_dump()
        # 获取入参
        featuredb = FeatureDB(**data["featuredb"])
        inference = Inference(featuredb=featuredb, **data["detection"])
        context["model"] = inference
        # 更新contexts
        web.contexts[str(index)] = {"context": context, "params": self.params}

    def sender(self, payload: RawPayload, context: Dict) -> ObjectsPayload:
        """
        数据发送函数

        :param payload: receiver的数据
        :param context: 上下文参数
        :return: 数据
        """
        model: Inference = context["model"]
        # 获取mask
        if context.get("mask") is None:
            mask = self.gen_mask(payload.raw, payload.raw_params)
            # 更新context内容，供web侧获取最新值
            context["mask"] = mask
            context["iou_thresh"] = payload.raw_params["iou_scale"]
        else:
            mask = context["mask"]
        defects = model.predict(payload.raw, self.params.is_record)
        objects = [ObjectPayload(**defect) for defect in defects]
        # 过滤与mask不重合的objects
        objects = self.filter_objects(mask, objects, payload.raw_params["iou_scale"])
        return ObjectsPayload(objects=objects, mode=InterfaceMode.APPEND)

    @classmethod
    def gen_mask(cls, raw: np.ndarray, raw_params: Dict[str, Any]):
        mask = np.zeros_like(raw)
        return cv2.fillPoly(mask, [np.array(raw_params["points"])], 1)

    @classmethod
    def filter_objects(
        cls, mask: np.ndarray, objects: List[ObjectPayload], iou_thresh: float
    ):
        filter_objects = []
        for object in objects:
            x1, y1, x2, y2 = object.box.x1, object.box.y1, object.box.x2, object.box.y2
            box_in_mask = np.sum(mask[x1:x2, y1:y2])
            box_area = (x2 - x1 + 1) * (y2 - y1 + 1)
            if box_area > 0 and (box_in_mask / box_area) >= iou_thresh:
                filter_objects.append(object)
        return filter_objects


if __name__ == "__main__":
    AIboxPerson().run()
