from collections import defaultdict, deque
import io
import os
import json
import shutil
import time
from typing import Dict, List
from threading import Thread

import cv2
import uvicorn
import numpy as np
from loguru import logger
from fastapi import FastAPI, APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from schema import ChangeResolutionModel, ParamsModel, CameraParamsModel, CameraOps

# 全局变量
node_id = None
contexts = {}
restart = False
stop_stream = False
is_actived = False
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
        target=uvicorn.run, args=(app,), kwargs={"host": "0.0.0.0", "port": 8010}
    ).start()


def restart_main_thread():
    global restart
    restart = True


def draw_mask_lines(frame, points: List[List[int]]):
    points = np.array(points, dtype=np.int32)
    cv2.polylines(frame, [points], isClosed=True, color=(0, 0, 255), thickness=2)


def check_config_fp_or_set_default(config_fp: str, default_config_fp: str):
    """
    校验配置文件是否存在，不存在则拷贝

    :param config_fp: 环境变量配置文件路径
    :param default_config_fp: 默认本地项目的配置文件路径
    """
    config_dir = os.path.split(config_fp)[0]
    if config_dir:
        os.makedirs(config_dir, exist_ok=True)
    if not os.path.exists(config_fp):
        logger.warning(f"{config_fp} not exists, copy from {default_config_fp}!")
        shutil.copyfile(default_config_fp, config_fp)
    if config_fp == default_config_fp:
        logger.warning(f"config_fp is default {default_config_fp}!")


# 持久化配置文件
def durable_config(
    camera_id: str, camera: CameraParamsModel = None, ops: str = CameraOps.DELETE
):
    from coral import CoralNode

    config_fp, _ = CoralNode.get_config()
    with open(config_fp, "r") as f:
        data = json.load(f)

    cameras: List = data["params"]["cameras"]
    camera_ids = {camera["name"]: idx for idx, camera in enumerate(cameras)}
    # !此处为适配node节点内的代码而写，需要优化
    camera_data = camera.model_dump()
    if ops == CameraOps.CHANGE:
        idx = camera_ids[camera_id]
        cameras[idx] = camera_data
    elif ops == CameraOps.DELETE:
        idx = camera_ids[camera_id]
        del cameras[idx]
        data["process"]["count"] = len(cameras)
    elif ops == CameraOps.ADD:
        # 新增数据
        cameras.append(camera_data)
        data["process"]["count"] = len(cameras)
    else:
        raise ValueError(f"不支持的操作 {ops}")

    with open(config_fp, "w") as f:
        json.dump(data, f, indent=4)


def durable_resolution_config(resolution: str):
    from coral import CoralNode

    config_fp, _ = CoralNode.get_config()
    with open(config_fp, "r") as f:
        data = json.load(f)

    data["params"]["resolution"] = resolution

    with open(config_fp, "w") as f:
        json.dump(data, f, indent=4)


@router.get("/cameras")
def cameras():
    return list(contexts.keys())


@router.get("/cameras/resolution")
def resolution():
    return contexts[list(contexts.keys())[0]]["resolution"]


@router.post("/cameras/resolution")
def change_resolution(item: ChangeResolutionModel):
    durable_resolution_config(item.level)
    restart_main_thread()
    return {"result": "success"}


@router.get("/cameras/is_actived")
def is_actived_view():
    return is_actived


@router.get("/cameras/stop_stream")
def stop_stream_view():
    global stop_stream
    stop_stream = True
    return {"result": "success"}


@router.get("/cameras/{camera_id}/stream")
def video_stream(camera_id: str, with_mask: bool = False):
    global stop_stream
    stop_stream = False

    def gen_frame():
        points: List[List[int]] = contexts[camera_id]["params"]["points"]
        while True:
            try:
                frame = cameras_queue[camera_id].popleft()
            except IndexError:
                # 队列不存在值
                time.sleep(0.01)
                continue

            if stop_stream:
                logger.info(f"{camera_id} stop stream!")
                break

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
    while True:
        try:
            frame = cameras_queue[camera_id].popleft()
            break
        except IndexError:
            # 队列不存在值
            time.sleep(0.01)
            continue

    if points:
        points = points.split(",")
        points = [
            [int(points[idx]), int(points[idx + 1])] for idx in range(0, len(points), 2)
        ]
        draw_mask_lines(frame, points)
    ret, frame = cv2.imencode(".jpg", frame)
    if not ret:
        logger.exception("图像编码失败！")
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
    durable_config(
        camera_id,
        CameraParamsModel(
            name=context["name"], url=context["url"], params=context["params"]
        ),
        ops=CameraOps.CHANGE,
    )
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
    durable_config(camera_id, ops=CameraOps.DELETE)
    # 重启服务
    restart_main_thread()
    return {"name": camera_id}


@router.get("/restart")
def restart_view():
    restart_main_thread()
    return {"result": "success"}
