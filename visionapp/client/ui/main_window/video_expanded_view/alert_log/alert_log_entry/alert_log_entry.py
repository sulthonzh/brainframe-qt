from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPixmap
from PyQt5.uic import loadUi
from PyQt5.QtCore import Qt

from visionapp.client.ui.resources.paths import qt_ui_paths, image_paths


class AlertLogEntry(QWidget):
    def __init__(self, time="", alarm_name="", parent=None):
        super().__init__(parent)
        loadUi(qt_ui_paths.alert_log_entry_ui, self)

        self.time_label.setText(time)
        self.alarm_name_label.setText(alarm_name)
        pixmap = QPixmap(str(image_paths.alert_icon))
        pixmap = pixmap.scaled(32, 32, transformMode=Qt.SmoothTransformation)
        self.alert_icon_label.setPixmap(pixmap)
