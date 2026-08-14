# -*- coding: utf-8 -*-
"""Stability check: fences stay at desktop level, no app window below them."""
import ctypes
import json
import time

import win32gui

u = ctypes.windll.user32
b = ctypes.create_unicode_buffer(256)

def cls(h):
    u.GetClassNameW(h, b, 256)
    return b.value

cfg = json.load(open(r"C:\Users\Administrator\Desktop\SKILL\MyDesktop\dist\nextgen_config.json",
                    encoding="utf-8"))
geoms = [tuple(f["geometry"]) for f in cfg["fences"]]

def snapshot():
    order = []
    win32gui.EnumWindows(lambda h, _: (order.append(h), True)[1], None)
    desk = 0
    for h in order:
        if cls(h) in ("Progman", "WorkerW") and win32gui.FindWindowEx(h, 0, "SHELLDLL_DefView", None):
            desk = h
            break
    di = order.index(desk)
    fz = []
    for h in order:
        if cls(h).startswith("Qt6"):
            l, t, r, b_ = win32gui.GetWindowRect(h)
            g = (l, t, r - l, b_ - t)
            for geo in geoms:
                if all(abs(g[k] - geo[k]) <= 3 for k in range(4)):
                    fz.append(order.index(h))
    viol = 0
    if fz:
        top = min(fz)
        skip = {"Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd",
                "Button", "SysListView64", "SHELLDLL_DefView"}
        for i, h in enumerate(order):
            if i <= top or i in fz or cls(h) in skip:
                continue
            try:
                if win32gui.IsWindowVisible(h) and not win32gui.IsIconic(h):
                    l, t, r, b_ = win32gui.GetWindowRect(h)
                    if r - l > 1 and b_ - t > 1:
                        viol += 1
            except Exception:
                pass
    return di, sorted(fz), viol

for n in range(3):
    di, fz, viol = snapshot()
    ok = viol == 0 and all(0 <= z < di for z in fz)
    print(f"t{n}: desk_z={di} fence_z={fz} app_below_fence={viol} -> {'PASS' if ok else 'FAIL'}")
    if n < 2:
        time.sleep(2)
