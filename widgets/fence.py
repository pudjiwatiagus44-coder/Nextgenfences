import os
import sys
import logging
import ctypes
import win32gui
import win32con
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QApplication, 
                             QGridLayout, QFrame, QScrollArea, QMenu, 
                             QInputDialog, QMessageBox, QSlider, QWidgetAction, QFileIconProvider, QStyleOption, QStyle)
from PyQt6.QtCore import Qt, QSize, QPoint, QMimeData, QFileInfo, QEvent, pyqtSignal, QRect, QUrl, QTimer
from PyQt6.QtGui import QIcon, QPixmap, QDrag, QAction, QCursor, QDesktopServices, QColor, QPainter, QActionGroup

# Import the new shell menu helper
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from utils.shell_menu import ShellContextMenu
from core.z_order_manager import ZOrderManager
from utils.window_markers import mark_partition_window, unmark_partition_window

SW_SHOWNORMAL = 1


def _shell_execute(path, working_dir):
    return ctypes.windll.shell32.ShellExecuteW(
        None,
        "open",
        path,
        None,
        working_dir,
        SW_SHOWNORMAL,
    )


def open_path(path):
    if not os.path.exists(path):
        raise FileNotFoundError(path)

    working_dir = path if os.path.isdir(path) else os.path.dirname(path)
    result = _shell_execute(path, working_dir or None)
    if int(result) <= 32:
        raise OSError(f"ShellExecuteW failed with code {int(result)}")

    return result

try:
    from send2trash import send2trash
except ImportError:
    def send2trash(path):
        os.remove(path)

class IconWidget(QWidget):
    clicked = pyqtSignal(object) # Emit self when clicked

    def __init__(self, file_path, view_mode="icon_medium", parent=None, font_size=12):
        super().__init__(parent)
        self.file_path = file_path
        self.file_info = QFileInfo(file_path)
        self.view_mode = view_mode
        self.font_size = font_size
        self.setAcceptDrops(True) # Changed to True for internal reordering if needed
        self.selected = False
        # Essential for QWidget stylesheet background painting
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setup_ui()
        self.dragging = False
        self.start_pos = None
        
    def paintEvent(self, event):
        opt = QStyleOption()
        opt.initFrom(self)
        p = QPainter(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt, p, self)
        
    def setup_ui(self):
        if self.layout():
            QWidget().setLayout(self.layout())
        
        if self.view_mode == "list":
            from PyQt6.QtWidgets import QHBoxLayout
            self.layout_obj = QHBoxLayout(self)
            self.layout_obj.setContentsMargins(5, 2, 5, 2)
            self.layout_obj.setSpacing(10)
            self.layout_obj.setAlignment(Qt.AlignmentFlag.AlignLeft)
        else:
            self.layout_obj = QVBoxLayout(self)
            self.layout_obj.setContentsMargins(2, 2, 2, 2)
            self.layout_obj.setSpacing(2)
            self.layout_obj.setDirection(QVBoxLayout.Direction.TopToBottom)
        
        if self.view_mode == "icon_large":
            self.setFixedSize(100, 110)
            icon_size = 64
        elif self.view_mode == "icon_small":
            self.setFixedSize(60, 70)
            icon_size = 32
        elif self.view_mode == "list":
            self.setFixedSize(280, 40)
            icon_size = 24
        else: # icon_medium
            self.setFixedSize(80, 90)
            icon_size = 48

        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setStyleSheet("background: transparent; border: none;")
        
        provider = QFileIconProvider()
        icon = provider.icon(self.file_info)
        pixmap = icon.pixmap(icon_size, icon_size)
        self.icon_label.setPixmap(pixmap)
        
        # Hide extension logic
        if self.file_info.isDir():
            display_name = self.file_info.fileName()
        else:
            display_name = self.file_info.completeBaseName()
            if not display_name: # Fallback for files starting with dot or empty base
                display_name = self.file_info.fileName()
        
        self.text_label = QLabel(display_name)
        self.text_label.setStyleSheet(f"""
            QLabel {{
                color: white; 
                font-size: {self.font_size}px; 
                background: transparent;
                border: none;
            }}
        """)
        
        if self.view_mode == "list":
            self.text_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.text_label.setWordWrap(False)
            if len(display_name) > 35:
                self.text_label.setText(display_name[:32] + "...")
        else:
            self.text_label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
            self.text_label.setWordWrap(True)
            if len(display_name) > 20 and self.view_mode != "icon_large":
                self.text_label.setText(display_name[:17] + "...")

        self.layout_obj.addWidget(self.icon_label)
        self.layout_obj.addWidget(self.text_label)
        
    def set_selected(self, selected):
        self.selected = selected
        self.update_style()

    def update_style(self):
        # Using Object Name for specificity if needed, but direct stylesheet on self usually works with WA_StyledBackground
        if self.selected:
            # Highlight style (Windows 10-ish selection blue)
            # Use !important to ensure it overrides any defaults
            self.setStyleSheet("""
                IconWidget {
                    background-color: rgba(0, 120, 215, 100); 
                    border-radius: 5px; 
                    border: 1px solid rgba(0, 120, 215, 200);
                }
            """)
        else:
            self.setStyleSheet("""
                IconWidget {
                    background-color: transparent; 
                    border: none;
                }
            """)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            logging.info(f"Opening file: {self.file_path}")
            try:
                open_path(self.file_path)
            except Exception as e:
                logging.error(f"Failed to open {self.file_path}: {e}")
                QMessageBox.warning(self, "打开失败", f"无法打开:\n{self.file_path}\n\n{e}")

    def contextMenuEvent(self, event):
        # Select on right click too
        self.clicked.emit(self)
        self.set_selected(True)
        
        logging.info(f"Context menu requested for {self.file_path}")
        success = False
        try:
            shell_menu = ShellContextMenu()
            hwnd = int(self.window().winId())
            result = shell_menu.show_menu(hwnd, event.globalPos(), [self.file_path])
            
            # Check for custom actions
            if result == "RENAME_ACTION":
                self.rename_file()
                success = True
            else:
                success = result
                
        except Exception as e:
            logging.error(f"Failed to show shell menu: {e}")
        
        if not success:
            logging.info("Falling back to basic menu")
            self.show_basic_menu(event)

    def show_basic_menu(self, event):
        menu = QMenu(self)
        
        open_action = QAction("Open", self)
        open_action.triggered.connect(self.open_item)
        menu.addAction(open_action)
        
        # Simulate 'Properties' - just show info
        prop_action = QAction("Properties (Basic)", self)
        prop_action.triggered.connect(self.show_properties)
        menu.addAction(prop_action)
        
        menu.addSeparator()

        # Open Folder
        open_folder_action = QAction("Open Folder", self)
        open_folder_action.triggered.connect(self.open_folder)
        menu.addAction(open_folder_action)
        
        menu.addSeparator()
        
        rename_action = QAction("Rename", self)
        rename_action.triggered.connect(self.rename_file)
        menu.addAction(rename_action)
        
        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(self.delete_file)
        menu.addAction(delete_action)
        
        menu.exec(event.globalPos())

    def open_item(self):
        logging.info(f"Opening file: {self.file_path}")
        try:
            open_path(self.file_path)
        except Exception as e:
            logging.error(f"Failed to open {self.file_path}: {e}")
            QMessageBox.warning(self, "打开失败", f"无法打开:\n{self.file_path}\n\n{e}")

    def open_folder(self):
        if self.current_path and os.path.exists(self.current_path):
            open_path(self.current_path)

    def set_sort(self, sort_by):
        self.sort_by = sort_by
        self.sort_changed.emit(self.fence_id, self.sort_by, self.sort_order)
        self.refresh_files()

    def set_sort_order(self, order):
        self.sort_order = order
        self.sort_changed.emit(self.fence_id, self.sort_by, self.sort_order)
        self.refresh_files()

    def show_properties(self):
        info = f"File: {self.file_info.fileName()}\nPath: {self.file_path}\nSize: {self.file_info.size()} bytes"
        QMessageBox.information(self, "Properties", info)

    def rename_file(self):
        # Improved rename logic: preserve extension if user doesn't provide one
        current_name = self.file_info.fileName()
        base_name = self.file_info.completeBaseName()
        extension = self.file_info.suffix()
        
        # Pre-fill with base name only (since we hide extensions)
        # Use QInputDialog instance to style it properly
        dialog = QInputDialog(self)
        dialog.setWindowTitle("Rename")
        dialog.setLabelText("New name:")
        dialog.setTextValue(base_name)
        # Force light theme for readability
        dialog.setStyleSheet("""
            QInputDialog { background-color: white; color: black; }
            QLabel { color: black; background-color: transparent; }
            QLineEdit { color: black; background-color: white; border: 1px solid #ccc; }
            QPushButton { color: black; background-color: #f0f0f0; border: 1px solid #ccc; padding: 5px; }
        """)
        
        ok = dialog.exec()
        new_base_name = dialog.textValue()
        
        if ok and new_base_name:
            if new_base_name == base_name:
                return # No change

            # Re-attach extension if needed
            if extension and not new_base_name.lower().endswith(f".{extension.lower()}"):
                new_full_name = f"{new_base_name}.{extension}"
            else:
                new_full_name = new_base_name
                
            new_path = os.path.join(self.file_info.path(), new_full_name)
            
            try:
                os.rename(self.file_path, new_path)
                self.file_path = new_path
                self.file_info = QFileInfo(new_path)
                self.setup_ui() 
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not rename file: {e}")

    def delete_file(self):
        confirm = QMessageBox.question(self, "Delete", f"Are you sure you want to delete {self.file_info.fileName()}?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                send2trash(self.file_path)
                self.setParent(None)
                self.deleteLater()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not delete file: {e}")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_pos = event.pos()
            self.clicked.emit(self) # Select on click
            self.set_selected(True)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            if not self.start_pos:
                return
                
            distance = (event.pos() - self.start_pos).manhattanLength()
            if distance > QApplication.startDragDistance():
                drag = QDrag(self)
                mime = QMimeData()
                mime.setUrls([QUrl.fromLocalFile(self.file_path)])
                # Add custom data for internal reordering
                mime.setText(f"internal_move:{self.file_path}") 
                drag.setMimeData(mime)
                
                pixmap = self.grab()
                drag.setPixmap(pixmap)
                drag.setHotSpot(event.position().toPoint())
                
                drag.exec(Qt.DropAction.MoveAction)
        
    def enterEvent(self, event):
        if not self.selected:
            self.setStyleSheet("""
                IconWidget {
                    background-color: rgba(255, 255, 255, 40); 
                    border-radius: 5px;
                }
            """)
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self.selected:
            self.setStyleSheet("""
                IconWidget {
                    background-color: transparent;
                }
            """)
        super().leaveEvent(event)


class FenceWidget(QWidget):
    geometry_changed = pyqtSignal(str, list)
    file_dropped = pyqtSignal(str, str) 
    fence_removed = pyqtSignal(str) 
    fence_renamed = pyqtSignal(str, str) 
    view_mode_changed = pyqtSignal(str, str) 
    opacity_changed = pyqtSignal(str, float)
    order_changed = pyqtSignal(str, list)
    font_size_changed = pyqtSignal(str, int) 
    sort_changed = pyqtSignal(str, str, str) # NEW Signal: id, sort_by, sort_order

    def __init__(self, fence_id, title="新分区", parent=None, opacity=0.1, view_mode="icon_medium", custom_order=None, font_size=12, sort_by="name", sort_order="asc"):
        super().__init__(parent)
        self.fence_id = fence_id
        self.title = title
        self.opacity_val = opacity
        self.view_mode = view_mode
        self.font_size = font_size
        self.sort_by = sort_by
        self.sort_order = sort_order
        self._user_dragged = False  # Flag to track if user manually reordered
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        
        if parent:
            self.setWindowFlags(Qt.WindowType.SubWindow)
        else:
            # 使用 FramelessWindowHint
            # 不使用 StaysOnBottomHint，避免被桌面图标覆盖
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
            )
            
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)  # 不激活窗口
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        self.frame = QFrame()
        self.frame.setObjectName("MainFrame")
        self.update_style()
        
        self.frame_layout = QVBoxLayout(self.frame)
        self.frame_layout.setContentsMargins(10, 5, 10, 10)
        
        self.header = QLabel(title)
        self.header.setStyleSheet("color: white; font-weight: bold; font-size: 14px; padding: 5px;")
        self.frame_layout.addWidget(self.header)
        
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background: transparent;")
        
        # Catch clicks on background to deselect
        self.content_widget.mousePressEvent = self.on_content_click
        
        self.grid_layout = QGridLayout(self.content_widget)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.grid_layout.setSpacing(5)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        
        self.scroll = QScrollArea()
        self.scroll.setWidget(self.content_widget)
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical { 
                border: none;
                background: rgba(0,0,0,0);
                width: 8px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255,255,255,50);
                min-height: 20px;
                border-radius: 4px;
            }
        """)
        
        self.frame_layout.addWidget(self.scroll)
        self.main_layout.addWidget(self.frame)
        
        self.old_pos = None
        self.resizing = False
        self.resize_edge = None
        self.resize_margin = 10 
        self.current_path = None
        self.custom_order = custom_order if custom_order else [] 

        # Attach to desktop if no parent
        if not parent:
# 暂时禁用桌面嵌入，避免分区窗口消失的问题
            # QTimer.singleShot(500, self.attach_to_desktop)
            # QTimer.singleShot(2000, self.attach_to_desktop)
            # QTimer.singleShot(5000, self.attach_to_desktop)

            # self.visibility_timer = QTimer(self)
            pass

    def check_attachment(self):
        """定期检查嵌入状态，确保窗口仍然附着在桌面层"""
        try:
            hwnd = int(self.winId())
            mark_partition_window(hwnd)
            if not win32gui.IsWindow(hwnd):
                # 窗口已被销毁，停止定时器
                if hasattr(self, 'attachment_timer'):
                    self.attachment_timer.stop()
                return

            current_parent = win32gui.GetParent(hwnd)
            target_parent = ZOrderManager.get_workerw()
            
            if target_parent and current_parent != target_parent:
                logging.info(f"Fence {self.fence_id} parent mismatch ({current_parent} != {target_parent}). Re-attaching.")
                # 清除缓存，强制重新查找 WorkerW
                ZOrderManager.refresh_desktop_binding()
                self.attach_to_desktop()
        except Exception as e:
            logging.error(f"Error checking attachment: {e}")

    def attach_to_desktop(self):
        """将分区窗口嵌入到 Windows 桌面层"""
        try:
            hwnd = int(self.winId())
            mark_partition_window(hwnd)
            
            # 调用 ZOrderManager 进行嵌入
            success = ZOrderManager.embed_to_desktop(hwnd)
            
            # 确保窗口可见
            self.show()
            win32gui.ShowWindow(hwnd, win32con.SW_SHOWNOACTIVATE)
            
            if success:
                logging.info(f"Fence {self.fence_id} successfully embedded to desktop")
            else:
                logging.warning(f"Fence {self.fence_id} embed failed, using fallback mode")
                # 备用方案：将窗口提升到顶层
                win32gui.SetWindowPos(
                    hwnd,
                    win32con.HWND_TOPMOST,
                    0, 0, 0, 0,
                    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE
                )
                QTimer.singleShot(200, lambda: win32gui.SetWindowPos(
                    hwnd,
                    win32con.HWND_TOP,
                    0, 0, 0, 0,
                    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE
                ))
                
        except Exception as e:
            logging.error(f"Failed to attach fence {self.fence_id} to desktop: {e}")

    def showEvent(self, event):
        super().showEvent(event)
        mark_partition_window(int(self.winId()))

    def closeEvent(self, event):
        unmark_partition_window(int(self.winId()))
        super().closeEvent(event)
    
    def recover_after_show_desktop(self):
        """Restore the fence after Win+D or the taskbar Show Desktop button."""
        try:
            hwnd = int(self.winId())
            if not win32gui.IsWindow(hwnd):
                return

            target_parent = ZOrderManager.get_workerw()
            if target_parent and win32gui.GetParent(hwnd) != target_parent:
                self.attach_to_desktop()

            self.show()
            ZOrderManager.force_show_window(hwnd)
        except Exception as e:
            logging.error(f"Failed to recover fence {self.fence_id}: {e}")

    def ensure_visible(self):
        """确保窗口始终可见"""
        try:
            hwnd = int(self.winId())
            if win32gui.IsWindow(hwnd):
                # 如果窗口不可见，显示它
                if not win32gui.IsWindowVisible(hwnd):
                    logging.info(f"Fence {self.fence_id} was hidden, showing it")
                    win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
                    self.show()
        except Exception as e:
            logging.error(f"Error ensuring visibility: {e}")

    def ensure_visible(self):
        """Keep the fence attached and visible."""
        try:
            hwnd = int(self.winId())
            if not win32gui.IsWindow(hwnd):
                return

            target_parent = ZOrderManager.get_workerw()
            if target_parent and win32gui.GetParent(hwnd) != target_parent:
                logging.info(f"Fence {self.fence_id} detached from desktop, re-attaching")
                self.attach_to_desktop()

            if not win32gui.IsWindowVisible(hwnd) or win32gui.IsIconic(hwnd):
                logging.info(f"Fence {self.fence_id} was hidden, showing it")
                self.show()
                ZOrderManager.force_show_window(hwnd)
        except Exception as e:
            logging.error(f"Error ensuring visibility: {e}")

    def on_content_click(self, event):
        # Deselect all when clicking background
        self.deselect_all()
        # Propagate event? No need for QWidget
        
    def deselect_all(self):
        for i in range(self.grid_layout.count()):
            w = self.grid_layout.itemAt(i).widget()
            if isinstance(w, IconWidget):
                w.set_selected(False)

    def on_icon_clicked(self, clicked_icon):
        for i in range(self.grid_layout.count()):
            w = self.grid_layout.itemAt(i).widget()
            if isinstance(w, IconWidget) and w != clicked_icon:
                w.set_selected(False)

    def set_path(self, path):
        self.current_path = os.path.normpath(path)
        if self.current_path and os.path.exists(self.current_path):
            self.refresh_timer = QTimer(self)
            self.refresh_timer.timeout.connect(self.refresh_files)
            self.refresh_timer.start(5000)  # 每 5 秒刷新一次
            self.refresh_files()

    def open_folder(self):
        if self.current_path and os.path.exists(self.current_path):
            try:
                open_path(self.current_path)
            except Exception as e:
                logging.error(f"Failed to open folder: {e}")
                QMessageBox.warning(self, "Error", f"Failed to open folder: {e}")
        else:
            QMessageBox.information(self, "Info", "这个分区没有关联文件夹。")

    def refresh_files(self):
        if not self.current_path or not os.path.exists(self.current_path):
            return

        try:
            current_files = set()
            file_stats = {}
            
            # Normalize current_path just in case
            norm_root = os.path.normpath(self.current_path)
            
            # Normalize existing custom order to ensure matching
            self.custom_order = [os.path.normpath(p) for p in self.custom_order]

            for item in os.listdir(norm_root):
                if item.startswith('.'): continue
                full_path = os.path.join(norm_root, item)
                full_path = os.path.normpath(full_path)
                
                if os.path.isfile(full_path) or os.path.isdir(full_path):
                    current_files.add(full_path)
                    try:
                        stat = os.stat(full_path)
                        file_stats[full_path] = {
                            "name": item.lower(),
                            "size": stat.st_size,
                            "date": stat.st_mtime,
                            "type": os.path.splitext(item)[1].lower() if os.path.isfile(full_path) else " folder"
                        }
                    except:
                        pass

            displayed_files = set()
            widgets_map = {}
            for i in range(self.grid_layout.count()):
                w = self.grid_layout.itemAt(i).widget()
                if isinstance(w, IconWidget):
                    # Ensure widget path is normalized
                    norm_w_path = os.path.normpath(w.file_path)
                    displayed_files.add(norm_w_path)
                    widgets_map[norm_w_path] = w

            added = False
            for f in current_files:
                if f not in displayed_files:
                    # New file found, append to order
                    if f not in self.custom_order:
                        self.custom_order.append(f)
                        # We don't emit order_changed here if we are sorting, 
                        # because sorting will re-arrange anyway.
                    added = True

            removed = False
            for f in displayed_files:
                if f not in current_files:
                    if f in self.custom_order:
                        self.custom_order.remove(f)
                        self.order_changed.emit(self.fence_id, self.custom_order)
                    removed = True
            
            # Rebuild layout if changes or view mode mismatch
            needs_reflow = added or removed
            if not needs_reflow:
                for path, w in widgets_map.items():
                    # Check for font size change as well
                    if w.view_mode != self.view_mode or w.font_size != self.font_size:
                        w.view_mode = self.view_mode
                        w.font_size = self.font_size # Update font size
                        w.setup_ui()
                        needs_reflow = True
            
            # Check if sort order needs to be applied
            if self.sort_by != "custom" and not self._user_dragged:
                # Sort custom_order based on sort_by
                def get_sort_key(path):
                    if path not in file_stats: return ""
                    return file_stats[path].get(self.sort_by, "")
                
                reverse = (self.sort_order == "desc")
                sorted_files = sorted([f for f in self.custom_order if f in current_files], key=get_sort_key, reverse=reverse)
                
                if sorted_files != self.custom_order:
                    logging.info(f"Applying sort: {self.sort_by} {self.sort_order}")
                    self.custom_order = sorted_files
                    needs_reflow = True
            
            # Reset the user-dragged flag after processing
            if self._user_dragged:
                self._user_dragged = False

            if needs_reflow:
                self.reflow_layout()
                
        except Exception as e:
            logging.error(f"Error refreshing files: {e}")

    def update_style(self):
        alpha = int(self.opacity_val * 255)
        self.frame.setStyleSheet(f"""
            QFrame#MainFrame {{
                background-color: rgba(20, 20, 20, {alpha});
                border-radius: 10px;
                border: 1px solid rgba(255, 255, 255, 30);
            }}
        """)

    def add_file(self, file_path):
        if file_path not in self.custom_order:
            self.custom_order.append(file_path)
            self.order_changed.emit(self.fence_id, self.custom_order)
        self.reflow_layout()

    def add_file_internal(self, file_path):
        # Deprecated: usage should go through reflow_layout via custom_order
        pass 

    def remove_file(self, file_path):
        if file_path in self.custom_order:
            self.custom_order.remove(file_path)
            self.order_changed.emit(self.fence_id, self.custom_order)
        self.reflow_layout()

    def remove_file_internal(self, file_path):
        pass

    def clear_files(self):
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def reflow_layout(self):
        # 1. Clear current layout
        self.clear_files()
        
        # 2. Add widgets in custom_order
        widgets = []
        for file_path in self.custom_order:
            if os.path.exists(file_path):
                try:
                    w = IconWidget(file_path, view_mode=self.view_mode, font_size=self.font_size)
                    w.clicked.connect(self.on_icon_clicked) # Connect signal
                    widgets.append(w)
                except Exception as e:
                    logging.error(f"Error creating widget for {file_path}: {e}")

        # 3. Layout them
        if self.view_mode == "list":
            for idx, w in enumerate(widgets):
                self.grid_layout.addWidget(w, idx, 0)
        else:
            icon_w = 80
            if self.view_mode == "icon_large": icon_w = 100
            if self.view_mode == "icon_small": icon_w = 60
            
            available_width = self.width() - 40 
            cols = max(1, available_width // (icon_w + 10))
            
            for idx, w in enumerate(widgets):
                row = idx // cols
                col = idx % cols
                self.grid_layout.addWidget(w, row, col)

    def resizeEvent(self, event):
        self.reflow_layout()
        super().resizeEvent(event)
        self.geometry_changed.emit(self.fence_id, [self.x(), self.y(), self.width(), self.height()])

    def moveEvent(self, event):
        super().moveEvent(event)
        self.geometry_changed.emit(self.fence_id, [self.x(), self.y(), self.width(), self.height()])
    
    def changeEvent(self, event):
        """处理窗口状态变化事件"""
        super().changeEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().text().startswith("internal_move:"):
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        mime = event.mimeData()
        
        # Internal Reorder
        if mime.text().startswith("internal_move:"):
            file_path = mime.text().replace("internal_move:", "")
            if file_path in self.custom_order:
                self.custom_order.remove(file_path)
                
                # Calculate drop position based on mouse position
                drop_y = event.position().y()
                drop_x = event.position().x()
                
                # Get icon sizes based on view mode
                icon_h = 80
                if self.view_mode == "icon_large": icon_h = 100
                if self.view_mode == "icon_small": icon_h = 60
                
                icon_w = 80
                if self.view_mode == "icon_large": icon_w = 100
                if self.view_mode == "icon_small": icon_w = 60
                
                # Calculate row/column from position
                row_height = icon_h + 5
                drop_row = max(0, int(drop_y / row_height))
                cols = max(1, (self.width() - 40) // (icon_w + 10))
                drop_col = max(0, min(int(drop_x / (icon_w + 10)), cols - 1))
                
                # Calculate insert position
                drop_pos = drop_row * cols + drop_col
                drop_pos = max(0, min(drop_pos, len(self.custom_order)))
                
                # Insert at calculated position
                self.custom_order.insert(drop_pos, file_path)
                
                # Set flag to prevent auto-sort from overriding
                self._user_dragged = True
                self.order_changed.emit(self.fence_id, self.custom_order)
                
                # 设置为自定义排序模式
                if self.sort_by != "custom":
                    self.sort_by = "custom"
                    self.sort_changed.emit(self.fence_id, self.sort_by, self.sort_order)
                
                self.reflow_layout()
                event.accept()
                return

        # External Drop
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        for f in files:
            self.file_dropped.emit(f, self.fence_id)
        
        QTimer.singleShot(200, self.refresh_files)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        # Apply white style to fence context menu as well
        menu.setStyleSheet("""
            QMenu {
                background-color: white;
                color: black;
                border: 1px solid #ccc;
                padding: 5px;
                font-size: 14px;
            }
            QMenu::item {
                padding: 5px 20px;
            }
            QMenu::item:selected {
                background-color: #eee;
            }
        """)
        
        # Add Open Folder here too
        open_folder_action = QAction("Open Folder", self)
        open_folder_action.triggered.connect(self.open_folder)
        menu.addAction(open_folder_action)
        
        menu.addSeparator()

        view_menu = menu.addMenu("View")
        
        action_large = QAction("Large Icons", self)
        action_large.setCheckable(True)
        action_large.setChecked(self.view_mode == "icon_large")
        action_large.triggered.connect(lambda _: self.set_view_mode("icon_large"))
        view_menu.addAction(action_large)
        
        action_medium = QAction("Medium Icons", self)
        action_medium.setCheckable(True)
        action_medium.setChecked(self.view_mode == "icon_medium")
        action_medium.triggered.connect(lambda _: self.set_view_mode("icon_medium"))
        view_menu.addAction(action_medium)
        
        action_small = QAction("Small Icons", self)
        action_small.setCheckable(True)
        action_small.setChecked(self.view_mode == "icon_small")
        action_small.triggered.connect(lambda _: self.set_view_mode("icon_small"))
        view_menu.addAction(action_small)
        
        action_list = QAction("List View", self)
        action_list.setCheckable(True)
        action_list.setChecked(self.view_mode == "list")
        action_list.triggered.connect(lambda _: self.set_view_mode("list"))
        view_menu.addAction(action_list)
        
        # Sort By
        sort_menu = menu.addMenu("Sort By")
        
        sort_group = QActionGroup(self)
        
        # Name
        action_name = QAction("Name", self)
        action_name.setCheckable(True)
        action_name.setChecked(self.sort_by == "name")
        action_name.triggered.connect(lambda _: self.set_sort("name"))
        sort_group.addAction(action_name)
        sort_menu.addAction(action_name)
        
        # Date
        action_date = QAction("Date", self)
        action_date.setCheckable(True)
        action_date.setChecked(self.sort_by == "date")
        action_date.triggered.connect(lambda _: self.set_sort("date"))
        sort_group.addAction(action_date)
        sort_menu.addAction(action_date)
        
        # Size
        action_size = QAction("Size", self)
        action_size.setCheckable(True)
        action_size.setChecked(self.sort_by == "size")
        action_size.triggered.connect(lambda _: self.set_sort("size"))
        sort_group.addAction(action_size)
        sort_menu.addAction(action_size)
        
        # Type
        action_type = QAction("Type", self)
        action_type.setCheckable(True)
        action_type.setChecked(self.sort_by == "type")
        action_type.triggered.connect(lambda _: self.set_sort("type"))
        sort_group.addAction(action_type)
        sort_menu.addAction(action_type)
        
        sort_menu.addSeparator()
        
        # Order
        action_asc = QAction("Ascending", self)
        action_asc.setCheckable(True)
        action_asc.setChecked(self.sort_order == "asc")
        action_asc.triggered.connect(lambda _: self.set_sort_order("asc"))
        sort_menu.addAction(action_asc)
        
        action_desc = QAction("Descending", self)
        action_desc.setCheckable(True)
        action_desc.setChecked(self.sort_order == "desc")
        action_desc.triggered.connect(lambda _: self.set_sort_order("desc"))
        sort_menu.addAction(action_desc)
        
        menu.addSeparator()
        
        # Opacity Slider
        opacity_action = QWidgetAction(self)
        slider_widget = QWidget()
        slider_layout = QVBoxLayout(slider_widget)
        slider_layout.setContentsMargins(5,5,5,5)
        slider_label = QLabel(f"Opacity: {int(self.opacity_val * 100)}%")
        slider_label.setStyleSheet("color: black;")
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(10, 100)
        slider.setValue(int(self.opacity_val * 100))
        slider.valueChanged.connect(lambda v: self.set_opacity(v, slider_label))
        slider_layout.addWidget(slider_label)
        slider_layout.addWidget(slider)
        opacity_action.setDefaultWidget(slider_widget)
        menu.addAction(opacity_action)

        menu.addSeparator()

        # Font Size Slider
        font_action = QWidgetAction(self)
        font_widget = QWidget()
        font_layout = QVBoxLayout(font_widget)
        font_layout.setContentsMargins(5,5,5,5)
        font_label = QLabel(f"Font Size: {self.font_size}px")
        font_label.setStyleSheet("color: black;")
        font_slider = QSlider(Qt.Orientation.Horizontal)
        font_slider.setRange(8, 24)
        font_slider.setValue(self.font_size)
        font_slider.valueChanged.connect(lambda v: self.set_font_size(v, font_label))
        font_layout.addWidget(font_label)
        font_layout.addWidget(font_slider)
        font_action.setDefaultWidget(font_widget)
        menu.addAction(font_action)
        
        menu.addSeparator()
        
        rename_action = QAction("重命名分区", self)
        rename_action.triggered.connect(self.rename_fence)
        menu.addAction(rename_action)
        
        remove_action = QAction("删除分区", self)
        remove_action.triggered.connect(self.remove_fence)
        menu.addAction(remove_action)
        
        menu.exec(event.globalPos())

    def set_view_mode(self, mode):
        self.view_mode = mode
        self.view_mode_changed.emit(self.fence_id, mode)
        self.refresh_files()

    def set_sort(self, sort_by):
        self.sort_by = sort_by
        self.sort_changed.emit(self.fence_id, self.sort_by, self.sort_order)
        self.refresh_files()

    def set_sort_order(self, order):
        self.sort_order = order
        self.sort_changed.emit(self.fence_id, self.sort_by, self.sort_order)
        self.refresh_files()

    def set_opacity(self, value, label):
        opacity = value / 100.0
        self.opacity_val = opacity
        label.setText(f"Opacity: {value}%")
        self.update_style()
        self.opacity_changed.emit(self.fence_id, opacity)

    def set_font_size(self, value, label):
        self.font_size = value
        label.setText(f"Font Size: {value}px")
        self.font_size_changed.emit(self.fence_id, value)
        # Trigger layout update to apply font size
        self.refresh_files()

    def rename_fence(self):
        # Use QInputDialog instance to style it properly
        dialog = QInputDialog(self)
        dialog.setWindowTitle("重命名分区")
        dialog.setLabelText("New Name:")
        dialog.setTextValue(self.title)
        # Force light theme for readability
        dialog.setStyleSheet("""
            QInputDialog { background-color: white; color: black; }
            QLabel { color: black; background-color: transparent; }
            QLineEdit { color: black; background-color: white; border: 1px solid #ccc; }
            QPushButton { color: black; background-color: #f0f0f0; border: 1px solid #ccc; padding: 5px; }
        """)
        
        ok = dialog.exec()
        new_title = dialog.textValue()

        if ok and new_title:
            self.title = new_title
            self.header.setText(new_title)
            self.fence_renamed.emit(self.fence_id, new_title)

    def remove_fence(self):
        confirm = QMessageBox.question(self, "删除分区", "确定删除这个分区吗？文件会保留在原文件夹中。",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            self.fence_removed.emit(self.fence_id)
            self.close()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.resize_edge = self.get_resize_edge(event.pos())
            if self.resize_edge:
                self.resizing = True
                self.old_pos = event.globalPosition().toPoint()
            else:
                self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        edge = self.get_resize_edge(event.pos())
        if edge:
            if edge == "right" or edge == "left":
                self.setCursor(Qt.CursorShape.SizeHorCursor)
            elif edge == "bottom" or edge == "top":
                self.setCursor(Qt.CursorShape.SizeVerCursor)
            elif edge == "bottom_right":
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

        if self.old_pos:
            delta = event.globalPosition().toPoint() - self.old_pos
            if self.resizing and self.resize_edge:
                rect = self.geometry()
                # Store original geometry for complex calculations
                original_rect = QRect(rect)
                
                if self.resize_edge == "right":
                    rect.setWidth(rect.width() + delta.x())
                elif self.resize_edge == "bottom":
                    rect.setHeight(rect.height() + delta.y())
                elif self.resize_edge == "bottom_right":
                    rect.setWidth(rect.width() + delta.x())
                    rect.setHeight(rect.height() + delta.y())
                elif self.resize_edge == "left":
                    # Resize from left: Need to change x AND width
                    # New X = Old X + delta
                    # New Width = Old Width - delta
                    new_x = rect.x() + delta.x()
                    new_w = rect.width() - delta.x()
                    
                    if new_w > 100:
                         rect.setX(new_x)
                         # setX automatically adjusts width if we don't handle it carefully? 
                         # No, setX moves the left edge, keeping width same? No, setX moves left edge, changing width?
                         # Actually in Qt QRect: setLeft changes left edge and width (keeping right edge fixed).
                         # setX just moves the whole rect? No, setX is same as setLeft for QRect?
                         # Let's verify: setLeft() moves the left edge.
                         rect.setLeft(new_x)
                
                if rect.width() > 100 and rect.height() > 100:
                    self.setGeometry(rect)
            else:
                self.move(self.pos() + delta)
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.old_pos = None
        self.resizing = False
        self.resize_edge = None
        self.geometry_changed.emit(self.fence_id, [self.x(), self.y(), self.width(), self.height()])

    def get_resize_edge(self, pos):
        m = self.resize_margin
        w, h = self.width(), self.height()
        
        if pos.x() > w - m and pos.y() > h - m: return "bottom_right"
        if pos.x() > w - m: return "right"
        if pos.y() > h - m: return "bottom"
        if pos.x() < m: return "left"
        return None
