from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer, QTime, QDate
from PyQt6.QtGui import QFont

class ClockWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resize(500, 300)
        # Ensure widget is visible and handles transparency
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.time_label = QLabel()
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_label.setStyleSheet("color: white; font-weight: bold; text-shadow: 2px 2px 4px #000000;")
        self.time_label.setFont(QFont("Segoe UI", 80))
        
        self.date_label = QLabel()
        self.date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.date_label.setStyleSheet("color: #E0E0E0; font-weight: bold; text-shadow: 1px 1px 2px #000000;")
        self.date_label.setFont(QFont("Segoe UI", 25))
        
        layout.addWidget(self.time_label)
        layout.addWidget(self.date_label)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)
        self.update_time()

        # Dragging
        self.dragging = False
        self.offset = None

    def update_time(self):
        current_time = QTime.currentTime()
        current_date = QDate.currentDate()
        self.time_label.setText(current_time.toString("HH:mm"))
        self.date_label.setText(current_date.toString("dddd, MMMM d"))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.offset = event.pos()

    def mouseMoveEvent(self, event):
        if self.dragging and self.offset:
            # Move relative to parent
            self.move(self.mapToParent(event.pos() - self.offset))

    def mouseReleaseEvent(self, event):
        self.dragging = False
