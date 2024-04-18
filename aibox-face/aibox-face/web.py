import os
import time
import json
import shutil
import base64
from typing import Dict
from threading import Thread
from collections import deque, defaultdict

import cv2
import uvicorn
import numpy as np
from loguru import logger
from coral import RawPayload
from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from algrothms.inference import Inference
from algrothms.utils import draw_image_with_boxes
from schema import RecordFeatureModel, ImageReqModel, WebNodeParams

# 全局变量
node_id = None
contexts = {}
cameras_queue: Dict[str, deque] = defaultdict(lambda: deque(maxlen=5))


"""
=========
web接口实现
=========
"""

router = APIRouter()


def async_run(_node_id: str) -> None:
    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router, prefix=f"/api/{_node_id}")
    logger.info(f"{_node_id} start web server")
    Thread(
        target=uvicorn.run, args=(app,), kwargs={"host": "0.0.0.0", "port": 8030}
    ).start()


def check_config_fp_or_set_default(config_fp: str, default_config_fp: str):
    """
    校验配置文件是否存在，不存在则拷贝

    :param config_fp: 环境变量配置文件路径
    :param default_config_fp: 默认本地项目的配置文件路径
    """
    config_dir = os.path.split(config_fp)[0]
    os.makedirs(config_dir, exist_ok=True)
    if not os.path.exists(config_fp):
        logger.warning(f"{config_fp} not exists, copy from {default_config_fp}!")
        shutil.copyfile(default_config_fp, config_fp)
    if config_fp == default_config_fp:
        logger.warning(f"config_fp is default {default_config_fp}!")


def append_payload_to_web_queue(payload: RawPayload) -> None:
    cameras_queue[payload.source_id].append(payload)


def durable_config(node_params: WebNodeParams):
    from node import CoralNode

    config_fp, _ = CoralNode.get_config()
    with open(config_fp, "r") as f:
        data = json.load(f)

    data["params"].update(node_params.model_dump())

    with open(config_fp, "w") as f:
        json.dump(data, f, indent=4)


@router.post("/record/featuredb")
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
    return WebNodeParams(**contexts[0]["params"].model_dump()).model_dump()


@router.post("/config")
def change_params(item: WebNodeParams):
    from node import AIboxFaceParamsModel

    context = contexts[0]
    params = context["params"].model_dump()
    params.update(item.model_dump())
    context["params"] = AIboxFaceParamsModel(**params)
    durable_config(item)
    return item.model_dump()


@router.post("/predict")
def predict(item: ImageReqModel):
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


@router.get("/cameras/{camera_id}/stream")
def get_frames(camera_id: str):

    def process_frames():
        while True:
            try:
                payload: RawPayload = cameras_queue[camera_id].popleft()
            except IndexError:
                # 队列不存在值
                time.sleep(0.01)
                continue

            frame: np.ndarray = payload.raw

            draw_image_with_boxes(frame, payload.objects)
            ret, frame = cv2.imencode(".jpg", frame)
            if not ret:
                raise HTTPException(status_code=500, detail="图像编码失败！")
            bframe = frame.tobytes()
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + bframe + b"\r\n\r\n"
            )

    return StreamingResponse(
        process_frames(), media_type="multipart/x-mixed-replace; boundary=frame"
    )
