import os
import json
import shutil
from typing import List
from threading import Thread
from urllib.parse import urljoin

from fastapi.staticfiles import StaticFiles
import requests
import uvicorn
from loguru import logger
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware


# 全局变量
node_id = None
contexts = {}


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
    app.include_router(router, prefix=f"/api/{_node_id}")
    app.mount("/static", StaticFiles(directory=mount_path), name="static")
    logger.info(f"{_node_id} start web server")
    Thread(
        target=uvicorn.run, args=(app,), kwargs={"host": "0.0.0.0", "port": 8050}
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
    CONFIG_URL = urljoin(CONFIG_REMOTE_HOST, "configs/aibox-record.json")
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


@router.get("/video/records")
def get_records():
    context = contexts[0]
    cameras_dir_fp = context["params"].base_dir
    results = {}
    for camera_dir_fn in os.listdir(cameras_dir_fp):
        camera_dir_fp = os.path.join(cameras_dir_fp, camera_dir_fn)
        if not os.path.isdir(camera_dir_fp):
            continue
        video_fns = sorted(
            [
                os.path.join(camera_dir_fn, f)
                for f in os.listdir(camera_dir_fp)
                if f.endswith(".mp4")
            ],
            reverse=True,
        )
        results[camera_dir_fn] = video_fns[1:]
    return results
