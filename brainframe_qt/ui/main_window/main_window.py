from typing import Optional

import typing
from PyQt5.QtWidgets import QWidget

from brainframe.client.ui.main_window.main_window_ui import MainWindowUI


class MainWindow(MainWindowUI):

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self._init_signals()

    def _init_signals(self):
        self.toolbar.stream_activity_action.triggered.connect(
            self.display_stream_configuration)

    def display_stream_configuration(self):
        print("Display")
