import sys
import time
from PyQt6.QtWidgets import QApplication, QLabel, QWidget
from PyQt6.QtCore import Qt, QTimer
import win32gui, win32con

app = QApplication(sys.argv)
w = QWidget()
w.setWindowFlags(Qt.WindowType.FramelessWindowHint)
l = QLabel("Hello Desktop 2!", w)
l.setStyleSheet("color: blue; font-size: 30px; background: white")
w.resize(300, 100)
w.show()

hwnd = int(w.winId())

def attach():
    progman = win32gui.FindWindow("Progman", None)
    win32gui.SendMessageTimeout(progman, 0x052C, 0, 0, win32con.SMTO_NORMAL, 1000)

    workerw = None
    def f(h, _):
        global workerw
        if win32gui.GetClassName(h) == "WorkerW":
            if win32gui.FindWindowEx(h, 0, "SHELLDLL_DefView", None):
                workerw = h
                return False
        return True
    win32gui.EnumWindows(f, None)

    target = workerw if workerw else progman
    # Try modifying style to WS_CHILD
    style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
    style = style & ~win32con.WS_POPUP
    style = style | win32con.WS_CHILD
    win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)

    win32gui.SetParent(hwnd, target)
    print("New Parent after style change:", hex(win32gui.GetParent(hwnd)))

QTimer.singleShot(1000, attach)

sys.exit(app.exec())
