import sys
import time
from PyQt6.QtWidgets import QApplication, QLabel, QWidget
from PyQt6.QtCore import Qt, QTimer
import win32gui, win32con

app = QApplication(sys.argv)
w = QWidget()
w.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
w.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

l = QLabel("Owner Test! Click me = ok", w)
l.setStyleSheet("color: green; font-size: 20px; background: rgba(255, 255, 255, 128)")
w.resize(300, 100)
w.show()

def attach():
    hwnd = int(w.winId())
    
    # Remove WS_EX_APPWINDOW to hide from alt-tab, if needed
    ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
    ex_style = ex_style & ~win32con.WS_EX_APPWINDOW
    ex_style = ex_style | win32con.WS_EX_TOOLWINDOW
    win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style)

    # Find the Progman or WorkerW
    progman = win32gui.FindWindow("Progman", None)
    
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
    print("Setting OWNER to:", hex(target))
    
    # Use SetWindowLong(GWLP_HWNDPARENT) to set the OWNER (not parent!)
    win32gui.SetWindowLong(hwnd, win32con.GWL_HWNDPARENT, target)
    print("Owner set!")

QTimer.singleShot(500, attach)

sys.exit(app.exec())
