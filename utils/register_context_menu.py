import winreg
import sys
import os
import ctypes

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def register():
    if not is_admin():
        print("Requesting admin privileges...")
        # Re-run the script with admin privileges
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, __file__, None, 1)
        return

    # Define paths
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir) # MyDesktop
    launch_vbs = os.path.join(project_root, "launch.vbs")
    
    # Check if launch.vbs exists
    if not os.path.exists(launch_vbs):
        print(f"Error: launch.vbs not found at {launch_vbs}")
        return

    # Command: wscript.exe "C:\Path\To\launch.vbs" --create-fence
    command_str = f'wscript.exe "{launch_vbs}" --create-fence'
    
    key_path = r"Directory\Background\shell\NextGenDesktop"
    
    try:
        # Create Key
        print(f"Creating Registry Key: HKCR\\{key_path}")
        key = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, key_path)
        winreg.SetValue(key, "", winreg.REG_SZ, "Create New Fence")
        
        # Optional: Icon
        # winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, "shell32.dll,3") 
        
        # Create Command Subkey
        cmd_key = winreg.CreateKey(key, "command")
        winreg.SetValue(cmd_key, "", winreg.REG_SZ, command_str)
        
        winreg.CloseKey(cmd_key)
        winreg.CloseKey(key)
        
        print("Successfully registered context menu!")
        # ctypes.windll.user32.MessageBoxW(0, "Context Menu 'Create New Fence' added successfully!", "Success", 0)
        
    except Exception as e:
        print(f"Error: {e}")
        # ctypes.windll.user32.MessageBoxW(0, f"Error: {e}", "Registration Failed", 0)

if __name__ == "__main__":
    register()
