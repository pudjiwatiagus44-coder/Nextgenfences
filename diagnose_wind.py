"""
详细诊断 Win+D 对窗口的影响
"""
import win32gui
import win32con
import time

def get_window_info(hwnd):
    """获取窗口的详细信息"""
    try:
        return {
            'visible': win32gui.IsWindowVisible(hwnd),
            'iconic': win32gui.IsIconic(hwnd),
            'enabled': win32gui.IsWindowEnabled(hwnd),
            'style': win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE),
            'ex_style': win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE),
        }
    except:
        return None

print("=" * 70)
print("Win+D 窗口状态详细诊断")
print("=" * 70)

# 查找 分区 窗口
def find_fence_windows():
    windows = []
    def callback(hwnd, extra):
        if win32gui.IsWindow(hwnd):
            title = win32gui.GetWindowText(hwnd)
            class_name = win32gui.GetClassName(hwnd)
            # 查找可能是 分区 的窗口
            if 'Qt' in class_name and win32gui.IsWindowVisible(hwnd):
                parent = win32gui.GetParent(hwnd)
                windows.append((hwnd, title, class_name, parent))
        return True
    
    win32gui.EnumWindows(callback, None)
    return windows

fences = find_fence_windows()
print(f"\n找到 {len(fences)} 个可见的 Qt 窗口：")
for hwnd, title, class_name, parent in fences:
    info = get_window_info(hwnd)
    print(f"\nHWND: {hwnd}")
    print(f"  Title: '{title}'")
    print(f"  Class: {class_name}")
    print(f"  Parent: {parent}")
    print(f"  Visible: {info['visible']}")
    print(f"  Iconic: {info['iconic']}")
    print(f"  Style: 0x{info['style']:08X}")
    print(f"  ExStyle: 0x{info['ex_style']:08X}")

if not fences:
    print("\n⚠️  没有找到可见的 Qt 窗口！")
    print("可能的原因：")
    print("1. 分区 窗口已经被隐藏")
    print("2. 分区 窗口使用了特殊的窗口类名")
    print("3. 应用没有正常运行")
    input("\n按回车键退出...")
    exit(1)

print("\n" + "=" * 70)
print("请按 Win+D，我会显示窗口状态的变化")
print("按 Ctrl+C 退出")
print("=" * 70)
print()

# 记录初始状态
last_states = {}
for hwnd, title, class_name, parent in fences:
    last_states[hwnd] = get_window_info(hwnd)

try:
    check_count = 0
    while True:
        check_count += 1
        
        for hwnd, title, class_name, parent in fences:
            current = get_window_info(hwnd)
            if current is None:
                continue
                
            last = last_states.get(hwnd)
            if last is None:
                continue
            
            # 检查所有可能的变化
            changes = []
            if current['visible'] != last['visible']:
                changes.append(f"Visible: {last['visible']} → {current['visible']}")
            if current['iconic'] != last['iconic']:
                changes.append(f"Iconic: {last['iconic']} → {current['iconic']}")
            if current['style'] != last['style']:
                changes.append(f"Style: 0x{last['style']:08X} → 0x{current['style']:08X}")
            if current['ex_style'] != last['ex_style']:
                changes.append(f"ExStyle: 0x{last['ex_style']:08X} → 0x{current['ex_style']:08X}")
            
            if changes:
                timestamp = time.strftime('%H:%M:%S.%f')[:-3]
                print(f"\n[{timestamp}] 窗口 {hwnd} 状态变化：")
                for change in changes:
                    print(f"  - {change}")
                
                last_states[hwnd] = current
        
        # 每 10 秒显示一次心跳
        if check_count % 100 == 0:
            print(f"[{time.strftime('%H:%M:%S')}] 监控中... (已检查 {check_count} 次)")
        
        time.sleep(0.1)
        
except KeyboardInterrupt:
    print("\n\n监控已停止")
