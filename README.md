# Air Writing with Python (live subtitle)

Write in the air with your index finger. The app tracks your hand (MediaPipe),
draws your strokes (OpenCV) and shows what you wrote as a live subtitle.

## Setup
```bash
pip install -r requirements.txt
python main.py
```
First run downloads a small hand model (~8 MB). Handwriting recognition needs
internet (it sends your pen strokes to Google's handwriting-input service).

## Screen layout
- **Top:** 20 ink colours (2 rows x 10)
- **Left:** filters - Normal, Warm, Cool, Sepia, B&W, Vivid
- **Right:** brightness slider (-100 to +100)
- **Middle:** writing area  |  **Bottom:** live subtitle

## Gestures
| Gesture | Action |
|---|---|
| Index finger only | Draw (middle area) |
| Index + middle | Select: touch a colour / filter / slide brightness |
| Index + middle + ring | Erase stroke |
| Open palm, hold 1 sec | Add word to subtitle + clear board |
| Fist | Pause |

## Keys
space next word, backspace remove last word, x clear subtitle, c clear board,
u undo stroke, s save PNG, +/- brush size, f next filter, [ / ] brightness,
0 reset look, h hide hand skeleton, q quit.

## Files
main.py (loop), ui.py (palette, filters, slider, subtitle), look.py (filters +
brightness), camera.py (threaded fast webcam), hand_tracker.py, canvas.py
(strokes, erase, undo), recognizer.py (live recognition thread)
"# Air-Writing-version-3" 
