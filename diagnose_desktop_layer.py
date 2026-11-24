"""Read-only snapshot of the desktop z-order layer.

Prints, in z-order (top = index 0):
  * Progman / WorkerW / SHELLDLL_DefView positions
  * every fence window (property DesktopPartition.Window or Qt window of the app)
so we can tell whether fences end up above or below the desktop layer.

Usage: python diagnose_desktop_layer.py [--tag LABEL]
"""
import ctypes
import ctypes.wintypes as wt
import sys

user32 = ctypes.windll.user32
user32.GetWindowLongW.argtypes = [wt.HWND, ctypes.c_int]
user32.GetWindowLongW.restype = ctypes.c_long
user32.EnumWindows.argtypes = [ctypes.c_void_p, wt.LPARAM]
user32.GetClassNameW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
user32.GetPropW.argtypes = [wt.HWND, wt.LPCWSTR]
user32.GetPropW.restype = wt.HANDLE
user32.GetWindow.argtypes = [wt.HWND, ctypes.c_uint]
user32.GetWindow.restype = wt.HWND
user32.GetWindowRect.argtypes = [wt.HWND, ctypes.POINTER(wt.RECT)]

GWL_EXSTYLE = -20
GWL_STYLE = -16
WS_CHILD = 0x40000000
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000
WS_EX_APPWINDOW = 0x00040000
GW_OWNER = 4
GW_HWNDPREV = 3
MARKER = "DesktopPartition.Window"

EnumProc = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)


def cls(hwnd):
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def title(hwnd):
    buf = ctypes.create_unicode_buffer(512)
    user32.GetWindowTextW(hwnd, buf, 512)
    return buf.value


def rect(hwnd):
    r = wt.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    return (r.left, r.top, r.right - r.left, r.bottom - r.top)


def snapshot(tag):
    order = []

    def cb(hwnd, _):
        order.append(hwnd)
        return True

    user32.EnumWindows(EnumProc(cb), 0)

    progman = user32.FindWindowW("Progman", None)
    fence_hwnds = [
        h for h in order
        if user32.GetPropW(h, MARKER) or cls(h) == "Qt51514QWindowToolSaveBits"
        or (cls(h).startswith("Qt") and "NextGen" in title(h))
    ]

    def index(hwnd):
        try:
            return order.index(hwnd)
        except ValueError:
            return None

    print(f"\n===== {tag} =====  total top-level windows: {len(order)}")
    print(f"Progman            hwnd={progman} z={index(progman)}")
    for h in order:
        c = cls(h)
        if c in ("WorkerW", "SHELLDLL_DefView", "Progman"):
            has_def = bool(user32.FindWindowExW(h, 0, "SHELLDLL_DefView", None))
            print(f"  {c:<18} hwnd={h:<10} z={index(h):<4} def_view_inside={has_def} "
                  f"vis={user32.IsWindowVisible(h)} rect={rect(h)}")
    print("fences:")
    for h in fence_hwnds:
        style = user32.GetWindowLongW(h, GWL_STYLE) & 0xFFFFFFFF
        ex = user32.GetWindowLongW(h, GWL_EXSTYLE) & 0xFFFFFFFF
        parent = user32.GetParent(h) if hasattr(user32, "GetParent") else 0
        print(f"  hwnd={h:<10} z={index(h):<4} class={cls(h):<32} title={title(h)!r}")
        print(f"      vis={user32.IsWindowVisible(h)} iconic={user32.IsIconic(h)} "
              f"rect={rect(h)} parent={parent} owner={user32.GetWindow(h, GW_OWNER)}")
        print(f"      CHILD={bool(style & WS_CHILD)} TOOLWINDOW={bool(ex & WS_EX_TOOLWINDOW)} "
              f"NOACTIVATE={bool(ex & WS_EX_NOACTIVATE)} APPWINDOW={bool(ex & WS_EX_APPWINDOW)}")
        prev = user32.GetWindow(h, GW_HWNDPREV)
        if prev:
            print(f"      direct window ABOVE it: hwnd={prev} class={cls(prev)}")
    # top 12 windows overall for context
    print("top 12 in z-order:")
    for i, h in enumerate(order[:12]):
        print(f"  {i:<3} hwnd={h:<10} class={cls(h):<28} vis={user32.IsWindowVisible(h)} "
              f"iconic={user32.IsIconic(h)} title={title(h)[:40]!r}")


if __name__ == "__main__":
    tag = sys.argv[2] if len(sys.argv) > 2 else "snapshot"
    snapshot(tag)
