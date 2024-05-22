import atexit
import os
import time
import shutil
from typing import List
from datetime import datetime

import cv2
from loguru import logger
import numpy as np
from coral import ObjectPayload
from coral.sched import bg_tasks


class Recorder:
    """
    记录画面 滚动删除
    """

    def __init__(
        self,
        base_dir,
        record_interval=600,
        auto_recycle_threshold=5,
        enable=True,
    ):
        self._writer = None
        self.base_dir = base_dir
        self.record_interval = record_interval
        self._last_record_at = None
        self._auto_recycle_threshold = auto_recycle_threshold
        self._enable = enable
        os.makedirs(self.base_dir, exist_ok=True)
        atexit.register(self.release_writer)

    def release_writer(self):
        if self._writer:
            self._writer.release()
        logger.info("release writer")

    def write(
        self,
        frame: np.ndarray,
        objects: List[ObjectPayload],
        target_dir_name: str,
        person_count: int,
        report_timestamp: float,
        crt_fps: int = 5,
        resize_ratio: float = 0.5,
        points: List[List[int]] = [],
    ):
        if not self._enable:
            return

        save_dir = os.path.join(self.base_dir, target_dir_name)
        os.makedirs(save_dir, exist_ok=True)

        if frame.shape[0] * frame.shape[1] == 0:
            return

        now = datetime.now()
        if (
            not self._last_record_at
            or (now - self._last_record_at).seconds > self.record_interval
        ):
            # 释放上一个视频的writer
            self.release_writer()

            video_save_fp = os.path.join(
                save_dir, f"{now.strftime('%Y-%m-%d-%H-%M')}.mp4"
            )
            self._writer = cv2.VideoWriter(
                video_save_fp,
                fourcc=cv2.VideoWriter_fourcc(*"avc1"),
                apiPreference=cv2.CAP_FFMPEG,
                fps=crt_fps,
                frameSize=(frame.shape[1], frame.shape[0]),
                isColor=True,
            )
            logger.info(f"start write video: {video_save_fp}")
            self._last_record_at = datetime.now()

        frame = self._draw_time_info(frame, report_timestamp, person_count)
        frame = self._draw_person_rect(frame, objects)
        if points:
            frame = self._draw_mask(frame, points)
        frame = self._resize_frame(frame, resize_ratio=resize_ratio)
        self._writer.write(frame)

    @classmethod
    def auto_recycle(cls, base_dir: str, recycle_threshold: int = 5):
        # 自动删除老数据，直到磁盘空间达到预期
        gb = 1024**3
        _, _, free_b = shutil.disk_usage("/")
        logger.info(
            f"start auto recycle. dir: {base_dir}, threshold: {recycle_threshold}GB , crt free: {free_b / gb}GB"
        )
        while True:
            # 当剩余空间小于指定阈值，触发删除逻辑，从最老的数据开始删除 （至少保留3个视频文件）
            if free_b < recycle_threshold * gb:
                # 遍历相机目录，删除最老的文件
                _cameras_dir = os.listdir(base_dir)
                for _camera_dir in _cameras_dir:
                    _camera_dir_fp = os.path.join(base_dir, _camera_dir)
                    if os.path.isdir(_camera_dir_fp):
                        _camera_video_fns = sorted(os.listdir(_camera_dir_fp))
                        if not len(_camera_video_fns) > 3:
                            continue
                        _camera_video_fns.sort()
                        _target_fp = os.path.join(_camera_dir_fp, _camera_video_fns[0])
                        os.remove(_target_fp)
                        logger.info(f"auto delete success. remove file: {_target_fp}")
                        time.sleep(1)
            else:
                break
        _, _, done_free_b = shutil.disk_usage("/")
        logger.info(f"auto recycle done. crt free: {done_free_b / gb}GB")

    @staticmethod
    def _draw_time_info(frame: np.ndarray, report_timestamp: float, person_count: int):
        time_str = datetime.fromtimestamp(report_timestamp).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        frame = cv2.putText(
            frame,
            f"Total Person: {person_count}  Time: {time_str}",
            (20, 40),
            fontScale=1,
            fontFace=cv2.FONT_HERSHEY_SIMPLEX,
            color=(0, 0, 0),
            thickness=1,
            lineType=4,
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
            object.label,
            (x1, y1 - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            label_color,
            2,
        )

    @staticmethod
    def _resize_frame(frame: np.ndarray, resize_ratio: float):
        if resize_ratio and resize_ratio != 1:
            oh, ow = frame.shape[:2]
            frame = cv2.resize(frame, (int(ow * resize_ratio), int(oh * resize_ratio)))
        return frame

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
                frame, object, box_color=(0, 0, 255), label_color=(255, 192, 203)
            )

        return frame

    def _draw_mask(self, frame: np.ndarray, points: List[List[int]]):
        points = np.array(points, dtype=np.int32)
        cv2.polylines(
            frame, [points], isClosed=True, color=(255, 255, 255), thickness=2
        )
        # 创建一个与frame相同大小的遮罩层
        mask = np.zeros_like(frame, dtype=np.uint8)
        cv2.fillPoly(mask, [points], (255, 255, 255))
        alpha = 0.3  # 半透明程度
        # 应用遮罩使得遮罩区域内的图像不变，外部区域半透明
        return cv2.addWeighted(mask, alpha, frame, 1 - alpha, 0, frame)
