import asyncio
import os
import json
import shutil
from typing import List
from threading import Thread
from urllib.parse import urljoin

from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import requests
import uvicorn
from loguru import logger
from fastapi import FastAPI, APIRouter, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from algrothms.event import EventRecord


# 全局变量
node_id = None
person_count = None
contexts = {}


"""
=========
web接口实现
=========
"""

router = APIRouter()


class ReportWebModel(BaseModel):
    report_scene: float = Field(
        description="上报场景, 越小表示场景遮挡越多，越相信历史数据", ge=0, le=1
    )


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
        target=uvicorn.run, args=(app,), kwargs={"host": "0.0.0.0", "port": 8040}
    ).start()


def durable_config(node_params: dict):
    from coral import CoralNode

    config_fp, _ = CoralNode.get_config()
    with open(config_fp, "r") as f:
        data = json.load(f)

    data["params"].update(node_params)

    with open(config_fp, "w") as f:
        json.dump(data, f, indent=4)


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
    CONFIG_URL = urljoin(CONFIG_REMOTE_HOST, "configs/aibox-report.json")
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


@router.get("/event/trigger/gpio")
def get_gpio_events():
    context = contexts[0]
    event: EventRecord = context["context"]["event"]
    return event.events


@router.get("/config")
def get_config():
    context = contexts[0]
    params = context["params"]
    return {"report_scene": params.report_scene}


@router.post("/config")
def set_config(item: ReportWebModel):
    for idx in contexts:
        context = contexts[idx]
        params = context["params"]
        kf = context["kf"]
        # 更新运行时数据
        params.report_scene = item.report_scene
        kf.Q = params.kf_Q
        kf.R = params.kf_R

    logger.info(f"{node_id} set config: {item.model_dump()}")
    # 更新数据
    new_params = contexts[0]["params"].model_dump()
    durable_config(new_params)
    return {"result": "success"}


@router.websocket("/ws/person_count")
async def person_count_ws(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            message = {"count": person_count}
            await websocket.send_json(message)
            await asyncio.sleep(0.01)
    except Exception as e:
        logger.warning(e)
    finally:
        await websocket.close()
