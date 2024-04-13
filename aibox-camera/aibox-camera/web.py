import uvicorn

from typing import List, Dict
from threading import Thread

import cv2
import numpy as np
from fastapi import FastAPI, APIRouter
from fastapi.responses import StreamingResponse

from .schema import ParamsModel


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

    @classmethod
    def draw_mask_lines(frame, points: List[List[int]]):
        points = np.array(points, dtype=np.int32)
        cv2.polylines(frame, [points], isClosed=True, color=(0, 0, 255), thickness=2)

    @router.get("/cameras")
    def _cameras(self):
        return self.contexts.keys()

    @router.get("/cameras/{camera_id}/stream")
    def _video_stream(self, camera_id: str, with_mask: bool = False):
        def gen_frame():
            vc: cv2.VideoCapture = self.contexts[camera_id]["vc"]
            points: List[List[int]] = self.contexts[camera_id]["params"]["points"]
            while True:
                ret, frame = vc.read()
                if not ret:
                    raise ValueError("摄像头读取失败")
                if with_mask:
                    self.draw_mask_lines(frame, points)
                ret, frame = cv2.imencode(".jpg", frame)
                if not ret:
                    raise ValueError("编码失败！")
                bframe = frame.tobytes()
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + bframe + b"\r\n\r\n"
                )

        return StreamingResponse(
            gen_frame(), media_type="multipart/x-mixed-replace; boundary=frame"
        )

    @router.post("/cameras/{camera_id}/mask")
    def _draw_mask(self, camera_id: str, points: List[List[int]]):
        vc: cv2.VideoCapture = self.contexts[camera_id]["vc"]
        ret, frame = vc.read()
        if not ret:
            raise ValueError("摄像头读取失败")

        self.draw_mask_lines(frame, points)
        ret, frame = cv2.imencode(".jpg", frame)
        if not ret:
            raise ValueError("编码失败！")
        bframe = frame.tobytes()
        return StreamingResponse(bframe, media_type="image/jpeg")

    @router.get("/cameras/{camera_id}/config")
    def _get_camera_params(self, camera_id: str):
        return self.contexts[camera_id]

    @router.post("/cameras/{camera_id}/config")
    def _change_camera_params(self, camera_id: str, item: ParamsModel):
        context = self.contexts[camera_id]
        context["params"] = item.model_dump()
        return context
