"""Threaded webcam reader: always hands back the newest frame, no buffer lag."""
import os
import threading
import time

import cv2


class Camera:
    def __init__(self, index=0, width=640, height=480):
        backend = cv2.CAP_DSHOW if os.name == "nt" else cv2.CAP_ANY  # DSHOW is much faster on Windows
        cap = cv2.VideoCapture(index, backend)
        if not cap.isOpened():
            cap = cv2.VideoCapture(index)
        if not cap.isOpened():
            raise SystemExit("Could not open the webcam. Try CAM_INDEX = 1 in main.py.")
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))  # compressed = higher fps
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        cap.set(cv2.CAP_PROP_FPS, 30)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.cap = cap
        self._frame, self._id = None, 0
        self._lock = threading.Lock()
        self._running = True
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        while self._running:
            ok, frame = self.cap.read()
            if ok:
                with self._lock:
                    self._frame, self._id = frame, self._id + 1
            else:
                time.sleep(0.01)

    def read(self):
        """Return (frame_id, frame). frame is None until the first image arrives."""
        with self._lock:
            return self._id, self._frame

    def release(self):
        self._running = False
        time.sleep(0.05)
        self.cap.release()
