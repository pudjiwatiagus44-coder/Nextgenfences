import win32gui
hwnds = []
def f(h, _):
    hwnds.append(h)
    return True
win32gui.EnumWindows(f, None)
def print_tree(hwnd, indent=0):
    try:
        cls = win32gui.GetClassName(hwnd)
        print("  " * indent + f"{hex(hwnd)} {cls}")
        child_hwnds = []
        try:
            win32gui.EnumChildWindows(hwnd, lambda child, _: child_hwnds.append(child), None)
        except Exception:
            pass
        # Only print direct children to avoid deep nesting
        for child in child_hwnds:
            if win32gui.GetParent(child) == hwnd:
                print("  " * (indent+1) + f"{hex(child)} {win32gui.GetClassName(child)}")
    except Exception:
        pass

for h in hwnds:
    if win32gui.GetClassName(h) == 'WorkerW':
        print_tree(h)
