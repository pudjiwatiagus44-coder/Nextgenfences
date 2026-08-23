"""
实时监控 Win+D 恢复过程
"""
import time
import win32gui
import win32con

def find_fence_windows():
    """查找所有 分区 窗口"""
    fences = []
    
    def callback(hwnd, extra):
        if win32gui.IsWindow(hwnd):
            title = win32gui.GetWindowText(hwnd)
            class_name = win32gui.GetClassName(hwnd)
            # 查找 Qt 窗口（分区 使用 Qt）
            if 'Qt' in class_name or '分区' in title:
                fences.append((hwnd, title, class_name))
        return True
    
    win32gui.EnumWindows(callback, None)
    return fences

print("=" * 60)
print("Win+D 恢复监控")
print("=" * 60)
print("正在查找 分区 窗口...")

fences = find_fence_windows()
print(f"\n找到 {len(fences)} 个可能的 分区 窗口：")
for hwnd, title, class_name in fences:
    is_visible = win32gui.IsWindowVisible(hwnd)
    print(f"  - HWND: {hwnd}, Title: '{title}', Class: '{class_name}', Visible: {is_visible}")

print("\n" + "=" * 60)
print("请按 Win+D，然后观察窗口状态变化")
print("按 Ctrl+C 退出")
print("=" * 60)
print()

last_states = {}
for hwnd, title, class_name in fences:
    last_states[hwnd] = win32gui.IsWindowVisible(hwnd)

try:
    while True:
        for hwnd, title, class_name in fences:
            try:
                current_visible = win32gui.IsWindowVisible(hwnd)
                if current_visible != last_states.get(hwnd):
                    status = "显示" if current_visible else "隐藏"
                    print(f"[{time.strftime('%H:%M:%S')}] 窗口 {hwnd} ({title}) 状态变化: {status}")
                    last_states[hwnd] = current_visible
            except:
                pass
        
        time.sleep(0.1)
        
except KeyboardInterrupt:
    print("\n监控已停止")
