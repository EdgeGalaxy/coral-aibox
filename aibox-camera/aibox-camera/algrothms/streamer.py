import os
import threading
from collections import deque

import cv2
import numpy as np
from loguru import logger


MODEL_TYPE = os.environ.get("MODEL_TYPE", "onnx")


class VideoStreamer:
    def __init__(self, video_idx: str, width: int, height: int) -> None:
        if MODEL_TYPE == "rknn":
            self.streamer = VideoAHDStreamer(video_idx, width, height)
        else:
            self.streamer = VideoCv2Streamer(video_idx, width, height)

    def read(self):
        return self.streamer.read()


class VideoCv2Streamer:

    def __init__(self, video_idx: str, width: int, height: int):
        if video_idx.isdigit():
            video_idx = int(video_idx)
        self.cap = cv2.VideoCapture(video_idx)

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

        if not self.cap.isOpened():
            raise ValueError("can't open camera!")

    def read(self):
        return self.cap.read()


class VideoAHDStreamer:

    AHD_SRC = "v4l2src device={video_idx} ! video/x-raw,format=YUY2,width={width},height={height},framerate=30/1 ! appsink name=sink"

    def __init__(self, video_idx: str, width: int, height: int):
        import gi

        gi.require_version("Gst", "1.0")
        from gi.repository import Gst

        # 初始化 GStreamer
        Gst.init(None)

        pipe = self.AHD_SRC.format(video_idx=video_idx, width=width, height=height)
        # 使用尽可能高效的管道设置
        self.pipeline = Gst.parse_launch(pipe)
        self.appsink = self.pipeline.get_by_name("sink")
        if self.appsink:
            self.appsink.connect("new-sample", self.on_new_sample)

        self.frame_queue = deque(maxlen=16)
        self._running = True
        # 自动运行后台线程
        self.run()

    def on_new_sample(self, sink):
        from gi.repository import Gst

        # 处理帧
        sample = sink.emit("pull-sample")
        if sample:
            buffer = sample.get_buffer()
            caps = sample.get_caps()
            height = caps.get_structure(0).get_value("height")
            width = caps.get_structure(0).get_value("width")
            success, map_info = buffer.map(Gst.MapFlags.READ)
            if success:
                frame = np.ndarray(
                    shape=(height, width, 3), dtype=np.uint8, buffer=map_info.data
                )
                # 添加
                self.frame_queue.append(frame.copy())
                buffer.unmap(map_info)
            return Gst.FlowReturn.OK
        return Gst.FlowReturn.ERROR

    def read(self):
        try:
            return True, self.frame_queue.popleft()
        except TypeError:
            return False, None

    def run(self):
        threading.Thread(target=self._start_gstreamer_loop).start()

    def _start_gstreamer_loop(self):
        from gi.repository import Gst, GLib

        self.pipeline.set_state(Gst.State.PLAYING)
        loop = GLib.MainLoop()
        try:
            loop.run()
        except KeyboardInterrupt:
            logger.warning("Stopping... ")
            # 停止
            loop.quit()
        finally:
            self.pipeline.set_state(Gst.State.NULL)
            self._running = False

    def is_running(self):
        return self._running
