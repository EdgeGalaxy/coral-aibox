import os
import io
import json
import shutil
import base64
from typing import Dict, List
from threading import Thread

import cv2
import requests
import uvicorn
import numpy as np
from loguru import logger
from coral import ObjectPayload
from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from algrothms.inference import Inference
from algrothms.utils import draw_image_with_boxes
from schema import RecordFeatureModel, ImageReqModel, WebNodeParams


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
        target=uvicorn.run, args=(app,), kwargs={"host": "0.0.0.0", "port": 8020}
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
    from node import AIboxPersonParamsModel

    context = contexts[0]
    params = context["params"].model_dump()
    params.update(item.model_dump())
    context["params"] = AIboxPersonParamsModel(**params)
    durable_config(item)
    return item.model_dump()


@router.post("/predict")
def predict(item: ImageReqModel, with_face_detect: bool = False):
    from .node import AIboxPerson

    context = contexts[0]["context"]
    model: Inference = context["model"]
    params = contexts[0]["params"]
    frame = np.frombuffer(base64.b64decode(item.image), np.uint8)
    # 获取mask
    mask = context["mask"]
    iou_thresh = context["iou_thresh"]

    defects = model.predict(frame, params.is_record)
    objects = [ObjectPayload(**defect) for defect in defects]
    # 过滤与mask不重合的objects
    objects: List[ObjectPayload] = AIboxPerson.filter_objects(mask, objects, iou_thresh)

    # ! 此处存在硬代码，执行另外face_node的web服务，简化前端调用逻辑
    if with_face_detect and objects:
        url = "http://localhost:8030/api/aibox_face/predict"
        data = {"image": item.image, "boxes": [object.box for object in objects]}
        r = requests.post(url, json=data)
        if r.ok:
            face_objects = r.json()
        else:
            raise HTTPException(
                status_code=500, detail=f"get face objects error: {r.text}!"
            )

        for object, face_object in zip(objects, face_objects):
            if not face_object:
                continue
            object.objects = [ObjectPayload(**face_object)]

    draw_image_with_boxes(frame, objects)
    ret, frame = cv2.imencode(".jpg", frame)
    if not ret:
        raise HTTPException(status_code=500, detail="图像编码失败！")
    bframe = io.BytesIO(frame.tobytes())
    return StreamingResponse(bframe, media_type="image/jpeg")
