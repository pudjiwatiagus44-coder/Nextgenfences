import logging
import os
import shlex
import shutil
import sys
import traceback

import win32con
import win32gui
from PyQt6.QtCore import QPoint, QTimer
from PyQt6.QtGui import QCursor
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtWidgets import QApplication, QFileDialog, QInputDialog, QMessageBox

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from managers.config_manager import ConfigManager
from managers.setup_manager import SetupManager
from widgets.fence import FenceWidget
from widgets.floating_ball import FloatingBallWidget

try:
    from core.keyboard_hook import GlobalKeyboardHook
except Exception:
    class GlobalKeyboardHook:
        @staticmethod
        def set_fence_hwnds(_hwnds):
            return None

        def install(self):
            return None

        def uninstall(self):
            return None


APP_ID = "NextGenFences_v3_Lock"


if getattr(sys, "frozen", False):
    runtime_dir = os.path.dirname(sys.executable)
else:
    runtime_dir = os.path.dirname(os.path.abspath(__file__))

log_file = os.path.join(runtime_dir, "app_debug.log")
logging.basicConfig(
    filename=log_file,
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    force=True,
)


def exception_hook(exctype, value, tb):
    logging.critical("Uncaught exception", exc_info=(exctype, value, tb))
    sys.__excepthook__(exctype, value, tb)


sys.excepthook = exception_hook


class SingleInstanceController:
    def __init__(
        self,
        app_id=APP_ID,
        socket_factory=QLocalSocket,
        server_factory=QLocalServer,
    ):
        self.app_id = app_id
        self.socket_factory = socket_factory
        self.server_factory = server_factory
        self.server = None

    def forward_to_existing_instance(self, args, timeout_ms=500):
        socket = self.socket_factory()
        socket.connectToServer(self.app_id)
        if not socket.waitForConnected(timeout_ms):
            return False

        message = self._encode_command(args)
        if message:
            socket.write(message.encode("utf-8"))
            socket.flush()
            socket.waitForBytesWritten(timeout_ms)
        socket.disconnectFromServer()
        return True

    def listen(self, on_new_connection):
        QLocalServer.removeServer(self.app_id)
        self.server = self.server_factory()
        if not self.server.listen(self.app_id):
            raise RuntimeError(f"Unable to listen on local server: {self.app_id}")
        self.server.newConnection.connect(on_new_connection)
        return self.server

    @staticmethod
    def _encode_command(args):
        if not args:
            return "SHOW"
        return " ".join(shlex.quote(str(arg)) for arg in args)

    @staticmethod
    def decode_command(data):
        if not data:
            return []
        return shlex.split(data)


class NextGenDesktopApp:
    def __init__(self):
        logging.info("App initializing...")
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        self.single_instance = SingleInstanceController()
        if self.single_instance.forward_to_existing_instance(sys.argv[1:]):
            logging.info("Forwarded command to existing instance. Exiting.")
            sys.exit(0)

        self.server = self.single_instance.listen(self.handle_new_connection)
        self.config_manager = ConfigManager()

        if getattr(sys, "frozen", False):
            SetupManager().run_first_time_setup()

        self.fences = {}
        self.load_fences()

        self.ball = FloatingBallWidget()
        self.ball.clicked.connect(self.restore_all_fences)
        self.ball.settings_requested.connect(self.open_settings)
        self.ball.create_custom_fence_requested.connect(self.add_custom_path_fence)
        self.ball.create_fence_requested.connect(self.add_new_fence)
        self.ball.uninstall_requested.connect(self.uninstall_app)
        self.ball.show()

        self.keyboard_hook = GlobalKeyboardHook()
        self.keyboard_hook.install()

        self.health_timer = QTimer()
        self.health_timer.timeout.connect(self.check_fences_health)
        self.health_timer.start(10000)

        QTimer.singleShot(1500, self.restore_all_fences)
        QTimer.singleShot(5000, self.restore_all_fences)
        QTimer.singleShot(10000, self.restore_all_fences)

        self.process_command(sys.argv[1:])
        logging.info("Desktop initialized")

    def handle_new_connection(self):
        socket = self.server.nextPendingConnection()
        if socket.waitForReadyRead(1000):
            data = bytes(socket.readAll().data()).decode("utf-8")
            logging.info(f"Received IPC message: {data}")
            self.process_command(SingleInstanceController.decode_command(data))
        socket.disconnectFromServer()

    def process_command(self, args):
        if not args:
            return

        cmd = args[0]
        if cmd == "SHOW":
            self.restore_all_fences()
        elif cmd == "--create-fence":
            QTimer.singleShot(100, lambda: self.add_new_fence(QCursor.pos()))
        elif cmd == "--create-custom-fence":
            QTimer.singleShot(100, self.add_custom_path_fence)

    def load_fences(self):
        fences_data = self.config_manager.data.get("fences", [])
        logging.info(f"Loading {len(fences_data)} partitions from config")
        for f_conf in fences_data:
            try:
                self.create_fence_widget(f_conf)
            except Exception as e:
                logging.exception(
                    f"Failed to create partition {f_conf.get('id')}: {e}"
                )

    def create_fence_widget(self, f_conf):
        if not f_conf:
            return

        fence_id = f_conf["id"]
        if fence_id in self.fences:
            return

        geo = f_conf.get("geometry", [200, 200, 300, 200])
        fence = FenceWidget(
            fence_id,
            f_conf.get("title", "新分区"),
            parent=None,
            opacity=f_conf.get("opacity", 0.7),
            view_mode=f_conf.get("view_mode", "icon_medium"),
            custom_order=f_conf.get("custom_order", []),
            font_size=f_conf.get("font_size", 12),
            sort_by=f_conf.get("sort_by", "name"),
            sort_order=f_conf.get("sort_order", "asc"),
        )
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

        path = f_conf.get("path")
        if path and os.path.exists(path):
            fence.set_path(path)

        fence.show()
        self.fences[fence_id] = fence
        self._update_fence_hwnds()
        logging.info(
            f"Created partition {fence_id}: {f_conf.get('title')} at {geo}"
        )

    def add_custom_path_fence(self):
        folder = QFileDialog.getExistingDirectory(None, "选择分区文件夹")
        if not folder:
            return

        default_name = os.path.basename(folder) or folder.replace("\\", "/").strip("/")
        dialog = self._new_light_input_dialog(
            "新分区名称",
            "请输入这个分区的名称:",
            default_name,
        )
        ok = dialog.exec()
        title = dialog.textValue()
        if not ok or not title:
            return

        new_id = self.config_manager.add_fence(title, path=folder)
        pos = QCursor.pos()
        self.config_manager.update_fence_property(
            new_id, "geometry", [pos.x(), pos.y(), 300, 200]
        )
        self.create_fence_widget(self.config_manager.get_fence_by_id(new_id))

    def add_new_fence(self, pos=None):
        dialog = self._new_light_input_dialog("新建分区", "分区名称:")
        ok = dialog.exec()
        title = dialog.textValue()
        if not ok or not title:
            return

        new_id = self.config_manager.add_fence(title)
        if pos is None:
            pos = QPoint(200, 200)
        self.config_manager.update_fence_property(
            new_id, "geometry", [pos.x(), pos.y(), 300, 200]
        )
        self.create_fence_widget(self.config_manager.get_fence_by_id(new_id))

    def restore_all_fences(self):
        logging.info("Restoring all partition windows")
        for fence_id, fence in list(self.fences.items()):
            try:
                hwnd = int(fence.winId())
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.ShowWindow(hwnd, win32con.SW_SHOWNOACTIVATE)
                win32gui.SetWindowPos(
                    hwnd,
                    win32con.HWND_TOPMOST,
                    0,
                    0,
                    0,
                    0,
                    win32con.SWP_NOMOVE
                    | win32con.SWP_NOSIZE
                    | win32con.SWP_NOACTIVATE,
                )
                QTimer.singleShot(
                    100,
                    lambda h=hwnd: win32gui.SetWindowPos(
                        h,
                        win32con.HWND_NOTOPMOST,
                        0,
                        0,
                        0,
                        0,
                        win32con.SWP_NOMOVE
                        | win32con.SWP_NOSIZE
                        | win32con.SWP_NOACTIVATE,
                    ),
                )
            except Exception as e:
                logging.error(f"Failed to restore fence {fence_id}: {e}")

    def check_fences_health(self):
        recreate_ids = []
        for fence_id, fence in list(self.fences.items()):
            try:
                if not fence or not win32gui.IsWindow(int(fence.winId())):
                    recreate_ids.append(fence_id)
            except Exception:
                recreate_ids.append(fence_id)

        for fence_id in recreate_ids:
            try:
                self.fences[fence_id].close()
            except Exception:
                pass
            self.fences.pop(fence_id, None)
            self.create_fence_widget(self.config_manager.get_fence_by_id(fence_id))

    def on_fence_geometry_changed(self, fence_id, geometry):
        self.config_manager.update_fence_property(fence_id, "geometry", geometry)

    def on_fence_renamed(self, fence_id, title):
        self.config_manager.update_fence_property(fence_id, "title", title)

    def on_view_mode_changed(self, fence_id, mode):
        self.config_manager.update_fence_property(fence_id, "view_mode", mode)

    def on_opacity_changed(self, fence_id, opacity):
        self.config_manager.update_fence_property(fence_id, "opacity", opacity)

    def on_order_changed(self, fence_id, order):
        self.config_manager.update_fence_property(fence_id, "custom_order", order)

    def on_font_size_changed(self, fence_id, value):
        self.config_manager.update_fence_property(fence_id, "font_size", value)

    def on_sort_changed(self, fence_id, sort_by, sort_order):
        self.config_manager.update_fence_property(fence_id, "sort_by", sort_by)
        self.config_manager.update_fence_property(fence_id, "sort_order", sort_order)

    def on_fence_removed(self, fence_id):
        self.fences.pop(fence_id, None)
        self.config_manager.remove_fence(fence_id)
        self._update_fence_hwnds()

    def on_file_dropped(self, file_path, fence_id):
        f_conf = self.config_manager.get_fence_by_id(fence_id)
        if not f_conf:
            return

        target_dir = f_conf["path"]
        if os.path.dirname(file_path) == target_dir:
            logging.info(f"Ignored internal drop: {file_path}")
            return

        try:
            filename = os.path.basename(file_path)
            new_path = os.path.join(target_dir, filename)
            base, ext = os.path.splitext(new_path)
            counter = 1
            while os.path.exists(new_path):
                new_path = f"{base} ({counter}){ext}"
                counter += 1

            shutil.move(file_path, new_path)
            if fence_id in self.fences:
                self.fences[fence_id].add_file(new_path)
        except Exception as e:
            logging.error(f"Move file failed: {e}")

    def open_settings(self):
        current_root = self.config_manager.root_dir
        new_dir = QFileDialog.getExistingDirectory(
            None, "Select New Default Storage Directory", current_root
        )
        if not new_dir or new_dir == current_root:
            return

        reply = QMessageBox.question(
            None,
            "Confirm Change",
            "Change default storage to:\n"
            f"{new_dir}?\n\n"
            "默认文件夹中的分区会被移动。\n"
            "指定目录分区会保持不变。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        if self.config_manager.update_root_dir(new_dir):
            QMessageBox.information(
                None, "Success", "Storage directory updated successfully."
            )
        else:
            QMessageBox.warning(
                None, "Error", "Failed to update directory. Check logs for details."
            )

    def uninstall_app(self):
        reply = QMessageBox.question(
            None,
            "Uninstall",
            "This will remove the context menu, startup shortcut, and desktop shortcut.\n\n"
            "你的分区文件不会被删除。\n\n"
            "Are you sure you want to uninstall?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            SetupManager().uninstall()
            QMessageBox.information(
                None,
                "Uninstalled",
                "Integrations removed successfully. The application will now exit.",
            )
            sys.exit(0)

    def _update_fence_hwnds(self):
        hwnds = []
        for fence in self.fences.values():
            try:
                hwnds.append(int(fence.winId()))
            except Exception:
                pass
        GlobalKeyboardHook.set_fence_hwnds(hwnds)
        logging.info(f"Updated fence HWNDs for keyboard hook: {hwnds}")

    @staticmethod
    def _new_light_input_dialog(title, label, value=""):
        dialog = QInputDialog(None)
        dialog.setWindowTitle(title)
        dialog.setLabelText(label)
        if value:
            dialog.setTextValue(value)
        dialog.setStyleSheet(
            """
            QInputDialog { background-color: white; color: black; }
            QLabel { color: black; background-color: transparent; }
            QLineEdit { color: black; background-color: white; border: 1px solid #ccc; }
            QPushButton { color: black; background-color: #f0f0f0; border: 1px solid #ccc; padding: 5px; }
            """
        )
        return dialog

    def run(self):
        logging.info("App running...")
        exit_code = self.app.exec()
        if hasattr(self, "keyboard_hook"):
            self.keyboard_hook.uninstall()
        sys.exit(exit_code)


if __name__ == "__main__":
    try:
        app = NextGenDesktopApp()
        app.run()
    except SystemExit:
        raise
    except Exception as e:
        logging.critical(f"Fatal error: {e}")
        traceback.print_exc()
