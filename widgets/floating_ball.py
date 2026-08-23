import sys
import os
import logging
import ctypes
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
        """Toggle desktop — exactly like Win+D / taskbar Show Desktop button.

        The OS maintains an internal toggle state: first call minimises all
        windows and shows the desktop; second call restores every window to
        its original position.  We must NOT touch fence windows ourselves
        between toggles — DesktopHook handles fence visibility/z-order after
        each toggle automatically.
        """
        logging.info("FloatingBall: toggling desktop (Win+D)")

        # ── Primary: SendInput (modern, reliable) ──────────────────────
        try:
            if self._send_win_d():
                logging.info("FloatingBall: Win+D sent via SendInput")
                return
            logging.warning("FloatingBall: SendInput returned partial success")
        except Exception as e:
            logging.warning(f"FloatingBall: SendInput failed: {e}")

        # ── Fallback: COM Shell.ToggleDesktop ──────────────────────────
        try:
            import win32com.client
            shell = win32com.client.Dispatch("Shell.Application")
            shell.ToggleDesktop()
            logging.info("FloatingBall: ToggleDesktop via COM")
            return
        except Exception as e:
            logging.warning(f"FloatingBall: COM toggle failed: {e}")

        # ── Last resort: keybd_event (deprecated but ubiquitous) ───────
        try:
            user32 = ctypes.windll.user32
            VK_LWIN = 0x5B
            VK_D = 0x44
            KEYEVENTF_KEYUP = 0x0002
            user32.keybd_event(VK_LWIN, 0, 0, 0)
            user32.keybd_event(VK_D, 0, 0, 0)
            user32.keybd_event(VK_D, 0, KEYEVENTF_KEYUP, 0)
            user32.keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, 0)
            logging.info("FloatingBall: Win+D via keybd_event (fallback)")
        except Exception as e:
            logging.error(f"FloatingBall: all desktop toggle methods failed: {e}")

    @staticmethod
    def _send_win_d():
        """Send Win+D via SendInput.  Returns True if all 4 events were
        accepted by the system."""
        INPUT_KEYBOARD = 1
        KEYEVENTF_KEYUP = 0x0002
        VK_LWIN = 0x5B
        VK_D = 0x44

        # ctypes structures matching tagINPUT (keyboard member only)
        class _KEYBDINPUT(ctypes.Structure):
            _fields_ = [
                ("wVk", ctypes.c_ushort),
                ("wScan", ctypes.c_ushort),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulonglong)),
            ]

        class _INPUT_UNION(ctypes.Union):
            _fields_ = [("ki", _KEYBDINPUT)]

        class _INPUT(ctypes.Structure):
            _anonymous_ = ("_input",)
            _fields_ = [
                ("type", ctypes.c_ulong),
                ("_input", _INPUT_UNION),
            ]

        extra = ctypes.pointer(ctypes.c_ulonglong(0))
        inputs = (_INPUT * 4)(
            _INPUT(type=INPUT_KEYBOARD,
                   ki=_KEYBDINPUT(wVk=VK_LWIN, wScan=0, dwFlags=0,
                                  time=0, dwExtraInfo=extra)),
            _INPUT(type=INPUT_KEYBOARD,
                   ki=_KEYBDINPUT(wVk=VK_D, wScan=0, dwFlags=0,
                                  time=0, dwExtraInfo=extra)),
            _INPUT(type=INPUT_KEYBOARD,
                   ki=_KEYBDINPUT(wVk=VK_D, wScan=0, dwFlags=KEYEVENTF_KEYUP,
                                  time=0, dwExtraInfo=extra)),
            _INPUT(type=INPUT_KEYBOARD,
                   ki=_KEYBDINPUT(wVk=VK_LWIN, wScan=0, dwFlags=KEYEVENTF_KEYUP,
                                  time=0, dwExtraInfo=extra)),
        )
        sent = ctypes.windll.user32.SendInput(
            4, inputs, ctypes.sizeof(_INPUT)
        )
        return sent == 4
