import os
import shutil
import platform
from io import BytesIO
from uuid import uuid4
from typing import List, Dict
from collections import defaultdict

import cv2
import requests
from loguru import logger
from PIL import Image
import numpy as np

from .utils import get_import_meta


class FeatureDB:

    def __init__(
        self,
        width: int,
        height: int,
        weight_path: str,
        model_type: str,
        device_id: int,
        db_path: str,
        use_preprocess: bool = True,
        user_faces_size: int = 10,
        sim_threshold: float = 0.9,
    ):
        meta = get_import_meta(model_type)
        self.model = meta.FaceEmbedding(
            model_path=weight_path,
            input_height=height,
            input_width=width,
            use_preprocess=use_preprocess,
            device_id=device_id,
            mean=None if model_type == "rknn" else [127.5, 127.5, 127.5],
            std=None if model_type == "rknn" else [127.5, 127.5, 127.5],
            swap=None if model_type == "rknn" else (2, 0, 1),
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
        self.user_faces_size = user_faces_size
        self.sim_threshold = sim_threshold

        # pre load data save
        self.images = []
        self.features = []
        self.mapper = {}
        # load users
        self.load_users()

    @classmethod
    def filter_files(cls, dir: str, suffix: str):
        return [os.path.join(dir, f) for f in os.listdir(dir) if f.endswith(suffix)]

    @classmethod
    def cosine_similarity(self, a, b):
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        similarity = dot_product / (norm_a * norm_b)
        return similarity

    def load_users(self):
        for user_id in os.listdir(self.db_path):
            self.load_user(user_id)

    def load_user(self, user_id):
        image_files = self.filter_files(os.path.join(self.db_path, user_id), ".jpg")
        # for循环每个image，替换jpg为npy，判断是否存在该文件
        for image_file in image_files:
            key = os.path.splitext(os.path.basename(image_file))[0]
            feature_file = image_file.replace(".jpg", ".npy")
            if os.path.exists(feature_file):
                self.images.append(key)
                self.features.append(np.load(feature_file))
                self.mapper[key] = user_id

    def show_users_faces(self):
        users = defaultdict(list)
        for face_key, user_id in self.mapper.items():
            users[user_id].append(face_key)
        return users

    @property
    def user_ids(self):
        return set(self.mapper.values())

    def remark_user_id(self, mark_user_id: str, old_user_id: str):
        if mark_user_id in self.user_ids:
            raise ValueError(f"{mark_user_id} already exists!")

        keys = [key for key, value in self.mapper.items() if value == old_user_id]
        for key in keys:
            self.mapper[key] = mark_user_id

        user_dir = os.path.join(self.db_path, old_user_id)
        # 重命名user_dir
        shutil.move(user_dir, os.path.join(self.db_path, mark_user_id))
        return True

    def move_face_to_user_id(self, key: str, user_id: str):
        old_user_id = self.mapper.get(key, None)
        if not old_user_id:
            logger.warning(f"key {key} not exists!")
            return False
        # 更新mapper
        self.mapper[key] = user_id
        # 移动key对应的文件
        shutil.move(
            os.path.join(self.db_path, old_user_id, key + ".jpg"),
            os.path.join(self.db_path, user_id, key + ".jpg"),
        )
        shutil.move(
            os.path.join(self.db_path, old_user_id, key + ".npy"),
            os.path.join(self.db_path, user_id, key + ".npy"),
        )
        return True

    def delete_user_faces(self, user_id: str, face_key: str):
        del self.mapper[face_key]
        # 删除key对应的文件
        os.remove(os.path.join(self.db_path, user_id, face_key + ".jpg"))
        os.remove(os.path.join(self.db_path, user_id, face_key + ".npy"))
        return True

    def update_user_date_from_remote(self, user_id: str, faces: List[Dict]):
        """
        更新用户面部数据，从远程获取

        :param user_id:
        :param faces:
        """
        for face in faces:
            try:
                face_key = face["face_key"]
                image_resp = requests.get(face["image"])
                # 将图像数据转换为OpenCV图像
                image = Image.open(BytesIO(image_resp.content))
                image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
                # 向量数据
                vector_resp = requests.get(face["vector"])
                vector = np.array(np.frombuffer(vector_resp.content))
            except Exception as e:
                logger.error(f"update user {user_id} face {face_key} error {e}!")
            else:
                self.save(image, vector, user_id, face_key)

    def delete_user(self, user_id: str):
        if user_id in self.user_ids:
            faces = [key for key, value in self.mapper.items() if value == user_id]
            for face in faces:
                del self.mapper[face]
            shutil.rmtree(os.path.join(self.db_path, user_id))

        return True

    def compare(self, feature: np.ndarray):
        if len(self.features) == 0:
            return None

        index_cossims = self.cosine_similarity(feature, np.vstack(self.features).T)[0]
        # 找出最大的相似度
        s = np.argmax(index_cossims)
        if index_cossims[s] > self.sim_threshold:
            max_similar_key = self.images[s]
            # 找出最大相似度的索引, 根据索引获取用户ID
            user_id = self.mapper.get(max_similar_key, None)
            return user_id

        return ""

    def predict(self, image: np.ndarray, save: bool = False) -> str:
        feature = self.model.predict(image)
        user_id = self.compare(feature)

        if save:
            self.save(image, feature, user_id)
        return user_id if user_id else "UNKNOWN"

    def save(
        self,
        image: np.ndarray,
        feature: np.ndarray,
        user_id: str = None,
        face_key: str = None,
    ):
        # if len(self.features) > self.db_size:
        #     logger.warning(f"db has more than {self.db_size} faces!")
        #     return

        if not user_id:
            # 默认的用户ID
            user_id = f"UNKNOWN_{str(uuid4())[:8]}"

        user_dir = os.path.join(self.db_path, user_id)
        # 存储用户特征到对应的User Dir
        os.makedirs(user_dir, exist_ok=True)

        # 判断是否超过单用户最大人脸数
        if (
            len(
                [
                    face_fn
                    for face_fn in os.listdir(user_dir)
                    if face_fn.endswith(".jpg")
                ]
            )
            > self.user_faces_size
        ):
            logger.warning(
                f"user {user_id} has more than {self.user_faces_size} faces!"
            )
            return

        key = face_key if face_key else str(uuid4())[:8]
        self.images.append(key)
        self.features.append(feature)
        self.mapper[key] = user_id

        logger.info(f"save user {user_id} face {key} to {user_dir}")

        cv2.imencode(".jpg", image[:, :, ::-1], [cv2.IMWRITE_JPEG_QUALITY, 100])[
            1
        ].tofile(os.path.join(user_dir, key + ".jpg"))
        np.save(os.path.join(user_dir, key + ".npy"), feature)
