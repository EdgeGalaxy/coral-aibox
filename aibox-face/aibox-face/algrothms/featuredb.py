import os
import platform
from uuid import uuid4

import cv2
import numpy as np

from .utils import get_import_meta


class FeatureDB:

    def __init__(
        self,
        width: int,
        height: int,
        weigth_path: str,
        model_type: str,
        device_id: int,
        db_path: str,
        use_preprocess: bool = True,
        db_size: int = 1000,
        sim_threshold: float = 0.9,
    ):
        meta = get_import_meta(model_type)
        self.model = meta.FaceEmbedding(
            model_path=weigth_path,
            input_height=height,
            input_width=width,
            use_preprocess=use_preprocess,
            device_id=device_id,
        )
        if platform.machine() == "x86_64" and model_type == "rknn":
            self.model.convert_and_load(
                quantize=False,
                dataset="feature_dataset.txt",
                is_hybrid=True,
                output_names=None,
                mean=[[127.5, 127.5, 127.5]],
                std=[[127.5, 127.5, 127.5]],
            )

        self.db_path = db_path
        self.db_size = db_size
        self.sim_threshold = sim_threshold

        # pre load data save
        self.images = []
        self.features = []

        self.load()

    @classmethod
    def filter_files(cls, dir: str, suffix: str):
        return [os.path.join(dir, f) for f in os.listdir(dir) if f.endswith(suffix)]

    @classmethod
    def cosine_similarity(a, b):
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        similarity = dot_product / (norm_a * norm_b)
        return similarity

    def load(self):
        image_files = self.filter_files(self.db_path, ".jpg")
        # for循环每个image，替换jpg为npy，判断是否存在该文件
        for image_file in image_files:
            key = os.path.splitext(os.path.basename(image_file))[0]
            feature_file = image_file.replace(".jpg", ".npy")
            if os.path.exists(feature_file):
                self.images.append(key)
                self.features.append(np.load(feature_file))

    def compare(self, feature: np.ndarray):
        if len(self.features) == 0:
            return None

        index_cossims = self.cosine_similarity(feature, np.vstack(self.features).T)[0]
        s = np.argmax(index_cossims)
        if index_cossims[s] > self.sim_threshold:
            return self.images[s]

        return None

    def predict(self, image: np.ndarray, save=False) -> bool:
        feature = self.model.predict(image)
        match_key = self.compare(feature)
        if match_key:
            return match_key

        if save:
            self.save(image, feature)
        return True

    def save(self, image, feature):
        if len(self.features) > self.db_size:
            return

        key = str(uuid4())[:8]
        self.images.append(key)
        self.features.append(feature)

        os.makedirs(self.db_path, exist_ok=True)
        cv2.imencode(".jpg", image[:, :, ::-1], [cv2.IMWRITE_JPEG_QUALITY, 100])[
            1
        ].tofile(os.path.join(self.db_path, key + ".jpg"))
        np.save(os.path.join(self.db_path, key + ".npy"), feature)
