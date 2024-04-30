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


def draw_mask(frame: np.ndarray, points: List[List[int]]):
    points = np.array(points, dtype=np.int32)
    cv2.polylines(frame, [points], isClosed=True, color=(255, 255, 255), thickness=2)
    # 创建一个与frame相同大小的遮罩层
    mask = np.zeros(frame.shape, dtype=np.uint8)
    cv2.fillPoly(mask, [points], (255, 255, 255))
    alpha = 0.3  # 半透明程度
    # 应用遮罩使得遮罩区域内的图像不变，外部区域半透明
    return cv2.addWeighted(mask, alpha, frame, 1 - alpha, 0, frame)


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
