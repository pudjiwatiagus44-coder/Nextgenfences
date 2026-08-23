# -*- coding: utf-8 -*-
"""Stability re-check: fences must STAY above the desktop view window a few
seconds after a Show-Desktop click (no explorer re-covering)."""
import ctypes
import ctypes.wintypes as wt
import json
import sys
import time

import win32gui

class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

user32 = ctypes.windll.user32
user32.GetWindowRect.argtypes = [wt.HWND, ctypes.POINTER(RECT)]
user32.GetClassNameW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
EnumWindowsProc = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)

def class_of(hwnd):
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value

def rect_of(hwnd):
    r = RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    return (r.left, r.top, r.right, r.bottom)

def z_windows():
    out = []
    cb = EnumWindowsProc(lambda h, l: (out.append(h), True)[1])
    user32.EnumWindows(cb, 0)
    return out

with open(r"C:\Users\Administrator\Desktop\SKILL\MyDesktop\dist\nextgen_config.json",
          "r", encoding="utf-8") as f:
    cfg = json.load(f)
geoms = [tuple(f["geometry"]) for f in cfg["fences"]]

def match_fences():
    fences = {}
    for hwnd in z_windows():
        l, t, r, b = rect_of(hwnd)
        g = (l, t, r - l, b - t)
        for i, geo in enumerate(geoms):
            if all(abs(g[k] - geo[k]) <= 3 for k in range(4)):
                fences[i] = hwnd
    return fences

def desk_hwnd_of(windows):
    for hwnd in windows:
        cls = class_of(hwnd)
        if cls in ("Progman", "WorkerW"):
            if user32.FindWindowExW(hwnd, None, "SHELLDLL_DefView", None):
                return hwnd
    for hwnd in windows:
        if class_of(hwnd) == "Progman":
            return hwnd
    return None

fences = match_fences()
print(f"fences matched: {len(fences)}/{len(geoms)}")

for pass_no in range(3):
    time.sleep(2.0)
    wins = z_windows()
    desk = desk_hwnd_of(wins)
    di = wins.index(desk) if desk else -1
    results = []
    for i in sorted(fences):
        fi = wins.index(fences[i])
        results.append((i, fi, di, 0 <= fi < di))
    ok = all(r[3] for r in results)
    print(f"check {pass_no+1} @ t+{2*(pass_no+1)}s: desk_z={di} | "
          + " ".join(f"f{i}={fi}{'^' if above else 'v'}" for i, fi, _, above in results)
          + f" -> {'PASS' if ok else 'FAIL'}")
    if not ok:
        sys.exit(1)
print("STABILITY PASS")
