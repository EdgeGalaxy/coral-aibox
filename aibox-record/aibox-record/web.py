import os
import json
import shutil
from typing import List
from threading import Thread

from fastapi.staticfiles import StaticFiles
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
