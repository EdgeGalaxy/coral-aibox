import socket
from typing import List

import cv2
import numpy as np
from coral import ObjectPayload


def get_import_meta(model_type: str):
    if model_type == "rt":
        import metart as meta
    elif model_type == "rknn":
        import metarknn as meta
    elif model_type == "onnx":
        import metaonnx as meta
    else:
        raise ValueError(f"未知的模型类型: {model_type}")
    return meta


def get_internal_ip():
    try:
        # 创建一个socket对象
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        ip_address = s.getsockname()[0]
        s.close()
    except OSError:
        ip_address = ""
    return ip_address


def draw_image_with_boxes(
    image: np.ndarray, objects: List[ObjectPayload], delay_time: float, fps: int
):
    # 基于objects的box和label在图像上画对应的框和label标记
    def _draw(
        image: np.ndarray,
        object: ObjectPayload,
        box_color=(0, 255, 0),
        label_color=(0, 0, 255),
    ):
        x1, y1, x2, y2 = object.box.x1, object.box.y1, object.box.x2, object.box.y2
        cv2.rectangle(image, (x1, y1), (x2, y2), box_color, 2)
        cv2.putText(
            image,
            object.label,
            (x1, y1 - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            label_color,
            2,
        )

    # 为图片右上角添加延时的时间标志
    cv2.putText(
        image,
        f"delay: {delay_time} ms fps: {fps}",
        (10, 20),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (0, 0, 255),
        2,
    )

    for object in objects:
        # box为绿色框，label为绿色
        sub_objects = object.objects or []
        for sub_object in sub_objects:
            _draw(image, sub_object, box_color=(0, 255, 0), label_color=(0, 255, 0))

        # box为红色框，label为粉红色
        _draw(image, object, box_color=(0, 0, 255), label_color=(255, 192, 203))

    return image


INTERNAL_IP = get_internal_ip()
BASE_URL = f"http://{INTERNAL_IP}:8030"
