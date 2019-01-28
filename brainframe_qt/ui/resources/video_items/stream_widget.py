from typing import Callable

from PyQt5.QtCore import Qt, QCoreApplication
from PyQt5.QtWidgets import QGraphicsView

from brainframe.shared.stream_listener import StreamListener
from brainframe.client.api import api
from brainframe.client.api.codecs import StreamConfiguration
from brainframe.client.api.synced_reader import SyncedStreamReader
from brainframe.client.ui.resources.paths import image_paths
from brainframe.client.ui.resources import settings

from .stream_graphics_scene import StreamGraphicsScene


class StreamWidget(QGraphicsView):
    """Base widget that uses Stream object to get frames.

    Makes use of a QTimer to get frames
    """
    _draw_lines = None
    _draw_regions = None
    _draw_detections = None
    _use_polygons = None
    _show_detection_labels = None
    _show_recognition_label = None
    _show_detection_tracks = None
    _show_attributes = None

    # Type hint that self.scene() is more than just a QGraphicsScene
    scene: Callable[[], StreamGraphicsScene]

    def __init__(self, stream_conf, parent=None):
        # Order matters here, unfortunately
        super().__init__(parent)

        # Remove ugly white background and border from QGraphicsView
        self.setStyleSheet("background-color: transparent; border: 0px")

        # Scene to draw items to
        self.setScene(StreamGraphicsScene())

        self.stream_listener = StreamListener()
        self.stream_reader: SyncedStreamReader = None  # Set in change_stream
        self.change_stream(stream_conf)

        self.startTimer(1000 // 30)

    def timerEvent(self, a0):
        if self.stream_listener.frame_event.is_set():
            self.stream_listener.frame_event.clear()
            self.handle_frame()

        if self.stream_listener.stream_initializing_event.is_set():
            self.stream_listener.stream_initializing_event.clear()
            self.handle_stream_initializing()

        if self.stream_listener.stream_halted_event.is_set():
            self.stream_listener.stream_halted_event.clear()
            self.handle_stream_halted()

        if self.stream_listener.stream_closed_event.is_set():
            self.stream_listener.stream_closed_event.clear()
            self.handle_stream_closed()

        if self.stream_listener.stream_error_event.is_set():
            self.stream_listener.stream_error_event.clear()
            self.handle_stream_error()

    def handle_frame(self):

        self.scene().remove_all_items()

        processed_frame = self.stream_reader.latest_processed_frame
        self.scene().set_frame(frame=processed_frame.frame)

        if self.draw_lines:
            self.scene().draw_lines(processed_frame.zone_statuses)

        if self.draw_regions:
            self.scene().draw_regions(processed_frame.zone_statuses)

        if self.draw_detections:
            self.scene().draw_detections(
                frame_tstamp=processed_frame.tstamp,
                tracks=processed_frame.tracks,
                use_polygons=self.use_polygons,
                show_recognition=self.show_recognition_label,
                show_tracks=self.show_detection_tracks,
                show_detection_labels=self.show_detection_labels,
                show_attributes=self.show_attributes)

    def handle_stream_initializing(self):
        self.scene().remove_all_items()
        self.scene().set_frame(path=image_paths.connecting_to_stream)
        ...

    def handle_stream_halted(self):
        self.scene().remove_all_items()
        self.scene().set_frame(path=image_paths.connection_lost)

    def handle_stream_closed(self):
        self.handle_stream_halted()

    def handle_stream_error(self):
        self.scene().remove_all_items()
        self.scene().set_frame(path=image_paths.error)

    def change_stream(self, stream_conf: StreamConfiguration):
        if not stream_conf:
            # User should never see this
            self.handle_stream_error()
            return

        if self.stream_reader:
            self.stream_reader.remove_listener(self.stream_listener)
            QCoreApplication.removePostedEvents(self)
        self.stream_reader = api.get_stream_reader(stream_conf)
        self.stream_reader.add_listener(self.stream_listener)

        # Make sure video is unsubscribed before it is GCed
        self.destroyed.disconnect()
        self.destroyed.connect(
            lambda: self.stream_reader.remove_listener(self.stream_listener))

    def hasHeightForWidth(self):
        """Enable the use of heightForWidth"""
        return True

    def heightForWidth(self, width: int):
        """Lock the aspect ratio of the widget to match the aspect ratio of the
        scene and its video frame
        """
        if not self.scene().width():
            return 0

        return width * self.scene().height() / self.scene().width()

    def resizeEvent(self, event=None):
        """Take up entire width using aspect ratio of scene"""

        current_frame = self.scene().current_frame

        if current_frame is not None:
            # EXTREMELY IMPORTANT LINE!
            # The sceneRect grows but never shrinks automatically
            self.scene().setSceneRect(current_frame.boundingRect())
            self.fitInView(current_frame.boundingRect(), Qt.KeepAspectRatio)

    @property
    def draw_lines(self):
        if self._draw_lines is not None:
            return self._draw_lines
        return settings.draw_lines.val()

    @draw_lines.setter
    def draw_lines(self, draw_lines):
        self._draw_lines = draw_lines

    @property
    def draw_regions(self):
        if self._draw_regions is not None:
            return self._draw_regions
        return settings.draw_regions.val()

    @draw_regions.setter
    def draw_regions(self, draw_regions):
        self._draw_regions = draw_regions

    @property
    def draw_detections(self):
        if self._draw_detections is not None:
            return self._draw_detections
        return settings.draw_detections.val()

    @draw_detections.setter
    def draw_detections(self, draw_detections):
        self._draw_detections = draw_detections

    @property
    def use_polygons(self):
        if self._use_polygons is not None:
            return self._use_polygons
        return settings.use_polygons.val()

    @use_polygons.setter
    def use_polygons(self, use_polygons):
        self._use_polygons = use_polygons

    @property
    def show_recognition_label(self):
        if self._show_recognition_label is not None:
            return self._show_recognition_label
        return settings.show_recognition_confidence.val()

    @show_recognition_label.setter
    def show_recognition_label(self, show_detection_confidence):
        self._show_recognition_label = show_detection_confidence

    @property
    def show_detection_tracks(self):
        if self._show_detection_tracks is not None:
            return self._show_detection_tracks
        return settings.show_detection_tracks.val()

    @show_detection_tracks.setter
    def show_detection_tracks(self, show_detection_tracks):
        self._show_detection_tracks = show_detection_tracks

    @property
    def show_detection_labels(self):
        if self._show_detection_labels is not None:
            return self._show_detection_labels
        return settings.show_detection_labels.val()

    @show_detection_labels.setter
    def show_detection_labels(self, show_detection_labels):
        self._show_detection_labels = show_detection_labels

    @property
    def show_attributes(self):
        if self._show_attributes is not None:
            return self._show_attributes
        return settings.show_attributes.val()

    @show_attributes.setter
    def show_attributes(self, show_attributes):
        self._show_attributes = show_attributes
