import sys
import os
import subprocess
import traceback
import logging
import shutil
import win32gui # Import win32gui for window checks
from PyQt6.QtWidgets import QApplication, QMessageBox, QMenu, QInputDialog, QFileDialog
from PyQt6.QtGui import QAction, QCursor
from PyQt6.QtCore import Qt, QTimer, QPoint, QEvent
from PyQt6.QtNetwork import QLocalServer, QLocalSocket

# Fix path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Logging
log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app_debug.log')
logging.basicConfig(filename=log_file, level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Hook unhandled exceptions
def exception_hook(exctype, value, tb):
    logging.critical("Uncaught exception", exc_info=(exctype, value, tb))
    sys.__excepthook__(exctype, value, tb)

sys.excepthook = exception_hook

from widgets.clock import ClockWidget
from widgets.fence import FenceWidget
from widgets.floating_ball import FloatingBallWidget
from managers.config_manager import ConfigManager
from managers.setup_manager import SetupManager
from core.z_order_manager import ZOrderManager
from core.desktop_hook import DesktopHook
from core.keyboard_hook import GlobalKeyboardHook
from utils.shell_menu import ShellContextMenu
import win32con

APP_ID = "NextGenFences_v3_Lock"

def kill_old_instances():
    """æ°å½èå¿é¢æ¥¼å¿èºèå¿é¢ç¦å¿è´æç«é©´è¸è½ç¯è¥æ°åºè»ç²æ®è¥èå½è¦ç²èµè§èèµç¦æ°éè»æ°è¬çæ°è¤ç¯?""
    try:
        current_pid = os.getpid()
        # Ê¹ÓÃ Popen ·Ç×èÈûÖ´ÐÐ£¬²»µÈ´ý½á¹û
        subprocess.Popen(
            f'taskkill /F /FI "PID ne {current_pid}" /IM NextGenFences.exe', 
            shell=True, 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL
        )
    except Exception as e:
        logging.error(f"Failed to kill old instances: {e}")

class NextGenDesktopApp:
    def __init__(self):
        kill_old_instances()
        logging.info("App initializing...")
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        
        # --- Single Instance Check ---
        self.socket = QLocalSocket()
        self.socket.connectToServer(APP_ID)
        if self.socket.waitForConnected(500):
            logging.info("Another instance is running. Exiting.")
            self.socket.disconnectFromServer()
            sys.exit(0) # Exit this instance without sending SHOW message
        
        # If we are here, we are the first instance. Start server.
        self.server = QLocalServer()
        # Cleanup potential stale lock file
        QLocalServer.removeServer(APP_ID)
        self.server.listen(APP_ID)
        self.server.newConnection.connect(self.handle_new_connection)
        
        self.config_manager = ConfigManager()
        
        # Check if first run or setup needed (e.g. check if config was just created or flag)
        # For simplicity, we can try to run setup every time (it overwrites) or check a config flag.
        # Let's run it if we are a frozen EXE.
        if getattr(sys, 'frozen', False):
             SetupManager().run_first_time_setup()

        self.fences = {}
        
        try:
            self.desktop = None 
            self.load_fences()
            
            self.ball = FloatingBallWidget()
            self.ball.clicked.connect(self.restore_all_fences)
            self.ball.settings_requested.connect(self.open_settings)
            self.ball.create_custom_fence_requested.connect(self.add_custom_path_fence)
            self.ball.create_fence_requested.connect(self.add_new_fence)
            self.ball.uninstall_requested.connect(self.uninstall_app)
            self.ball.show()
            
            # æ°è¢èºæ°æè¥æ°è¦è³æ°èç¯æ°å¤èèè°åºè½è¸èµèè®æ¼æ°é¢è¬èå½è¦å¿è¥å¨èé©?Win+D
            self.keyboard_hook = GlobalKeyboardHook()
            self.keyboard_hook.install()
            logging.info("Global keyboard hook installed for Win+D interception")

            # å¿è·èå¿è´é²è½å¨èè½è°ç¯å¿éè¦èèºåèè®æ¼æ°é¢è¬èå½è¦èèé©´æ°èè§ç«ççç«æå¨æ°è«è­
            self.desktop_hook = DesktopHook()
            self.desktop_hook.desktop_shown.connect(self.on_desktop_shown)
            self.desktop_hook.start(300)
            logging.info("Desktop visibility hook started")

            self.health_timer = QTimer()
            self.health_timer.timeout.connect(self.check_fences_health)
            self.health_timer.start(10000)

            QTimer.singleShot(1500, self.restore_all_fences)
            QTimer.singleShot(5000, self.restore_all_fences)
            QTimer.singleShot(10000, self.restore_all_fences)
            
            logging.info("Desktop initialized with keyboard hook for Win+D monitoring")
            
            # Handle initial args if any (e.g. if launched with --create-fence first time)
            self.process_command(sys.argv[1:])
            
        except Exception as e:
            logging.error(f"Initialization error: {e}")
            traceback.print_exc()

    def on_desktop_shown(self):
        """
        æ°éè¯å¿æ¢èå¿ç¢è¥æ°è¢æ³å¿éè¦èèºåå¿èµæ®è½éæ½èå½è¢Win+Dèå½è£å¿è´é²èå½è¦å¿èåèé©´?Fences è½è·èå¿èµæ®èé©´?        """
        logging.info("Win+D detected: Attempting to restore fences")
        self.restore_all_fences()

    def restore_all_fences(self):
        """
        å¿èåæ°éè§å¿è£èèé©?Fence è½éè´æ°è«æ¢è½è·èå¿èµæ®è½éæ½èå½è¢Win+D æ°è¬è¨ç«æ³èè½è°ç¯èå½è£
        """
        logging.info("FloatingBall: User clicked to restore fences.")
        
        # èå¨è³æ°èè¢æ°æ³èºç«çè²å¿è¹èæ°æ³è«æ°è¦è³å¿è£èå¿è¹è£è½éè´æ°è«æ¢èå½è¦èè¹èæ°è¡æ½å¿éè¦èèºåèå½è¢æ°è®è¦å¿è¢è­ç²ç¦å¢èé©´?Fencesèé©´?        # ç«é©´è¶å¿èµçç²èµæ½ç²æ½è å¿ç¯éå¿è¥è¼èèè¹å¿èµæ®è½éæ½å¿éè¦èèºåèèèºç²éè ç²é©´èºè½è²è?Fences è½è·èå¿è²è¢èé©´?        # self.ball.show_desktop() # æ°åºè»èè¶èèé©´?show_desktop æ°è·¯èè½ç¦è«æ°èè·ç²æ½è å¿è¹èæ°æ³è«æ°è¦è?
        
        # è½èé²æ°è¬è¨æ°å½æ½æ°è¢é²å¿è«è¬æ°è§è¡ Fences
        for fence_id, fence in self.fences.items():
            try:
                if hasattr(fence, "recover_after_show_desktop"):
                    fence.recover_after_show_desktop()
                    logging.info(f"Recovered fence {fence_id}")
                    continue

                hwnd = int(fence.winId())
                
                # 1. æ°å½æ½æ°è¢é²å¿èµæ®è½éæ½
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE) # æ°å¨èå¿è»è¹å¿è¹èæ°æ³è«æ°è¦è³ç²æ½è æ°èè¢å¿èåæ°éè?
                win32gui.ShowWindow(hwnd, win32con.SW_SHOWNOACTIVATE)
                
                # 2. èè¡è§å¿è³æ³ç«æ³èå¿è²éº Z-Orderèå½è¦è½éåºç²é©´èºæ°åºèç²ç¦å¢æ°è¹ç¯æ°è¸æ®å¿è½è¡æ°å¤èç²é¹¿è¥èé©´?                # å¿é²ç¯å¿èè«èå½è·ç²èµè§ç«èéè½è°ç¯ HWND_BOTTOMèå½è¦æ°è¸è½ç²èµæ½èèæ¢å¿è½è·¯ç²å½è·èé©´?Win+D æ°è¨è¥æ°è¹ç¯ç²èµè¥èèºå
                # æ°æ³èºç«çè²è½éåºèéé²ç²èµèå¿å¢éèå½è¦è½èé²æ°è¬è¨æ°è è§å¿è°æ®æ°è¢æ³æ°æ½è²æ°å¤èèå½è¼å¿è¢è³ç«èèè½è¸éºå¿è¨æ¥¼å¿è°æ®æ°è¢æ³æ°æ½è²æ°å¤èèå½è¼
                # æ°å¨èå¿è»è¹è½è°ç¯å¿è¢è·¯å¿è¦è£ç²æ½è  Win+Dèå½è¦å¿è£èå¿è¹è£è½éè´æ°è«æ¢èå½è¢æ°è¦èå¿è¥å¢ Fencesèå½è£èèéç«åè¦èè·è¬èé©´?å¿è¹èæ°æ³è«æ°è¦è³èé©?                # å¿è¢è­ç²ç¦å¢èè¹èèé©?"Undo" ç«é©´è¶ç²èµéèè·è¬ç«è´è«èé©´?                
                # æ°æ³èºç«çè²ç«åºæ®è½éåºèé©´?HWND_TOPMOST è½èé²æ°è¬è¨æ°è«è³å¿é²è¢èå½è¦å¿è¢è³ç«èèè½è¸éºèé©´?SetWindowPos
                win32gui.SetWindowPos(
                    hwnd, 
                    win32con.HWND_TOPMOST, 
                    0, 0, 0, 0, 
                    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE
                )
                
                # è½ç¯è§æ°æ®åºæ°ç¦é²ç«é©´è¼æ°è¬è¨æ°è«è³å¿é²è¢è½éåºèéé²èå½è¦èèé©´æ°èè§ç²èµèè½è¸éºèèåºå¿è¦éæ°èé²ç²ç¦è³è½éè´èé©?                QTimer.singleShot(100, lambda h=hwnd: win32gui.SetWindowPos(
                    h, 
                    win32con.HWND_NOTOPMOST, 
                    0, 0, 0, 0, 
                    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE
                ))
                
                logging.info(f"Restored fence {fence_id}")
            except Exception as e:
                logging.error(f"Failed to restore fence {fence_id}: {e}")

    def handle_new_connection(self):
        socket = self.server.nextPendingConnection()
        if socket.waitForReadyRead(1000):
            data = socket.readAll().data().decode('utf-8')
            logging.info(f"Received IPC message: {data}")
            self.process_command(data.split())
        socket.disconnectFromServer()

    def uninstall_app(self):
        reply = QMessageBox.question(None, "Uninstall", 
                                   "This will remove the context menu, startup shortcut, and desktop shortcut.\n\nYour Fence files will NOT be deleted.\n\nAre you sure you want to uninstall?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            SetupManager().uninstall()
            QMessageBox.information(None, "Uninstalled", "Integrations removed successfully. The application will now exit.")
            sys.exit(0)

    def process_command(self, args):
        if not args:
            return
            
        cmd = args[0]
        if cmd == "SHOW":
            # Bring windows to front if needed?
            # Re-attach all fences to be safe
            for fence in self.fences.values():
                fence.attach_to_desktop()
        elif cmd == "--create-fence":
            # Delay slightly to ensure UI is ready?
            QTimer.singleShot(100, lambda: self.add_new_fence(QCursor.pos()))
        elif cmd == "--create-custom-fence":
            QTimer.singleShot(100, self.add_custom_path_fence)

    def check_fences_health(self):
        """Check if fence windows are still valid and recreate if necessary."""
        recreate_ids = []
        for fence_id, fence in self.fences.items():
            try:
                # Check if underlying C++ object is deleted
                if not fence or not win32gui.IsWindow(int(fence.winId())):
                    logging.warning(f"Fence {fence_id} window is gone. Marking for recreation.")
                    recreate_ids.append(fence_id)
            except Exception as e:
                logging.error(f"Error checking fence {fence_id}: {e}")
                recreate_ids.append(fence_id)
        
        for fid in recreate_ids:
            logging.info(f"Recreating fence {fid}")
            if fid in self.fences:
                try:
                    self.fences[fid].close()
                except:
                    pass
                del self.fences[fid]
            
            # Reload from config
            f_conf = self.config_manager.get_fence_by_id(fid)
            if f_conf:
                self.create_fence_widget(f_conf)

    def show_context_menu(self, pos):
        pass

    def add_custom_path_fence(self):
        # 1. Select Folder
        folder = QFileDialog.getExistingDirectory(None, "Select Folder for Fence")
        if not folder:
            return
            
        # 2. Ask for Name (Default to folder name)
        default_name = os.path.basename(folder)
        if not default_name: # Handle root drives e.g. "C:/"
            default_name = folder.replace("\\", "/").strip("/")
            
        dialog = QInputDialog(None)
        dialog.setWindowTitle("New Fence Name")
        dialog.setLabelText("Enter name for this fence:")
        dialog.setTextValue(default_name)
        # Force light theme
        dialog.setStyleSheet("""
            QInputDialog { background-color: white; color: black; }
            QLabel { color: black; background-color: transparent; }
            QLineEdit { color: black; background-color: white; border: 1px solid #ccc; }
            QPushButton { color: black; background-color: #f0f0f0; border: 1px solid #ccc; padding: 5px; }
        """)
        
        ok = dialog.exec()
        title = dialog.textValue()
        
        if ok and title:
            # 3. Create Fence
            new_id = self.config_manager.add_fence(title, path=folder)
            
            # 4. Show it at cursor pos
            pos = QCursor.pos()
            self.config_manager.update_fence_property(new_id, "geometry", [pos.x(), pos.y(), 300, 200])
            
            f_conf = self.config_manager.get_fence_by_id(new_id)
            self.create_fence_widget(f_conf)

    def add_new_fence(self, pos=None):
        dialog = QInputDialog(None)
        dialog.setWindowTitle("New Fence")
        dialog.setLabelText("Fence Name:")
        # Force light theme
        dialog.setStyleSheet("""
            QInputDialog { background-color: white; color: black; }
            QLabel { color: black; background-color: transparent; }
            QLineEdit { color: black; background-color: white; border: 1px solid #ccc; }
            QPushButton { color: black; background-color: #f0f0f0; border: 1px solid #ccc; padding: 5px; }
        """)
        
        ok = dialog.exec()
        title = dialog.textValue()
        
        if ok and title:
            new_id = self.config_manager.add_fence(title)
            
            if not pos:
                pos = QPoint(200, 200)
                
            self.config_manager.update_fence_property(new_id, "geometry", [pos.x(), pos.y(), 300, 200])
            
            f_conf = self.config_manager.get_fence_by_id(new_id)
            self.create_fence_widget(f_conf)

    def load_fences(self):
        """æ°è¢è å¿è£é¹¿æ°ç¦é²ç«é©´è¼æ°è¤è½ç«éé Fenceèå½è¦æ°è¤è½èèè¼æ°è¬çèé©´?""
        fences_data = self.config_manager.data["fences"]
        
        # å¿çè«ç²èµé Fence æ°ç¦é²ç«é©´è¼ 100ms æ°è¤è½ç«ééèå½è¦æ°è¡è«æ°æ³è­æ°è¬çæ°è¤ç¯æ°è§éèé©´?        for i, f_conf in enumerate(fences_data):
            delay = 100 * i  # 0ms, 100ms, 200ms...
            QTimer.singleShot(delay, lambda c=f_conf: self.create_fence_widget(c))
            
    def create_fence_widget(self, f_conf):
        fence_id = f_conf["id"]
        title = f_conf["title"]
        geo = f_conf["geometry"]
        opacity = f_conf.get("opacity", 0.7)
        view_mode = f_conf.get("view_mode", "icon_medium")
        path = f_conf.get("path")
        custom_order = f_conf.get("custom_order", [])
        font_size = f_conf.get("font_size", 12)
        sort_by = f_conf.get("sort_by", "name")
        sort_order = f_conf.get("sort_order", "asc")
        
        fence = FenceWidget(fence_id, title, parent=None, opacity=opacity, view_mode=view_mode, custom_order=custom_order, font_size=font_size, sort_by=sort_by, sort_order=sort_order)
        fence.setGeometry(geo[0], geo[1], geo[2], geo[3])
        
        fence.geometry_changed.connect(self.on_fence_geometry_changed)
        fence.file_dropped.connect(self.on_file_dropped)
        fence.fence_removed.connect(self.on_fence_removed)
        fence.fence_renamed.connect(self.on_fence_renamed)
        fence.view_mode_changed.connect(self.on_view_mode_changed)
        fence.opacity_changed.connect(self.on_opacity_changed)
        fence.order_changed.connect(self.on_order_changed)
        fence.font_size_changed.connect(self.on_font_size_changed)
        fence.sort_changed.connect(self.on_sort_changed)
        
        if path and os.path.exists(path):
            fence.set_path(path)
        
        fence.show()
        self.fences[fence_id] = fence
        
        # å¿è¸éºå¿è³æ³èè°åºè½è¸èµèè®æ¼æ°é¢è¬èé©´?Fence è½éè´æ°è«æ¢æ°è«æ¥¼å¿è¼èæ°è¢è´ç«éç¯
        self._update_fence_hwnds()

    def _update_fence_hwnds(self):
        """å¿è¸éºå¿è³æ³èè°åºè½è¸èµèè®æ¼æ°é¢è¬èé©´?Fence è½éè´æ°è«æ¢æ°è«æ¥¼å¿è¼èæ°è¢è´ç«éç¯"""
        hwnds = []
        for fence in self.fences.values():
            try:
                hwnds.append(int(fence.winId()))
            except:
                pass
        GlobalKeyboardHook.set_fence_hwnds(hwnds)
        logging.info(f"Updated fence HWNDs for keyboard hook: {hwnds}")

    def on_fence_geometry_changed(self, fence_id, geometry):
        self.config_manager.update_fence_property(fence_id, "geometry", geometry)

    def on_fence_renamed(self, fence_id, new_title):
        self.config_manager.update_fence_property(fence_id, "title", new_title)

    def on_view_mode_changed(self, fence_id, mode):
        self.config_manager.update_fence_property(fence_id, "view_mode", mode)

    def on_opacity_changed(self, fence_id, value):
        self.config_manager.update_fence_property(fence_id, "opacity", value)

    def on_order_changed(self, fence_id, order):
        self.config_manager.update_fence_property(fence_id, "custom_order", order)
    
    def on_font_size_changed(self, fence_id, value):
        self.config_manager.update_fence_property(fence_id, "font_size", value)

    def on_sort_changed(self, fence_id, sort_by, sort_order):
        self.config_manager.update_fence_property(fence_id, "sort_by", sort_by)
        self.config_manager.update_fence_property(fence_id, "sort_order", sort_order)

    def on_fence_removed(self, fence_id):
        if fence_id in self.fences:
            del self.fences[fence_id]
            self.config_manager.remove_fence(fence_id)

    def on_file_dropped(self, file_path, fence_id):
        f_conf = self.config_manager.get_fence_by_id(fence_id)
        if not f_conf: return
        
        target_dir = f_conf["path"]
        
        if os.path.dirname(file_path) == target_dir:
            logging.info(f"Ignored internal drop: {file_path}")
            return

        filename = os.path.basename(file_path)
        
        try:
            new_path = os.path.join(target_dir, filename)
            base, ext = os.path.splitext(new_path)
            counter = 1
            while os.path.exists(new_path):
                new_path = f"{base} ({counter}){ext}"
                counter += 1
                
            shutil.move(file_path, new_path)
            
            if os.path.exists(file_path):
                if os.path.exists(new_path):
                    try:
                        if os.path.isdir(file_path):
                            shutil.rmtree(file_path)
                        else:
                            os.remove(file_path)
                        logging.info(f"Force deleted source: {file_path}")
                    except Exception as ex:
                        logging.error(f"Failed to force delete source: {ex}")

            if fence_id in self.fences:
                self.fences[fence_id].add_file(new_path)
                
        except Exception as e:
            logging.error(f"Move file failed: {e}")

    def open_settings(self):
        # Open directory dialog
        current_root = self.config_manager.root_dir
        new_dir = QFileDialog.getExistingDirectory(None, "Select New Default Storage Directory", current_root)
        
        if new_dir and new_dir != current_root:
            reply = QMessageBox.question(None, "Confirm Change", 
                                       f"Change default storage to:\n{new_dir}?\n\nFences currently in the default folder will be moved.\nCustom directory fences will remain unchanged.",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
            if reply == QMessageBox.StandardButton.Yes:
                success = self.config_manager.update_root_dir(new_dir)
                if success:
                    QMessageBox.information(None, "Success", "Storage directory updated successfully.\nThe application will now restart to apply changes.")
                    # Restart app
                    import subprocess
                    subprocess.Popen([sys.executable] + sys.argv)
                    sys.exit(0)
                else:
                    QMessageBox.warning(None, "Error", "Failed to update directory. Check logs for details.")

    def run(self):
        logging.info("App running...")
        
        # ç«é©´è¬ç«éè¦ Qt ç²æ½è¥ç²ç¦é²æ°æ®éè½è¨ç
        exit_code = self.app.exec()
        
        # èèèæ°è¡æ½æ°è£è§æ°è§èµç«ééèè°åºè½è¸èµèè®æ¼æ°é¢è?
        if hasattr(self, 'keyboard_hook'):
            self.keyboard_hook.uninstall()
        
        sys.exit(exit_code)

if __name__ == "__main__":
    try:
        app = NextGenDesktopApp()
        app.run()
    except Exception as e:
        logging.critical(f"Fatal error: {e}")
        traceback.print_exc()















