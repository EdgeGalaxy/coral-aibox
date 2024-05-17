import os
import time
import platform

import cv2
import numpy as np
from loguru import logger

from .utils import get_import_meta


class FeatureData:
    def __init__(self, data: dict, db_path: str, db_size_threshold: int):
        self.db_size_threshold = db_size_threshold
        self.db_path = db_path
        self._data = data

    @classmethod
    def filter_files(cls, dir: str, suffix: str):
        return [os.path.join(dir, f) for f in os.listdir(dir) if f.endswith(suffix)]

    @classmethod
    def load(cls, db_path: str, db_size_threshold: int):
        # 创建文件夹
        if not os.path.exists(db_path):
            os.makedirs(db_path, mode=774, exist_ok=True)

        data = {}
        image_files = cls.filter_files(db_path, ".jpg")
        # for循环每个image，替换jpg为npy，判断是否存在该文件
        for image_file in image_files:
            key = os.path.splitext(os.path.basename(image_file))[0]
            feature_file = image_file.replace(".jpg", ".npy")
            if os.path.exists(feature_file):
                try:
                    data[key] = np.load(feature_file)
                except Exception as e:
                    logger.warning(f"load feature {key} error: {e}")

        logger.info(
            f"load {len(image_files)} images from {db_path}, init data size: {len(data)}"
        )
        return cls(data, db_path, db_size_threshold)

    @property
    def data(self):
        return self._data

    @property
    def size(self):
        return len(self.data)

    def add(self, key: str, image: np.ndarray, feature: np.ndarray):
        if self.size > self.db_size_threshold:
            logger.info(
                f"db has more than {self.db_size_threshold} fake persons, skip add!!!"
            )
            return

        self._data[key] = feature
        # 持久化
        cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 100])[1].tofile(
            os.path.join(self.db_path, key + ".jpg")
        )
        np.save(os.path.join(self.db_path, key + ".npy"), feature)

    def delete(self, key: str):
        if key in self.data:
            del self._data[key]
        # 删除
        try:
            os.remove(os.path.join(self.db_path, key + ".jpg"))
            os.remove(os.path.join(self.db_path, key + ".npy"))
        except Exception as e:
            logger.warning(f"delete feature {key} error: {e}")

    def prune(self):
        keys = list(self.data.keys())
        for key in keys:
            self.delete(key)


class FeatureDB:

    def __init__(
        self,
        width: int,
        height: int,
        weight_path: str,
        model_type: str,
        device_id: int,
        db_instance: FeatureData,
        use_preprocess: bool = True,
        sim_threshold: float = 0.9,
    ):
        meta = get_import_meta(model_type)
        self.model = meta.Classification(
            model_path=weight_path,
            input_height=height,
            input_width=width,
            use_preprocess=use_preprocess,
            device_id=device_id,
            swap=None if model_type == "rknn" else (2, 0, 1),
        )
        if platform.machine() == "x86_64" and model_type == "rknn":
            self.model.convert_and_load(
                quantize=False,
                dataset="feature_dataset.txt",
                is_hybrid=True,
                output_names=None,
                mean=[[123.675, 116.28, 103.53]],
                std=[[58.395, 57.12, 57.375]],
            )

        self.sim_threshold = sim_threshold

        self.db_instance = db_instance

    @classmethod
    def cosine_similarity(self, a, b):
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        # 计算b的每个列向量的范数
        norm_b = np.linalg.norm(b, axis=0)
        similarity = dot_product / (norm_a * norm_b)
        return similarity

    def get_fake_person_ids(self):
        return list(self.db_instance.data.keys())

    def delete_fake_person(self, person_id: str):
        self.db_instance.delete(person_id)

    def compare(self, feature: np.ndarray):
        if self.db_instance.size == 0:
            return False, 0

        index_cossims = self.cosine_similarity(
            feature, np.vstack(list(self.db_instance.data.values())).T
        )[0]
        s = np.argmax(index_cossims)
        above_threshold_indices = np.where(index_cossims > self.sim_threshold)[0]
        if index_cossims[s] > self.sim_threshold:
            logger.warning(
                f"matched fake person threshold: {index_cossims[s]} above max threshold {self.sim_threshold}"
            )
            return True, len(above_threshold_indices)

        return False, 0

    def predict(self, image: np.ndarray, save: bool = False) -> bool:
        st = time.time()
        feature = self.model.feature(image)
        et = time.time()
        matched, above_count = self.compare(feature)

        logger.debug(
            f"predict {matched} cost: {int((et - st) * 1000)} ms, feature compare cost: {int((time.time() - et) * 1000)} ms, feature count: {self.db_instance.size} "
        )

        # 需要保存且相似的素材数量不超过10张时再添加，避免加入过多相似的特征
        if save and above_count < 15:
            key = str(int(time.time() * 1000000))
            self.db_instance.add(key, image, feature)

        return True if not matched else False
