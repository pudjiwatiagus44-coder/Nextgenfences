"""
最简单的 Win+D 测试 - 直接显示窗口状态
"""
import win32gui
import win32con
import time

print("正在查找 Qt 窗口...")

# 查找所有窗口
all_windows = []
def enum_callback(hwnd, results):
    if win32gui.IsWindow(hwnd):
        class_name = win32gui.GetClassName(hwnd)
        if 'Qt' in class_name and win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            results.append((hwnd, title, class_name))
    return True

win32gui.EnumWindows(enum_callback, all_windows)

if not all_windows:
    print("没有找到可见的 Qt 窗口！应用可能没有运行。")
    exit(1)

print(f"找到 {len(all_windows)} 个 Qt 窗口\n")

# 选择前几个窗口进行监控
windows_to_monitor = all_windows[:6]

for hwnd, title, class_name in windows_to_monitor:
    ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
    is_tool = (ex_style & win32con.WS_EX_TOOLWINDOW) != 0
    print(f"HWND {hwnd}: Tool={is_tool}, Title='{title[:20]}'")

print("\n" + "="*60)
print("现在请按 Win+D，我会显示窗口状态")
print("="*60 + "\n")

# 监控循环
last_states = {}
for hwnd, _, _ in windows_to_monitor:
    last_states[hwnd] = {
        'visible': win32gui.IsWindowVisible(hwnd),
        'iconic': win32gui.IsIconic(hwnd)
    }

try:
    while True:
        for hwnd, title, _ in windows_to_monitor:
            try:
                visible = win32gui.IsWindowVisible(hwnd)
                iconic = win32gui.IsIconic(hwnd)
                
                last = last_states[hwnd]
                
                if visible != last['visible'] or iconic != last['iconic']:
                    ts = time.strftime('%H:%M:%S')
                    print(f"[{ts}] HWND {hwnd}: Visible={visible}, Iconic={iconic}")
                    
                    last_states[hwnd] = {'visible': visible, 'iconic': iconic}
            except:
                pass
        
        time.sleep(0.05)
        
except KeyboardInterrupt:
    print("\n停止监控")
