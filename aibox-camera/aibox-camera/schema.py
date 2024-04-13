from typing import List

from pydantic import Field, BaseModel


class ParamsModel(BaseModel):
    iou_scale: float = 0.03
    points: List[List[int]]


class CameraParamsModel(BaseModel):
    name: str
    url: str = Field(description="摄像头url")
    params: ParamsModel
