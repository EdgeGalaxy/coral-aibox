from typing import List, Optional, Union

from pydantic import Field, BaseModel


class ParamsModel(BaseModel):
    iou_scale: float = 0.03
    points: List[List[int]] = []


class CameraParamsModel(BaseModel):
    name: str
    url: str = Field(description="摄像头url")
    width: Optional[Union[int, None]] = None
    height: Optional[Union[int, None]] = None
    params: ParamsModel = ParamsModel()


class CameraOps:
    ADD = "add"
    CHANGE = "change"
    DELETE = "delete"


class ActivedCodeModel(BaseModel):
    code: str
