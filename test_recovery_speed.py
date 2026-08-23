"""
测试 Win+D 恢复机制
实时显示窗口状态变化
"""
import time
import win32gui
import win32con

print("=" * 60)
print("Win+D 恢复测试")
print("=" * 60)
print("正在查找 分区 窗口...")

def find_qt_windows():
    """查找所有 Qt 窗口（分区 使用 Qt）"""
    windows = []
    
    def callback(hwnd, extra):
        if win32gui.IsWindow(hwnd):
            class_name = win32gui.GetClassName(hwnd)
            if 'Qt' in class_name:
                title = win32gui.GetWindowText(hwnd)
                windows.append((hwnd, title, class_name))
        return True
    
    win32gui.EnumWindows(callback, None)
    return windows

windows = find_qt_windows()
print(f"\n找到 {len(windows)} 个 Qt 窗口：")
for hwnd, title, class_name in windows:
    is_visible = win32gui.IsWindowVisible(hwnd)
    print(f"  HWND: {hwnd:6d} | Visible: {is_visible} | Title: '{title[:30]}'")

print("\n" + "=" * 60)
print("请按 Win+D，观察窗口恢复速度")
print("按 Ctrl+C 退出")
print("=" * 60)
print()

# 持续监控
last_states = {hwnd: win32gui.IsWindowVisible(hwnd) for hwnd, _, _ in windows}
hidden_time = {}

try:
    while True:
        for hwnd, title, class_name in windows:
            try:
                current_visible = win32gui.IsWindowVisible(hwnd)
                last_visible = last_states.get(hwnd)
                
                if current_visible != last_visible:
                    timestamp = time.strftime('%H:%M:%S')
                    
                    if not current_visible:
                        # 窗口被隐藏
                        hidden_time[hwnd] = time.time()
                        print(f"[{timestamp}] ❌ 窗口 {hwnd} 被隐藏")
                    else:
                        # 窗口恢复显示
                        if hwnd in hidden_time:
                            recovery_time = (time.time() - hidden_time[hwnd]) * 1000
                            print(f"[{timestamp}] ✅ 窗口 {hwnd} 恢复显示 (耗时: {recovery_time:.0f}ms)")
                            del hidden_time[hwnd]
                        else:
                            print(f"[{timestamp}] ✅ 窗口 {hwnd} 显示")
                    
                    last_states[hwnd] = current_visible
            except:
                pass
        
        time.sleep(0.05)  # 50ms 检查一次
        
except KeyboardInterrupt:
    print("\n监控已停止")
