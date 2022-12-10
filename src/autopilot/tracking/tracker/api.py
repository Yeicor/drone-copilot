"""This is the API that any object detector shares"""

import abc
from typing import Optional, List

import numpy as np

from autopilot.tracking.detector.api import Detection


class Tracker(abc.ABC):
    """An object tracker API that follows an object through an image sequence (video)."""

    @abc.abstractmethod
    def track(self, img: np.ndarray, min_confidence: float = 0.5) -> (Optional[Detection], List[Detection]):
        """
        :param img: the image where the detector should run in the format [height, width, channels(3)].
            Note that the implementation will resize and crop the image if required.
            It should also adapt the data type, assuming floats to be in the range [0, 1].
        :param min_confidence: the minimum confidence required to return a detection.
        :return: the tracked object or None if no object was detected. It also returns the list of all raw detections.
        """
        pass

# TODO: Implement state of the art trackers and recovery strategies like matching the image with the previous detection
