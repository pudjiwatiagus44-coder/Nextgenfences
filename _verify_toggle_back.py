# -*- coding: utf-8 -*-
"""Desktop-widget z-order semantics test.

Scenario C (the user-reported bug):
  1. Open a real window (Notepad) positioned OVER a fence.
  2. Click show-desktop -> all windows minimise, fences must stay visible
     (above the desktop layer WorkerW).
  3. Click show-desktop AGAIN (toggle back) -> Notepad is restored and must
     now COVER the fence (fence stays at desktop level, below app windows).
"""
import ctypes
import ctypes.wintypes as wt
import json
import subprocess
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
    cfg = json.load(f)
geoms = [tuple(x["geometry"]) for x in cfg["fences"]]

def fences_now():
    res = {}
    for hwnd in z_windows():
        if not class_of(hwnd).startswith("Qt6"):   # only our fence windows
            continue
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
    return None

def zpos(hwnd, wins=None):
    wins = wins or z_windows()
    return wins.index(hwnd) if hwnd in wins else -1

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

# ── step 0: open a GDI console window over fence 0 ──
print("=== TEST C: window-over-fence -> show desktop -> toggle back ===")
x, y, w, h = geoms[0]
np = subprocess.Popen(["cmd.exe", "/c", "pause"])
time.sleep(1.5)
# find the console window and move it over fence 0
note_hwnd = None
deadline = time.time() + 5
while time.time() < deadline and not note_hwnd:
    for h_ in z_windows():
        if class_of(h_) == "ConsoleWindowClass":
            note_hwnd = h_
            break
    time.sleep(0.3)
assert note_hwnd, "console window not found"
win32gui.SetWindowPos(note_hwnd, 0, x, y, max(w, 400), max(h, 300), 0x0004)
win32gui.ShowWindow(note_hwnd, 1)  # SW_NORMAL, brings to front
time.sleep(0.8)

fs = fences_now()
wins = z_windows()
note_z, fence_z = zpos(note_hwnd, wins), zpos(fs[0], wins)
print(f"[C1 baseline] notepad_z={note_z} fence0_z={fence_z} "
      f"notepad_in_front={note_z < fence_z}")
ok1 = note_z < fence_z

# ── step 1: click show desktop ──
n0 = len(log_lines())
real_click()
time.sleep(1.8)
fs = fences_now()
wins = z_windows()
desk = desk_of(wins)
di = wins.index(desk) if desk in wins else -1
note_z = zpos(note_hwnd, wins)
fz = [zpos(fs[i], wins) for i in sorted(fs)]
covered_by_desk = any(z > di for z in fz if z >= 0)
visible = all(0 <= z < di for z in fz)
print(f"[C2 show-desktop] desk_z={di} fence_z={fz} notepad_z={note_z}(iconic) "
      f"fences_visible_above_desk={visible}")
ok2 = visible and not covered_by_desk

# ── step 2: click again to toggle back ──
real_click()
time.sleep(1.8)
fs = fences_now()
wins = z_windows()
note_z, fence_z = zpos(note_hwnd, wins), zpos(fs[0], wins)
# WindowFromPoint at fence-0 centre should hit Notepad (it covers the fence)
cxp, cyp = x + w // 2, y + h // 2
hit = user32.WindowFromPoint(wt.POINT(cxp, cyp))
hit_desc = f"{hex(hit)}/{class_of(hit)}" if hit else "none"
print(f"[C3 toggle-back] window_z={note_z} fence0_z={fence_z} "
      f"window_in_front={note_z < fence_z} WindowFromPoint={hit_desc} (info only)")
ok3 = note_z < fence_z

new = "".join(log_lines()[n0:])
print("log:", " | ".join(l.split(" - ", 1)[1].strip() for l in new if "INFO" in l) or "(none)")

# cleanup: close notepad
win32gui.PostMessage(note_hwnd, 0x0010, 0, 0)  # WM_CLOSE

print(f"\nRESULT: C1={'PASS' if ok1 else 'FAIL'} C2={'PASS' if ok2 else 'FAIL'} "
      f"C3={'PASS' if ok3 else 'FAIL'}  -> {'ALL PASS' if (ok1 and ok2 and ok3) else 'FAIL'}")
