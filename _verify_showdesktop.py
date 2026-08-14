# -*- coding: utf-8 -*-
"""Programmatic verification: does clicking the taskbar "Show Desktop" button
keep the NextGenFences partition windows visible?

Method:
1. Match fence HWNDs by rect against nextgen_config.json geometries.
2. Identify the desktop view window (Progman / WorkerW w/ SHELLDLL_DefView).
3. Real mouse click on the show-desktop strip (far-right edge of taskbar).
4. Compare z-order + WindowFromPoint at fence centers BEFORE vs AFTER.
5. Save before/after screenshots and per-region mean-color for pixel diff.

PASS = after click, every fence is above the desktop view window in z-order
       AND WindowFromPoint at fence centers still hits the fence (or child).
"""

import ctypes
import ctypes.wintypes as wt
import json
import sys
import time

import win32gui

from PIL import ImageGrab

# ── constants ─────────────────────────────────────────────────────────
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
WM_COMMAND = 0x0111
SC_MINIMIZEALL = 0xF020
SHOWDESKTOP_CMD = 419  # what the taskbar button sends

user32 = ctypes.windll.user32

class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

EnumWindowsProc = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)

user32.GetWindowRect.argtypes = [wt.HWND, ctypes.POINTER(RECT)]
user32.GetClassNameW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
user32.WindowFromPoint.argtypes = [POINT]
user32.WindowFromPoint.restype = wt.HWND
user32.FindWindowExW.argtypes = [wt.HWND, wt.HWND, wt.LPWSTR, wt.LPWSTR]
user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
user32.SendMessageW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]

# ── helpers ───────────────────────────────────────────────────────────

def class_of(hwnd):
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value

def rect_of(hwnd):
    r = RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    return (r.left, r.top, r.right, r.bottom)

def z_windows():
    """Return top-level windows in top→bottom z-order (EnumWindows order)."""
    out = []
    cb = EnumWindowsProc(lambda h, l: (out.append(h), True)[1])
    user32.EnumWindows(cb, 0)
    return out

def z_index(windows, hwnd):
    try:
        return windows.index(hwnd)
    except ValueError:
        return -1

def click_at(x, y):
    user32.SetCursorPos(int(x), int(y))
    time.sleep(0.05)
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.05)
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

def visible_normal_count(windows, fence_set):
    """Count non-fence top-level windows that are currently visible."""
    n = 0
    for hwnd in windows:
        if hwnd in fence_set:
            continue
        cls = class_of(hwnd)
        if cls in ("Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd"):
            continue
        if win32gui.IsWindowVisible(hwnd) and not win32gui.IsIconic(hwnd):
            n += 1
    return n

# ── load config ───────────────────────────────────────────────────────

CFG = r"C:\Users\Administrator\Desktop\SKILL\MyDesktop\dist\nextgen_config.json"
with open(CFG, "r", encoding="utf-8") as f:
    cfg = json.load(f)

geoms = [tuple(f["geometry"]) for f in cfg["fences"]]  # (x, y, w, h)
print(f"[cfg] {len(geoms)} fence geometries:")
for g in geoms:
    print("   ", g)

# ── match fence HWNDs ─────────────────────────────────────────────────

def match_fences():
    fences = {}
    for hwnd in z_windows():
        l, t, r, b = rect_of(hwnd)
        g = (l, t, r - l, b - t)
        for i, geo in enumerate(geoms):
            if abs(g[0] - geo[0]) <= 3 and abs(g[1] - geo[1]) <= 3 \
               and abs(g[2] - geo[2]) <= 3 and abs(g[3] - geo[3]) <= 3:
                fences[i] = hwnd
    return fences

fences = match_fences()
if len(fences) != len(geoms):
    print(f"[WARN] matched {len(fences)}/{len(geoms)} fence windows")
    missing = [i for i in range(len(geoms)) if i not in fences]
    print("   missing indices:", missing)
    for hwnd in z_windows():
        cls = class_of(hwnd)
        if "Qt" in cls and win32gui.IsWindowVisible(hwnd):
            print("   qt candidate:", hwnd, cls, rect_of(hwnd))
fence_set = set(fences.values())
print(f"[match] fence HWNDs: {[(i, hex(fences[i])) for i in sorted(fences)]}")

# ── desktop view window ───────────────────────────────────────────────

def find_desktop_view(windows):
    found = []
    for hwnd in windows:
        cls = class_of(hwnd)
        if cls in ("Progman", "WorkerW"):
            if user32.FindWindowExW(hwnd, None, "SHELLDLL_DefView", None):
                found.append((hwnd, cls))
    return found

windows = z_windows()
desk = find_desktop_view(windows)
print(f"[desk] desktop-view windows: {[(hex(h), c) for h, c in desk]}")
desk_hwnd = desk[0][0] if desk else None
if not desk_hwnd:
    # fallback: Progman
    for hwnd in windows:
        if class_of(hwnd) == "Progman":
            desk_hwnd = hwnd
            break
print(f"[desk] using desktop hwnd = {hex(desk_hwnd) if desk_hwnd else None} "
      f"({class_of(desk_hwnd) if desk_hwnd else '?'})")

# ── state snapshot ────────────────────────────────────────────────────

def snapshot(tag):
    wins = z_windows()
    di = z_index(wins, desk_hwnd) if desk_hwnd else -1
    rows = []
    for i in sorted(fences):
        h = fences[i]
        p = POINT(*(lambda r: ((r[0] + r[2]) // 2, (r[1] + r[3]) // 2))(rect_of(h)))
        hit = user32.WindowFromPoint(p)
        is_fence_hit = (hit == h) or (bool(user32.IsChild(h, hit)) if hit else False)
        rows.append((i, hex(h), z_index(wins, h), di, hex(hit) if hit else None,
                     class_of(hit) if hit else "?", is_fence_hit))
    print(f"\n=== {tag} ===")
    print(f"[z] desktop view index (0=top, -1=absent): {di}")
    ok = True
    for i, h, fi, di_, hit, hcls, is_fence in rows:
        above = di_ >= 0 and 0 <= fi < di_
        if not (above and is_fence):
            ok = False
        print(f"  fence[{i}] {h} z={fi} desk_z={di_} above_desk={above} "
              f"hit={hit} ({hcls}) fence_hit={is_fence}")
    print(f"  → {'PASS' if ok else 'FAIL'}")
    return ok

print("\n[pre] baseline snapshot...")
pre_ok = snapshot("BEFORE CLICK")

# full-screen screenshot for pixel diff
def save_region(tag):
    img = ImageGrab.grab()
    img.save(rf"C:\Users\Administrator\Desktop\SKILL\MyDesktop\_sd_{tag}_full.png")
    means = {}
    for i in sorted(fences):
        h = fences[i]
        l, t, r, b = rect_of(h)
        crop = img.crop((l, t, r, b)).resize((64, 40))
        px = list(crop.getdata())
        avg = tuple(sum(c[j] for c in px) // len(px) for j in range(3))
        means[i] = avg
    return means

means_before = save_region("before")

# ── click the show-desktop strip ──────────────────────────────────────

tray = win32gui.FindWindow("Shell_TrayWnd", None)
if tray:
    l, t, r, b = rect_of(tray)
    h = b - t
    w = r - l
    print(f"\n[click] Shell_TrayWnd rect = ({l},{t})-({r},{b})")
    if w > h:  # horizontal taskbar → strip at far right
        cx, cy = r - 6, t + h // 2
    else:      # vertical taskbar → strip at bottom
        cx, cy = l + w // 2, b - 6
    print(f"[click] clicking show-desktop strip at ({cx},{cy})")
    before_vis = visible_normal_count(z_windows(), fence_set)
    click_at(cx, cy)
    # confirm the click fired show-desktop: visible non-fence windows drop
    fired = False
    for attempt in range(4):
        time.sleep(0.35)
        now_vis = visible_normal_count(z_windows(), fence_set)
        print(f"  [t+{(attempt+1)*0.35:.2f}s] visible non-fence windows: {now_vis} (was {before_vis})")
        if now_vis < before_vis:
            fired = True
            break
    if not fired:
        # retry a couple of pixels in, then fall back to WM_COMMAND 419
        print("[click] no drop detected, retrying slightly inside...")
        click_at(r - 3 if w > h else b - 3 and r - 3, t + h // 2 if w > h else l + w // 2)
        time.sleep(0.6)
        now_vis = visible_normal_count(z_windows(), fence_set)
        print(f"  retry: visible non-fence windows: {now_vis} (was {before_vis})")
        fired = now_vis < before_vis
    if not fired and tray:
        print("[click] falling back to WM_COMMAND 419 on Shell_TrayWnd")
        user32.SendMessageW(tray, WM_COMMAND, SHOWDESKTOP_CMD, 0)
        time.sleep(0.6)
else:
    print("[click] Shell_TrayWnd not found; falling back to WM_COMMAND 419 on desktop")
    progman = win32gui.FindWindow("Progman", None)
    user32.SendMessageW(progman, WM_COMMAND, SHOWDESKTOP_CMD, 0)
    time.sleep(0.6)

# ── final state (allow 0/150/400/800ms staggered restores to finish) ──
time.sleep(1.0)
print("\n[post] waiting done, final snapshot...")
post_ok = snapshot("AFTER CLICK")
means_after = save_region("after")

# pixel-diff report
print("\n=== region mean-color before→after ===")
all_same = True
for i in sorted(fences):
    same = means_before[i] == means_after[i]
    if not same:
        all_same = False
    print(f"  fence[{i}] {means_before[i]} → {means_after[i]}  {'same' if same else 'DIFF'}")
print(f"  → regions {'identical' if all_same else 'changed (some region altered)'}")

print(f"\nRESULT: {'PASS ✅' if post_ok else 'FAIL ❌'} (before={pre_ok})")
sys.exit(0 if post_ok else 1)
