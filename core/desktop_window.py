from PyQt6.QtWidgets import QWidget, QApplication, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QColor
import sys
import win32gui
import win32con
import logging
from .z_order_manager import ZOrderManager

class DesktopWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NextGen Desktop Canvas")
        
        # Standard flags
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        
        # Make it click-through initially just in case
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(0, 0, screen.width(), screen.height())
        
        # Test content
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label = QLabel("Initializing NextGen Desktop...")
        self.label.setStyleSheet("font-size: 40px; color: yellow; background: rgba(0,0,0,100); padding: 20px;")
        layout.addWidget(self.label)
        
        # Try to attach
        QTimer.singleShot(500, self.attach_to_desktop)

    def attach_to_desktop(self):
        hwnd = int(self.winId())
        success = ZOrderManager.set_as_wallpaper(hwnd)
        
        if success:
            self.label.setText("NextGen Desktop: Active")
            self.label.setStyleSheet("font-size: 40px; color: green; background: rgba(0,0,0,100); padding: 20px;")
            QTimer.singleShot(3000, self.label.hide) # Hide label after success
            self.show()
        else:
            logging.error("Attachment failed. Fallback mode.")
            self.label.setText("NextGen Desktop: Fallback Mode")
            self.label.setStyleSheet("font-size: 40px; color: red; background: rgba(0,0,0,100); padding: 20px;")
            
            # Fallback: Just stay at bottom
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnBottomHint | Qt.WindowType.Tool)
            self.showLower()
            self.show()

    def paintEvent(self, event):
        # Optional: debug background
        # painter = QPainter(self)
        # painter.fillRect(self.rect(), QColor(0, 0, 255, 20)) # Faint blue
        pass
