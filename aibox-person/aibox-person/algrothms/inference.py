import platform
from typing import List

import cv2
from loguru import logger
import numpy as np

from .featuredb import FeatureDB
from .utils import get_import_meta


class Inference:
    def __init__(
        self,
        featuredb: FeatureDB,
        width: int,
        height: int,
        weight_path: str,
        model_type: str,
        device_id: int,
        class_names: List[str] = ["person"],
        nms_thresh: float = 0.6,
        use_preprocess: bool = True,
        confidence_thresh: float = 0.4,
    ):
        meta = get_import_meta(model_type)
        self.model = meta.Detection(
            model_path=weight_path,
            input_height=height,
            input_width=width,
            use_preprocess=use_preprocess,
            device_id=device_id,
            class_names=class_names,
            nms_thresh=nms_thresh,
            confidence_thresh=confidence_thresh,
            pad=True,
            normal=None if model_type == "rknn" else True,
            swap=None if model_type == "rknn" else (2, 0, 1),
        )
        if platform.machine() == "x86_64" and model_type == "rknn":
            self.model.convert_and_load(
                quantize=False,
                dataset="det_dataset.txt",
                is_hybrid=True,
                output_names=None,
                mean=[[0, 0, 0]],
                std=[[255, 255, 255]],
            )

        self.featuredb = featuredb

    def predict(self, image: np.ndarray, is_record: bool = False):
        defects = []
        dets, det_scores, det_labels = self.model.predict(image)
        for det, conf, cls in zip(dets[0], det_scores[0], det_labels[0]):
            try:
                xmin, ymin, xmax, ymax = det
                person_img = image[ymin : ymax + 1, xmin : xmax + 1]
                # 正常模式下，如果背景特征库为空时，不调用特征匹配
                if len(self.featuredb.fake_persons_features) == 0 and not is_record:
                    is_person = True
                else:
                    # todo 先匹配坐标IOU
                    is_person = self.featuredb.predict(person_img, is_record)

                # 过滤掉特征匹配到的错误人物数据
                if not is_person:
                    continue

                defect = {
                    "label": (self.model.class_names[int(cls)]),
                    "class_id": int(cls),
                    "prob": round(float(conf), 4),
                    "box": {
                        "x1": xmin,
                        "y1": ymin,
                        "x2": xmax,
                        "y2": ymax,
                    },
                }
                defects.append(defect)
            except Exception as e:
                logger.exception(f"person predict error: {e}")

        return defects
