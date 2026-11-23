# BongoCatBot (PurrfectClicker)
[![Ko-fi](https://img.shields.io/badge/Support%20on-Ko--fi-FF5E5B?style=for-the-badge&logo=ko-fi&logoColor=white)](https://ko-fi.com/gamerec)


Lightweight Windows desktop utility built with Python, OpenCV, and `mss` for template-based chest detection and automated key presses (`F21–F24` or standard keys) with modifier-key pause support.

## Features

- Interactive screen region snipping for left and right scan areas.
- Template matching (`cv2.matchTemplate`) against image assets inside `assets/`.
- Independent hotkeys: `F8` for chest scanning, `F9` for auto-clicking, `Esc` to exit.
- Automatic pause when `Shift`, `Ctrl`, or `Alt` is held down.
- Optional debug build (`PurrfectClicker_Debug.py`) with live modifier state, key counters, and key-method toggles.

## Requirements

- Windows
- Python 3.10+

Install dependencies:

```bash
pip install opencv-python numpy mss pyinstaller
```

## Usage
Run main application:

```bash
python PurrfectClicker.py
```

Run debug build:

```bash
python PurrfectClicker_Debug.py
```

## Build Standalone Executable (.exe)

```bash
pyinstaller --noconfirm --onefile --windowed PurrfectClicker.py
```

Remember to keep the assets/ folder next to the compiled executable in dist/.

---

## Support the Project

If this utility makes your workflow easier, consider buying me a coffee — it directly supports building more free tools for creators:

👉 **[Support GameRec on Ko-fi](https://ko-fi.com/gamerec)**


👉 **[GitHub Sponsors: GameRec](https://github.com/sponsors/gamerec)**

---

## License
Part of the **GameRec** open-source utilities collection (gamerec.org).