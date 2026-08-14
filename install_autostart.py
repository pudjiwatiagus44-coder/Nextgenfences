import sys
import os
import winreg

def install_autostart():
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    app_name = "NextGenDesktop"
    
    python_exe = sys.executable
    # Use pythonw.exe instead of python.exe for no console
    if python_exe.endswith("python.exe"):
        pythonw_exe = python_exe.replace("python.exe", "pythonw.exe")
    else:
        pythonw_exe = python_exe

    # Locate main.py relative to this script
    script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "main.py"))
    
    command = f'"{pythonw_exe}" "{script_path}"'
    
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, command)
        winreg.CloseKey(key)
        print(f"Successfully added to startup: {command}")
    except Exception as e:
        print(f"Failed to add to startup: {e}")

if __name__ == "__main__":
    install_autostart()
