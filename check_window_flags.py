"""
检查当前 Fence 窗口的窗口标志
"""
import win32gui
import win32con

def get_window_flags(hwnd):
    """获取窗口标志"""
    try:
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
        ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        
        # 检查关键标志
        is_tool = (ex_style & win32con.WS_EX_TOOLWINDOW) != 0
        is_appwindow = (ex_style & win32con.WS_EX_APPWINDOW) != 0
        is_popup = (style & win32con.WS_POPUP) != 0
        is_child = (style & win32con.WS_CHILD) != 0
        
        return {
            'style': style,
            'ex_style': ex_style,
            'is_tool': is_tool,
            'is_appwindow': is_appwindow,
            'is_popup': is_popup,
            'is_child': is_child,
        }
    except Exception as e:
        return {'error': str(e)}

print("=" * 70)
print("Fence 窗口标志检查")
print("=" * 70)

# 查找所有可见的 Qt 窗口
def find_qt_windows():
    windows = []
    def callback(hwnd, extra):
        if win32gui.IsWindow(hwnd) and win32gui.IsWindowVisible(hwnd):
            class_name = win32gui.GetClassName(hwnd)
            if 'Qt' in class_name:
                title = win32gui.GetWindowText(hwnd)
                windows.append((hwnd, title, class_name))
        return True
    
    win32gui.EnumWindows(callback, None)
    return windows

windows = find_qt_windows()
print(f"\n找到 {len(windows)} 个可见的 Qt 窗口：\n")

for hwnd, title, class_name in windows:
    flags = get_window_flags(hwnd)
    
    print(f"HWND: {hwnd}")
    print(f"  Title: '{title}'")
    print(f"  Class: {class_name}")
    
    if 'error' in flags:
        print(f"  Error: {flags['error']}")
    else:
        print(f"  Style: 0x{flags['style']:08X}")
        print(f"  ExStyle: 0x{flags['ex_style']:08X}")
        print(f"  Is Tool Window: {flags['is_tool']}")
        print(f"  Is App Window: {flags['is_appwindow']}")
        print(f"  Is Popup: {flags['is_popup']}")
        print(f"  Is Child: {flags['is_child']}")
        
        # 判断是否会被 Win+D 影响
        # Tool 窗口不受 Win+D 影响
        # 有 WS_EX_TOOLWINDOW 且没有 WS_EX_APPWINDOW 的窗口不在任务栏显示
        if flags['is_tool'] and not flags['is_appwindow']:
            print(f"  ⚠️  这个窗口不会被 Win+D 影响（Tool 窗口）")
        else:
            print(f"  ✅ 这个窗口应该会被 Win+D 影响")
    
    print()

print("=" * 70)
print("说明：")
print("- Tool 窗口（WS_EX_TOOLWINDOW）不受 Win+D 影响")
print("- 如果看到 ⚠️，说明窗口标志设置有问题")
print("=" * 70)
