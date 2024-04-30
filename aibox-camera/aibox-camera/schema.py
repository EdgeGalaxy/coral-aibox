from typing import List, Optional, Union

from pydantic import Field, BaseModel


class ParamsModel(BaseModel):
    iou_scale: float = 0.03
    points: List[List[int]] = []


class CameraParamsModel(BaseModel):
    name: str = "camera01"
    url: str = Field(default="0", description="摄像头url")
    params: ParamsModel = ParamsModel()


class CameraOps:
    ADD = "add"
    CHANGE = "change"
    DELETE = "delete"


class ActivedCodeModel(BaseModel):
    code: str


class ChangeResolutionModel(BaseModel):
    level: str
