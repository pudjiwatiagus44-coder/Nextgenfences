"""
全局键盘钩子，拦截 Win+D 按键。
当 Win+D 被按下时，最小化所有窗口（除了 Fence 分区窗口），从而"模拟"显示桌面效果。
"""

import logging

import ctypes
import ctypes.wintypes as wintypes

import win32gui
import win32con

from utils.window_markers import is_partition_window

logger = logging.getLogger(__name__)

WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_SYSKEYDOWN = 0x0104
WM_KEYUP = 0x0101
WM_SYSKEYUP = 0x0105

VK_LWIN = 0x5B
VK_RWIN = 0x5C
VK_D = 0x44


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class GlobalKeyboardHook:
    """
    全局键盘钩子，拦截 Win+D 按键。
    """

    _instance = None
    _hook_id = None
    _pressed_keys: set = set()
    _fence_hwnds: set = set()

    def __init__(self):
        GlobalKeyboardHook._instance = self

    @classmethod
    def set_fence_hwnds(cls, hwnds):
        """设置需要监控的 Fence 窗口句柄。"""
        cls._fence_hwnds = set(hwnds)
        logger.info(f"Updated fence HWNDs: {hwnds}")

    @classmethod
    def add_fence_hwnd(cls, hwnd):
        """添加一个 Fence 窗口句柄。"""
        cls._fence_hwnds.add(hwnd)

    @classmethod
    def clear_fence_hwnds(cls):
        """清除所有 Fence 窗口句柄。"""
        cls._fence_hwnds.clear()

    @classmethod
    def _low_level_keyboard_proc(cls, nCode, wParam, lParam):
        """
        低级键盘钩子回调函数。
        """
        if nCode >= 0:
            kb_struct = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
            vk_code = kb_struct.vkCode

            if wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
                # Track Win key
                if vk_code in (VK_LWIN, VK_RWIN):
                    cls._pressed_keys.add("WIN")
                # Detect Win+D
                elif vk_code == VK_D and "WIN" in cls._pressed_keys:
                    logger.info("Win+D intercepted by GlobalKeyboardHook")
                    cls._pressed_keys.clear()
                    cls._minimize_except_fences()
                    return 1  # Suppress the keypress

            elif wParam in (WM_KEYUP, WM_SYSKEYUP):
                if vk_code in (VK_LWIN, VK_RWIN):
                    cls._pressed_keys.discard("WIN")

        return ctypes.windll.user32.CallNextHookEx(
            cls._hook_id, nCode, wParam, lParam
        )

    @classmethod
    def _minimize_except_fences(cls):
        """
        最小化所有窗口，除了 Fence 分区窗口。
        """

        def enum_handler(hwnd, _):
            if not win32gui.IsWindowVisible(hwnd):
                return True

            if win32gui.IsIconic(hwnd):
                return True

            # Skip our own fence windows
            if hwnd in cls._fence_hwnds or is_partition_window(hwnd):
                return True

            # Skip shell / desktop / taskbar
            cls_name = win32gui.GetClassName(hwnd)
            if cls_name in ("Progman", "WorkerW", "Shell_TrayWnd",
                            "Button", "Shell_SecondaryTrayWnd"):
                return True

            # Minimize everything else
            try:
                win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
            except Exception:
                pass

            return True

        try:
            win32gui.EnumWindows(enum_handler, None)
            logger.info("Minimized all windows except fences")
        except Exception as e:
            logger.error(f"Error minimizing windows: {e}")

    @classmethod
    def get_pressed_keys(cls):
        return cls._pressed_keys.copy()

    def install(self):
        """
        安装全局键盘钩子。
        """
        try:
            cls = GlobalKeyboardHook

            # Create the callback function
            cls._hook_proc = ctypes.WINFUNCTYPE(
                ctypes.c_long,   # return type
                ctypes.c_int,    # nCode
                ctypes.c_uint,   # wParam
                ctypes.POINTER(ctypes.c_ulong),  # lParam
            )(cls._low_level_keyboard_proc)

            # NOTE: 钩子回调位于当前进程内（Python ctypes 回调），hMod 必须传 NULL。
            # 传 GetModuleHandleW(0) 会导致 SetWindowsHookExW 返回 126
            # (ERROR_MOD_NOT_FOUND)，详见 MSDN 对 hMod 参数的说明。
            cls._hook_id = ctypes.windll.user32.SetWindowsHookExW(
                WH_KEYBOARD_LL,
                cls._hook_proc,
                0,  # hMod: NULL (callback is in current process)
                0,  # dwThreadId: 0 = hook all threads
            )

            if cls._hook_id:
                logger.info("Global keyboard hook installed successfully")
            else:
                err = ctypes.windll.kernel32.GetLastError()
                logger.error(f"Failed to install keyboard hook, GetLastError={err}")
        except Exception as e:
            logger.error(f"Error installing keyboard hook: {e}")

    def uninstall(self):
        """
        卸载全局键盘钩子。
        """
        cls = GlobalKeyboardHook
        if cls._hook_id:
            try:
                ctypes.windll.user32.UnhookWindowsHookEx(cls._hook_id)
                cls._hook_id = None
                logger.info("Global keyboard hook uninstalled")
            except Exception as e:
                logger.error(f"Error uninstalling keyboard hook: {e}")
