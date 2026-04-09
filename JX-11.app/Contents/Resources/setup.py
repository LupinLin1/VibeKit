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
    root.geometry("460x320")
    root.resizable(False, False)
    root.eval('tk::PlaceWindow . center')

    tk.Label(root,
        text="JX-11 需要以下两项权限才能正常工作",
        font=("", 13, "bold"), pady=16).pack()

    f1 = tk.Frame(root)
    f1.pack(fill='x', padx=24, pady=4)
    acc_icon = tk.Label(f1, text="●", fg="orange", width=2, font=("", 14))
    acc_icon.pack(side='left')
    acc_info = tk.Frame(f1)
    acc_info.pack(side='left', expand=True, fill='x')
    tk.Label(acc_info, text="辅助功能（用于模拟键盘）", anchor='w').pack(side='top')
    tk.Label(acc_info, text="  让 JX-11 能发送按键到其他应用", anchor='w',
             fg="#888888", font=("", 9)).pack(side='top')
    acc_btn = tk.Button(f1, text="去开启 →",
        command=open_accessibility_prefs)
    acc_btn.pack(side='right')

    f2 = tk.Frame(root)
    f2.pack(fill='x', padx=24, pady=4)
    inp_icon = tk.Label(f2, text="●", fg="orange", width=2, font=("", 14))
    inp_icon.pack(side='left')
    inp_info = tk.Frame(f2)
    inp_info.pack(side='left', expand=True, fill='x')
    tk.Label(inp_info, text="输入监控（用于读取 JX-11 设备）", anchor='w').pack(side='top')
    tk.Label(inp_info, text="  让 JX-11 能接收蓝牙遥控器按键", anchor='w',
             fg="#888888", font=("", 9)).pack(side='top')
    inp_btn = tk.Button(f2, text="去开启 →",
        command=open_input_monitoring_prefs)
    inp_btn.pack(side='right')

    tk.Label(root,
        text="开启权限后「继续」按钮将自动激活",
        fg="gray", pady=12).pack()

    continue_btn = tk.Button(root, text="继续", width=12,
        state="disabled", command=root.destroy)
    continue_btn.pack(pady=8)

    def poll_permissions():
        acc_ok = check_accessibility()
        inp_ok = check_input_monitoring()
        acc_icon.config(text="✓" if acc_ok else "●",
                        fg="green" if acc_ok else "orange")
        inp_icon.config(text="✓" if inp_ok else "●",
                        fg="green" if inp_ok else "orange")
        if acc_ok and inp_ok:
            continue_btn.config(state="normal")
        else:
            root.after(1500, poll_permissions)

    root.after(1500, poll_permissions)

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
