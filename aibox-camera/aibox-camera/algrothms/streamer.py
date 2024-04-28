import os
import threading
from collections import deque

import cv2
import numpy as np
from loguru import logger


MODEL_TYPE = os.environ.get("MODEL_TYPE", "onnx")


class VideoStreamer:
    def __init__(self, video_idx: str, width: int = None) -> None:
        if MODEL_TYPE == "rknn":
            self.streamer = VideoAHDStreamer(video_idx, width)
        else:
            self.streamer = VideoCv2Streamer(video_idx, width)

    def read(self):
        return self.streamer.read()


class VideoCv2Streamer:

    def __init__(self, video_idx: str, width: int = None):
        if video_idx.isdigit():
            video_idx = int(video_idx)
        self.cap = cv2.VideoCapture(video_idx)

        if width:
            ow = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            oh = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            scale = ow / width
            cw, ch = width, int(oh / scale)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, cw)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, ch)
            logger.info(f"video origin wh: {ow}x{oh} -> {cw}x{ch}")

        if not self.cap.isOpened():
            raise ValueError("can't open camera!")

    def read(self):
        return self.cap.read()


class VideoAHDStreamer:

    AHD_SRC = "v4l2src device=/dev/video{video_idx} ! video/x-raw,format=NV12,width={width},framerate=30/1 ! videoconvert n-threads=4 ! video/x-raw,format=BGR ! appsink name=sink emit-signals=True max-buffers=2 drop=True"
    AHD_SRC_NO_WH = "v4l2src device=/dev/video{video_idx} ! video/x-raw,format=NV12,framerate=30/1 ! videoconvert n-threads=4 ! video/x-raw,format=BGR ! appsink name=sink emit-signals=True max-buffers=2 drop=True"

    def __init__(self, video_idx: str, width: int = None):
        try:
            import gi
        except ModuleNotFoundError:
            raise ModuleNotFoundError(
                "Use MODEL_TYPE=rknn, GStreamer is not installed!"
            )

        gi.require_version("Gst", "1.0")
        from gi.repository import Gst

        # 初始化 GStreamer
        Gst.init(None)
        if not width:
            pipe = self.AHD_SRC_NO_WH.format(video_idx=video_idx)
        else:
            pipe = self.AHD_SRC.format(video_idx=video_idx, width=width)
        logger.info(f"gstreamer pipe: {pipe}")
        # 使用尽可能高效的管道设置
        self.pipeline = Gst.parse_launch(pipe)
        self.appsink = self.pipeline.get_by_name("sink")
        if self.appsink:
            self.appsink.connect("new-sample", self.on_new_sample)

        self.frame_queue = deque(maxlen=16)
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
        except IndexError:
            return False, None

    def run(self):
        threading.Thread(target=self._start_gstreamer_loop).start()

    def _start_gstreamer_loop(self):
        from gi.repository import Gst, GLib

        self.pipeline.set_state(Gst.State.PLAYING)
        loop = GLib.MainLoop()
        try:
            self._running = True
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
