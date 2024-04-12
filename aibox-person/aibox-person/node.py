
import os
from typing import Dict, List, Any
from functools import cached_property
from urllib.parse import urljoin

import cv2
import numpy as np
import requests
from loguru import logger
from pydantic import BaseModel, computed_field, field_validator
from coral.constants import MOUNT_PATH
from coral import CoralNode, BaseParamsModel, ObjectPayload, PTManager, ObjectsPayload, InterfaceMode, NodeType, RawPayload

from algrothms.featuredb import FeatureDB
from algrothms.inference import Inference


MOUNT_NODE_PATH = os.path.join(MOUNT_PATH, "aibox")
os.makedirs(MOUNT_NODE_PATH, exist_ok=True)
WEIGHTS_REMOTE_HOST = os.environ.get('WEIGHTS_REMOTE_HOST', 'https://nbstore.oss-cn-shanghai.aliyuncs.com/aibox-pro2/nx/weights/')


class ModelParamsModel(BaseModel):
    weight_path: str

    @computed_field
    @cached_property
    def model_type(self) -> str:
        return self.weight_path.split('.')[-1]

    @field_validator('weight_path')
    @classmethod
    def validate_model_path(cls, v: str):
        _dir = os.path.join(MOUNT_NODE_PATH, 'weights')
        os.makedirs(_dir, exist_ok=True)
        _file = os.path.join(_dir, v)
        if not os.path.exists(_file):
            url = urljoin(WEIGHTS_REMOTE_HOST, v)
            logger.warning(f'file {_file} not exists, download from {url}')
            r = requests.get(url)
            if r.ok:
                with open(_file, 'wb') as f:
                    f.write(r.content)
                logger.warning(f'file {_file} download success!')
            else:
                raise ValueError(f'file {_file} not exists, download from {url} error: {r.text}!')
        return os.path.join(MOUNT_NODE_PATH, v)

class DetectionParamsModel(ModelParamsModel):
    width: int = 1088
    height: int = 608
    device_id: int = 0
    class_names: List[str] = ["person"]
    nms_thresh: float = 0.4
    confidence_thresh: float = 0.5


class FeatureDBParamsModel(ModelParamsModel):
    width: int = 224
    height: int = 224
    device_id: int = 0
    db_path: str = 'db/person'
    db_size: int = 1000
    sim_threshold: float = 0.9

    @field_validator('db_path')
    @classmethod
    def validate_db_path(cls, v: str):
        _dir = os.path.join(MOUNT_NODE_PATH, v)
        if not os.path.exists(_dir):
            os.makedirs(_dir, exist_ok=True)
        return os.path.join(MOUNT_NODE_PATH, v)


@PTManager.register()
class AIboxPersonParamsModel(BaseParamsModel):
    detection: DetectionParamsModel
    featuredb: FeatureDBParamsModel


class AIboxPerson(CoralNode):

    # 配置文件，默认文件config.json, 可通过环境变量 CORAL_NODE_CONFIG_PATH 覆盖
    node_name = '人物识别'
    node_desc = '识别物体是否是人类'
    config_path = 'config.json'
    node_type = NodeType.interface

    def init(self, index: int, context: dict):
        """
        初始化参数，可传递到sender方法中

        :param context: 上下文参数
        """
        data = self.params.model_dump()
        # 获取入参
        featuredb = FeatureDB(**data['featuredb'])
        inference = Inference(
            featuredb=featuredb,
            **data['detection']
        )
        context['model'] = inference

    def sender(self, payload: RawPayload, context: Dict) -> ObjectsPayload:
        """
        数据发送函数

        :param payload: receiver的数据
        :param context: 上下文参数
        :return: 数据
        """
        model: Inference = context['model']
        # 获取mask
        if not context.get('mask'):
            mask = self.gen_mask(payload.raw, payload.raw_params)
        else:
            mask = context['mask']
        defects = model.predict(payload.raw)
        objects = [ObjectPayload(**defect) for defect in defects]
        # 过滤与mask不重合的objects
        objects = self.filter_objects(mask, objects, payload.raw_params)
        return ObjectsPayload(objects=objects, mode=InterfaceMode.APPEND)
    
    def gen_mask(self, raw: np.ndarray, raw_params: Dict[str, Any]):
        mask = np.zeros_like(raw)
        return cv2.fillPoly(mask, [np.array(raw_params['points'])], 1)

    def filter_objects(self, mask: np.ndarray, objects: List[ObjectPayload], iou_thresh: float):
        filter_objects = []
        for object in objects:
            x1, y1, x2, y2 = object.box.x1, object.box.y1, object.box.x2, object.box.y2
            box_in_mask = np.sum(mask[x1:x2, y1:y2])
            box_area = (x2 - x1 + 1) * (y2 - y1 + 1)
            if box_area > 0 and (box_in_mask / box_area) >= iou_thresh:
                filter_objects.append(object)
        return filter_objects


if __name__ == '__main__':
    # 脚本入口，包括注册和启动
    import os
    run_type = os.getenv("CORAL_NODE_RUN_TYPE", "run")
    if run_type == 'register':
        AIboxPerson.node_register()
    else:
        AIboxPerson().run()