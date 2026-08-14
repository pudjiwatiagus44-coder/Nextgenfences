import win32gui
with open('out_utf8.txt', 'w', encoding='utf-8') as f:
    hwnds = []
    win32gui.EnumWindows(lambda h, _: hwnds.append(h), None)
    for h in hwnds:
        cls = win32gui.GetClassName(h)
        if 'QWidget' in cls or 'WorkerW' in cls:
            parent = win32gui.GetParent(h)
            title = win32gui.GetWindowText(h)
            f.write(f"HWND: {hex(h)}, Parent: {hex(parent)}, Class: {cls}, Title: {title}\n")
