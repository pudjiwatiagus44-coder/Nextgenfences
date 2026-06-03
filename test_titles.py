import win32gui
with open('out_utf8_2.txt', 'w', encoding='utf-8') as f:
    hwnds = []
    win32gui.EnumWindows(lambda h, _: hwnds.append(h), None)
    for h in hwnds:
        title = win32gui.GetWindowText(h)
        if title:
            parent = win32gui.GetParent(h)
            cls = win32gui.GetClassName(h)
            f.write(f"HWND: {hex(h)}, Parent: {hex(parent)}, Class: {cls}, Title: {title}\n")
