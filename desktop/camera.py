"""摄像头采集：OpenCV 只负责抓帧与编码，不进行任何人脸识别。"""

import base64
from datetime import datetime

import cv2


class CameraError(RuntimeError):
    """摄像头打开或抓帧失败。"""


class CameraCapture:
    def __init__(self, index: int = 0):
        self.index = index
        self._capture: cv2.VideoCapture | None = None

    def open(self) -> None:
        if self._capture is not None and self._capture.isOpened():
            return
        capture = cv2.VideoCapture(self.index, cv2.CAP_DSHOW)
        if not capture.isOpened():
            capture.release()
            raise CameraError("未检测到可用摄像头")
        self._capture = capture

    def read_frame(self):
        self.open()
        ok, frame = self._capture.read()
        if not ok or frame is None:
            raise CameraError("摄像头读取失败")
        return frame

    def read_data_url(self, quality: int = 85) -> str:
        frame = self.read_frame()
        ok, buffer = cv2.imencode(
            ".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality]
        )
        if not ok:
            raise CameraError("图片编码失败")
        encoded = base64.b64encode(buffer.tobytes()).decode("ascii")
        return f"data:image/jpeg;base64,{encoded}"

    def close(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *_):
        self.close()
