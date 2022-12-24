"""This is the API that any object detector shares"""

import abc
from typing import Optional, List, Callable

import numpy as np

from autopilot.tracking.detector.api import Detection


class Tracker(abc.ABC):
    """An object tracker API that follows an object through an image sequence (video)."""

    _loaded: bool = False

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Returns the name of the tracker."""
        return 'Unnamed'

    @property
    @abc.abstractmethod
    def detector(self) -> Optional['Detector']:
        """Returns the detector used by the tracker, or None if detector is not used by the tracker.
        It will always return a value if the tracker supports detection."""
        return None

    @detector.setter
    @abc.abstractmethod
    def detector(self, detector: 'Detector'):
        """Sets the detector to be used by the tracker, if any."""
        pass

    def load(self, callback: Callable[[float], None] = None):
        """Synchronously starts loading the model (if required).

        No other method should be called until this method returns.

        :param callback: a callback that will be called with the progress of the loading [0, 1].
        """
        if callback:
            callback(1)
        self._loaded = True

    def is_loaded(self) -> bool:
        """Returns True if the model is loaded."""
        return self._loaded

    def unload(self):
        """Unloads the model (if required)."""
        self._loaded = False

    @abc.abstractmethod
    def track(self, img: np.ndarray, min_confidence: float = 0.5, max_results: int = -1) -> (
            Optional[Detection], List[Detection]):
        """
        :param img: the image where the detector should run in the format [height, width, channels(3)].
            Note that the implementation will resize and crop the image if required.
            It should also adapt the data type, assuming floats to be in the range [0, 1].
        :param min_confidence: the minimum confidence required to return a detection.
        :param max_results: the maximum number of results to return, or -1 for no limit.
        :return: the tracked object or None if no object was detected. It also returns the list of all raw detections.
        """
        pass

# TODO: Implement state of the art trackers and recovery strategies like matching the image with the previous detection
