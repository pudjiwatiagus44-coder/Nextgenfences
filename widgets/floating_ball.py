import sys
import os
import logging
from PyQt6.QtWidgets import QWidget, QMenu, QApplication
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QRect, QPropertyAnimation, QEasingCurve, QTimer
from PyQt6.QtGui import QPainter, QColor, QBrush, QCursor, QAction

import win32gui
import win32con

from utils.window_markers import is_partition_window

class FloatingBallWidget(QWidget):
    clicked = pyqtSignal()
    settings_requested = pyqtSignal()
    create_custom_fence_requested = pyqtSignal()
    create_fence_requested = pyqtSignal()
    uninstall_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Initial size and position
        self.resize(60, 60)
        # Position at bottom center by default, but customizable
        screen_geo = QApplication.primaryScreen().geometry()
        x_pos = (screen_geo.width() - self.width()) // 2
        y_pos = screen_geo.height() - 150
        self.move(x_pos, y_pos)
        
        self.dragging = False
        self.drag_start_pos = QPoint()
        self.window_start_pos = QPoint()
        
        # Color style
        self.bg_color = QColor(0, 120, 215, 200) # Windows Blue
        self.hover_color = QColor(0, 150, 255, 230)
        self.current_color = self.bg_color
        
        # Docking state
        self.is_docked = False
        self.dock_edge = None # 'left', 'right', 'top'
        self.dock_timer = QTimer(self)
        self.dock_timer.setSingleShot(True)
        self.dock_timer.timeout.connect(self.animate_hide_dock)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        painter.setBrush(QBrush(self.current_color))
        painter.setPen(Qt.PenStyle.NoPen)
        
        # Draw circle
        painter.drawEllipse(0, 0, self.width(), self.height())
        
        # Draw "Home" icon or text (Simple rectangle for now representing desktop)
        if self.is_docked and self.dock_edge:
            # If docked and hidden (mostly), we might want to draw a simple line or indicator
            # But since we slide the widget off screen, the normal drawing is fine.
            # Just ensure we have a visual cue when mostly hidden.
            pass

        painter.setBrush(QBrush(QColor(255, 255, 255)))
        
        # Draw a little "Desktop" icon shape
        # Screen rect
        w, h = self.width(), self.height()
        rect_w, rect_h = w * 0.5, h * 0.4
        painter.drawRoundedRect(int((w - rect_w)/2), int((h - rect_h)/2), int(rect_w), int(rect_h), 2, 2)
        # Stand
        painter.drawRect(int(w/2 - 2), int(h/2 + rect_h/2), 4, 4)
        # Base
        painter.drawRect(int(w/2 - 8), int(h/2 + rect_h/2 + 4), 16, 2)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.drag_start_pos = event.globalPosition().toPoint()
            self.window_start_pos = self.pos()
            self.current_color = self.hover_color
            self.update()

    def mouseMoveEvent(self, event):
        if self.dragging:
            delta = event.globalPosition().toPoint() - self.drag_start_pos
            self.move(self.window_start_pos + delta)

    def mouseReleaseEvent(self, event):
        if self.dragging:
            self.dragging = False
            self.current_color = self.bg_color
            self.update()
            
            # Check if it was a click (small movement)
            if (event.globalPosition().toPoint() - self.drag_start_pos).manhattanLength() < 5:
                self.clicked.emit()
                self.show_desktop()
            else:
                # Check docking
                self.check_docking()

    def check_docking(self):
        # 使用完整的屏幕几何形状（包括任务栏区域）
        screen_geo = QApplication.primaryScreen().geometry()
        pos = self.pos()
        x, y = pos.x(), pos.y()
        w, h = self.width(), self.height()
        
        # Threshold to trigger docking
        threshold = 20
        
        docked = False
        target_x = x
        target_y = y
        
        # Left edge
        if x < threshold:
            target_x = 0
            self.dock_edge = 'left'
            docked = True
        # Right edge
        elif x + w > screen_geo.width() - threshold:
            target_x = screen_geo.width() - w
            self.dock_edge = 'right'
            docked = True
        # Top edge
        elif y < threshold:
            target_y = 0
            self.dock_edge = 'top'
            docked = True
        # Bottom edge - 使用完整屏幕高度
        elif y + h > screen_geo.height() - threshold:
            target_y = screen_geo.height() - h
            self.dock_edge = 'bottom'
            docked = True
            
        if docked:
            self.is_docked = True
            # Snap to edge first
            self.move(target_x, target_y)
            # Then hide after delay
            self.dock_timer.start(500)
        else:
            self.is_docked = False
            self.dock_edge = None

    def animate_hide_dock(self):
        if not self.is_docked: return
        
        # 使用 geometry() 获取完整屏幕区域（包括任务栏）
        screen_geo = QApplication.primaryScreen().geometry()
        pos = self.pos()
        w, h = self.width(), self.height()
        
        target_pos = pos
        visible_amount = 12 # 显示的像素数量，增加一点确保可见
        
        if self.dock_edge == 'left':
            target_pos = QPoint(-w + visible_amount, pos.y())
        elif self.dock_edge == 'right':
            target_pos = QPoint(screen_geo.width() - visible_amount, pos.y())
        elif self.dock_edge == 'top':
            target_pos = QPoint(pos.x(), -h + visible_amount)
        elif self.dock_edge == 'bottom':
            # 底部停靠时，让大部分隐藏在任务栏下方，只露出顶部一点点
            # 使用 screen_geo.height() - visible_amount 确保顶部有可见部分
            target_pos = QPoint(pos.x(), screen_geo.height() - visible_amount)
            
        # 确保窗口始终可见
        self.show()
        self.setWindowOpacity(1.0)
        
        self.start_animation(target_pos)

    def animate_show_dock(self):
        if not self.is_docked: return
        
        # 使用完整的屏幕几何形状
        screen_geo = QApplication.primaryScreen().geometry()
        pos = self.pos()
        w, h = self.width(), self.height()
        
        target_pos = pos
        
        if self.dock_edge == 'left':
            target_pos = QPoint(0, pos.y())
        elif self.dock_edge == 'right':
            target_pos = QPoint(screen_geo.width() - w, pos.y())
        elif self.dock_edge == 'top':
            target_pos = QPoint(pos.x(), 0)
        elif self.dock_edge == 'bottom':
            target_pos = QPoint(pos.x(), screen_geo.height() - h)
            
        self.start_animation(target_pos)

    def start_animation(self, target_pos):
        self.anim = QPropertyAnimation(self, b"pos")
        self.anim.setDuration(200)
        self.anim.setStartValue(self.pos())
        self.anim.setEndValue(target_pos)
        self.anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        self.anim.start()

    def enterEvent(self, event):
        self.current_color = self.hover_color
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        if self.is_docked:
            self.dock_timer.stop()
            self.animate_show_dock()
            
        self.update()

    def leaveEvent(self, event):
        self.current_color = self.bg_color
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        
        if self.is_docked:
            self.dock_timer.start(300) # Delay before hiding again
            
        self.update()
        
    def contextMenuEvent(self, event):
        menu = QMenu(self)
        
        new_fence_action = QAction("新建分区（默认目录）", self)
        new_fence_action.triggered.connect(self.create_fence_requested.emit)
        menu.addAction(new_fence_action)
        
        custom_fence_action = QAction("新建指定目录分区", self)
        custom_fence_action.triggered.connect(self.create_custom_fence_requested.emit)
        menu.addAction(custom_fence_action)

        settings_action = QAction("更改默认目录", self)
        settings_action.triggered.connect(self.settings_requested.emit)
        menu.addAction(settings_action)
        
        menu.addSeparator()
        
        uninstall_action = QAction("卸载 (Uninstall)", self)
        uninstall_action.triggered.connect(self.uninstall_requested.emit)
        menu.addAction(uninstall_action)
        
        menu.addSeparator()
        
        quit_action = QAction("Exit App", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        menu.addAction(quit_action)
        
        menu.exec(event.globalPos())

    def show_desktop(self):
        """Toggle the desktop: first click hides app windows (fences stay), next restores.

        We drive the toggle ourselves instead of asking the shell, because on
        this machine Shell ToggleDesktop (and Win+D) hide the windows but do
        not bring them back on the reverse toggle, so the second click looked
        like a no-op.  We snapshot what is on screen, minimise exactly that
        list, and restore exactly that list on the next click.
        """
        if self._desktop_is_shown():
            count = len(getattr(self, "_visible_before_hide", None) or [])
            logging.info(f"FloatingBall: desktop hidden, restoring {count} windows")
            self._restore_snapshot()
        else:
            logging.info("FloatingBall: showing desktop, hiding app windows")
            self._snapshot_visible_windows()
            self._hide_snapshot()

    # ── snapshot / restore plumbing ───────────────────────────────────

    def _own_hwnds(self):
        hwnds = set()
        app = QApplication.instance()
        for widget in app.topLevelWidgets():
            try:
                hwnds.add(int(widget.winId()))
            except Exception:
                pass
        return hwnds

    def _eligible_window(self, hwnd, own):
        """A window we are willing to hide and bring back."""
        try:
            if hwnd in own or is_partition_window(hwnd):
                return False
            # Only windows that are actually on screen: never touch something
            # the user had already minimised.
            if not win32gui.IsWindowVisible(hwnd) or win32gui.IsIconic(hwnd):
                return False
            cls = win32gui.GetClassName(hwnd)
            if cls in ("Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd",
                       "Button", "tooltips_class32", "ForegroundStaging",
                       "TaskListThumbnailWnd", "IME", "MSCTFIME UI"):
                return False
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            ex = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            if style & win32con.WS_CHILD:
                return False
            if ex & win32con.WS_EX_TOOLWINDOW:
                return False
            rect = win32gui.GetWindowRect(hwnd)
            if rect[2] - rect[0] < 200 or rect[3] - rect[1] < 150:
                return False
            if not win32gui.GetWindowText(hwnd).strip():
                return False
            return True
        except Exception:
            return False

    def _snapshot_visible_windows(self):
        own = self._own_hwnds()
        hwnds = []
        try:
            def cb(hwnd, _):
                if self._eligible_window(hwnd, own):
                    hwnds.append(hwnd)
                return True
            win32gui.EnumWindows(cb, None)
        except Exception as e:
            logging.error(f"FloatingBall: snapshot failed: {e}")
        self._visible_before_hide = hwnds
        logging.info(f"FloatingBall: snapshotted {len(hwnds)} visible windows")

    def _desktop_is_shown(self):
        """True when every snapshotted window is off screen again."""
        snap = getattr(self, "_visible_before_hide", None)
        if not snap:
            return False
        alive_hidden = 0
        still_visible = 0
        for hwnd in snap:
            try:
                if not win32gui.IsWindow(hwnd):
                    continue
                if win32gui.IsWindowVisible(hwnd) and not win32gui.IsIconic(hwnd):
                    still_visible += 1
                else:
                    alive_hidden += 1
            except Exception:
                continue
        return alive_hidden > 0 and still_visible == 0

    def _hide_snapshot(self):
        hidden = 0
        for hwnd in list(getattr(self, "_visible_before_hide", None) or []):
            try:
                if not win32gui.IsWindow(hwnd):
                    continue
                if win32gui.IsIconic(hwnd) or not win32gui.IsWindowVisible(hwnd):
                    continue
                win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
                hidden += 1
            except Exception as e:
                logging.debug(f"FloatingBall: minimising {hwnd} failed: {e}")
        logging.info(f"FloatingBall: minimised {hidden} windows, fences untouched")

    def _restore_snapshot(self):
        snap = list(getattr(self, "_visible_before_hide", None) or [])
        restored = 0
        for hwnd in snap:
            try:
                if not win32gui.IsWindow(hwnd):
                    continue
                if win32gui.IsIconic(hwnd):
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                    restored += 1
                elif not win32gui.IsWindowVisible(hwnd):
                    win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
                    restored += 1
            except Exception as e:
                logging.debug(f"FloatingBall: restore of {hwnd} failed: {e}")
        logging.info(f"FloatingBall: restored {restored}/{len(snap)} windows")
        self._visible_before_hide = []

    def _toggle_desktop_via_com(self):
        try:
            if getattr(self, "_shell_app", None) is None:
                import win32com.client
                self._shell_app = win32com.client.Dispatch("Shell.Application")
            self._shell_app.ToggleDesktop()
            return True
        except Exception as e:
            logging.debug(f"FloatingBall: COM ToggleDesktop failed: {e}")
            self._shell_app = None
            return False

    @staticmethod
    def _toggle_desktop_via_key():
        """Fallback: inject Win+D with SendInput."""
        try:
            import ctypes
            import ctypes.wintypes as wt
            import time as _time

            ULONG_PTR = ctypes.POINTER(ctypes.c_ulong)

            class KEYBDINPUT(ctypes.Structure):
                _fields_ = [("wVk", wt.WORD), ("wScan", wt.WORD), ("dwFlags", wt.DWORD),
                            ("time", wt.DWORD), ("dwExtraInfo", ULONG_PTR)]

            class INPUT(ctypes.Structure):
                _fields_ = [("type", wt.DWORD), ("ki", KEYBDINPUT), ("pad", ctypes.c_byte * 8)]

            user32 = ctypes.windll.user32
            for vk, flags in ((0x5B, 0), (0x44, 0), (0x44, 2), (0x5B, 2)):
                inp = INPUT(type=1, ki=KEYBDINPUT(wVk=vk, wScan=0, dwFlags=flags,
                                                  time=0, dwExtraInfo=None))
                user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
                _time.sleep(0.02)
            return True
        except Exception as e:
            logging.warning(f"FloatingBall: Win+D injection failed: {e}")
            return False

    def _minimize_except_fences(self):
        logging.info("FloatingBall: Minimizing windows...")
        
        # Get our own HWNDs to exclude
        my_hwnds = []
        app = QApplication.instance()
        for widget in app.topLevelWidgets():
            try:
                my_hwnds.append(int(widget.winId()))
            except:
                pass
                
        def enum_handler(hwnd, _):
            if not win32gui.IsWindowVisible(hwnd):
                return True
                
            # Skip our own windows
            if hwnd in my_hwnds:
                return True

            if is_partition_window(hwnd):
                return True
                
            # Skip the Shell/Desktop itself
            cls_name = win32gui.GetClassName(hwnd)
            if cls_name in ["Progman", "WorkerW", "Shell_TrayWnd", "Button"]: # Taskbar and Start button
                return True
                
            # Skip empty title windows (often hidden system windows)
            # title = win32gui.GetWindowText(hwnd)
            # if not title:
            #    return True
                
            # Minimize
            # Use SW_MINIMIZE (6)
            # Check if already minimized?
            placement = win32gui.GetWindowPlacement(hwnd)
            if placement[1] != win32con.SW_SHOWMINIMIZED:
                 win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
            
            return True

        try:
            win32gui.EnumWindows(enum_handler, None)
            
            # FORCE Fences to Top (of bottom layer) just in case?
            # No, if they are attached to DefView, they shouldn't be affected by minimization of top-level windows.
            # But just in case some logic hid them, we can try to repaint or update them.
            # But we can't easily "show" them if they are hidden by parent.
            # However, since we are ONLY minimizing top-level windows, the desktop child windows (Fences) are safe.
            
        except Exception as e:
            logging.error(f"Error showing desktop: {e}")
