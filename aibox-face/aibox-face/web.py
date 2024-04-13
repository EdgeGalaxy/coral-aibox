import base64
from typing import Dict, Any
from threading import Thread

import uvicorn
import numpy as np
from loguru import logger
from fastapi import FastAPI, APIRouter

from .algrothms.inference import Inference
from .schema import RecordFeatureModel, ImageReqModel


class WebBackGroundTask(Thread):
    """
    =========
    web接口实现
    =========
    """

    router = APIRouter()

    def __init__(
        self, node_id: str, contexts: Dict[str, Any], port: int, *args, **kwargs
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
    def predict(self, item: ImageReqModel):
        from .node import AIboxFace

        face_objects = []
        model: Inference = self.contexts[0]["context"]["model"]
        frame = np.frombuffer(base64.b64decode(item.image), np.uint8)
        for box in item.boxes:
            # base64 image to ndarray
            person_frame = frame[box.x1 : box.x2, box.y1 : box.y2, :]
            objects = model.predict(person_frame)
            similar_object = AIboxFace.get_max_face(objects)
            face_objects.append(similar_object)
        return face_objects
