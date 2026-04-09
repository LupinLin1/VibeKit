#!/usr/bin/env python3
"""
JX-11 首次引导：检查依赖 + 权限引导
退出码 0 = 一切就绪，1 = 用户取消或出错
"""
import sys
import os
import subprocess
import tkinter as tk
from tkinter import ttk
import time

REQUIRED_PACKAGES = [
    ("hid",    "hidapi"),
    ("Quartz", "pyobjc-framework-Quartz"),
    ("AppKit", "pyobjc-framework-AppKit"),
]

def pip_install(pkg_name):
    subprocess.check_call([
        sys.executable, "-m", "pip", "install",
        "--break-system-packages", "-q", pkg_name
    ])

def check_deps():
    missing = []
    for import_name, pkg_name in REQUIRED_PACKAGES:
        try:
            __import__(import_name)
        except ImportError:
            missing.append((import_name, pkg_name))
    return missing

def check_accessibility():
    import ctypes, ctypes.util
    appservices = ctypes.cdll.LoadLibrary(
        ctypes.util.find_library('ApplicationServices'))
    appservices.AXIsProcessTrusted.restype = ctypes.c_bool
    return appservices.AXIsProcessTrusted()

def check_input_monitoring():
    try:
        import hid
        needle = "jx-11"
        devs = hid.enumerate(0, 0)
        matches = [
            d for d in devs
            if needle in (d.get('product_string') or '').lower()
            or needle in (d.get('manufacturer_string') or '').lower()
        ]
        if not matches:
            return True   # 设备未连接，无法检测，暂时放行
        d = next((x for x in matches if x.get('usage_page') == 12), matches[0])
        h = hid.device()
        h.open_path(d['path'])
        h.close()
        return True
    except Exception:
        return False

def open_accessibility_prefs():
    os.system("open 'x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility'")

def open_input_monitoring_prefs():
    os.system("open 'x-apple.systempreferences:com.apple.preference.security?Privacy_ListenEvent'")

def is_already_running():
    result = subprocess.run(
        ["pgrep", "-f", "daemon.py"],
        capture_output=True)
    return result.returncode == 0

if is_already_running():
    sys.exit(0)

missing = check_deps()

if missing:
    root = tk.Tk()
    root.title("JX-11 安装")
    root.geometry("400x160")
    root.resizable(False, False)
    root.eval('tk::PlaceWindow . center')

    lbl = tk.Label(root, text="正在安装必要组件，请稍候...", pady=20)
    lbl.pack()
    bar = ttk.Progressbar(root, length=340, mode='determinate')
    bar.pack(pady=10)
    status = tk.Label(root, text="", fg="gray")
    status.pack()

    def install_all():
        for i, (import_name, pkg_name) in enumerate(missing):
            status.config(text=f"安装 {pkg_name}...")
            root.update()
            try:
                pip_install(pkg_name)
            except Exception as e:
                status.config(text=f"安装失败: {e}", fg="red")
                root.update()
                time.sleep(3)
                root.destroy()
                sys.exit(1)
            bar['value'] = (i + 1) / len(missing) * 100
            root.update()

        status.config(text="安装完成 ✓", fg="green")
        root.update()
        time.sleep(1)
        root.destroy()

    root.after(100, install_all)
    root.mainloop()

import importlib
for import_name, _ in REQUIRED_PACKAGES:
    try:
        importlib.import_module(import_name)
    except ImportError:
        pass

needs_guide = (
    not check_accessibility() or
    not check_input_monitoring()
)

if needs_guide:
    root = tk.Tk()
    root.title("JX-11 权限设置")
    root.geometry("420x280")
    root.resizable(False, False)
    root.eval('tk::PlaceWindow . center')

    tk.Label(root,
        text="JX-11 需要以下两项权限才能正常工作",
        font=("", 13, "bold"), pady=16).pack()

    f1 = tk.Frame(root)
    f1.pack(fill='x', padx=24, pady=4)
    acc_icon = tk.Label(f1, text="●", fg="orange", width=2)
    acc_icon.pack(side='left')
    tk.Label(f1, text="辅助功能（用于模拟键盘）", anchor='w').pack(side='left', expand=True, fill='x')
    acc_btn = tk.Button(f1, text="去开启 →",
        command=open_accessibility_prefs)
    acc_btn.pack(side='right')

    f2 = tk.Frame(root)
    f2.pack(fill='x', padx=24, pady=4)
    inp_icon = tk.Label(f2, text="●", fg="orange", width=2)
    inp_icon.pack(side='left')
    tk.Label(f2, text="输入监控（用于读取 JX-11 设备）", anchor='w').pack(side='left', expand=True, fill='x')
    inp_btn = tk.Button(f2, text="去开启 →",
        command=open_input_monitoring_prefs)
    inp_btn.pack(side='right')

    tk.Label(root,
        text="开启权限后点击「完成」",
        fg="gray", pady=12).pack()

    def on_done():
        acc_ok = check_accessibility()
        inp_ok = check_input_monitoring()
        acc_icon.config(fg="green" if acc_ok else "orange")
        inp_icon.config(fg="green" if inp_ok else "orange")
        if acc_ok and inp_ok:
            root.destroy()
        else:
            missing_list = []
            if not acc_ok: missing_list.append("辅助功能")
            if not inp_ok: missing_list.append("输入监控")
            tk.messagebox.showwarning(
                "权限未完成",
                f"请先开启：{', '.join(missing_list)}")

    import tkinter.messagebox
    tk.Button(root, text="完成", width=12,
        command=on_done).pack(pady=8)

    root.mainloop()

    if not check_accessibility() or not check_input_monitoring():
        sys.exit(1)

app_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..'))

check_script = f'''
tell application "System Events"
    set loginItems to get the name of every login item
    if loginItems does not contain "JX-11" then
        make login item at end with properties {{path:"{app_path}", hidden:true}}
    end if
end tell
'''
subprocess.run(['osascript', '-e', check_script], capture_output=True)

sys.exit(0)
