import io
import json
import uvicorn

from typing import List
from threading import Thread

import cv2
import numpy as np
from loguru import logger
from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from schema import ParamsModel, CameraParamsModel, CameraOps

# 全局变量
node_id = None
contexts = {}
restart = False


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


def restart_main_thread():
    global restart
    restart = True


def draw_mask_lines(frame, points: List[List[int]]):
    points = np.array(points, dtype=np.int32)
    cv2.polylines(frame, [points], isClosed=True, color=(0, 0, 255), thickness=2)


# 持久化配置文件
def durable_config(
    camera_id: str, camera: CameraParamsModel = None, ops: str = CameraOps.DELETE
):
    from node import CoralNode

    config_fp, _ = CoralNode.get_config()
    with open(config_fp, "r") as f:
        data = json.load(f)

    cameras: List = data["params"]["cameras"]
    camera_ids = {camera["name"]: idx for idx, camera in enumerate(cameras)}
    if ops == CameraOps.CHANGE:
        idx = camera_ids[camera_id]
        cameras[idx] = camera.model_dump()
    elif ops == CameraOps.DELETE:
        idx = camera_ids[camera_id]
        del cameras[idx]
    elif ops == CameraOps.ADD:
        # 新增数据
        cameras.append(camera.model_dump())
        data["process"]["count"] = len(cameras)
    else:
        raise ValueError(f"不支持的操作 {ops}")

    with open(config_fp, "w") as f:
        json.dump(data, f, indent=4)


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
    # 持久化配置
    durable_config(camera_id, CameraParamsModel(**context), ops=CameraOps.CHANGE)
    return context["params"]


@router.post("/cameras/add")
def add_camera(item: CameraParamsModel):
    # 持久化
    durable_config(item.name, item, ops=CameraOps.ADD)
    # 重启服务
    restart_main_thread()
    return item.model_dump()


@router.delete("/cameras/{camera_id}")
def delete_camera(camera_id: str):
    # 持久化
    durable_config(camera_id, ops=CameraOps.ADD)
    # 重启服务
    restart_main_thread()
    return {"name": camera_id}
