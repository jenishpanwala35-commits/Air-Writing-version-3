"""On-screen controls: 20-colour palette, filter buttons, brightness slider, subtitle."""
import cv2
from look import FILTERS

HEADER_H, LEFT_W, RIGHT_W, BAR_H, BTN_H, COLS = 60, 64, 44, 80, 44, 10
FILTER_Y0 = HEADER_H + 30


def _rgb(r, g, b):
    return (b, g, r)


PALETTE = [  # 20 colours (name, BGR). "Black" is near-black so it still counts as ink.
    ("Red", _rgb(230, 25, 25)), ("Orange", _rgb(255, 128, 0)), ("Amber", _rgb(255, 191, 0)),
    ("Yellow", _rgb(255, 235, 0)), ("Lime", _rgb(170, 255, 0)), ("Green", _rgb(0, 200, 60)),
    ("Teal", _rgb(0, 160, 150)), ("Cyan", _rgb(0, 220, 255)), ("Sky", _rgb(80, 170, 255)),
    ("Blue", _rgb(30, 80, 255)), ("Indigo", _rgb(75, 0, 200)), ("Purple", _rgb(150, 50, 220)),
    ("Magenta", _rgb(230, 0, 200)), ("Pink", _rgb(255, 100, 170)), ("Rose", _rgb(255, 160, 160)),
    ("Brown", _rgb(130, 80, 40)), ("Maroon", _rgb(128, 0, 32)), ("Gray", _rgb(140, 140, 140)),
    ("White", _rgb(255, 255, 255)), ("Black", _rgb(12, 12, 12)),
]


# ---------- hit tests (finger position -> control) ------------------------
def slider_top():
    return HEADER_H + 34


def slider_bottom(h):
    return h - BAR_H - 24


def in_writing(x, y, w, h):
    return LEFT_W <= x < w - RIGHT_W and HEADER_H < y < h - BAR_H


def hit_color(x, y, w):
    if y >= HEADER_H:
        return None
    col = min(x // (w // COLS), COLS - 1)
    row = 0 if y < HEADER_H // 2 else 1
    return min(row * COLS + col, len(PALETTE) - 1)


def hit_filter(x, y):
    if x < LEFT_W and FILTER_Y0 <= y < FILTER_Y0 + BTN_H * len(FILTERS):
        return (y - FILTER_Y0) // BTN_H
    return None


def hit_brightness(x, y, w, h):
    top, bottom = slider_top(), slider_bottom(h)
    if x >= w - RIGHT_W and top - 12 <= y <= bottom + 12:
        frac = min(max((bottom - y) / (bottom - top), 0.0), 1.0)
        return int(round((frac * 200 - 100) / 5) * 5)
    return None


# ---------- drawing ---------------------------------------------------------
def draw_ui(out, color_idx, filter_idx, brightness, words, live, status, info):
    h, w = out.shape[:2]
    font = cv2.FONT_HERSHEY_SIMPLEX

    # translucent panels (one blend for all)
    shade = out.copy()
    cv2.rectangle(shade, (0, HEADER_H), (LEFT_W, FILTER_Y0 + BTN_H * len(FILTERS) + 6), (0, 0, 0), -1)
    cv2.rectangle(shade, (w - RIGHT_W, HEADER_H), (w, h - BAR_H), (0, 0, 0), -1)
    cv2.rectangle(shade, (0, h - BAR_H), (w, h), (0, 0, 0), -1)
    cv2.addWeighted(shade, 0.6, out, 0.4, 0, out)

    # palette: 2 rows x 10
    bw, bh = w // COLS, HEADER_H // 2
    for i, (_, c) in enumerate(PALETTE):
        r, col = divmod(i, COLS)
        x1, y1 = col * bw, r * bh
        cv2.rectangle(out, (x1, y1), (x1 + bw, y1 + bh), c, -1)
        cv2.rectangle(out, (x1, y1), (x1 + bw, y1 + bh), (40, 40, 40), 1)
        if i == color_idx:
            cv2.rectangle(out, (x1 + 2, y1 + 2), (x1 + bw - 2, y1 + bh - 2), (255, 255, 255), 2)
            cv2.rectangle(out, (x1 + 4, y1 + 4), (x1 + bw - 4, y1 + bh - 4), (0, 0, 0), 1)

    # filter buttons (left)
    cv2.putText(out, "FILTER", (8, HEADER_H + 20), font, 0.45, (200, 200, 200), 1, cv2.LINE_AA)
    for i, name in enumerate(FILTERS):
        y1 = FILTER_Y0 + i * BTN_H
        active = i == filter_idx
        if active:
            cv2.rectangle(out, (3, y1 + 2), (LEFT_W - 3, y1 + BTN_H - 2), (0, 230, 255), 2)
        cv2.putText(out, name, (8, y1 + 28), font, 0.5,
                    (0, 230, 255) if active else (255, 255, 255), 1, cv2.LINE_AA)

    # brightness slider (right)
    top, bottom = slider_top(), slider_bottom(h)
    cx = w - RIGHT_W // 2
    cv2.putText(out, "LIGHT", (w - RIGHT_W + 4, HEADER_H + 20), font, 0.4, (200, 200, 200), 1, cv2.LINE_AA)
    cv2.line(out, (cx, top), (cx, bottom), (180, 180, 180), 3)
    mid = (top + bottom) // 2
    cv2.line(out, (cx - 8, mid), (cx + 8, mid), (180, 180, 180), 1)
    ky = int(bottom - (brightness + 100) / 200 * (bottom - top))
    cv2.circle(out, (cx, ky), 9, (0, 230, 255), -1)
    cv2.putText(out, f"{brightness:+d}", (w - RIGHT_W + 4, bottom + 20), font, 0.45,
                (255, 255, 255), 1, cv2.LINE_AA)

    # subtitle
    sf, scale, th = cv2.FONT_HERSHEY_SIMPLEX, 0.9, 2
    done, live = " ".join(words), live or ""
    sep = " " if done and live else ""
    while done and cv2.getTextSize(done + sep + live, sf, scale, th)[0][0] > w - 30:
        done = done[3:] if len(done) > 3 else ""
        sep = " " if done and live else ""
    x, y = 15, h - 20
    if done:
        cv2.putText(out, done + sep, (x, y), sf, scale, (255, 255, 255), th, cv2.LINE_AA)
        x += cv2.getTextSize(done + sep, sf, scale, th)[0][0]
    cv2.putText(out, live, (x, y), sf, scale, (0, 230, 255), th, cv2.LINE_AA)

    if status.startswith("error"):
        cv2.putText(out, "Recognition " + status + " (check internet)", (15, h - BAR_H + 20),
                    sf, 0.5, (80, 80, 255), 1, cv2.LINE_AA)
    elif status == "thinking":
        cv2.putText(out, "reading...", (15, h - BAR_H + 20), sf, 0.5, (180, 180, 180), 1, cv2.LINE_AA)
    elif not done and not live:
        cv2.putText(out, "Write with your index finger...", (15, h - 30), sf, 0.7, (150, 150, 150), 1, cv2.LINE_AA)

    size = cv2.getTextSize(info, sf, 0.5, 1)[0][0]
    cv2.putText(out, info, (w - size - 10, h - BAR_H + 20), sf, 0.5, (200, 200, 200), 1, cv2.LINE_AA)
