#!/usr/bin/env python3
import hid, time, subprocess, os, sys, json, signal, threading
import Quartz

LOG         = os.path.expanduser("~/Library/Logs/jx11-daemon.log")
CONFIG_PATH = os.path.expanduser("~/.config/jx11/config.json")

VENDOR_ID  = 0x05AC
PRODUCT_ID = 0x0220

DOUBLE_CLICK_WINDOW  = 0.30
LONG_PRESS_THRESHOLD = 0.50

BUTTONS = {
    (0xF4, 0xE1, 0x15): "滚轮上",
    (0xF4, 0xC1, 0x26): "滚轮下",
    (0x2C, 0x91, 0x1F): "向左",
    (0xBC, 0x92, 0x1F): "向右",
    (0xF4, 0x01, 0x19): "确认键",
}

DEFAULT_CONFIG = {
    "滚轮上": {"type": "key", "keycode": 126, "modifiers": [], "label": "↑"},
    "滚轮下": {"type": "key", "keycode": 125, "modifiers": [], "label": "↓"},
    "向左":  {"type": "key", "keycode": 53,  "modifiers": [], "label": "ESC"},
    "向右":  {"type": "key", "keycode": 36,  "modifiers": [], "label": "↩"},
    "确认键": {"type": "double_modifier", "keycode": 58, "flag": "left_option", "label": "⌥⌥"},
}

def log(msg):
    with open(LOG, "a") as f:
        import datetime
        f.write(f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S.%f}] {msg}\n")

def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH) as f:
                return json.load(f)
        except Exception as e:
            log(f"配置加载失败，使用默认: {e}")
    return dict(DEFAULT_CONFIG)

def osascript(script):
    subprocess.Popen(['osascript', '-e', script])

def execute_action(action):
    if not action:
        return
    t = action.get('type', 'key')
    if t == 'key':
        kc   = action['keycode']
        mods = action.get('modifiers', [])
        if mods:
            mod_str = ', '.join(f'{m} down' for m in mods)
            osascript(f'tell application "System Events" to key code {kc} using {{{mod_str}}}')
        else:
            osascript(f'tell application "System Events" to key code {kc}')
    elif t == 'double_modifier':
        _send_double_modifier(action['keycode'], action.get('flag', 'left_option'))
    elif t == 'cycle_windows':
        _cycle_windows()

def _send_double_modifier(keycode, flag_name):
    flag_map = {
        'left_option':   Quartz.kCGEventFlagMaskAlternate | 0x000020,
        'right_option':  Quartz.kCGEventFlagMaskAlternate | 0x000040,
        'left_command':  Quartz.kCGEventFlagMaskCommand   | 0x000008,
        'right_command': Quartz.kCGEventFlagMaskCommand   | 0x000010,
    }
    flags = flag_map.get(flag_name, Quartz.kCGEventFlagMaskAlternate | 0x000020)
    src = Quartz.CGEventSourceCreate(Quartz.kCGEventSourceStateHIDSystemState)
    for _ in range(2):
        press = Quartz.CGEventCreate(src)
        Quartz.CGEventSetType(press, Quartz.kCGEventFlagsChanged)
        Quartz.CGEventSetIntegerValueField(press, Quartz.kCGKeyboardEventKeycode, keycode)
        Quartz.CGEventSetFlags(press, flags)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, press)
        time.sleep(0.01)
        release = Quartz.CGEventCreate(src)
        Quartz.CGEventSetType(release, Quartz.kCGEventFlagsChanged)
        Quartz.CGEventSetIntegerValueField(release, Quartz.kCGKeyboardEventKeycode, keycode)
        Quartz.CGEventSetFlags(release, 0)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, release)
        time.sleep(0.05)

# ── 轮换窗口 ──────────────────────────────────────────────
_cycle_idx = 0

def _cycle_windows():
    global _cycle_idx
    try:
        import AppKit
        ws = AppKit.NSWorkspace.sharedWorkspace()
        apps = sorted(
            [a for a in ws.runningApplications()
             if a.activationPolicy() == AppKit.NSApplicationActivationPolicyRegular
             and a.localizedName()],
            key=lambda a: a.localizedName().lower()
        )
        if not apps:
            return
        _cycle_idx = _cycle_idx % len(apps)
        app = apps[_cycle_idx]
        _cycle_idx = (_cycle_idx + 1) % len(apps)
        app.activateWithOptions_(AppKit.NSApplicationActivateIgnoringOtherApps)
        log(f"轮换应用: {app.localizedName()}")
    except Exception as e:
        log(f"轮换窗口失败: {e}")

# ── 按键处理 ──────────────────────────────────────────────
DOUBLE_CLICK_WINDOW  = 0.55   # 秒：松开后等待第二次按压的窗口
LONG_PRESS_THRESHOLD = 0.50   # 秒：按住超过此时长视为长按

_pending          = {}   # name -> Timer
_press_time       = {}   # name -> press timestamp
_suppress_release = set()  # 双击后抑制第二次松开触发单击
_last_press       = [None]

def on_press(name):
    _press_time[name] = time.time()
    cfg    = load_config()
    action = cfg.get(name)
    double = cfg.get(name + '_double')

    if not double:
        if action:
            log(f"触发: {name} → {action.get('label', '?')}")
            execute_action(action)
        return

    if name in _pending:
        _pending.pop(name).cancel()
        _suppress_release.add(name)   # 抑制第二次松开
        log(f"触发: {name} 双击 → {double.get('label', '?')}")
        execute_action(double)
    else:
        pass  # 等待第二次按下

def on_release(name):
    # 双击后第二次松开：忽略
    if name in _suppress_release:
        _suppress_release.discard(name)
        return

    cfg    = load_config()
    action = cfg.get(name)
    double = cfg.get(name + '_double')
    long   = cfg.get(name + '_long')

    # 长按检测（优先于双击）
    if long and name not in _pending:
        held = time.time() - _press_time.get(name, time.time())
        if held >= LONG_PRESS_THRESHOLD:
            log(f"触发: {name} 长按 → {long.get('label', '?')}")
            execute_action(long)
            return

    if not double or name in _pending:
        return

    def fire_single():
        _pending.pop(name, None)
        if action:
            log(f"触发: {name} → {action.get('label', '?')}")
            execute_action(action)

    t = threading.Timer(DOUBLE_CLICK_WINDOW, fire_single)
    _pending[name] = t
    t.start()

# SIGHUP → 配置在每次按键时动态读取，无需重启
signal.signal(signal.SIGHUP, lambda *_: log("收到 SIGHUP"))

# ── 设备连接 ──────────────────────────────────────────────
def connect():
    try:
        devs = hid.enumerate(VENDOR_ID, PRODUCT_ID)
        if not devs:
            return None
        d = next((x for x in devs if x['usage_page'] == 12), devs[0])
        h = hid.device()
        h.open_path(d['path'])
        h.set_nonblocking(True)
        return h
    except Exception:
        return None

log("守护进程启动")
h = None
retry = 0
while not h:
    h = connect()
    if not h:
        retry += 1
        if retry % 20 == 0:
            log(f"等待 JX-11 连接中...（已重试 {retry} 次）")
        if retry >= 200:
            log("超时：200次重试后仍未找到 JX-11，退出")
            sys.exit(1)
        time.sleep(3)

prev_btn = 0x00
log("JX-11 已连接")

try:
    while True:
        try:
            data = h.read(64)
        except Exception:
            log("设备断开，等待重连...")
            h = None
            while not h:
                time.sleep(2)
                h = connect()
            log("已重连")
            prev_btn = 0x00
            continue

        if data and len(data) >= 5:
            btn         = data[1]
            fingerprint = (data[2], data[3], data[4])
            name        = BUTTONS.get(fingerprint)

            if btn == 0x07 and prev_btn != 0x07:
                if name:
                    _last_press[0] = name
                    on_press(name)
            elif btn != 0x07 and prev_btn == 0x07:
                if _last_press[0]:
                    on_release(_last_press[0])
                    _last_press[0] = None

            prev_btn = btn

        time.sleep(0.001)

except Exception as e:
    log(f"异常退出: {e}")
    sys.exit(1)
