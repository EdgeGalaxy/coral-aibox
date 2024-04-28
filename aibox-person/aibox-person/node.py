from typing import Dict, List, Any

import cv2
import numpy as np
from coral import (
    CoralNode,
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
from schema import AIboxPersonParamsModel


## 注册PT
PTManager.register()(AIboxPersonParamsModel)


class AIboxPerson(CoralNode):

    # 配置文件，默认文件config.json, 可通过环境变量 CORAL_NODE_CONFIG_PATH 覆盖
    node_name = "人物识别"
    node_desc = "识别物体是否是人类"
    config_path = "config.json"
    node_type = NodeType.interface

    web.check_config_fp_or_set_default(
        CoralNode.get_config()[0], CoralNode.default_config_fp()
    )

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
        params: AIboxPersonParamsModel = self.params
        feat_params = params.featuredb
        infer_params = params.detection
        featuredb = FeatureDB(
            width=feat_params.width,
            height=feat_params.height,
            weight_path=feat_params.weight_path,
            model_type=feat_params.model_type,
            device_id=feat_params.device_id,
            db_path=feat_params.db_path,
            db_size=feat_params.db_size,
            sim_threshold=feat_params.sim_threshold,
        )
        inference = Inference(
            featuredb=featuredb,
            width=infer_params.width,
            height=infer_params.height,
            weight_path=infer_params.weight_path,
            model_type=infer_params.model_type,
            device_id=infer_params.device_id,
            class_names=infer_params.class_names,
            nms_thresh=infer_params.nms_thresh,
            confidence_thresh=infer_params.confidence_thresh,
        )
        context["model"] = inference
        # 更新contexts
        web.contexts[index] = {"context": context, "params": self.params}

    def sender(self, payload: RawPayload, context: Dict) -> ObjectsPayload:
        """
        数据发送函数

        :param payload: receiver的数据
        :param context: 上下文参数
        :return: 数据
        """
        if self.params.is_open:
            model: Inference = context["model"]
            iou_thresh = payload.raw_params["iou_scale"]
            # 获取mask
            if context.get("mask") is None:
                mask = self.gen_mask(payload.raw, payload.raw_params)
                # 更新context内容，供web侧获取最新值
                context["mask"] = mask
                context["iou_thresh"] = iou_thresh
            else:
                mask = context["mask"]
            defects = model.predict(payload.raw, self.params.is_record)
            objects = [ObjectPayload(**defect) for defect in defects]
            # 过滤与mask不重合的objects
            if mask is not None:
                objects = self.filter_objects(mask, objects, iou_thresh)
        else:
            objects = []
        return ObjectsPayload(objects=objects, mode=InterfaceMode.APPEND)

    @classmethod
    def gen_mask(cls, raw: np.ndarray, raw_params: Dict[str, Any]):
        if not raw_params.get("points"):
            return None
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
