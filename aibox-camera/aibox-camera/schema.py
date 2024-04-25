from typing import List

from pydantic import Field, BaseModel


class ParamsModel(BaseModel):
    iou_scale: float = 0.03
    points: List[List[int]] = []


class CameraParamsModel(BaseModel):
    name: str
    url: str = Field(description="摄像头url")
    width: int = 640
    height: int = 480
    params: ParamsModel = ParamsModel()


class CameraOps:
    ADD = "add"
    CHANGE = "change"
    DELETE = "delete"
