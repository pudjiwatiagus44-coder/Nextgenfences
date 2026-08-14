import win32gui
hwnds = []
win32gui.EnumWindows(lambda h, _: hwnds.append(h), None)
for h in hwnds:
    cls = win32gui.GetClassName(h)
    if 'QWidget' in cls or 'Window' in cls:
        parent = win32gui.GetParent(h)
        title = win32gui.GetWindowText(h)
        print("HWND:", hex(h), "Parent:", hex(parent), "Class:", cls, "Title:", title)
