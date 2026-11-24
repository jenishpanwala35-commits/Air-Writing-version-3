"""Camera filters + brightness. Everything is done with one fast lookup table."""
import cv2
import numpy as np

FILTERS = ["Normal", "Warm", "Cool", "Sepia", "B&W", "Vivid"]

_GAINS = {                      # (B, G, R) multipliers
    "Warm": (0.80, 1.00, 1.20),
    "Cool": (1.20, 1.00, 0.80),
}
_SEPIA = np.array([[0.272, 0.534, 0.131],
                   [0.349, 0.686, 0.168],
                   [0.393, 0.769, 0.189]], dtype=np.float32)
_cache = {}


def _lut(name, brightness):
    key = (name, brightness)
    if key not in _cache:
        x = np.arange(256, dtype=np.float32)
        contrast = 1.3 if name == "Vivid" else 1.0
        chans = []
        for gain in _GAINS.get(name, (1.0, 1.0, 1.0)):
            y = ((x - 128) * contrast + 128) * gain + brightness
            chans.append(np.clip(y, 0, 255).astype(np.uint8))
        _cache[key] = np.stack(chans, axis=-1).reshape(256, 1, 3)
    return _cache[key]


def apply(frame, filter_index, brightness):
    """Return the frame with the chosen filter and brightness (-100..100)."""
    name = FILTERS[filter_index]
    if name == "B&W":
        frame = cv2.cvtColor(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR)
    elif name == "Sepia":
        frame = cv2.transform(frame, _SEPIA)
    if name == "Normal" and brightness == 0:
        return frame
    return cv2.LUT(frame, _lut(name, int(brightness)))
