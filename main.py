import schedule
import time
import os
import sys
import subprocess
import psutil
from datetime import datetime
from automation import AmazonAutomation

# 解决控制台输出编码
sys.stdout.reconfigure(encoding='utf-8')

def is_process_running(process_name):
    """检查进程是否在运行"""
    try:
        for proc in psutil.process_iter(['name']):
            if process_name.lower() in proc.info['name'].lower():
                return True
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        pass
    return False

def check_vpn_and_handle():
    """检查VPN并处理重启逻辑"""
    vpn_process_name = "LetsVPN.exe" # 假设这是LetsVPN的进程名，如果不同请修改
    # 也可以检查是否存在特定窗口，或者简单地检查进程
    
    # 这里我们使用简单的进程检查。如果不确定进程名，可以打开任务管理器查看。
    # 通常是 LetsVPN.exe 或 similar. 
    # 或者直接检查文件是否存在来判断是否安装了（但这里要求是"开启了"）
    # 用户说"检测到电脑开启了vpn"，通常指进程在运行。
    
    if is_process_running(vpn_process_name) or is_process_running("LetsVPN") or is_process_running("Lets") or is_process_running("Unified"):
        print(f"⚠️ 检测到 VPN ({vpn_process_name}) 正在运行...")
        
        bat_path = r"C:\Users\Administrator\Desktop\紫鸟定时\翻墙后开亚马逊.bat"
        if os.path.exists(bat_path):
            print(f"🚀 正在执行重启脚本: {bat_path}")
            # 执行bat文件。由于该bat文件会重启电脑，所以我们只需要启动它
            # 注意：bat文件里有提权操作，可能需要以管理员身份运行
            # 但当前脚本如果是管理员启动的，子进程也会继承
            try:
                # 使用 start 命令启动，这样主程序可以继续（虽然bat会重启电脑）
                os.startfile(bat_path)
                return True # 表示执行了重启操作
            except Exception as e:
                print(f"❌ 执行脚本失败: {e}")
        else:
            print(f"❌ 找不到脚本文件: {bat_path}")
    
    return False

def job_1500():
    print(f"\n⏰ [15:00] 触发定时任务")
    
    if check_vpn_and_handle():
        print("🔄 系统即将重启，请等待重启后任务自动执行...")
        return

def job_1500():
    print(f"\n⏰ [15:00] 触发定时任务: 设置低预算")
    # 不再检测VPN，直接运行
    print("✅ 开始执行广告任务: 设置低预算")
    bot = AmazonAutomation()
    # 使用 GUI 模式运行
    bot.run_with_gui('low')

def job_2000():
    print(f"\n⏰ [20:00] 触发定时任务: 设置高预算")
    # 不再检测VPN，直接运行
    print("✅ 开始执行广告任务: 设置高预算")
    bot = AmazonAutomation()
    # 使用 GUI 模式运行
    bot.run_with_gui('high')

def main():
    os.system('cls' if os.name == 'nt' else 'clear')
    print("="*60)
    print("🤖 亚马逊广告预算自动管理系统 (VPN监控版)")
    print("="*60)

    # --- 新增：检查是否有待处理的重启后任务 ---
    # 使用绝对路径，确保不受启动位置影响
    base_dir = os.path.dirname(os.path.abspath(__file__))
    flag_file = os.path.join(base_dir, "pending_high_budget.flag")
    
    # 增加调试信息
    print(f"正在检查自动执行标记: {flag_file}")
    
    if os.path.exists(flag_file):
        print("🚀 检测到重启后的【高预算任务标记】")
        print("⏳ 正在等待 15 秒以确保系统完全就绪...")
        
        # 倒计时显示
        for i in range(15, 0, -1):
            print(f"\r还剩 {i} 秒...", end="")
            time.sleep(1)
        print("\n")
        
        print("▶️ 立即执行：设置高预算")
        try:
            bot = AmazonAutomation()
            bot.run_task('high')
            print("✅ 立即任务执行完毕。正在删除标记文件...")
            os.remove(flag_file) 
        except Exception as e:
            print(f"❌ 立即任务执行失败: {e}")
    else:
        # print("ℹ️ 未检测到重启标记文件，进入正常待机模式。")
        pass
    # ------------------------------------------

    print(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n📅 任务计划:")
    print("  1. 每天 14:55 -> 检查VPN (若开启则重启电脑)")
    print("  2. 每天 15:00 -> 设置预算为 1 (低预算)")
    print("  3. 每天 19:55 -> 检查VPN (若开启则重启电脑)")
    print("  4. 每天 20:00 -> 设置预算为 100000 (无限制)")
    print("\n✅ 程序运行中... (请不要关闭此窗口)")
    print("   按 Ctrl+C 可停止程序")
    print("="*60)

    # 注册VPN检查任务 (提前5分钟)
    schedule.every().day.at("14:55").do(check_vpn_and_handle)
    schedule.every().day.at("19:55").do(check_vpn_and_handle)

    # 注册广告任务
    schedule.every().day.at("15:00").do(job_1500)
    schedule.every().day.at("20:00").do(job_2000)

    print("\n⏳ 程序已就绪。正在后台运行监控中...")
    
    # 循环检查
    while True:
        try:
            schedule.run_pending()
            
            # 动态显示当前时间，证明程序活着
            # current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            # print(f"\r✅ 当前时间: {current_time} | 等待任务触发...", end="")
            
            time.sleep(1) # 每秒刷新一次时间显示
        except KeyboardInterrupt:
            print("\n👋 程序已退出")
            break
        except Exception as e:
            print(f"\n❌ 发生错误: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
