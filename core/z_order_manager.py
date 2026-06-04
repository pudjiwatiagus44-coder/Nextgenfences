import logging

import win32con
import win32gui

logger = logging.getLogger(__name__)


class ZOrderManager:
    """Manage the window host used for desktop-level fence windows."""

    _desktop_parent = None
    _progman = None

    @staticmethod
    def is_desktop_visible():
        try:
            foreground = win32gui.GetForegroundWindow()
            if foreground == 0:
                return True

            class_name = win32gui.GetClassName(foreground)
            if class_name in ("Progman", "WorkerW", "Shell_TrayWnd"):
                return True

            try:
                title = win32gui.GetWindowText(foreground)
                if not title or title == "Program Manager":
                    return True
            except Exception:
                pass

            return False
        except Exception as e:
            logger.error(f"Error in is_desktop_visible: {e}")
            return False

    @staticmethod
    def setup_window_style(hwnd):
        try:
            ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            ex_style |= win32con.WS_EX_TOOLWINDOW
            ex_style |= win32con.WS_EX_NOACTIVATE
            ex_style &= ~win32con.WS_EX_APPWINDOW
            ex_style &= ~win32con.WS_EX_TRANSPARENT
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style)
            logger.info(f"Window style configured for {hwnd}")
            return True
        except Exception as e:
            logger.error(f"Failed to setup window style: {e}")
            return False

    @staticmethod
    def force_show_window(hwnd):
        try:
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

            win32gui.ShowWindow(hwnd, win32con.SW_SHOWNOACTIVATE)
            win32gui.SetWindowPos(
                hwnd,
                win32con.HWND_TOP,
                0,
                0,
                0,
                0,
                win32con.SWP_NOMOVE
                | win32con.SWP_NOSIZE
                | win32con.SWP_NOACTIVATE
                | win32con.SWP_SHOWWINDOW,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to force show window {hwnd}: {e}")
            return False

    @staticmethod
    def embed_to_desktop(hwnd):
        try:
            ZOrderManager.setup_window_style(hwnd)
            target = ZOrderManager.get_desktop_parent(force_refresh=True)
            if not target:
                logger.error("Could not find target desktop parent")
                return False

            win32gui.SetParent(hwnd, target)
            win32gui.ShowWindow(hwnd, win32con.SW_SHOWNOACTIVATE)
            ZOrderManager.force_show_window(hwnd)
            logger.info(f"Window {hwnd} embedded to desktop parent {target}")
            return True
        except Exception as e:
            logger.error(f"Error in embed_to_desktop: {e}")
            return False

    @staticmethod
    def send_to_bottom(hwnd):
        try:
            win32gui.SetWindowPos(
                hwnd,
                win32con.HWND_BOTTOM,
                0,
                0,
                0,
                0,
                win32con.SWP_NOMOVE
                | win32con.SWP_NOSIZE
                | win32con.SWP_NOACTIVATE
                | win32con.SWP_NOSENDCHANGING,
            )
        except Exception as e:
            logger.error(f"Failed to send window {hwnd} to bottom: {e}")

    @staticmethod
    def get_workerw():
        return ZOrderManager.get_desktop_parent()

    @staticmethod
    def get_desktop_window():
        return ZOrderManager.get_desktop_parent()

    @staticmethod
    def set_as_wallpaper(hwnd):
        return ZOrderManager.embed_to_desktop(hwnd)

    @staticmethod
    def refresh_desktop_binding():
        ZOrderManager._desktop_parent = None
        ZOrderManager._progman = None
        return ZOrderManager.get_desktop_parent(force_refresh=True)

    @staticmethod
    def get_desktop_parent(force_refresh=False):
        """Return a stable Explorer desktop host window."""
        if not force_refresh and ZOrderManager._desktop_parent:
            try:
                if win32gui.IsWindow(ZOrderManager._desktop_parent):
                    return ZOrderManager._desktop_parent
            except Exception:
                pass

        progman = win32gui.FindWindow("Progman", None)
        if not progman:
            logger.error("Could not find Progman")
            return None

        ZOrderManager._progman = progman

        try:
            win32gui.SendMessageTimeout(
                progman,
                0x052C,
                0,
                0,
                win32con.SMTO_NORMAL,
                1000,
            )
        except Exception as e:
            logger.warning(f"Could not request WorkerW creation: {e}")

        desktop_parent = None

        def enum_windows(hwnd, _):
            nonlocal desktop_parent

            try:
                shell_view = win32gui.FindWindowEx(hwnd, 0, "SHELLDLL_DefView", None)
                if shell_view:
                    desktop_parent = hwnd
                    return False

                child_worker = win32gui.FindWindowEx(hwnd, 0, "WorkerW", None)
                if child_worker:
                    shell_view = win32gui.FindWindowEx(child_worker, 0, "SHELLDLL_DefView", None)
                    if shell_view:
                        desktop_parent = child_worker
                        return False
            except Exception:
                return True

            return True

        try:
            win32gui.EnumWindows(enum_windows, None)
        except Exception as e:
            logger.error(f"Failed to enumerate desktop windows: {e}")

        ZOrderManager._desktop_parent = desktop_parent or progman
        logger.info(f"Desktop parent resolved: {ZOrderManager._desktop_parent}")
        return ZOrderManager._desktop_parent
