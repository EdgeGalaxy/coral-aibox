import os
from typing import List
from functools import cached_property
from urllib.parse import urljoin

import requests
from loguru import logger
from coral.constants import MOUNT_PATH
from coral.types.payload import Box
from pydantic import BaseModel, computed_field, field_validator, Field


MOUNT_NODE_PATH = os.path.join(MOUNT_PATH, "aibox")
os.makedirs(MOUNT_NODE_PATH, exist_ok=True)
MODEL_TYPE = os.environ["MODEL_TYPE"]
WEIGHTS_REMOTE_HOST = os.environ["WEIGHTS_REMOTE_HOST"]


class ModelParamsModel(BaseModel):
    weight_path: str = Field(description="模型权重文件名")

    @computed_field
    @cached_property
    def model_type(self) -> str:
        return MODEL_TYPE

    @field_validator("weight_path")
    @classmethod
    def validate_model_path(cls, v: str):
        v = ".".join([v, MOUNT_PATH])
        _dir = os.path.join(MOUNT_NODE_PATH, "weights")
        os.makedirs(_dir, exist_ok=True)
        _file = os.path.join(_dir, v)
        if not os.path.exists(_file):
            url = urljoin(WEIGHTS_REMOTE_HOST, v)
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
        return _file


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
    db_path: str = "db/face"
    db_size: int = 1000
    sim_threshold: float = 0.9

    @field_validator("db_path")
    @classmethod
    def validate_db_path(cls, v: str):
        _dir = os.path.join(MOUNT_NODE_PATH, v)
        if not os.path.exists(_dir):
            os.makedirs(_dir, exist_ok=True)
        return os.path.join(MOUNT_NODE_PATH, v)


## ======= Web Schema ======= ##


class RecordFeatureModel(BaseModel):
    is_record: bool = False


class ImageReqModel(BaseModel):
    image: str = Field(description="base64 image")
    boxes: List[Box] = Field(description="识别到的人框列表")
