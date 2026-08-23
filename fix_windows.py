"""
手动移除所有 Qt 窗口的 TOOLWINDOW 标志
"""
import win32gui
import win32con

print("正在查找并修复 Qt 窗口...")

# 查找所有 Qt 窗口
qt_windows = []
def enum_callback(hwnd, results):
    if win32gui.IsWindow(hwnd):
        class_name = win32gui.GetClassName(hwnd)
        if 'Qt' in class_name and win32gui.IsWindowVisible(hwnd):
            results.append(hwnd)
    return True

win32gui.EnumWindows(enum_callback, qt_windows)

print(f"找到 {len(qt_windows)} 个 Qt 窗口\n")

fixed_count = 0
for hwnd in qt_windows:
    try:
        # 获取当前样式
        ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        
        # 检查是否有 TOOLWINDOW 标志
        has_tool = (ex_style & win32con.WS_EX_TOOLWINDOW) != 0
        
        if has_tool:
            # 移除 TOOLWINDOW 标志
            new_ex_style = ex_style & ~win32con.WS_EX_TOOLWINDOW
            # 同时移除 APPWINDOW 以保持不在任务栏显示
            new_ex_style = new_ex_style & ~win32con.WS_EX_APPWINDOW
            
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, new_ex_style)
            
            # 验证修改
            verify_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            still_tool = (verify_style & win32con.WS_EX_TOOLWINDOW) != 0
            
            if not still_tool:
                print(f"✓ HWND {hwnd}: 成功移除 TOOLWINDOW 标志")
                fixed_count += 1
            else:
                print(f"✗ HWND {hwnd}: 移除失败")
        else:
            print(f"- HWND {hwnd}: 已经没有 TOOLWINDOW 标志")
            
    except Exception as e:
        print(f"✗ HWND {hwnd}: 错误 - {e}")

print(f"\n完成！修复了 {fixed_count} 个窗口")
print("\n现在请按 Win+D 测试")
