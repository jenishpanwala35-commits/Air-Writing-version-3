"""Hand tracking using the MediaPipe Tasks API (works with mediapipe >= 0.10.30)."""
import os
import urllib.request

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/hand_landmarker.task"
)
MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hand_landmarker.task")

# Standard 21-point hand skeleton
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20),
    (0, 17),
]


def _ensure_model():
    if not os.path.exists(MODEL_PATH):
        print("Downloading hand landmark model (one time, ~8 MB)...")
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        print("Done.")


class HandTracker:
    INDEX_TIP = 8
    # (tip, pip) landmark pairs for index, middle, ring, pinky
    FINGERS = [(8, 6), (12, 10), (16, 14), (20, 18)]

    def __init__(self, detection_conf=0.7, tracking_conf=0.6):
        _ensure_model()
        options = vision.HandLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=MODEL_PATH),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=1,
            min_hand_detection_confidence=detection_conf,
            min_hand_presence_confidence=tracking_conf,
            min_tracking_confidence=tracking_conf,
        )
        self.landmarker = vision.HandLandmarker.create_from_options(options)
        self._last_ts = 0

    def process(self, frame_bgr, timestamp_ms):
        """Return the list of 21 landmarks for the first hand, or None."""
        # timestamps must be strictly increasing
        timestamp_ms = max(int(timestamp_ms), self._last_ts + 1)
        self._last_ts = timestamp_ms
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self.landmarker.detect_for_video(image, timestamp_ms)
        return result.hand_landmarks[0] if result.hand_landmarks else None

    def fingers_up(self, lm):
        """[index, middle, ring, pinky] -> True if finger is extended."""
        return [lm[tip].y < lm[pip].y for tip, pip in self.FINGERS]

    def index_tip(self, lm, width, height):
        p = lm[self.INDEX_TIP]
        return int(p.x * width), int(p.y * height)

    def draw(self, frame, lm):
        h, w = frame.shape[:2]
        pts = [(int(p.x * w), int(p.y * h)) for p in lm]
        for a, b in HAND_CONNECTIONS:
            cv2.line(frame, pts[a], pts[b], (0, 255, 0), 2)
        for p in pts:
            cv2.circle(frame, p, 4, (0, 0, 255), -1)

    def close(self):
        self.landmarker.close()
