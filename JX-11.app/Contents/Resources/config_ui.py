#!/usr/bin/env python3
"""
JX-11 按键自定义界面
"""
import json
import os
import tkinter as tk
from tkinter import messagebox

CONFIG_PATH = os.path.expanduser("~/.config/jx11/config.json")

DEFAULT_CONFIG = {
    "滚轮上":        {"type": "key",            "keycode": 126, "modifiers": [],          "label": "↑"},
    "滚轮下":        {"type": "key",            "keycode": 125, "modifiers": [],          "label": "↓"},
    "向左":          {"type": "key",            "keycode": 53,  "modifiers": [],          "label": "ESC"},
    "向左_double":   {"type": "key",            "keycode": 50,  "modifiers": ["command"], "label": "⌘`"},
    "向右":          {"type": "key",            "keycode": 36,  "modifiers": [],          "label": "↩"},
    "向右_double":   {"type": "key",            "keycode": 44,  "modifiers": [],          "label": "/"},
    "确认键":        {"type": "double_modifier","keycode": 58,  "flag": "left_option",    "label": "⌥⌥"},
}

BUTTON_NAMES = ["滚轮上", "滚轮下", "向左", "向右", "确认键"]

CAPTURABLE_MODS = {
    "Option_L": ("left_option",  58, "⌥⌥"),
    "Alt_L":    ("left_option",  58, "⌥⌥"),
    "Option_R": ("right_option", 61, "⌥⌥"),
    "Alt_R":    ("right_option", 61, "⌥⌥"),
    "Meta_L":   ("left_command", 55, "⌘⌘"),
    "Meta_R":   ("right_command",54, "⌘⌘"),
}

MODIFIER_KEYSYMS = set(CAPTURABLE_MODS.keys()) | {
    "Shift_L", "Shift_R", "Control_L", "Control_R",
    "Caps_Lock", "Num_Lock", "Scroll_Lock",
}

KEYSYM_TO_MOD = {
    "Shift_L":   "shift",   "Shift_R":   "shift",
    "Control_L": "control", "Control_R": "control",
    "Option_L":  "option",  "Option_R":  "option",
    "Alt_L":     "option",  "Alt_R":     "option",
    "Meta_L":    "command", "Meta_R":    "command",
}

MOD_SYMS  = {"shift": "⇧", "option": "⌥", "control": "⌃", "command": "⌘"}
MOD_ORDER = ["shift", "control", "option", "command"]

KEYSYM_LABELS = {
    "Return": "↩", "Escape": "ESC", "Tab": "⇥",
    "Up": "↑", "Down": "↓", "Left": "←", "Right": "→",
    "space": "Space", "BackSpace": "⌫", "Delete": "⌦",
    **{f"F{i}": f"F{i}" for i in range(1, 13)},
}

KEYSYM_TO_KEYCODE = {
    "Return": 36, "Escape": 53, "Tab": 48, "space": 49,
    "Up": 126, "Down": 125, "Left": 123, "Right": 124,
    "BackSpace": 51, "Delete": 117,
    "F1": 122, "F2": 120, "F3": 99,  "F4": 118,
    "F5": 96,  "F6": 97,  "F7": 98,  "F8": 100,
    "F9": 101, "F10": 109,"F11": 103,"F12": 111,
    "a": 0,  "b": 11, "c": 8,  "d": 2,  "e": 14, "f": 3,
    "g": 5,  "h": 4,  "i": 34, "j": 38, "k": 40, "l": 37,
    "m": 46, "n": 45, "o": 31, "p": 35, "q": 12, "r": 15,
    "s": 1,  "t": 17, "u": 32, "v": 9,  "w": 13, "x": 7,
    "y": 16, "z": 6,
    "1": 18, "2": 19, "3": 20, "4": 21, "5": 23,
    "6": 22, "7": 26, "8": 28, "9": 25, "0": 29,
}

SPECIAL_ACTIONS = [
    ("cycle_windows", "⊞ 轮换窗口"),
]


def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return dict(DEFAULT_CONFIG)


def save_config(cfg):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def action_label(action):
    if action is None:
        return "—"
    return action.get("label", "?")


def capture_key(parent):
    """
    弹出按键捕获对话框。
    返回: action dict（新映射），None（清除），False（取消）
    """
    result    = [False]
    pending   = [None]
    held_mods = set()
    last_mod  = [None]

    top = tk.Toplevel(parent)
    top.title("设置按键")
    top.resizable(False, False)
    top.transient(parent)
    top.grab_set()

    tk.Label(top, text="请按下要映射的键",
             font=("", 12, "bold"), pady=10).pack()

    preview = tk.Label(top, text="等待按键…",
                       fg="#888888", font=("", 16), pady=6)
    preview.pack()

    tk.Frame(top, height=1, bg="#cccccc").pack(fill="x", padx=16, pady=6)
    tk.Label(top, text="或选择特殊功能：", fg="#555", font=("", 9)).pack()

    sf = tk.Frame(top)
    sf.pack(pady=4)
    for at, al in SPECIAL_ACTIONS:
        def on_special(t=at, l=al):
            _show(l, {"type": t, "label": l})
        tk.Button(sf, text=al, font=("", 10), command=on_special).pack(side="left", padx=4)

    btn_frame = tk.Frame(top, pady=8)
    btn_frame.pack()

    confirm_btn = tk.Button(btn_frame, text="确认", width=8,
                            state="disabled", command=lambda: _confirm())
    confirm_btn.pack(side="left", padx=4)
    tk.Button(btn_frame, text="清除映射", width=8,
              command=lambda: _clear()).pack(side="left", padx=4)
    tk.Button(btn_frame, text="取消", width=8,
              command=lambda: top.destroy()).pack(side="left", padx=4)

    def _confirm():
        result[0] = pending[0]
        top.destroy()

    def _clear():
        result[0] = None
        top.destroy()

    def _show(text, action):
        pending[0] = action
        preview.config(text=text, fg="#0066cc")
        confirm_btn.config(state="normal")

    def on_press(event):
        keysym  = event.keysym
        keycode = event.keycode
        if keysym in KEYSYM_TO_MOD:
            held_mods.add(KEYSYM_TO_MOD[keysym])
        if keysym in CAPTURABLE_MODS:
            last_mod[0] = keysym
            return
        if keysym in MODIFIER_KEYSYMS:
            return
        last_mod[0] = None
        active  = [m for m in MOD_ORDER if m in held_mods]
        mod_str = "".join(MOD_SYMS[m] for m in active)
        key_str = KEYSYM_LABELS.get(keysym,
                  keysym.upper() if len(keysym) == 1 else keysym)
        if keycode > 200 or keycode == 0:
            keycode = KEYSYM_TO_KEYCODE.get(keysym,
                      KEYSYM_TO_KEYCODE.get(keysym.lower(), keycode))
        _show(mod_str + key_str,
              {"type": "key", "keycode": keycode,
               "modifiers": active, "label": mod_str + key_str})

    def on_release(event):
        keysym = event.keysym
        if keysym in CAPTURABLE_MODS and last_mod[0] == keysym:
            flag, kc, lbl = CAPTURABLE_MODS[keysym]
            _show(lbl, {"type": "double_modifier",
                        "keycode": kc, "flag": flag, "label": lbl})
            last_mod[0] = None
        if keysym in KEYSYM_TO_MOD:
            held_mods.discard(KEYSYM_TO_MOD[keysym])

    top.bind("<KeyPress>",   on_press)
    top.bind("<KeyRelease>", on_release)
    top.focus_force()

    top.update_idletasks()
    tw, th = top.winfo_reqwidth(), top.winfo_reqheight()
    px, py = parent.winfo_x(), parent.winfo_y()
    pw, ph = parent.winfo_width(), parent.winfo_height()
    top.geometry(f"{tw}x{th}+{px + (pw - tw) // 2}+{py + (ph - th) // 2}")

    parent.wait_window(top)
    return result[0]


class ConfigUI:
    def __init__(self):
        self.cfg  = load_config()
        self.root = tk.Tk()
        self.root.title("JX-11 按键设置")
        self.root.resizable(False, False)
        self._cells = {}
        self._build()

    def _build(self):
        root = self.root
        tk.Label(root, text="JX-11 按键自定义",
                 font=("", 14, "bold"), pady=12).pack()

        frame = tk.Frame(root, padx=20, pady=4)
        frame.pack()

        # 表头：按键 | 点按 | [设置] | 长按 | [设置]
        for col, text in enumerate(["按键", "单击", "", "双击", ""]):
            tk.Label(frame, text=text, font=("", 11, "bold"),
                     width=12 if col in (1, 3) else 4,
                     anchor="center", relief="ridge", bg="#e8e8e8",
                     padx=4, pady=6).grid(
                row=0, column=col, sticky="nsew", padx=1, pady=1)

        for row, btn in enumerate(BUTTON_NAMES, start=1):
            tk.Label(frame, text=btn, font=("", 11, "bold"),
                     width=8, anchor="center",
                     padx=4, pady=8).grid(
                row=row, column=0, padx=1, pady=1)

            # 点按列
            tap_lbl = tk.Label(frame, text=action_label(self.cfg.get(btn)),
                               font=("", 12), width=12, anchor="center")
            tap_lbl.grid(row=row, column=1, padx=1, pady=1)
            self._cells[btn] = tap_lbl
            tk.Button(frame, text="设置", font=("", 10),
                      command=lambda b=btn: self._set(b, long=False)
                      ).grid(row=row, column=2, padx=4, pady=1)

            # 长按列
            long_key = btn + '_double'
            long_lbl = tk.Label(frame, text=action_label(self.cfg.get(long_key)),
                                font=("", 12), width=12, anchor="center",
                                fg="#555555")
            long_lbl.grid(row=row, column=3, padx=1, pady=1)
            self._cells[long_key] = long_lbl
            tk.Button(frame, text="设置", font=("", 10),
                      command=lambda b=btn: self._set(b, long=True)
                      ).grid(row=row, column=4, padx=4, pady=1)

        footer = tk.Frame(root, pady=10)
        footer.pack()
        tk.Button(footer, text="恢复默认", width=10,
                  command=self._reset).pack(side="left", padx=6)
        tk.Button(footer, text="关闭", width=10,
                  command=root.destroy).pack(side="left", padx=6)

        root.update_idletasks()
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        w  = root.winfo_width()
        h  = root.winfo_height()
        root.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")

    def _set(self, btn, long=False):
        r = capture_key(self.root)
        if r is False:
            return
        key = btn + '_double' if long else btn
        self.cfg[key] = r
        save_config(self.cfg)
        self._cells[key].config(text=action_label(r))

    def _reset(self):
        if messagebox.askyesno("恢复默认", "将所有按键映射恢复为默认设置？"):
            self.cfg = dict(DEFAULT_CONFIG)
            save_config(self.cfg)
            for btn in BUTTON_NAMES:
                self._cells[btn].config(text=action_label(self.cfg.get(btn)))
                long_key = btn + '_double'
                if long_key in self._cells:
                    self._cells[long_key].config(text=action_label(self.cfg.get(long_key)))

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    ConfigUI().run()
