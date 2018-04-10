from datetime import datetime

from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import QTimer, pyqtSlot
from PyQt5.uic import loadUi

from visionapp.client.ui.resources.paths import qt_ui_paths
from .alert_log_entry.alert_log_entry import AlertLogEntry
from visionapp.client.api import api


class AlertLog(QWidget):
    def __init__(self, parent):
        super().__init__(parent)

        loadUi(qt_ui_paths.alert_log_ui, self)

        self.stream_id = None
        self.alert_widgets = {}  # {alert_id: Alert}

        self.status_poller = api.get_status_poller()

        # Start a QTimer for periodically updating unverified alerts
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_unverified_alerts)
        self.timer.start(1000)

        self.alert_log.setLayout(QVBoxLayout())

    def update_unverified_alerts(self):
        if self.stream_id is None: return

        unverified = api.get_unverified_alerts(self.stream_id)

        for alert in unverified:

            if self.alert_widgets.get(alert.id, None) is None:
                # If the alert widget hasn't been made yet
                alarm = self.status_poller.get_alarm(self.stream_id,
                                                     alert.alarm_id)
                if alarm is None: continue
                alert_widget = AlertLogEntry(start_time=alert.start_time,
                                             end_time=alert.end_time,
                                             alarm_name=alarm.name)
                self.alert_log.layout().insertWidget(0, alert_widget)
                self.alert_widgets[alert.id] = alert_widget
            else:
                # If the alert already exists, update the information
                alert_widget = self.alert_widgets[alert.id]
                alert_widget.update_time(alert.start_time, alert.end_time)


    @pyqtSlot(int)
    def change_stream(self, stream_id):
        for alert_widget in self.alert_widgets.values():
            alert_widget.deleteLater()
        self.alert_widgets = {}
        self.stream_id = stream_id
