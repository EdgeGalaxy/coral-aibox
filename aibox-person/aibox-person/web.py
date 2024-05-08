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

from algrothms.inference import Inference
from schema import RecordFeatureModel, WebNodeParams, MOUNT_NODE_PATH


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
        target=uvicorn.run, args=(app,), kwargs={"host": "0.0.0.0", "port": 8020}
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
    CONFIG_URL = urljoin(CONFIG_REMOTE_HOST, "configs/aibox-person.json")
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


def durable_config(node_params: dict):
    from coral import CoralNode

    config_fp, _ = CoralNode.get_config()
    with open(config_fp, "r") as f:
        data = json.load(f)

    data["params"].update(node_params)

    with open(config_fp, "w") as f:
        json.dump(data, f, indent=4)


@router.get("/fake/persons")
def get_fake_persons():
    context = contexts[0]
    inference: Inference = context["context"]["model"]
    featuredb = inference.featuredb
    return [image + ".jpg" for image in featuredb.get_fake_person_ids()]


@router.delete("/fake/persons/{fake_person_id}")
def delete_fake_person(fake_person_id: str):
    context = contexts[0]
    inference: Inference = context["context"]["model"]
    featuredb = inference.featuredb
    featuredb.delete_fake_person(fake_person_id)
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
                "db_size": featuredb.db_size,
                "sim_threshold": featuredb.sim_threshold,
            },
        }
    )


@router.post("/config")
def change_params(item: WebNodeParams):
    from schema import AIboxPersonParamsModel

    for idx in contexts:
        context = contexts[idx]
        params = context["params"].model_dump()
        params.update(item.model_dump())
        context["params"] = AIboxPersonParamsModel(**params)
    durable_config(item.model_dump())
    return item.model_dump()
