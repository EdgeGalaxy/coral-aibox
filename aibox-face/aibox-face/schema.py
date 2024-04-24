import os
from typing import List, Optional
from functools import cached_property
from urllib.parse import urljoin

import requests
from loguru import logger
from coral import BaseParamsModel
from coral.constants import MOUNT_PATH
from coral.types.payload import Box
from pydantic import BaseModel, computed_field, field_validator, Field


MOUNT_NODE_PATH = os.path.join(MOUNT_PATH, "aibox")
os.makedirs(MOUNT_NODE_PATH, exist_ok=True)
MODEL_TYPE = os.environ.get("MODEL_TYPE", "onnx")
WEIGHTS_REMOTE_HOST = os.environ.get(
    "WEIGHTS_REMOTE_HOST",
    "https://nbstore.oss-cn-shanghai.aliyuncs.com/aibox-pro2/onnx/weights/",
)


class ModelParamsModel(BaseModel):
    weight_name: str = Field(description="模型权重文件名")

    @property
    def model_type(self) -> str:
        return MODEL_TYPE

    @field_validator("weight_name")
    @classmethod
    def validate_model_path(cls, v: str):
        fn = ".".join([v, MODEL_TYPE])
        _dir = os.path.join(MOUNT_NODE_PATH, "weights")
        os.makedirs(_dir, exist_ok=True)
        _file = os.path.join(_dir, fn)
        if not os.path.exists(_file):
            url = urljoin(WEIGHTS_REMOTE_HOST, fn)
            logger.warning(f"file {_file} not exists, download from {url}")
            r = requests.get(url)
            if r.ok:
                with open(_file, "wb") as f:
                    f.write(r.content)
                logger.warning(f"file {_file} download success!")
            else:
                raise ValueError(
                    f"file {_file} not exists, download from {url} error: {r.text}!"
                )
        return v

    @property
    def weight_path(self) -> str:
        weight_fn = ".".join([self.weight_name, MODEL_TYPE])
        return os.path.join(MOUNT_NODE_PATH, "weights", weight_fn)


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
    base_dir: str
    user_faces_size: int = 10
    sim_threshold: float = 0.9

    @property
    def db_path(self):
        _dir = os.path.join(MOUNT_NODE_PATH, self.base_dir)
        if not os.path.exists(_dir):
            os.makedirs(_dir, exist_ok=True)
        return _dir


class AIboxFaceParamsModel(BaseParamsModel):
    detection: DetectionParamsModel
    featuredb: FeatureDBParamsModel
    is_open: bool = Field(default=True, description="是否开启人脸识别")
    is_record: bool = Field(
        default=False, description="是否记录当前获取的图像信息和特征"
    )


## ======= Web Schema ======= ##


class RecordFeatureModel(BaseModel):
    is_record: bool
    is_open: bool = True
    confidence_thresh: float = 0.5
    sim_threshold: float = 0.9


class ImageReqModel(BaseModel):
    image: str = Field(description="base64 image")
    boxes: List[Box] = Field(description="识别到的人框列表")


class WebDetectionParams(BaseModel):
    width: int
    height: int
    nms_thresh: float = 0.4
    confidence_thresh: float = 0.5


class WebFeatureDBParams(BaseModel):
    width: int
    height: int
    user_faces_size: int = 10
    sim_threshold: float = 0.9


class WebNodeParams(BaseModel):
    detection: Optional[WebDetectionParams] = None
    featuredb: Optional[WebFeatureDBParams] = None
    is_open: bool = True
    is_record: bool


class UsersRemarkModel(BaseModel):
    remark_user_id: str
    old_user_id: str


class UserFacesModel(BaseModel):
    faces: List[str]


class UserFaceModel(BaseModel):
    face: str
