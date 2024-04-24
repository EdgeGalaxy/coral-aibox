import platform
from typing import List

from loguru import logger
import numpy as np
from metacv import Face as F
from coral.types.payload import Box

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
        nms_thresh: float = 0.4,
        use_preprocess: bool = True,
        confidence_thresh: float = 0.5,
    ):
        meta = get_import_meta(model_type)
        self.model = meta.FaceDetection(
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
            mean=None if model_type == "rknn" else [0.485, 0.456, 0.406],
            std=None if model_type == "rknn" else [0.229, 0.224, 0.225],
            swap=None if model_type == "rknn" else (2, 0, 1),
        )
        if platform.machine() == "x86_64" and model_type == "rknn":
            self.model.convert_and_load(
                quantize=False,
                dataset="det_dataset.txt",
                is_hybrid=True,
                output_names=None,
                mean=[[123.675, 116.28, 103.53]],
                std=[[58.395, 57.12, 57.375]],
            )

        self.featuredb = featuredb

    def predict(self, image: np.ndarray, box: Box, is_record: bool = False):
        defects = []
        dets, det_scores, det_kpss = self.model.predict(image)
        for det, conf, kps in zip(dets[0], det_scores[0], det_kpss[0]):
            try:
                xmin, ymin, xmax, ymax = det
                face_img = F.norm_crop(image, np.array(kps))
                # 正常模式下，如果背景特征库为空时，不调用特征匹配
                if len(self.featuredb.features) == 0 and not is_record:
                    user_id = "UNKNOWN"
                else:
                    user_id = self.featuredb.predict(face_img, is_record)

                defect = {
                    "label": (
                        user_id if not user_id.startswith("UNKNOWN") else "UNKNOWN"
                    ),
                    "class_id": 0,
                    "prob": round(float(conf), 4),
                    "box": {
                        "x1": box.x1 + xmin,
                        "y1": box.y1 + ymin,
                        "x2": box.x1 + xmax,
                        "y2": box.y1 + ymax,
                    },
                }
                defects.append(defect)
            except Exception as e:
                logger.warning(f"face predict error: {e}")

        return defects
