import ctypes
import ctypes.wintypes
import logging


PARTITION_WINDOW_MARKER = "DesktopPartition.Window"

_user32 = ctypes.windll.user32
_user32.SetPropW.argtypes = [ctypes.wintypes.HWND, ctypes.wintypes.LPCWSTR, ctypes.wintypes.HANDLE]
_user32.SetPropW.restype = ctypes.wintypes.BOOL
_user32.GetPropW.argtypes = [ctypes.wintypes.HWND, ctypes.wintypes.LPCWSTR]
_user32.GetPropW.restype = ctypes.wintypes.HANDLE
_user32.RemovePropW.argtypes = [ctypes.wintypes.HWND, ctypes.wintypes.LPCWSTR]
_user32.RemovePropW.restype = ctypes.wintypes.HANDLE


def mark_partition_window(hwnd):
    try:
        return bool(_user32.SetPropW(int(hwnd), PARTITION_WINDOW_MARKER, 1))
    except Exception as e:
        logging.error(f"Failed to mark partition window {hwnd}: {e}")
        return False


def unmark_partition_window(hwnd):
    try:
        _user32.RemovePropW(int(hwnd), PARTITION_WINDOW_MARKER)
    except Exception as e:
        logging.error(f"Failed to unmark partition window {hwnd}: {e}")


def is_partition_window(hwnd):
    try:
        return bool(_user32.GetPropW(int(hwnd), PARTITION_WINDOW_MARKER))
    except Exception:
        return False
