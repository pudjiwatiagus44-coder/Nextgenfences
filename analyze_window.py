"""
详细检查窗口样式，找出为什么不受 Win+D 影响
"""
import win32gui
import win32con

# 查找 Qt 窗口
qt_windows = []
def enum_callback(hwnd, results):
    if win32gui.IsWindow(hwnd):
        class_name = win32gui.GetClassName(hwnd)
        if 'Qt' in class_name and win32gui.IsWindowVisible(hwnd):
            results.append(hwnd)
    return True

win32gui.EnumWindows(enum_callback, qt_windows)

if not qt_windows:
    print("没有找到 Qt 窗口")
    exit(1)

hwnd = qt_windows[0]
print(f"检查窗口 {hwnd}:\n")

# 获取样式
style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)

print(f"Style: 0x{style:08X}")
print(f"ExStyle: 0x{ex_style:08X}\n")

# 检查所有相关标志
print("Style 标志:")
print(f"  WS_POPUP: {bool(style & win32con.WS_POPUP)}")
print(f"  WS_CHILD: {bool(style & win32con.WS_CHILD)}")
print(f"  WS_MINIMIZE: {bool(style & win32con.WS_MINIMIZE)}")
print(f"  WS_VISIBLE: {bool(style & win32con.WS_VISIBLE)}")
print(f"  WS_DISABLED: {bool(style & win32con.WS_DISABLED)}")

print("\nExStyle 标志:")
print(f"  WS_EX_TOOLWINDOW: {bool(ex_style & win32con.WS_EX_TOOLWINDOW)}")
print(f"  WS_EX_APPWINDOW: {bool(ex_style & win32con.WS_EX_APPWINDOW)}")
print(f"  WS_EX_TOPMOST: {bool(ex_style & win32con.WS_EX_TOPMOST)}")
print(f"  WS_EX_LAYERED: {bool(ex_style & win32con.WS_EX_LAYERED)}")
print(f"  WS_EX_TRANSPARENT: {bool(ex_style & win32con.WS_EX_TRANSPARENT)}")
print(f"  WS_EX_NOACTIVATE: {bool(ex_style & win32con.WS_EX_NOACTIVATE)}")

# 检查父窗口
parent = win32gui.GetParent(hwnd)
print(f"\n父窗口: {parent}")
if parent:
    parent_class = win32gui.GetClassName(parent)
    print(f"父窗口类名: {parent_class}")

# 检查所有者窗口
owner = win32gui.GetWindow(hwnd, win32con.GW_OWNER)
print(f"所有者窗口: {owner}")

print("\n" + "="*60)
print("分析:")
print("="*60)

# 判断为什么不受 Win+D 影响
reasons = []

if ex_style & win32con.WS_EX_TOOLWINDOW:
    reasons.append("有 WS_EX_TOOLWINDOW 标志（Tool 窗口）")

if parent != 0:
    reasons.append(f"有父窗口 ({parent})，可能是子窗口")

if not (style & win32con.WS_POPUP):
    if not (style & win32con.WS_OVERLAPPEDWINDOW):
        reasons.append("既不是 POPUP 也不是 OVERLAPPED 窗口")

if ex_style & win32con.WS_EX_NOACTIVATE:
    reasons.append("有 WS_EX_NOACTIVATE 标志")

if reasons:
    print("可能不受 Win+D 影响的原因:")
    for r in reasons:
        print(f"  - {r}")
else:
    print("理论上应该受 Win+D 影响")

print("\n建议的修复:")
print("  1. 确保没有 WS_EX_TOOLWINDOW")
print("  2. 确保没有父窗口（或父窗口不是桌面）")
print("  3. 添加 WS_OVERLAPPEDWINDOW 或至少是 WS_POPUP")
