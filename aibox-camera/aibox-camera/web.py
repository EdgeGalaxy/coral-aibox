import io
import os
import json
import shutil
import subprocess
import sys
import time
from typing import Dict, List
from threading import Thread
from urllib.parse import urljoin
from collections import defaultdict, deque

import cv2
import requests
import uvicorn
import numpy as np
from loguru import logger
from coral.constants import MOUNT_PATH
from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse, Response
from fastapi.middleware.cors import CORSMiddleware

from schema import ChangeResolutionModel, ParamsModel, CameraParamsModel, CameraOps

# 全局变量
node_id = None
contexts = {}
stop_stream = False
is_actived = False
cameras_queue: Dict[str, deque] = defaultdict(lambda: deque(maxlen=5))

MOUNT_NODE_PATH = os.path.join(MOUNT_PATH, "aibox")
os.makedirs(MOUNT_NODE_PATH, exist_ok=True)


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


def resolution_height_mapper(resolution: str) -> int:
    if resolution == "origin":
        return None
    elif resolution == "middle":
        return 480
    elif resolution == "low":
        return 360
    else:
        return None


def restart_program():
    """重启当前程序。"""
    python = sys.executable
    args = sys.argv[:]

    subprocess.Popen([python] + args)

    os_kill()


def os_kill():
    # 退出当前进程, 运行两次，冷退出,
    # signal 2 确保图片内存缓存记录落盘
    os.kill(os.getpid(), 2)
    time.sleep(0.1)
    os.kill(os.getpid(), 2)
    time.sleep(0.3)
    os.kill(os.getpid(), 9)


def restart_main_thread():
    Thread(target=restart_program).start()


def stop_main_thread():
    Thread(target=os_kill).start()


def draw_mask_lines(frame, points: List[List[int]]):
    points = np.array(points, dtype=np.int32)
    cv2.polylines(frame, [points], isClosed=True, color=(0, 0, 255), thickness=2)


def check_config_fp_or_set_default(config_fp: str):
    """
    校验配置文件是否存在，不存在则下载默认配置

    :param config_fp: 环境变量配置文件路径
    :param default_config_fp: 默认本地项目的配置文件路径
    """
    CONFIG_REMOTE_HOST = os.environ.get(
        "CONFIG_REMOTE_HOST",
        "https://nbstore.oss-cn-shanghai.aliyuncs.com/coral-aibox/onnx/",
    )
    CONFIG_URL = urljoin(CONFIG_REMOTE_HOST, "configs/aibox-camera.json")
    config_dir = os.path.split(config_fp)[0]
    if config_dir:
        os.makedirs(config_dir, exist_ok=True)
    if not os.path.exists(config_fp):
        logger.warning(f"{config_fp} not exists, download from {CONFIG_URL}!")
        r = requests.get(CONFIG_URL)
        if r.ok:
            with open(config_fp, "wb") as f:
                f.write(r.content)
            logger.warning(f"file {config_fp} download success!")
        else:
            raise ValueError(
                f"file {config_fp} not exists, download from {CONFIG_URL} error: {r.text}!"
            )


# 持久化配置文件
def durable_config(
    camera_id: str, camera: CameraParamsModel = None, ops: str = CameraOps.DELETE
):
    from coral import CoralNode

    config_fp, _ = CoralNode.get_config()
    with open(config_fp, "r") as f:
        data = json.load(f)

    cameras: List = data["params"].get("cameras", [CameraParamsModel().model_dump()])
    camera_ids = {camera["name"]: idx for idx, camera in enumerate(cameras)}
    camera_urls = {camera["url"]: idx for idx, camera in enumerate(cameras)}
    # !此处为适配node节点内的代码而写，需要优化
    if ops == CameraOps.CHANGE:
        camera_data = camera.model_dump()
        idx = camera_ids[camera_id]
        cameras[idx] = camera_data
    elif ops == CameraOps.DELETE:
        idx = camera_ids[camera_id]
        del cameras[idx]
    elif ops == CameraOps.ADD:
        if camera_id in camera_ids:
            raise ValueError(f"相机名称需要保持唯一, 已存在相机 {camera_id}")
        if camera.url in camera_urls:
            raise ValueError(f"相机地址需要保持唯一, 已存在相机 {camera.url}")
        camera_data = camera.model_dump()
        # 新增数据
        cameras.append(camera_data)
    else:
        raise ValueError(f"不支持的操作 {ops}")

    data["process"]["count"] = len(cameras)
    data["params"]["cameras"] = cameras

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
    return sorted(list(contexts.keys()))


@router.get("/cameras/resolution")
def resolution():
    if len(contexts) == 0:
        return None
    return contexts[list(contexts.keys())[0]]["resolution"]


@router.post("/cameras/resolution")
def change_resolution(item: ChangeResolutionModel):
    # 动态修改分辨率
    for camera_id in contexts:
        contexts[camera_id]["resolution"] = item.level
    durable_resolution_config(item.level)
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
def video_stream(camera_id: str):
    global stop_stream
    stop_stream = False

    def gen_frame():
        camera_height = resolution_height_mapper(contexts[camera_id]["resolution"])
        while True:
            try:
                frame = cameras_queue[camera_id].popleft()
            except IndexError:
                # 队列不存在值
                time.sleep(0.005)
                continue

            if stop_stream:
                logger.info(f"{camera_id} stop stream!")
                break

            # 修改分辨率
            if camera_height:
                oh, ow = frame.shape[:2]
                scale = camera_height / oh
                frame = cv2.resize(frame, (int(ow * scale), int(camera_height)))

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


@router.get("/cameras/{camera_id}/draw-mask", summary="绘制Mask")
def draw_mask(camera_id: str, points: str = None):
    while True:
        try:
            frame = cameras_queue[camera_id].popleft()
            break
        except IndexError:
            # 队列不存在值
            time.sleep(0.005)
            continue

    if points:
        points = points.split(",")
        points = [
            [int(points[idx]), int(points[idx + 1])] for idx in range(0, len(points), 2)
        ]
        draw_mask_lines(frame, points)
    _dir = os.path.join(MOUNT_NODE_PATH, "cameras", camera_id)
    os.makedirs(_dir, exist_ok=True)
    fp = os.path.join(_dir, "mask.jpg")
    # 先删除旧文件
    if os.path.exists(fp):
        os.remove(fp)
    cv2.imwrite(fp, frame)
    return FileResponse(fp, media_type="image/jpeg")


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
    try:
        # 持久化
        durable_config(item.name, item, ops=CameraOps.ADD)
    except Exception as e:
        return HTTPException(status_code=500, detail=str(e))
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
