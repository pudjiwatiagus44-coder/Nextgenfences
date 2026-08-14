import os
import sys
import winreg
import ctypes
from win32com.client import Dispatch

class SetupManager:
    APP_NAME = "桌面分区"
    
    def __init__(self):
        if getattr(sys, 'frozen', False):
            self.exe_path = sys.executable
            self.command_prefix = f'"{self.exe_path}"'
        else:
            # For source code: python.exe "path/to/main.py"
            main_py = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "main.py"))
            self.exe_path = sys.executable 
            
            # Use pythonw.exe to avoid console window
            python_dir = os.path.dirname(sys.executable)
            pythonw = os.path.join(python_dir, 'pythonw.exe')
            if os.path.exists(pythonw):
                self.command_prefix = f'"{pythonw}" "{main_py}"'
            else:
                self.command_prefix = f'"{self.exe_path}" "{main_py}"'
            
    def is_admin(self):
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False

    def remove_old_keys(self):
        """Removes legacy context menu keys"""
        keys_to_remove = [
            r"Software\Classes\Directory\Background\shell\NextGenDesktop", # Old one from vbs/register script
            r"Directory\Background\shell\NextGenDesktop", # Another possible location
            r"Software\Classes\Directory\Background\shell\NextGenFences", # Previous version key
            r"Software\Classes\Directory\Background\shell\NextGenFencesCustom" # Previous custom key
        ]
        
        for key_path in keys_to_remove:
            try:
                # Try HKCU
                try:
                    winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key_path + r"\command")
                    winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key_path)
                    print(f"Removed HKCU key: {key_path}")
                except:
                    pass

                # Try HKCR (Needs Admin usually, but good to try)
                try:
                    winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, key_path + r"\command")
                    winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, key_path)
                    print(f"Removed HKCR key: {key_path}")
                except:
                    pass
            except Exception as e:
                print(f"Error removing key {key_path}: {e}")

    def install_context_menu(self):
        """Adds partition actions to the desktop right-click menu."""
        self.remove_old_keys()
        try:
            # 1. Standard partition
            user_key_path = r"Software\Classes\Directory\Background\shell\NextGenFences"
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, user_key_path)
            winreg.SetValue(key, "", winreg.REG_SZ, "新建分区")
            winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, self.exe_path)
            
            cmd_key = winreg.CreateKey(key, "command")
            winreg.SetValue(cmd_key, "", winreg.REG_SZ, f'{self.command_prefix} --create-fence')
            winreg.CloseKey(cmd_key)
            winreg.CloseKey(key)

            # 2. Custom path partition
            user_key_path_custom = r"Software\Classes\Directory\Background\shell\NextGenFencesCustom"
            key_custom = winreg.CreateKey(winreg.HKEY_CURRENT_USER, user_key_path_custom)
            winreg.SetValue(key_custom, "", winreg.REG_SZ, "新建指定目录分区")
            winreg.SetValueEx(key_custom, "Icon", 0, winreg.REG_SZ, self.exe_path)
            
            cmd_key_custom = winreg.CreateKey(key_custom, "command")
            winreg.SetValue(cmd_key_custom, "", winreg.REG_SZ, f'{self.command_prefix} --create-custom-fence')
            winreg.CloseKey(cmd_key_custom)
            winreg.CloseKey(key_custom)

            return True
        except Exception as e:
            print(f"Failed to install context menu: {e}")
            return False

    def install_startup(self):
        """Adds shortcut to Windows Startup Folder"""
        try:
            startup_dir = os.path.join(os.getenv('APPDATA'), r'Microsoft\Windows\Start Menu\Programs\Startup')
            shortcut_path = os.path.join(startup_dir, f"{self.APP_NAME}.lnk")
            
            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(shortcut_path)
            shortcut.TargetPath = self.exe_path
            shortcut.WorkingDirectory = os.path.dirname(self.exe_path)
            shortcut.Description = "桌面分区"
            shortcut.IconLocation = self.exe_path
            shortcut.Save()
            return True
        except Exception as e:
            print(f"Failed to install startup shortcut: {e}")
            return False

    def create_desktop_shortcut(self):
        """Creates shortcut on Desktop"""
        try:
            desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
            shortcut_path = os.path.join(desktop_dir, f"{self.APP_NAME}.lnk")
            
            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(shortcut_path)
            shortcut.TargetPath = self.exe_path
            shortcut.WorkingDirectory = os.path.dirname(self.exe_path)
            shortcut.Description = "桌面分区"
            shortcut.IconLocation = self.exe_path
            shortcut.Save()
            return True
        except Exception as e:
            print(f"Failed to create desktop shortcut: {e}")
            return False

    def uninstall(self):
        """Removes all system integrations"""
        print("Uninstalling...")
        # 1. Remove Registry Keys
        self.remove_old_keys()
        
        # 2. Remove Startup Shortcut
        try:
            startup_dir = os.path.join(os.getenv('APPDATA'), r'Microsoft\Windows\Start Menu\Programs\Startup')
            for shortcut_name in (f"{self.APP_NAME}.lnk", "NextGenFences.lnk"):
                shortcut_path = os.path.join(startup_dir, shortcut_name)
                if os.path.exists(shortcut_path):
                    os.remove(shortcut_path)
                    print("Removed startup shortcut")
        except Exception as e:
            print(f"Error removing startup shortcut: {e}")

        # 3. Remove Desktop Shortcut
        try:
            desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
            for shortcut_name in (f"{self.APP_NAME}.lnk", "NextGenFences.lnk"):
                shortcut_path = os.path.join(desktop_dir, shortcut_name)
                if os.path.exists(shortcut_path):
                    os.remove(shortcut_path)
                    print("Removed desktop shortcut")
        except Exception as e:
            print(f"Error removing desktop shortcut: {e}")
            
        return True

    def run_first_time_setup(self):
        """Runs all setup tasks"""
        print("Running First Time Setup...")
        self.install_context_menu()
        self.install_startup()
        self.create_desktop_shortcut()
