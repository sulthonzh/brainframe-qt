from uuid import UUID
from typing import Tuple, Deque, Iterator
from collections import deque

from brainframe.client.api import codecs

DET_HIST_TYPE = Tuple[codecs.Detection, float]


class DetectionTrack:
    def __init__(self, history=None, max_size=1000):
        """"""
        self._max_size = max_size
        self._history: Deque[DET_HIST_TYPE]
        self._history = history if history else deque(maxlen=self._max_size)

    def __iter__(self) -> Iterator[DET_HIST_TYPE]:
        """
        The 0th index in track should be the latest

        """
        for item in self._history:
            yield item

    def __repr__(self):
        if len(self._history):
            return f"DetectionTrack(tstamp: {self.latest_tstamp}, " \
                f"det:{self.latest_det})"
        else:
            return "DetectionTrack()"

    def add_detection(self, detection, tstamp):
        """Pops the oldest (if len is > max size) and inserts the newest
        to the beginning of the list."""
        self._history.appendleft((detection, tstamp))

    @property
    def class_name(self) -> str:
        """Get the class name for this detection"""
        return self._history[0][0].class_name

    @property
    def track_id(self) -> UUID:
        """Get the track_id for this detection"""
        return self._history[0][0].track_id

    @property
    def latest_tstamp(self) -> float:
        return self._history[0][1]

    @property
    def latest_det(self) -> codecs.Detection:
        return self._history[0][0]

    def copy(self) -> 'DetectionTrack':
        return DetectionTrack(
            max_size=self._max_size,
            history=self._history.copy())
