# -*- coding: utf-8 -*-
"""Test A: real mouse click on show-desktop strip (normal scenario).
Test B: minimize everything first (<2 minimise events => burst blind spot),
then click – the z-order poll must catch and restore the fences."""
import ctypes
import ctypes.wintypes as wt
import json
import time

import win32gui

user32 = ctypes.windll.user32

class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

user32.GetWindowRect.argtypes = [wt.HWND, ctypes.POINTER(RECT)]
EnumWindowsProc = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)

def z_windows():
    out = []
    cb = EnumWindowsProc(lambda h, l: (out.append(h), True)[1])
    user32.EnumWindows(cb, 0)
    return out

def class_of(hwnd):
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value

def rect_of(hwnd):
    r = RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    return (r.left, r.top, r.right, r.bottom)

with open(r"C:\Users\Administrator\Desktop\SKILL\MyDesktop\dist\nextgen_config.json",
          "r", encoding="utf-8") as f:
    geoms = [tuple(x["geometry"]) for x in json.load(f)["fences"]]

def fences_now():
    res = {}
    for hwnd in z_windows():
        l, t, r, b = rect_of(hwnd)
        g = (l, t, r - l, b - t)
        for i, geo in enumerate(geoms):
            if all(abs(g[k] - geo[k]) <= 3 for k in range(4)):
                res[i] = hwnd
    return res

def desk_of(wins):
    for h in wins:
        if class_of(h) in ("Progman", "WorkerW"):
            if user32.FindWindowExW(h, None, "SHELLDLL_DefView", None):
                return h
    for h in wins:
        if class_of(h) == "Progman":
            return h
    return None

def report(tag):
    wins = z_windows()
    desk = desk_of(wins)
    di = wins.index(desk) if desk in wins else -1
    fs = fences_now()
    vis = [h for h in wins
           if h not in fs.values()
           and class_of(h) not in ("Progman", "WorkerW", "Shell_TrayWnd",
                                   "Shell_SecondaryTrayWnd")
           and win32gui.IsWindowVisible(h) and not win32gui.IsIconic(h)]
    above = all(wins.index(fs[i]) < di for i in fs if fs[i] in wins) if di >= 0 else False
    print(f"[{tag}] desk_z={di} visible_others={len(vis)} fences={len(fs)} "
          f"all_above_desk={above}")
    return above, vis

def real_click():
    tray = win32gui.FindWindow("Shell_TrayWnd", None)
    l, t, r, b = rect_of(tray)
    cx, cy = r - 6, t + (b - t) // 2
    user32.SetCursorPos(cx, cy)
    time.sleep(0.08)
    user32.mouse_event(0x0002, 0, 0, 0, 0)
    time.sleep(0.06)
    user32.mouse_event(0x0004, 0, 0, 0, 0)
    print(f"clicked show-desktop strip at ({cx},{cy})")

def log_lines():
    with open(r"C:\Users\Administrator\Desktop\SKILL\MyDesktop\dist\app_debug.log",
              "r", encoding="utf-8", errors="replace") as f:
        return f.readlines()

# ── Test A ──
print("=== TEST A: real click, normal windows ===")
n0 = len(log_lines())
real_click()
time.sleep(1.6)
okA, _ = report("A after")
newA = "".join(log_lines()[n0:])
print("log:", " | ".join(l.split(" - ", 1)[1].strip() for l in newA if "INFO" in l) or "(none)")

# ── Test B: burst blind spot ──
print("\n=== TEST B: minimize all others first, then click ===")
# bring windows back from test A so we start from a normal state
wins = z_windows()
fs = fences_now()
for h in wins:
    if h not in fs.values() and class_of(h) not in ("Progman", "WorkerW", "Shell_TrayWnd"):
        if win32gui.IsWindowVisible(h):
            try:
                win32gui.ShowWindow(h, 9)  # SW_RESTORE
            except Exception:
                pass
time.sleep(0.8)
report("B baseline")
# minimize every visible non-fence window (one by one, spread out >0.6s to avoid burst trigger)
targets = [h for h in z_windows()
           if h not in fs.values()
           and class_of(h) not in ("Progman", "WorkerW", "Shell_TrayWnd")
           and win32gui.IsWindowVisible(h) and not win32gui.IsIconic(h)]
print(f"minimizing {len(targets)} windows slowly (no burst)...")
for h in targets:
    try:
        win32gui.ShowWindow(h, 6)  # SW_MINIMIZE
    except Exception:
        pass
    time.sleep(0.7)
report("B all-minimized")
n1 = len(log_lines())
real_click()
time.sleep(1.6)
okB, _ = report("B after click")
newB = "".join(log_lines()[n1:])
print("log:", " | ".join(l.split(" - ", 1)[1].strip() for l in newB if "INFO" in l) or "(none)")

print(f"\nRESULT: A={'PASS' if okA else 'FAIL'}  B={'PASS' if okB else 'FAIL'}")
