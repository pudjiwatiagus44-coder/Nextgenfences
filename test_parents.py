import win32gui
hwnds = []
def f(h, _):
    hwnds.append(h)
win32gui.EnumWindows(f, None)
for h in hwnds:
    cls = win32gui.GetClassName(h)
    text = win32gui.GetWindowText(h)
    if 'QWidget' in cls and len(text) > 0:
        parent = win32gui.GetParent(h)
        print(f"HWND: {hex(h)}, Parent: {hex(parent)}, Class: {cls}, Text: {text}")
