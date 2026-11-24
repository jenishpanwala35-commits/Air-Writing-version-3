"""Stroke-based drawing layer. Strokes are the source of truth, so erase/undo
work per stroke and the same data can be sent to the handwriting recogniser."""
import os
import time

import cv2
import numpy as np


class AirCanvas:
    MIN_STEP = 2  # ignore points closer than this (px) - removes jitter

    def __init__(self, width, height):
        self.w, self.h = width, height
        self.layer = np.zeros((height, width, 3), dtype=np.uint8)
        self.color = (255, 80, 0)  # BGR
        self.thickness = 4
        self.strokes = []   # each: {"color", "th", "pts": [(x, y, t_ms), ...]}
        self.current = None
        self.prev = None

    # ---- drawing --------------------------------------------------------
    def add_point(self, pt, t_ms):
        if self.current is None:
            self.current = {"color": self.color, "th": self.thickness, "pts": []}
            self.strokes.append(self.current)
            self.prev = None
        if self.prev is not None:
            if abs(pt[0] - self.prev[0]) + abs(pt[1] - self.prev[1]) < self.MIN_STEP:
                return
            cv2.line(self.layer, self.prev, pt, self.current["color"], self.current["th"], cv2.LINE_AA)
        self.current["pts"].append((pt[0], pt[1], t_ms))
        self.prev = pt

    def end_stroke(self):
        """Finish the current stroke. Returns True if a real stroke was completed."""
        if self.current is None:
            return False
        stroke, self.current, self.prev = self.current, None, None
        if len(stroke["pts"]) < 3:      # accidental flick -> discard
            self.strokes.remove(stroke)
            self._render()
            return False
        return True

    def erase_at(self, pt, radius=30):
        """Remove every stroke touched by the eraser. Returns True if anything changed."""
        r2 = radius * radius
        keep = [s for s in self.strokes
                if not any((x - pt[0]) ** 2 + (y - pt[1]) ** 2 <= r2 for x, y, _ in s["pts"])]
        if len(keep) == len(self.strokes):
            return False
        self.strokes = keep
        self._render()
        return True

    def undo(self):
        if self.strokes:
            self.strokes.pop()
            self._render()

    def clear(self):
        self.strokes, self.current, self.prev = [], None, None
        self.layer[:] = 0

    def change_thickness(self, delta):
        self.thickness = int(np.clip(self.thickness + delta, 2, 20))

    def _render(self):
        self.layer[:] = 0
        for s in self.strokes:
            pts = np.array([(x, y) for x, y, _ in s["pts"]], dtype=np.int32)
            cv2.polylines(self.layer, [pts], False, s["color"], s["th"], cv2.LINE_AA)

    # ---- output ---------------------------------------------------------
    def ink(self):
        """Strokes in the format the handwriting recogniser expects."""
        strokes = [s for s in self.strokes if s["pts"]]
        if not strokes:
            return []
        t0 = strokes[0]["pts"][0][2]
        return [[[p[0] for p in s["pts"]],
                 [p[1] for p in s["pts"]],
                 [int(p[2] - t0) for p in s["pts"]]] for s in strokes]

    def overlay_on(self, frame):
        mask = self.layer.any(axis=2)
        out = frame.copy()
        out[mask] = self.layer[mask]
        return out

    def save(self, folder="output"):
        os.makedirs(folder, exist_ok=True)
        page = np.full((self.h, self.w), 255, dtype=np.uint8)
        page[self.layer.any(axis=2)] = 0
        path = os.path.join(folder, f"airwriting_{time.strftime('%Y%m%d_%H%M%S')}.png")
        cv2.imwrite(path, page)
        return path
