"""
测试新的桌面监听器
运行此脚本，然后按 Win+D 查看是否能正确检测到桌面显示事件
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from core.desktop_hook import DesktopHook

def on_desktop_shown():
    print(">>> 桌面显示事件触发！(Win+D 被按下)")

def on_desktop_hidden():
    print(">>> 桌面隐藏事件触发！(切换到其他窗口)")

if __name__ == "__main__":
    print("=" * 60)
    print("桌面监听器测试")
    print("=" * 60)
    print("请按 Win+D 来显示桌面，观察事件是否被正确触发")
    print("按 Ctrl+C 退出")
    print("-" * 60)
    
    app = QApplication(sys.argv)
    
    # 创建桌面监听器
    hook = DesktopHook()
    hook.desktop_shown.connect(on_desktop_shown)
    hook.desktop_hidden.connect(on_desktop_hidden)
    
    # 启动监听（500ms 检查一次）
    hook.start(interval_ms=500)
    
    print("监听器已启动，等待桌面事件...")
    print()
    
    sys.exit(app.exec())
