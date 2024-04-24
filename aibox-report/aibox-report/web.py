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

from algrothms.event import EventRecord


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
        target=uvicorn.run, args=(app,), kwargs={"host": "0.0.0.0", "port": 8040}
    ).start()


@router.get("/event/trigger/gpio")
def get_gpio_events():
    context = contexts[0]
    event: EventRecord = context["context"]["event"]
    return event.events
