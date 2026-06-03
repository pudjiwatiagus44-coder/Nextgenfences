import os
import ctypes
import win32con
import win32gui
import win32api
import logging
from win32com.shell import shell, shellcon

# Define missing constants manually
CMF_NORMAL = 0x00000000
CMF_DEFAULTONLY = 0x00000001
CMF_VERBSONLY = 0x00000002
CMF_EXPLORE = 0x00000004
CMF_NOVERBS = 0x00000008
CMF_CANRENAME = 0x00000010
CMF_NODEFAULT = 0x00000020
CMF_INCLUDESTATIC = 0x00000040
CMF_ITEMMENU = 0x00000080
CMF_EXTENDEDVERBS = 0x00000100
CMF_DISABLEDVERBS = 0x00000200
CMF_ASYNCVERBSTATE = 0x00000400
CMF_OPTIMIZEFORINVOKE = 0x00000800
CMF_SYNCCASCADEMENU = 0x00001000
CMF_DONOTPICKDEFAULT = 0x00002000
CMF_RESERVED = 0xffff0000

# Custom Command IDs
CMD_CUSTOM_RENAME = 50000 # Just a safe high number, but within range?
# TrackPopupMenu result is command ID directly if TPM_RETURNCMD is used.
# The Shell Menu items start at 1 and go up.
# We should shift our custom IDs to be very high or very low (negative?).
# Actually, TrackPopupMenu returns the item ID.
# QueryContextMenu adds items starting from idCmdFirst (which we passed as 0).
# So the shell items will be 0, 1, 2...
# Wait, we passed 1 as idCmdFirst in QueryContextMenu(hmenu, 0, 1, 0x7FFF, flags)
# So shell items are 1, 2, 3...
# We can use a large ID for our custom item, e.g. 10000.

class ShellContextMenu:
    def __init__(self):
        pass

    def show_menu(self, hwnd, point, file_paths):
        logging.info(f"ShellContextMenu: Request for {file_paths}")
        if not file_paths:
            return False

        abs_path = os.path.abspath(file_paths[0])
        if not os.path.exists(abs_path):
            return False

        folder_path, file_name = os.path.split(abs_path)
        desktop = shell.SHGetDesktopFolder()
        
        try:
            folder_item = desktop.ParseDisplayName(0, None, folder_path)[1]
            folder = desktop.BindToObject(folder_item, None, shell.IID_IShellFolder)
            file_item = folder.ParseDisplayName(0, None, file_name)[1]
            items = [file_item]
        except Exception as e:
            logging.error(f"Error parsing path: {e}")
            return False

        try:
            pcm = folder.GetUIObjectOf(0, items, shell.IID_IContextMenu, 0)[1]
        except Exception as e:
            logging.error(f"Error getting IContextMenu: {e}")
            return False

        hmenu = win32gui.CreatePopupMenu()
        if not hmenu:
            return False
        
        try:
            # Removed CMF_CANRENAME to avoid native rename issues. We provide a custom rename.
            flags = CMF_NORMAL | CMF_EXPLORE
            # Shell items start at ID 1
            pcm.QueryContextMenu(hmenu, 0, 1, 0x7FFF, flags)
            
            # Insert Custom Rename Item at the top
            # ID: 10001
            win32gui.InsertMenu(hmenu, 0, win32con.MF_BYPOSITION | win32con.MF_STRING, 10001, "Rename (Fence)")
            win32gui.InsertMenu(hmenu, 1, win32con.MF_BYPOSITION | win32con.MF_SEPARATOR, 0, None)
            
        except Exception as e:
            logging.error(f"Error querying context menu: {e}")
            win32gui.DestroyMenu(hmenu)
            return False

        tpm_flags = win32con.TPM_LEFTALIGN | win32con.TPM_RIGHTBUTTON | win32con.TPM_RETURNCMD | win32con.TPM_NONOTIFY
        
        try:
            win32gui.SetForegroundWindow(hwnd)
        except Exception:
            pass

        command = win32gui.TrackPopupMenu(hmenu, tpm_flags, point.x(), point.y(), 0, hwnd, None)

        success = True
        if command == 10001:
            # Custom Rename
            logging.info("Custom Rename selected")
            success = "RENAME_ACTION" # Return special code
        elif command > 0:
            try:
                cmd_id = command - 1 # Adjust for idCmdFirst=1
                
                ci = (
                    0,                      # fMask
                    hwnd,                   # hwnd
                    cmd_id,                 # lpVerb
                    None,                   # lpParameters
                    None,                   # lpDirectory
                    win32con.SW_SHOWNORMAL, # nShow
                    0,                      # dwHotKey
                    None                    # hIcon
                )
                
                pcm.InvokeCommand(ci)
            except Exception as e:
                logging.error(f"Error invoking command: {e}")
                success = False
        else:
            success = False

        win32gui.DestroyMenu(hmenu)
        return success
