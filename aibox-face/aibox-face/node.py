
import os
from typing import Dict, List
from functools import cached_property
from urllib.parse import urljoin

import requests
from loguru import logger
from pydantic import BaseModel, computed_field, field_validator
from coral.constants import MOUNT_PATH
from coral import CoralNode, BaseParamsModel, PTManager, ObjectsPayload, InterfaceMode, NodeType, RawPayload, ObjectPayload

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
    width: int = 480
    height: int = 640
    device_id: int = 0
    class_names: List[str] = ["person"]
    nms_thresh: float = 0.4
    confidence_thresh: float = 0.5


class FeatureDBParamsModel(ModelParamsModel):
    width: int = 112
    height: int = 112
    device_id: int = 0
    db_path: str = 'db/face'
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


class AIboxFace(CoralNode):

    # 配置文件，默认文件config.json, 可通过环境变量 CORAL_NODE_CONFIG_PATH 覆盖
    node_name = '人脸识别'
    node_desc = '识别检测出的人物的人脸信息'
    config_path = 'config.json'
    node_type = NodeType.interface

    def init(self, index: int, context: dict):
        """
        初始化参数，可传递到sender方法中

        :param context: 上下文参数
        """
        data = self.params.model_dump()
        featuredb = FeatureDB(**data['featuredb'])
        inference = Inference(
            featuredb=featuredb,
            **data['detection']
        )
        context['model'] = inference

    def get_max_face(self, objects: List[ObjectPayload]):
        if len(objects) < 1: 
            return None

        max_area, max_index = 0, 0
        for idx, object in enumerate(objects):
            box = object.box
            x1, y1, x2, y2 = box.x1, box.y1, box.x2, box.y2
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
        raw = payload.raw
        model: Inference = context['model']
        for object in payload.objects:
            box = object.box
            face_raw = raw[box.x1:box.x2, box.y1:box.y2, :]
            face_objects = model.predict(face_raw)
            similar_face_object = self.get_max_face(face_objects)
            object.objects = [similar_face_object]

        return ObjectsPayload(objects=payload.objects, mode=InterfaceMode.OVERWRITE)



if __name__ == '__main__':
    # 脚本入口，包括注册和启动
    import os
    run_type = os.getenv("CORAL_NODE_RUN_TYPE", "run")
    if run_type == 'register':
        AIboxFace.node_register()
    else:
        AIboxFace().run()