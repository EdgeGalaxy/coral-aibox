import io
import json
from pydantic import BaseModel
import uvicorn

from typing import List, Dict
from threading import Thread

import cv2
import numpy as np
from loguru import logger
from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.responses import StreamingResponse, Response
from fastapi.middleware.cors import CORSMiddleware

from schema import ParamsModel

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
        target=uvicorn.run, args=(app,), kwargs={"host": "0.0.0.0", "port": 8010}
    ).start()


def draw_mask_lines(frame, points: List[List[int]]):
    points = np.array(points, dtype=np.int32)
    cv2.polylines(frame, [points], isClosed=True, color=(0, 0, 255), thickness=2)


@router.get("/cameras")
def cameras():
    return list(contexts.keys())


@router.get("/cameras/{camera_id}/stream")
def video_stream(camera_id: str, with_mask: bool = False):
    def gen_frame():
        vc: cv2.VideoCapture = contexts[camera_id]["vc"]
        points: List[List[int]] = contexts[camera_id]["params"]["points"]
        while True:
            ret, frame = vc.read()
            if not ret:
                raise HTTPException(status_code=500, detail="摄像头读取失败")
            if with_mask:
                draw_mask_lines(frame, points)
            ret, frame = cv2.imencode(".jpg", frame)
            if not ret:
                raise HTTPException(status_code=500, detail="图像编码失败！")
            bframe = frame.tobytes()
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + bframe + b"\r\n\r\n"
            )

    return StreamingResponse(
        gen_frame(), media_type="multipart/x-mixed-replace; boundary=frame"
    )


@router.get("/cameras/{camera_id}/mask", summary="绘制Mask")
def draw_mask(camera_id: str, points: str = None):
    vc: cv2.VideoCapture = contexts[camera_id]["vc"]
    ret, frame = vc.read()
    if not ret:
        raise HTTPException(status_code=500, detail="摄像头读取失败")

    if points:
        points = points.split(",")
        points = [
            [int(points[idx]), int(points[idx + 1])] for idx in range(0, len(points), 2)
        ]
        draw_mask_lines(frame, points)
    ret, frame = cv2.imencode(".jpg", frame)
    if not ret:
        raise HTTPException(status_code=500, detail="图像编码失败！")
    bframe = io.BytesIO(frame.tobytes())
    return StreamingResponse(bframe, media_type="image/jpeg")


@router.get("/cameras/{camera_id}/config")
def get_camera_params(camera_id: str):
    return contexts[camera_id]["params"]


@router.post("/cameras/{camera_id}/config")
def change_camera_params(camera_id: str, item: ParamsModel):
    context = contexts[camera_id]
    context["params"] = item.model_dump()
    return context["params"]


d = {"is_record": False}


@router.get("/config")
def person_face_mock_config():
    print("ddd", d)
    return d


class MockModel(BaseModel):
    is_record: bool


@router.post("/record/featuredb")
def record_feature(item: MockModel):
    d["is_record"] = item.is_record
    print("featuredb", d)
    return d
