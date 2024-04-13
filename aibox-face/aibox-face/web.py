import base64
from typing import Dict, Any
from threading import Thread

import uvicorn
import numpy as np
from loguru import logger
from fastapi import FastAPI, APIRouter

from algrothms.inference import Inference
from schema import RecordFeatureModel, ImageReqModel

# 全局变量
node_id = None
contexts = {}


"""
=========
web接口实现
=========
"""

router = APIRouter()


def async_run(_node_id: str) -> None:
    app = FastAPI()
    app.include_router(router, prefix=f"/api/{_node_id}")
    logger.info(f"{_node_id} start web server")
    Thread(
        target=uvicorn.run, args=(app,), kwargs={"host": "0.0.0.0", "port": 8030}
    ).start()


@router.post("/record")
def record_feature(item: RecordFeatureModel):
    context = contexts[0]
    params = context["params"]
    # params 为 AIboxPersonParamsModel
    params.is_record = item.is_record
    if item.is_record:
        logger.info(f"{node_id} start record feature!!")
    else:
        logger.info(f"{node_id} stop record feature!!")
    return params.model_dump()


@router.get("/config")
def get_params():
    return contexts[0]["params"].model_dump()


@router.post("/predict")
def predict(self, item: ImageReqModel):
    from .node import AIboxFace

    face_objects = []
    model: Inference = contexts[0]["context"]["model"]
    frame = np.frombuffer(base64.b64decode(item.image), np.uint8)
    for box in item.boxes:
        # base64 image to ndarray
        person_frame = frame[box.x1 : box.x2, box.y1 : box.y2, :]
        objects = model.predict(person_frame)
        similar_object = AIboxFace.get_max_face(objects)
        face_objects.append(similar_object)
    return face_objects
