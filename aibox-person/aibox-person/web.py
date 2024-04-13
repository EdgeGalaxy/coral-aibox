import base64
from typing import Dict, List
from threading import Thread

import cv2
import requests
import uvicorn
import numpy as np
from loguru import logger
from fastapi import FastAPI, APIRouter
from fastapi.responses import StreamingResponse
from coral import ObjectPayload

from .algrothms.inference import Inference
from .algrothms.utils import draw_image_with_boxes
from .schema import RecordFeatureModel, ImageReqModel


class WebBackGroundTask(Thread):
    """
    =========
    web接口实现
    =========
    """

    router = APIRouter()

    def __init__(
        self, node_id: str, contexts: Dict[str, Dict], port: int, *args, **kwargs
    ) -> None:
        super().__init__(*args, **kwargs)
        self.node_id = node_id
        self.contexts = contexts
        self.port = port

    def run(self):
        app = FastAPI()
        app.include_router(self.router, prefix=f"/api/{self.node_id}")
        uvicorn.run(self.router, host="0.0.0.0", port=self.port)

    @router.post("/record")
    def record_feature(self, item: RecordFeatureModel):
        context = self.contexts[0]
        params = context["params"]
        # params 为 AIboxPersonParamsModel
        params.is_record = item.is_record
        if item.is_record:
            logger.info(f"{self.node_id} start record feature!!")
        else:
            logger.info(f"{self.node_id} stop record feature!!")
        return params.model_dump()

    @router.get("/config")
    def _get_params(self):
        return self.contexts[0]["params"].model_dump()

    @router.post("/predict")
    def predict(self, item: ImageReqModel, with_face_detect: bool = False):
        from .node import AIboxPerson

        context = self.contexts[0]["context"]
        model: Inference = context["model"]
        params = self.contexts[0]["params"]
        frame = np.frombuffer(base64.b64decode(item.image), np.uint8)
        # 获取mask
        mask = context["mask"]
        iou_thresh = context["iou_thresh"]

        defects = model.predict(frame, params.is_record)
        objects = [ObjectPayload(**defect) for defect in defects]
        # 过滤与mask不重合的objects
        objects: List[ObjectPayload] = AIboxPerson.filter_objects(
            mask, objects, iou_thresh
        )

        # ! 此处存在硬代码，执行另外face_node的web服务，简化前端调用逻辑
        if with_face_detect and objects:
            url = "http://localhost:8030/api/aibox_face/predict"
            data = {"image": item.image, "boxes": [object.box for object in objects]}
            r = requests.post(url, json=data)
            if r.ok:
                face_objects = r.json()
            else:
                raise ValueError(f"get face objects error: {r.text}!")

            for object, face_object in zip(objects, face_objects):
                if not face_object:
                    continue
                object.objects = [ObjectPayload(**face_object)]
        draw_image_with_boxes(frame, objects)
        ret, frame = cv2.imencode(".jpg", frame)
        if not ret:
            raise ValueError("编码失败！")
        bframe = frame.tobytes()
        return StreamingResponse(bframe, media_type="image/jpeg")
