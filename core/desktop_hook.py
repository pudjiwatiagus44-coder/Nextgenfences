"""
Windows 妗岄潰鏄剧ず/闅愯棌浜嬩欢鐩戝惉鍣?
"""
import logging
import os

import win32con
import win32gui
import win32process
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

logger = logging.getLogger(__name__)

class DesktopHook(QObject):
    """
    鐩戝惉 Windows 妗岄潰鏄剧ず浜嬩欢锛圵in+D锛?
    褰撴娴嬪埌妗岄潰鏄剧ず鏃讹紝鍙戝嚭淇″彿閫氱煡涓荤▼搴忔仮澶?Fence 绐楀彛
    """
    desktop_shown = pyqtSignal()  # 妗岄潰鏄剧ず淇″彿
    desktop_hidden = pyqtSignal()  # 妗岄潰闅愯棌淇″彿
    
    def __init__(self):
        super().__init__()
        self._last_desktop_state = False
        self._check_timer = QTimer()
        self._check_timer.timeout.connect(self._check_desktop_state)
        self._self_pid = os.getpid()
        self._ignored_classes = {
            "Progman",
            "WorkerW",
            "Shell_TrayWnd",
            "Button",  # Start button
            "Shell_SecondaryTrayWnd",
        }        
    def start(self, interval_ms=500):
        logger.info(f"Starting desktop hook with {interval_ms}ms interval")
        self._check_timer.start(interval_ms)
        
    def stop(self):
        """鍋滄鐩戝惉"""
        logger.info("Stopping desktop hook")
        self._check_timer.stop()
        
    def _check_desktop_state(self):
        """妫€鏌ユ闈㈡樉绀虹姸鎬?""
        try:
            is_visible = self._is_desktop_visible()
            
            # 鐘舵€佸彉鍖栨椂鍙戝嚭淇″彿
            if is_visible != self._last_desktop_state:
                if is_visible:
                    logger.info("Desktop shown detected (Win+D pressed)")
                    self.desktop_shown.emit()
                else:
                    logger.info("Desktop hidden detected")
                    self.desktop_hidden.emit()
                    
                self._last_desktop_state = is_visible
                
        except Exception as e:
            logger.error(f"Error checking desktop state: {e}")
    
    def _is_desktop_visible(self):
        """Return True when no other process has a visible, non-minimized window."""
        try:
            visible_found = False

            def enum_handler(hwnd, _):
                nonlocal visible_found
                if visible_found:
                    return False

                if not win32gui.IsWindowVisible(hwnd):
                    return True

                if win32gui.IsIconic(hwnd):
                    return True

                class_name = win32gui.GetClassName(hwnd)
                if class_name in self._ignored_classes:
                    return True

                try:
                    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
                    if right - left == 0 or bottom - top == 0:
                        return True
                except win32gui.error:
                    return True

                try:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                except win32gui.error:
                    return True

                if pid == self._self_pid:
                    return True

                title = win32gui.GetWindowText(hwnd)
                if title == "Program Manager":
                    return True

                visible_found = True
                return False

            win32gui.EnumWindows(enum_handler, None)
            return not visible_found

        except Exception as e:
            logger.error(f"Error in _is_desktop_visible: {e}")
            return False
