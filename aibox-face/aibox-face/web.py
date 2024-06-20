import os
import time
import json
import shutil
from typing import Dict
from threading import Thread
from collections import deque, defaultdict
from urllib.parse import urljoin

import cv2
from fastapi.staticfiles import StaticFiles
import requests
import uvicorn
import numpy as np
from loguru import logger
from coral import RawPayload
from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from algrothms.inference import Inference
from algrothms.gossip import GossipCommunicate
from algrothms.utils import draw_image_with_boxes, BASE_URL, draw_mask
from schema import (
    RecordFeatureModel,
    WebNodeParams,
    UsersRemarkModel,
    UserFaceModel,
)

# 全局变量
node_id = None
contexts = {}
stop_stream = False
cameras_queue: Dict[str, deque] = defaultdict(lambda: deque(maxlen=5))


"""
=========
web接口实现
=========
"""

router = APIRouter()


def async_run(_node_id: str, mount_path: str) -> None:
    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    prefix = f"/api/{_node_id}"
    app.include_router(router, prefix=prefix)
    app.mount(f"{prefix}/static", StaticFiles(directory=mount_path), name="static")
    logger.info(f"{_node_id} start web server")
    Thread(
        target=uvicorn.run, args=(app,), kwargs={"host": "0.0.0.0", "port": 8030}
    ).start()


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
    CONFIG_URL = urljoin(CONFIG_REMOTE_HOST, "configs/aibox-face.json")
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


def append_payload_to_web_queue(payload: RawPayload, fps: int) -> None:
    cameras_queue[payload.source_id].append((payload, fps))


def durable_config(node_params: dict):
    from coral import CoralNode

    config_fp, _ = CoralNode.get_config()
    with open(config_fp, "r") as f:
        data = json.load(f)

    data["params"].update(node_params)

    with open(config_fp, "w") as f:
        json.dump(data, f, indent=4)


@router.get("/users")
def show_faces():
    context = contexts[0]
    inference: Inference = context["context"]["model"]
    featuredb = inference.featuredb
    users = featuredb.show_users_faces()
    # 按照是否有新命名排序
    sorted_users = sorted(
        [(user_id, 1 if user_id.startswith("UNKNOWN") else 0) for user_id in users],
        key=lambda x: x[1],
    )
    return {user_id: users[user_id] for user_id, _ in sorted_users}


@router.post("/users/remark")
def update_user_remark(item: UsersRemarkModel):
    context = contexts[0]
    inference: Inference = context["context"]["model"]
    featuredb = inference.featuredb
    gossip: GossipCommunicate = context["context"]["gossip"]
    logger.info(
        f"{node_id} update user remark: {item.remark_user_id} to {item.old_user_id}"
    )
    featuredb.remark_user_id(item.remark_user_id, item.old_user_id)
    # 更新gossip
    user_faces = featuredb.show_users_faces()[item.remark_user_id]
    user_faces_url = [
        {
            "face_key": user_face,
            "image": f"api/{node_id}/static/{user_face}.jpg",
            "vector": f"api/{node_id}/static/{user_face}.npy",
        }
        for user_face in user_faces
    ]
    # 默认从UNKOWN文件重命名，对其他节点实行创建
    if item.old_user_id.startswith("UNKNOWN"):
        gossip.user_faces_create(item.remark_user_id, user_faces_url)
    else:  # 重命名对其他节点实行重命名操作
        gossip.user_faces_move(
            item.old_user_id, item.remark_user_id, faces=user_faces_url
        )
    return {"result": "success"}


@router.delete("/users/{user_id}/faces/{face_id}")
def delete_user_faces(user_id: str, face_id: str):
    context = contexts[0]
    inference: Inference = context["context"]["model"]
    featuredb = inference.featuredb
    gossip: GossipCommunicate = context["context"]["gossip"]
    logger.info(f"{node_id} delete user {user_id} face {face_id}")
    featuredb.delete_user_faces(user_id, face_id)
    # 更新gossip
    gossip.user_delete(user_id)
    return {"result": "success"}


@router.post("/users/{src_user_id}/move/{dest_user_id}")
def move_user_faces(src_user_id: str, dest_user_id: str, item: UserFaceModel):
    context = contexts[0]
    inference: Inference = context["context"]["model"]
    featuredb = inference.featuredb
    gossip: GossipCommunicate = context["context"]["gossip"]
    logger.info(
        f"{node_id} move face: {item.face} user {src_user_id} to {dest_user_id}"
    )
    featuredb.move_face_to_user_id(item.face, dest_user_id)
    # 更新gossip
    user_face_url = {
        "face_key": item.face,
        "image": f"api/{node_id}/static/{item.face}.jpg",
        "vector": f"api/{node_id}/static/{item.face}.npy",
    }
    gossip.user_faces_move(src_user_id, dest_user_id, faces=[user_face_url])
    return {"result": "success"}


@router.delete("/users/{user_id}")
def delete_user(user_id: str):
    context = contexts[0]
    inference: Inference = context["context"]["model"]
    featuredb = inference.featuredb
    logger.info(f"{node_id} delete user: {user_id}")
    featuredb.delete_user(user_id)
    return {"result": "success"}


@router.get("/users/sync")
def sync_users():
    context = contexts[0]
    inference: Inference = context["context"]["model"]
    featuredb = inference.featuredb
    gossip: GossipCommunicate = context["context"]["gossip"]
    users_faces = featuredb.show_users_faces()
    for user_id, user_faces in users_faces.items():
        user_faces_url = [
            {
                "face_key": user_face,
                "image": f"api/{node_id}/static/{user_face}.jpg",
                "vector": f"api/{node_id}/static/{user_face}.npy",
            }
            for user_face in user_faces
        ]
        gossip.user_sync(user_id, user_faces_url)
        logger.info(f"sync user: {user_id} success!")
    return {"result": "success"}


@router.post("/record/featuredb")
def record_feature(item: RecordFeatureModel):
    for idx in contexts:
        context = contexts[idx]
        params = context["params"]
        # params 为 AIboxPersonParamsModel
        params.is_record = item.is_record
        if item.is_record:
            logger.info(f"{node_id} start record feature!!")
        else:
            logger.info(f"{node_id} stop record feature!!")
        params.is_open = item.is_open
        params.detection.confidence_thresh = item.confidence_thresh
        params.featuredb.sim_threshold = item.sim_threshold

        # 动态更新模型阈值
        inference: Inference = context["context"]["model"]
        inference.model.nms_thresh = item.confidence_thresh
        inference.featuredb.sim_threshold = item.sim_threshold

    new_params = contexts[0]["params"].model_dump()
    # 更新数据
    durable_config(new_params)
    return {"result": "success"}


@router.get("/config")
def get_params():
    params = contexts[0]["params"]
    detection = params.detection
    featuredb = params.featuredb
    return WebNodeParams(
        **{
            "is_record": params.is_record,
            "is_open": params.is_open,
            "detection": {
                "width": detection.width,
                "height": detection.height,
                "nms_thresh": detection.nms_thresh,
                "confidence_thresh": detection.confidence_thresh,
            },
            "featuredb": {
                "width": featuredb.width,
                "height": featuredb.height,
                "user_faces_size": featuredb.user_faces_size,
                "sim_threshold": featuredb.sim_threshold,
            },
        }
    )


@router.post("/config")
def change_params(item: WebNodeParams):
    from schema import AIboxFaceParamsModel

    for idx in contexts:
        context = contexts[idx]
        params = context["params"].model_dump()
        params.update(item.model_dump())
        context["params"] = AIboxFaceParamsModel(**params)

    durable_config(item.model_dump())
    return item.model_dump()


@router.get("/cameras/stop_stream")
def stop_stream_view():
    global stop_stream
    stop_stream = True
    return {"result": "success"}


@router.get("/cameras/{camera_id}/stream")
def get_frames(camera_id: str):
    global stop_stream
    stop_stream = False

    def process_frames():
        while True:
            try:
                message = cameras_queue[camera_id].popleft()
                payload: RawPayload = message[0]
                fps: int = message[1]
            except IndexError:
                # 队列不存在值
                continue

            if stop_stream:
                logger.info(f"{camera_id} stop stream!")
                break

            frame: np.ndarray = payload.raw

            draw_image_with_boxes(
                frame, payload.objects, int(payload.nodes_cost * 1000), fps
            )
            # 画mask
            if payload.raw_params["points"]:
                frame = draw_mask(frame, payload.raw_params["points"])

            # 修改分辨率
            camera_height = payload.raw_params.get("camera_height", None)
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
        process_frames(), media_type="multipart/x-mixed-replace; boundary=frame"
    )
