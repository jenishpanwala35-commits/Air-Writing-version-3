"""
Air Writing - write in the air, see it as a live subtitle.

Gestures
  Index finger only ............ DRAW  (inside the middle area)
  Index + middle ............... SELECT: touch a colour (top), a filter (left)
                                 or slide brightness (right)
  Index + middle + ring ........ ERASE (removes the stroke you touch)
  Open palm (hold 1 sec) ....... NEXT WORD: adds word to subtitle, clears board
  Fist ......................... PAUSE

Keys: space next word | backspace remove last word | x clear subtitle
      c clear board | u undo stroke | s save PNG | + / - brush size
      f next filter | [ / ] brightness | 0 reset look | h hide hand skeleton
      w full screen on/off | q or Esc quit
"""
import time

import cv2

import look
import ui
from camera import Camera
from canvas import AirCanvas
from hand_tracker import HandTracker
from recognizer import LiveRecognizer

CAM_INDEX = 0
FRAME_W, FRAME_H = 640, 480
SMOOTHING = 0.6        # 0..1  higher = snappier, lower = smoother
HOLD_SECONDS = 1.0     # open-palm hold time for "next word"
ERASER_RADIUS = 30
LANGUAGE = "en"        # handwriting language code
FULLSCREEN = True      # start in full screen (press w to toggle)
WIN = "Air Writing"


def main():
    cam = Camera(CAM_INDEX, FRAME_W, FRAME_H)
    frame = None
    while frame is None:
        _, frame = cam.read()
        time.sleep(0.01)
    h, w = frame.shape[:2]

    cv2.namedWindow(WIN, cv2.WINDOW_NORMAL)
    fullscreen = FULLSCREEN
    if fullscreen:
        cv2.setWindowProperty(WIN, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    tracker = HandTracker()
    canvas = AirCanvas(w, h)
    rec = LiveRecognizer(LANGUAGE)

    color_idx = 9                     # start with Blue
    canvas.color = ui.PALETTE[color_idx][1]
    filter_idx, brightness = 0, 0
    show_skeleton = True

    words = []
    sx = sy = None
    last_id = -1
    start = time.time()
    palm_since, palm_done = None, False
    fps, fps_t, fps_n = 0.0, time.time(), 0

    def ask_recognizer():
        rec.request(canvas.ink(), w, h)

    def next_word():
        text = rec.text.strip()
        if text:
            words.append(text)
        canvas.clear()
        rec.reset()

    def set_color(i):
        nonlocal color_idx
        color_idx = i
        canvas.color = ui.PALETTE[i][1]

    while True:
        fid, raw = cam.read()
        if raw is None or fid == last_id:
            if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
                break
            time.sleep(0.002)
            continue
        last_id = fid
        frame = cv2.flip(raw, 1)
        now_ms = (time.time() - start) * 1000

        # track on the untouched frame (filters never confuse the tracker)
        hand = tracker.process(frame, now_ms)
        mode, pt, stroke_done = "PAUSE", None, False

        if hand:
            idx, mid, ring, pinky = tracker.fingers_up(hand)
            x, y = tracker.index_tip(hand, w, h)
            sx = x if sx is None else int(sx + SMOOTHING * (x - sx))
            sy = y if sy is None else int(sy + SMOOTHING * (y - sy))
            pt = (sx, sy)

            if idx and not mid and not ring and not pinky:
                mode = "DRAW"
            elif idx and mid and not ring and not pinky:
                mode = "SELECT"
            elif idx and mid and ring and not pinky:
                mode = "ERASE"
            elif idx and mid and ring and pinky:
                mode = "NEXT"

            if mode == "DRAW":
                if ui.in_writing(sx, sy, w, h):
                    canvas.add_point(pt, now_ms)
                else:
                    stroke_done = canvas.end_stroke()
            else:
                stroke_done = canvas.end_stroke()
                if mode == "SELECT":
                    c = ui.hit_color(sx, sy, w)
                    f = ui.hit_filter(sx, sy)
                    b = ui.hit_brightness(sx, sy, w, h)
                    if c is not None:
                        set_color(c)
                    elif f is not None:
                        filter_idx = f
                    elif b is not None:
                        brightness = b
                elif mode == "ERASE":
                    if canvas.erase_at(pt, ERASER_RADIUS):
                        ask_recognizer()
        else:
            stroke_done = canvas.end_stroke()
            sx = sy = None

        if stroke_done:
            ask_recognizer()

        # filtered camera view, then cursor + drawing on top (ink keeps true colours)
        view = look.apply(frame, filter_idx, brightness)
        if hand:
            if show_skeleton:
                tracker.draw(view, hand)
            if mode == "DRAW":
                cv2.circle(view, pt, canvas.thickness + 2, canvas.color, -1)
            elif mode == "SELECT":
                cv2.circle(view, pt, 14, (255, 255, 255), 2)
            elif mode == "ERASE":
                cv2.circle(view, pt, ERASER_RADIUS, (200, 200, 200), 2)

        if mode == "NEXT":
            if palm_since is None:
                palm_since = time.time()
            prog = min((time.time() - palm_since) / HOLD_SECONDS, 1.0)
            cv2.rectangle(view, (0, ui.HEADER_H + 2), (int(w * prog), ui.HEADER_H + 10), (0, 230, 255), -1)
            if prog >= 1.0 and not palm_done:
                next_word()
                palm_done = True
        else:
            palm_since, palm_done = None, False

        out = canvas.overlay_on(view)

        fps_n += 1
        if time.time() - fps_t >= 1.0:
            fps, fps_n, fps_t = fps_n / (time.time() - fps_t), 0, time.time()
        info = f"{fps:.0f} FPS | {mode} | {ui.PALETTE[color_idx][0]}"
        ui.draw_ui(out, color_idx, filter_idx, brightness, words, rec.text, rec.status, info)
        try:
            _, _, win_w, win_h = cv2.getWindowImageRect(WIN)
        except cv2.error:
            win_w = win_h = 0
        cv2.imshow(WIN, ui.letterbox(out, win_w, win_h) if win_w > 0 and win_h > 0 else out)

        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), 27):
            break
        elif key == ord(" "):
            next_word()
        elif key == 8 and words:
            words.pop()
        elif key == ord("x"):
            words.clear()
        elif key == ord("c"):
            canvas.clear()
            rec.reset()
        elif key == ord("u"):
            canvas.undo()
            ask_recognizer()
        elif key == ord("s"):
            print("Saved:", canvas.save())
        elif key in (ord("+"), ord("=")):
            canvas.change_thickness(1)
        elif key == ord("-"):
            canvas.change_thickness(-1)
        elif key == ord("f"):
            filter_idx = (filter_idx + 1) % len(look.FILTERS)
        elif key == ord("]"):
            brightness = min(brightness + 5, 100)
        elif key == ord("["):
            brightness = max(brightness - 5, -100)
        elif key == ord("0"):
            filter_idx, brightness = 0, 0
        elif key == ord("h"):
            show_skeleton = not show_skeleton
        elif key == ord("w"):
            fullscreen = not fullscreen
            cv2.setWindowProperty(WIN, cv2.WND_PROP_FULLSCREEN,
                                  cv2.WINDOW_FULLSCREEN if fullscreen else cv2.WINDOW_NORMAL)

    tracker.close()
    cam.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
