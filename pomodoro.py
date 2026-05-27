import tkinter as tk
import math
import json
import os
import winsound
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "pomodoro_config.json"

MODES = {
    "work":      {"label": "工作中", "minutes": 25, "color": "#E74C3C", "accent": "#C0392B"},
    "short_break": {"label": "短休息", "minutes": 5,  "color": "#E67E22", "accent": "#D35400"},
    "long_break":  {"label": "长休息", "minutes": 15, "color": "#C0392B", "accent": "#A93226"},
}

BG = "#1E1A1A"
FG = "#FFFFFF"
FG_DIM = "#AA9999"
BTN_BG = "#342424"
BTN_ACTIVE = "#4A2E2E"

class PomodoroApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Pomodoro")
        self.root.overrideredirect(True)
        self.root.configure(bg=BG)
        self.root.attributes("-topmost", False)

        self.running = False
        self.paused = False
        self.remaining_seconds = 0
        self.total_seconds = 0
        self.current_mode = "work"
        self.session_count = 0
        self.after_id = None
        self.flash_id = None
        self.flash_on = False

        self.drag_x = 0
        self.drag_y = 0

        self.topmost_var = tk.BooleanVar(value=False)

        self.config = self.load_config()
        self.apply_config()

        self.build_ui()
        self.set_mode("work")
        self.root.after(100, self._center_window)

        self.root.bind("<Button-1>", self._on_drag_start)
        self.root.bind("<B1-Motion>", self._on_drag_move)
        self.root.bind("<Button-3>", self._on_right_click)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---- config ----
    def load_config(self):
        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def save_config(self):
        data = {
            "x": self.root.winfo_x(),
            "y": self.root.winfo_y(),
            "topmost": self.topmost_var.get(),
            "session_count": self.session_count,
            "minutes": {k: MODES[k]["minutes"] for k in MODES},
        }
        try:
            with open(CONFIG_PATH, "w") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def apply_config(self):
        if "minutes" in self.config:
            for k, v in self.config["minutes"].items():
                if k in MODES:
                    MODES[k]["minutes"] = v
        self.session_count = self.config.get("session_count", 0)
        self.topmost_var.set(self.config.get("topmost", False))

    # ---- window mgmt ----
    def _center_window(self):
        w, h = 340, 480
        x = self.config.get("x")
        y = self.config.get("y")
        if x is not None and y is not None:
            self.root.geometry(f"{w}x{h}+{x}+{y}")
        else:
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            x = (sw - w) // 2
            y = (sh - h) // 2
            self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _on_drag_start(self, event):
        self.drag_x = event.x
        self.drag_y = event.y

    def _on_drag_move(self, event):
        x = self.root.winfo_x() + event.x - self.drag_x
        y = self.root.winfo_y() + event.y - self.drag_y
        self.root.geometry(f"+{x}+{y}")

    def _on_right_click(self, event):
        menu = tk.Menu(self.root, tearoff=0, bg=BTN_BG, fg=FG,
                       activebackground=BTN_ACTIVE, activeforeground=FG)
        menu.add_command(label="置顶", command=self._toggle_topmost_menu)
        menu.add_separator()
        menu.add_command(label="退出", command=self._on_close)
        menu.post(event.x_root, event.y_root)

    def _toggle_topmost_menu(self):
        self.topmost_var.set(not self.topmost_var.get())
        self.root.attributes("-topmost", self.topmost_var.get())
        self._update_topmost_btn()

    def _toggle_topmost(self):
        self.root.attributes("-topmost", self.topmost_var.get())
        self._update_topmost_btn()

    def _update_topmost_btn(self):
        text = "📌置顶" if self.topmost_var.get() else "📍置顶"
        self.topmost_btn.config(text=text)

    # ---- UI ----
    def build_ui(self):
        # -- top bar --
        top = tk.Frame(self.root, bg=BG)
        top.pack(fill=tk.X, padx=14, pady=(10, 0))

        self.session_label = tk.Label(top, text="", bg=BG, fg=FG_DIM,
                                      font=("Segoe UI", 10))
        self.session_label.pack(side=tk.LEFT)

        self.topmost_btn = tk.Label(top, text="📍置顶", bg=BG, fg=FG_DIM,
                                    font=("Segoe UI", 10), cursor="hand2")
        self.topmost_btn.pack(side=tk.RIGHT)
        self.topmost_btn.bind("<Button-1>", lambda e: (
            self.topmost_var.set(not self.topmost_var.get()),
            self._toggle_topmost()
        ))
        self._update_topmost_btn()

        close_btn = tk.Label(top, text="✕", bg=BG, fg=FG_DIM,
                             font=("Segoe UI", 12, "bold"), cursor="hand2")
        close_btn.pack(side=tk.RIGHT, padx=(10, 0))
        close_btn.bind("<Button-1>", lambda e: self._on_close())

        # -- canvas ring --
        self.canvas_size = 260
        self.canvas = tk.Canvas(self.root, width=self.canvas_size,
                                height=self.canvas_size, bg=BG,
                                highlightthickness=0)
        self.canvas.pack(pady=(20, 0))

        # -- time label (overlay on canvas) --
        self.time_label = tk.Label(self.root, text="25:00", bg=BG, fg=FG,
                                   font=("Segoe UI", 40, "bold"))
        self.time_label.place(relx=0.5, rely=0.38, anchor=tk.CENTER)

        self.mode_label = tk.Label(self.root, text="工作中", bg=BG, fg=FG_DIM,
                                   font=("Segoe UI", 11))
        self.mode_label.place(relx=0.5, rely=0.50, anchor=tk.CENTER)

        # -- mode buttons --
        mode_frame = tk.Frame(self.root, bg=BG)
        mode_frame.pack(pady=(24, 0))

        self.mode_btns = {}
        mode_order = [("short_break", "短休息"), ("work", "工作"), ("long_break", "长休息")]
        for key, label in mode_order:
            btn = tk.Label(mode_frame, text=label, bg=BTN_BG, fg=FG_DIM,
                           font=("Segoe UI", 10), padx=12, pady=6,
                           cursor="hand2",
                           relief="flat", borderwidth=0)
            btn.pack(side=tk.LEFT, padx=4)
            btn.bind("<Button-1>", lambda e, k=key: self.set_mode(k))
            self.mode_btns[key] = btn

        # -- control buttons --
        ctrl_frame = tk.Frame(self.root, bg=BG)
        ctrl_frame.pack(pady=(20, 0))

        self.start_btn = tk.Label(ctrl_frame, text="开始", bg=MODES["work"]["color"],
                                  fg=FG, font=("Segoe UI", 12, "bold"),
                                  padx=28, pady=8, cursor="hand2",
                                  relief="flat", borderwidth=0)
        self.start_btn.pack(side=tk.LEFT, padx=6)
        self.start_btn.bind("<Button-1>", lambda e: self.start())

        self.pause_btn = tk.Label(ctrl_frame, text="暂停", bg=BTN_BG, fg=FG_DIM,
                                  font=("Segoe UI", 12, "bold"),
                                  padx=28, pady=8, cursor="hand2",
                                  relief="flat", borderwidth=0)
        self.pause_btn.pack(side=tk.LEFT, padx=6)
        self.pause_btn.bind("<Button-1>", lambda e: self.pause())

        reset_btn = tk.Label(ctrl_frame, text="重置", bg=BTN_BG, fg=FG_DIM,
                             font=("Segoe UI", 12, "bold"),
                             padx=28, pady=8, cursor="hand2",
                             relief="flat", borderwidth=0)
        reset_btn.pack(side=tk.LEFT, padx=6)
        reset_btn.bind("<Button-1>", lambda e: self.reset())

        # -- bottom hint --
        hint = tk.Label(self.root, text="右键菜单 | 拖动窗口", bg=BG, fg="#5A4444",
                        font=("Segoe UI", 8))
        hint.pack(side=tk.BOTTOM, pady=10)

    # ---- drawing ----
    def draw_ring(self, ratio):
        self.canvas.delete("all")
        color = MODES[self.current_mode]["color"]
        cx = cy = self.canvas_size // 2
        r = 100
        width = 10

        # bg ring
        self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r,
                                outline="#333333", width=width)

        if ratio > 0:
            # arc: tkinter draws from 3-o'clock going counter-clockwise.
            # We want from 12-o'clock going clockwise.
            start = 90  # 12 o'clock
            extent = -(360 * ratio)  # clockwise
            self.canvas.create_arc(cx - r, cy - r, cx + r, cy + r,
                                   start=start, extent=extent,
                                   outline=color, width=width,
                                   style="arc")

        # center dot
        if ratio < 1:
            self.canvas.create_oval(cx - 4, cy - 4, cx + 4, cy + 4,
                                    fill=color, outline="")

    # ---- timer logic ----
    def set_mode(self, mode):
        if self.running:
            self.reset()
        self.current_mode = mode
        self.total_seconds = MODES[mode]["minutes"] * 60
        self.remaining_seconds = self.total_seconds
        self.update_display()
        self.draw_ring(1.0)
        self._highlight_mode()
        self._update_pause_btn_state()

    def _highlight_mode(self):
        color = MODES[self.current_mode]["color"]
        for key, btn in self.mode_btns.items():
            if key == self.current_mode:
                btn.config(bg=color, fg=FG)
            else:
                btn.config(bg=BTN_BG, fg=FG_DIM)

    def start(self):
        if self.running and not self.paused:
            return
        if self.remaining_seconds <= 0:
            self.set_mode(self.current_mode)

        self.running = True
        self.paused = False
        self.start_btn.config(bg="#555555", fg=FG_DIM)
        self._update_pause_btn_state()
        self._tick()

    def pause(self):
        if not self.running or self.paused:
            return
        self.paused = True
        if self.after_id:
            self.root.after_cancel(self.after_id)
            self.after_id = None
        self.start_btn.config(bg=MODES[self.current_mode]["color"], fg=FG)
        self._update_pause_btn_state()

    def reset(self):
        self.running = False
        self.paused = False
        self.remaining_seconds = self.total_seconds
        if self.after_id:
            self.root.after_cancel(self.after_id)
            self.after_id = None
        self._stop_flash()
        self.start_btn.config(bg=MODES[self.current_mode]["color"], fg=FG)
        self.update_display()
        self.draw_ring(1.0)
        self._update_pause_btn_state()

    def _tick(self):
        if not self.running or self.paused:
            return
        if self.remaining_seconds <= 0:
            self._on_finish()
            return

        self.remaining_seconds -= 1
        self.update_display()
        ratio = self.remaining_seconds / self.total_seconds if self.total_seconds > 0 else 0
        self.draw_ring(ratio)
        self.after_id = self.root.after(1000, self._tick)

    def _on_finish(self):
        self.running = False
        self.paused = False
        self.remaining_seconds = 0
        self.update_display()
        self.draw_ring(0)
        self.start_btn.config(bg=MODES[self.current_mode]["color"], fg=FG)
        self._update_pause_btn_state()

        # increment session count only for work
        if self.current_mode == "work":
            self.session_count += 1
            self._update_session_label()

        # notification
        self._flash_window()
        self._beep()

        # auto-switch mode
        if self.current_mode == "work":
            next_mode = "long_break" if self.session_count > 0 and self.session_count % 4 == 0 else "short_break"
        else:
            next_mode = "work"
        self.set_mode(next_mode)

    def _beep(self):
        try:
            winsound.Beep(1000, 200)
            self.root.after(250, lambda: winsound.Beep(1200, 200))
            self.root.after(500, lambda: winsound.Beep(1400, 300))
        except Exception:
            pass

    def _flash_window(self):
        if not self.running and not self.paused:
            self.flash_on = not self.flash_on
            bg = MODES[self.current_mode]["color"] if self.flash_on else BG
            self.canvas.configure(bg=bg)
            self.flash_id = self.root.after(300, self._flash_window)
            # stop after a few flashes
            if not hasattr(self, "_flash_count"):
                self._flash_count = 0
            self._flash_count += 1
            if self._flash_count > 10:
                self._stop_flash()

    def _stop_flash(self):
        self._flash_count = 0
        if self.flash_id:
            self.root.after_cancel(self.flash_id)
            self.flash_id = None
        self.canvas.configure(bg=BG)

    # ---- display helpers ----
    def update_display(self):
        mins = self.remaining_seconds // 60
        secs = self.remaining_seconds % 60
        self.time_label.config(text=f"{mins:02d}:{secs:02d}")
        self.mode_label.config(text=MODES[self.current_mode]["label"],
                               fg=MODES[self.current_mode]["color"])
        self._update_session_label()

    def _update_session_label(self):
        self.session_label.config(text=f"🍅 x{self.session_count}")

    def _update_pause_btn_state(self):
        if self.running and not self.paused:
            self.pause_btn.config(bg="#F39C12", fg=FG)
        else:
            self.pause_btn.config(bg=BTN_BG, fg=FG_DIM)

    # ---- lifecycle ----
    def _on_close(self):
        self.running = False
        self.paused = False
        if self.after_id:
            self.root.after_cancel(self.after_id)
        self._stop_flash()
        x = self.root.winfo_x()
        y = self.root.winfo_y()
        self.config["x"] = x
        self.config["y"] = y
        self.config["topmost"] = self.topmost_var.get()
        self.config["session_count"] = self.session_count
        self.save_config()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = PomodoroApp()
    app.run()
