"""
通过线程异步上报图片信息
"""

import os
import time
import threading
from collections import deque
from typing import Dict, List

import cv2
import requests
import numpy as np
from retry import retry
from loguru import logger
from coral import ObjectPayload, RawPayload
from coral.types.payload import Box
from requests.exceptions import ConnectionError


report_queue = deque(maxlen=1000)


class ImageSnapshotReport(threading.Thread):
    def __init__(self, url: str, report_image_dir: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.url = url
        self.report_image_dir = report_image_dir
        os.makedirs(self.report_image_dir, exist_ok=True)

    def run(self):
        logger.info(f"start report to server: {self.url}")
        while True:
            try:
                payload = report_queue.popleft()
                self.report(payload)
            except IndexError:
                # 队列不存在值
                time.sleep(0.1)
                continue
            except Exception as e:
                logger.warning(f"report error: {e}")
                time.sleep(0.05)
                continue

    def report(self, payload):
        raw_id, person_count, cameras = payload
        concat_image_fp = os.path.join(self.report_image_dir, f"{raw_id}.jpg")
        try:
            self.concat_image_save(cameras, concat_image_fp)
            self.report_to_server(raw_id, concat_image_fp)
        except Exception as e:
            logger.exception(
                f"uid: {raw_id} report count: {person_count} send failed: {e}!"
            )
        else:
            logger.debug(f"uid: {raw_id} report count: {person_count} send success!")
        finally:
            if os.path.exists(concat_image_fp):
                os.remove(concat_image_fp)

    @staticmethod
    def _resize_frame(frame: np.ndarray, resize_ratio: float):
        if resize_ratio and resize_ratio != 1:
            oh, ow = frame.shape[:2]
            frame = cv2.resize(frame, (int(ow * resize_ratio), int(oh * resize_ratio)))
        return frame

    @retry(ConnectionError, tries=2, delay=5)
    def report_to_server(self, raw_id: str, image_fp: str):
        with open(image_fp, "rb") as file:
            files = {"file": (image_fp, file)}
            data = {"name": raw_id}
            response = requests.post(self.url, files=files, data=data)
            if response.status_code != 200:
                raise ConnectionError(response.status_code)

    def concat_image_save(self, cameras: Dict[str, List], concat_image_fp: str):
        raws = []
        camera_ids = sorted(list(cameras.keys()))
        for camera_id in camera_ids:
            camera_payload: RawPayload = cameras[camera_id]
            count, objects, raw = (
                len(camera_payload.objects or []),
                camera_payload.objects,
                camera_payload.raw,
            )
            self._draw_camera_id(raw, camera_id, count)
            self._draw_person_rect(raw, objects)
            resize_raw = self._resize_frame(raw, 360 / raw.shape[0])
            raws.append(resize_raw)
        image = self._concatenate_images(raws)
        cv2.imwrite(concat_image_fp, image)

    @staticmethod
    def _draw_camera_id(frame: np.ndarray, camera_id: str, count: int):
        frame = cv2.putText(
            frame,
            f"CameraID: {camera_id} CrtCount: {count}",
            (20, 40),
            fontScale=0.7,
            fontFace=cv2.FONT_HERSHEY_SIMPLEX,
            color=(0, 0, 0),
            thickness=2,
        )
        return frame

    @staticmethod
    def _draw_infer_rect_text(
        image: np.ndarray,
        object: ObjectPayload,
        box_color=(0, 255, 0),
        label_color=(0, 0, 255),
    ):
        x1, y1, x2, y2 = object.box.x1, object.box.y1, object.box.x2, object.box.y2
        cv2.rectangle(image, (x1, y1), (x2, y2), box_color, 2)
        cv2.putText(
            image,
            str(object.prob),
            (x1, y1 - 10),
            fontScale=1,
            fontFace=cv2.FONT_HERSHEY_SIMPLEX,
            color=label_color,
            thickness=2,
        )

    def _draw_person_rect(self, frame: np.ndarray, objects: List[ObjectPayload]):
        for object in objects:
            # box为绿色框，label为绿色
            sub_objects = object.objects or []
            for sub_object in sub_objects:
                self._draw_infer_rect_text(
                    frame, sub_object, box_color=(0, 255, 0), label_color=(0, 255, 0)
                )

            # box为红色框，label为粉红色
            self._draw_infer_rect_text(
                frame, object, box_color=(0, 0, 255), label_color=(0, 0, 255)
            )

        return frame

    @staticmethod
    def add_border(
        image: np.ndarray, border_size: int = 1, border_color: tuple = (0, 255, 0)
    ):
        return cv2.copyMakeBorder(
            image,
            border_size,
            border_size,
            border_size,
            border_size,
            cv2.BORDER_CONSTANT,
            value=border_color,
        )

    @classmethod
    def _concatenate_images(cls, images: List[np.ndarray]):
        num_images = len(images)
        if num_images < 6:
            num_per_row = 2
        else:
            num_per_row = 3

        images_with_border = [cls.add_border(img) for img in images]

        # 获取每张图片的高度和宽度
        h, w = images_with_border[0].shape[:2]

        # 计算新图片的宽度和高度
        rows = (num_images + num_per_row - 1) // num_per_row  # 向上取整计算行数
        new_h = h * rows
        new_w = w * num_per_row

        # 创建一个全黑的画布
        new_image = np.zeros((new_h, new_w, 3), dtype=np.uint8)

        for idx, img in enumerate(images_with_border):
            row = idx // num_per_row
            col = idx % num_per_row
            new_image[row * h : (row + 1) * h, col * w : (col + 1) * w, :] = img

        return new_image


if __name__ == "__main__":
    payload = [
        "raw_idxxxx",
        2,
        {
            "ahd1": [
                1,
                [
                    ObjectPayload(
                        label="person",
                        box=Box(x1=0, y1=0, x2=100, y2=100),
                        prob=0.9,
                        class_id=0,
                    )
                ],
                np.ones((480, 720, 3), dtype=np.uint8) * 255,
                # ],
                # "ahd2": [
                #     1,
                #     [
                #         ObjectPayload(
                #             label="person",
                #             box=Box(x1=0, y1=0, x2=100, y2=100),
                #             prob=0.9,
                #             class_id=0,
                #         )
                #     ],
                #     np.ones((480, 720, 3), dtype=np.uint8) * 255,
                # ],
                # "ahd3": [
                #     1,
                #     [
                #         ObjectPayload(
                #             label="person",
                #             box=Box(x1=0, y1=0, x2=100, y2=100),
                #             prob=0.9,
                #             class_id=0,
                #         )
                #     ],
                #     np.ones((480, 720, 3), dtype=np.uint8) * 255,
                # ],
                # "ahd4": [
                #     1,
                #     [
                #         ObjectPayload(
                #             label="person",
                #             box=Box(x1=0, y1=0, x2=100, y2=100),
                #             prob=0.9,
                #             class_id=0,
                #         )
                #     ],
                #     np.ones((480, 720, 3), dtype=np.uint8) * 255,
                # ],
                # "ahd5": [
                #     1,
                #     [
                #         ObjectPayload(
                #             label="person",
                #             box=Box(x1=0, y1=0, x2=100, y2=100),
                #             prob=0.9,
                #             class_id=0,
                #         )
                #     ],
                #     np.ones((480, 720, 3), dtype=np.uint8) * 255,
                # ],
                # "ahd6": [
                #     1,
                #     [
                #         ObjectPayload(
                #             label="person",
                #             box=Box(x1=0, y1=0, x2=100, y2=100),
                #             prob=0.9,
                #             class_id=0,
                #         )
                #     ],
                #     np.ones((480, 720, 3), dtype=np.uint8) * 255,
            ],
        },
    ]
    report = ImageSnapshotReport(
        url="https://iot.lhehs.com/iot-api/resource/uploadNoAuthor",
        report_image_dir="report_image",
    )
    report.report(payload)
