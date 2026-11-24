"""Trigger Show Desktop (Win+D) and dump the desktop-layer z-order right after.

Usage: python probe_showdesktop.py
"""
import ctypes
import ctypes.wintypes as wt
import time

user32 = ctypes.windll.user32

# SendInput structures
ULONG_PTR = ctypes.POINTER(ctypes.c_ulong)

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wt.WORD), ("wScan", wt.WORD), ("dwFlags", wt.DWORD),
                ("time", wt.DWORD), ("dwExtraInfo", ULONG_PTR)]

class INPUT(ctypes.Structure):
    _fields_ = [("type", wt.DWORD), ("ki", KEYBDINPUT), ("pad", ctypes.c_byte * 8)]


def send_win_d():
    INPUT_KEYBOARD = 1
    KEYEVENTF_KEYUP = 0x0002
    seq = [
        ("win down", 0x5B, 0),
        ("d down", 0x44, 0),
        ("d up", 0x44, KEYEVENTF_KEYUP),
        ("win up", 0x5B, KEYEVENTF_KEYUP),
    ]
    for name, vk, flags in seq:
        inp = INPUT(type=INPUT_KEYBOARD,
                    ki=KEYBDINPUT(wVk=vk, wScan=0, dwFlags=flags, time=0, dwExtraInfo=None))
        user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
        time.sleep(0.02)
    print("Win+D sent")


if __name__ == "__main__":
    send_win_d()
