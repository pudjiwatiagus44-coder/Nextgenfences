"""测试桌面检测逻辑"""
import win32gui
import time

def is_desktop_visible():
    try:
        foreground = win32gui.GetForegroundWindow()
        
        if foreground == 0:
            return True
            
        class_name = win32gui.GetClassName(foreground)
        title = win32gui.GetWindowText(foreground)
        
        print(f"前台窗口: hwnd={foreground}, class={class_name}, title={title}")
        
        if class_name in ("Progman", "WorkerW", "Shell_TrayWnd"):
            return True
            
        if not title or title == "Program Manager":
            return True
            
        return False
        
    except Exception as e:
        print(f"Error: {e}")
        return False

print("开始监测前台窗口...")
print("请按 Win+D 测试，按 Ctrl+C 退出")
print("-" * 50)

last_state = None
while True:
    state = is_desktop_visible()
    if state != last_state:
        print(f">>> 桌面可见: {state}")
        last_state = state
    time.sleep(0.3)
