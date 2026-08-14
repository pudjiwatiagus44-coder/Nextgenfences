import sys
from PyQt6.QtWidgets import QApplication, QLabel, QWidget
from PyQt6.QtCore import Qt
import win32gui, win32con

app = QApplication(sys.argv)
w = QWidget()
w.setWindowFlags(Qt.WindowType.FramelessWindowHint)
l = QLabel("Hello Desktop!", w)
l.setStyleSheet("color: red; font-size: 30px; background: white")
w.resize(300, 100)
w.show()

hwnd = int(w.winId())
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
print("Embeding to:", hex(target))

win32gui.SetParent(hwnd, target)
print("Parent is now:", hex(win32gui.GetParent(hwnd)))

sys.exit(app.exec())
