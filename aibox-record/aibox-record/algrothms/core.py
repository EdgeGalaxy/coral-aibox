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
        auto_recycle_threshold=2,
        enable=True,
    ):
        self._writer = None
        self.base_dir = base_dir
        self.record_interval = record_interval
        self._last_record_at = None
        self._auto_recycle_threshold = auto_recycle_threshold
        self._enable = enable
        os.makedirs(self.base_dir, exist_ok=True)
        # 启动后台清理程序, 每5分钟清理一次
        bg_tasks.add_job(self.auto_recycle, "interval", minutes=5)

    def write(
        self, frame: np.ndarray, objects: List[ObjectPayload], target_dir_name: str
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
            video_save_fp = os.path.join(
                save_dir, f"{now.strftime('%Y-%m-%d_%H:%M:%S')}.mp4"
            )
            self._writer = cv2.VideoWriter(
                video_save_fp,
                fourcc=cv2.VideoWriter_fourcc(*"mp4v"),
                fps=25,
                frameSize=(frame.shape[1], frame.shape[0]),
                isColor=True,
            )
            self._last_record_at = datetime.now()

        frame = self._draw_time_info(frame)
        frame = self._draw_person_rect(frame, objects)
        self._writer.write(frame)

    def auto_recycle(self):
        # 自动删除老数据，直到磁盘空间达到预期
        gb = 1024**3
        while True:
            _, _, free_b = shutil.disk_usage("/")
            # 当剩余空间小于指定阈值，触发删除逻辑，从最老的数据开始删除 （至少保留3个视频文件）
            if free_b < self._auto_recycle_threshold * gb:
                # 遍历相机目录，删除最老的文件
                _cameras_dir = os.listdir(self.base_dir)
                for _camera_dir in _cameras_dir:
                    _camera_dir_fp = os.path.join(self.base_dir, _camera_dir)
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

    def _resize(self, frame):
        h, w = frame.shape[:2]
        frame = cv2.resize(
            frame, (int(w * self.resize_rate[0]), int(h * self.resize_rate[1]))
        )
        return frame

    @staticmethod
    def _draw_time_info(frame):
        time_str = time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        frame = cv2.putText(
            frame,
            time_str,
            (20, 40),
            fontScale=1,
            fontFace=cv2.FONT_HERSHEY_SIMPLEX,
            color=(0, 0, 0),
            thickness=1,
            lineType=4,
        )
        return frame

    def _draw_person_rect(self, frame: np.ndarray, objects: List[ObjectPayload]):
        for obj in objects:
            x1, y1, x2, y2 = obj.box.x1, obj.box.y1, obj.box.x2, obj.box.y2
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), thickness=1)
        return frame
