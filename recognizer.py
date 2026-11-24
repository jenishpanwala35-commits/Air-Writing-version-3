"""Live handwriting recognition in a background thread (never blocks the camera).

Uses Google's online handwriting-input endpoint, which takes pen strokes
(x, y, time) directly - far more accurate than OCR on a picture.
It is an unofficial endpoint, so it needs internet and could change.
"""
import json
import threading
import urllib.request

URL = "https://inputtools.google.com/request?itc=en-t-i0-handwrit&app=demopage"


class LiveRecognizer:
    def __init__(self, language="en"):
        self.language = language
        self.text = ""          # latest recognised text
        self.status = "idle"    # idle | thinking | ok | error: ...
        self._pending = None
        self._gen = 0
        self._cond = threading.Condition()
        threading.Thread(target=self._run, daemon=True).start()

    def request(self, ink, width, height):
        with self._cond:
            self._gen += 1
            if not ink:
                self.text, self.status, self._pending = "", "idle", None
                return
            self._pending = (self._gen, ink, width, height)
            self.status = "thinking"
            self._cond.notify()

    def reset(self):
        with self._cond:
            self._gen += 1
            self.text, self.status, self._pending = "", "idle", None

    def _recognize(self, ink, width, height):
        body = json.dumps({
            "options": "enable_pre_space",
            "requests": [{
                "writing_guide": {"writing_area_width": width, "writing_area_height": height},
                "ink": ink,
                "language": self.language,
            }],
        }).encode("utf-8")
        req = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if data[0] != "SUCCESS":
            raise RuntimeError(str(data[0]))
        return data[1][0][1][0].strip()

    def _run(self):
        while True:
            with self._cond:
                while self._pending is None:
                    self._cond.wait()
                gen, ink, w, h = self._pending
                self._pending = None
            try:
                result, err = self._recognize(ink, w, h), None
            except Exception as e:  # network down, timeout, etc.
                result, err = None, str(e)[:40]
            with self._cond:
                if gen != self._gen:      # a newer request/reset happened - drop stale result
                    continue
                if err:
                    self.status = "error: " + err
                else:
                    self.text, self.status = result, "ok"
