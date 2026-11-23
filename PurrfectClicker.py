import ctypes
import os
import random
import sys
import threading
import time
import tkinter as tk
import tkinter.messagebox

import cv2
import mss
import numpy as np

# Enable high-DPI awareness and 1ms Windows timer resolution
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
    ctypes.windll.winmm.timeBeginPeriod(1)
except Exception:
    pass

# Virtual key and scan codes for F21-F24
KEYS_DATA = [
    (0x84, 0x6C),  # F21
    (0x85, 0x6D),  # F22
    (0x86, 0x6E),  # F23
    (0x87, 0x76),  # F24
]

KEYEVENTF_KEYUP = 0x0002


def send_hardware_key():
    """Send a single key press using F21-F24 virtual/scan codes."""
    vk, sc = random.choice(KEYS_DATA)
    ctypes.windll.user32.keybd_event(vk, sc, 0, 0)
    time.sleep(0.012)
    ctypes.windll.user32.keybd_event(vk, sc, KEYEVENTF_KEYUP, 0)


def hard_click(x, y):
    """Move cursor and perform a native left mouse click at (x, y)."""
    ctypes.windll.user32.SetCursorPos(x, y)
    time.sleep(0.02)
    ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTDOWN
    time.sleep(0.02)
    ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTUP


def is_keyboard_modifier_held():
    """Return True if Shift, Ctrl, or Alt is currently held down."""
    for vk in (0x10, 0x11, 0x12):
        if ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000:
            return True
    return False


def is_key_pressed(vk):
    """Check physical key state via GetAsyncKeyState."""
    return bool(ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000)


class SnippingWidget:
    """Fullscreen overlay tool for selecting screen regions."""

    def __init__(self, parent, callback):
        self.top = tk.Toplevel(parent)
        self.top.attributes("-fullscreen", True)
        self.top.attributes("-alpha", 0.3)
        self.top.attributes("-topmost", True)
        self.top.config(cursor="cross")

        self.canvas = tk.Canvas(self.top, cursor="cross", bg="gray")
        self.canvas.pack(fill="both", expand=True)
        self.callback = callback

        self.start_x = None
        self.start_y = None
        self.rect = None

        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

    def on_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        self.rect = self.canvas.create_rectangle(
            self.start_x, self.start_y, 1, 1, outline="red", width=2, fill="white"
        )

    def on_drag(self, event):
        self.canvas.coords(self.rect, self.start_x, self.start_y, event.x, event.y)

    def on_release(self, event):
        end_x, end_y = event.x, event.y
        self.top.destroy()

        x1, y1 = int(min(self.start_x, end_x)), int(min(self.start_y, end_y))
        x2, y2 = int(max(self.start_x, end_x)), int(max(self.start_y, end_y))

        if x2 - x1 > 5 and y2 - y1 > 5:
            self.callback((x1, y1, x2 - x1, y2 - y1))
        else:
            self.callback(None)


class PurrfectClickerApp(tk.Tk):
    """Main desktop GUI for chest scanning and paw auto-clicking."""

    def __init__(self):
        super().__init__()
        self.title("PurrfectClicker Pro")
        self.geometry("460x600")
        self.attributes("-topmost", True)

        self.left_region = None
        self.right_region = None
        self.templates = []

        self.chest_hunter_running = False
        self.key_presser_running = False

        self.create_ui()
        self.load_templates_from_assets()

        self.key_spam_thread = threading.Thread(target=self.key_spam_loop, daemon=True)
        self.key_spam_thread.start()

        self.bot_thread = threading.Thread(target=self.bot_loop, daemon=True)
        self.bot_thread.start()

        self.hotkey_thread = threading.Thread(target=self.hotkey_loop, daemon=True)
        self.hotkey_thread.start()

    def create_ui(self):
        tk.Label(
            self, text="PurrfectClicker Pro", font=("Segoe UI", 14, "bold")
        ).pack(pady=8)

        self.btn_left = tk.Button(
            self,
            text="1. Select Left Region",
            command=lambda: SnippingWidget(self, self.set_left_region),
            width=34,
        )
        self.btn_left.pack(pady=3)
        self.lbl_left = tk.Label(self, text="Left region: None", fg="red")
        self.lbl_left.pack()

        self.btn_right = tk.Button(
            self,
            text="2. Select Right Region",
            command=lambda: SnippingWidget(self, self.set_right_region),
            width=34,
        )
        self.btn_right.pack(pady=3)
        self.lbl_right = tk.Label(self, text="Right region: None", fg="red")
        self.lbl_right.pack()

        self.btn_tpl = tk.Button(
            self,
            text="Reload Templates from 'assets'",
            command=self.load_templates_from_assets,
            width=34,
        )
        self.btn_tpl.pack(pady=5)
        self.lbl_tpl = tk.Label(self, text="Loading templates...", fg="orange")
        self.lbl_tpl.pack()

        tk.Frame(self, height=1, bg="gray").pack(fill="x", padx=20, pady=8)

        self.btn_chest = tk.Button(
            self,
            text="CHEST SCANNER: OFF (F8)",
            command=self.toggle_chest_hunter,
            bg="#e74c3c",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            width=32,
            height=2,
        )
        self.btn_chest.pack(pady=4)

        self.btn_keys = tk.Button(
            self,
            text="PAW AUTOCLICKER: OFF (F9)",
            command=self.toggle_key_presser,
            bg="#e74c3c",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            width=32,
            height=2,
        )
        self.btn_keys.pack(pady=4)

        self.btn_test = tk.Button(
            self,
            text="Test Key (Send 1x F21)",
            command=send_hardware_key,
            width=24,
        )
        self.btn_test.pack(pady=4)

        tk.Label(
            self, text="Live Status Log:", font=("Segoe UI", 9, "bold")
        ).pack(pady=(5, 0))
        self.log_box = tk.Text(self, height=7, width=54, font=("Consolas", 8))
        self.log_box.pack(pady=5, padx=10)

        tk.Label(
            self,
            text="Hotkeys: F8 = Chests | F9 = Auto-Clicker | Esc = Exit",
            fg="gray",
        ).pack()

    def log(self, text):
        self.log_box.insert(tk.END, text + "\n")
        self.log_box.see(tk.END)

    def load_templates_from_assets(self):
        """Load grayscale template images from the 'assets' folder."""
        self.templates = []
        if getattr(sys, "frozen", False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))

        assets_dir = os.path.join(base_dir, "assets")
        os.makedirs(assets_dir, exist_ok=True)

        loaded_names = []
        for root, _dirs, files in os.walk(assets_dir):
            for file in files:
                if file.lower().endswith((".png", ".jpg", ".jpeg")):
                    full_path = os.path.join(root, file)
                    img = cv2.imread(full_path, cv2.IMREAD_GRAYSCALE)
                    if img is not None:
                        self.templates.append(img)
                        loaded_names.append(file)

        if self.templates:
            self.lbl_tpl.config(
                text=f"Loaded {len(self.templates)} templates from assets/", fg="green"
            )
            self.log(f"[OK] Loaded chest templates: {', '.join(loaded_names)}")
        else:
            self.lbl_tpl.config(text="No images found in 'assets'!", fg="red")
            self.log("[!] No PNG/JPG files found in 'assets' folder!")

    def set_left_region(self, bbox):
        if bbox:
            self.left_region = bbox
            self.lbl_left.config(
                text=f"Left region: Set ({bbox[2]}x{bbox[3]})", fg="green"
            )
            self.log(f"[OK] Left region set to: {bbox}")

    def set_right_region(self, bbox):
        if bbox:
            self.right_region = bbox
            self.lbl_right.config(
                text=f"Right region: Set ({bbox[2]}x{bbox[3]})", fg="green"
            )
            self.log(f"[OK] Right region set to: {bbox}")

    def toggle_chest_hunter(self):
        if not self.templates:
            tk.messagebox.showwarning(
                "Missing Templates", "Place chest template images inside the 'assets' folder!"
            )
            return

        self.chest_hunter_running = not self.chest_hunter_running
        if self.chest_hunter_running:
            self.btn_chest.config(text="CHEST SCANNER: ON (F8)", bg="#2ecc71")
            self.log("[STATUS] Chest scanner: ENABLED")
        else:
            self.btn_chest.config(text="CHEST SCANNER: OFF (F8)", bg="#e74c3c")
            self.log("[STATUS] Chest scanner: DISABLED")

    def toggle_key_presser(self):
        self.key_presser_running = not self.key_presser_running
        if self.key_presser_running:
            self.btn_keys.config(text="PAW AUTOCLICKER: ON (F9)", bg="#2ecc71")
            self.log("[STATUS] Paw auto-clicker: ENABLED")
        else:
            self.btn_keys.config(text="PAW AUTOCLICKER: OFF (F9)", bg="#e74c3c")
            self.log("[STATUS] Paw auto-clicker: DISABLED")

    def hotkey_loop(self):
        f8_was_pressed = False
        f9_was_pressed = False
        esc_was_pressed = False

        while True:
            f8_state = is_key_pressed(0x77)  # F8
            if f8_state and not f8_was_pressed:
                self.after(0, self.toggle_chest_hunter)
            f8_was_pressed = f8_state

            f9_state = is_key_pressed(0x78)  # F9
            if f9_state and not f9_was_pressed:
                self.after(0, self.toggle_key_presser)
            f9_was_pressed = f9_state

            esc_state = is_key_pressed(0x1B)  # Esc
            if esc_state and not esc_was_pressed:
                self.after(0, self.close_app)
            esc_was_pressed = esc_state

            time.sleep(0.05)

    def close_app(self):
        try:
            ctypes.windll.winmm.timeEndPeriod(1)
        except Exception:
            pass
        self.destroy()
        sys.exit()

    def key_spam_loop(self):
        """Background loop sending F21-F24 key presses when F9 toggle is active."""
        while True:
            if self.key_presser_running:
                if not is_keyboard_modifier_held():
                    send_hardware_key()
                    time.sleep(0.01)
                else:
                    time.sleep(0.02)
            else:
                time.sleep(0.05)

    def check_and_click_chests(self, sct, region, side_name):
        if region is None:
            return False, 0.0

        monitor = {
            "top": region[1],
            "left": region[0],
            "width": region[2],
            "height": region[3],
        }
        img = np.array(sct.grab(monitor))
        gray_screen = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)

        best_match = 0.0
        for tpl in self.templates:
            if tpl.shape[0] > gray_screen.shape[0] or tpl.shape[1] > gray_screen.shape[1]:
                continue

            res = cv2.matchTemplate(gray_screen, tpl, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(res)

            if max_val > best_match:
                best_match = max_val

            if max_val >= 0.55:
                click_x = region[0] + (region[2] // 2)
                click_y = region[1] + (region[3] // 2)
                hard_click(click_x, click_y)
                self.after(
                    0,
                    self.log,
                    f"[!] CHEST DETECTED ({side_name})! Match: {max_val * 100:.1f}% -> CLICKED!",
                )
                return True, best_match

        return False, best_match

    def bot_loop(self):
        """Background loop scanning left/right regions for chest templates."""
        last_log_time = 0
        last_chest_check = 0

        with mss.MSS() as sct:
            while True:
                if self.chest_hunter_running:
                    if not is_keyboard_modifier_held():
                        curr_time = time.time()

                        if curr_time - last_chest_check > 0.1:
                            last_chest_check = curr_time
                            c1, m1 = self.check_and_click_chests(
                                sct, self.left_region, "LEFT"
                            )
                            c2, m2 = self.check_and_click_chests(
                                sct, self.right_region, "RIGHT"
                            )

                            if curr_time - last_log_time > 3.0:
                                last_log_time = curr_time
                                self.after(
                                    0,
                                    self.log,
                                    f"[SCAN] Max match: Left={m1 * 100:.1f}% | Right={m2 * 100:.1f}%",
                                )

                            if c1 or c2:
                                time.sleep(0.5)

                time.sleep(0.02)


if __name__ == "__main__":
    app = PurrfectClickerApp()
    app.protocol("WM_DELETE_WINDOW", app.close_app)
    app.mainloop()