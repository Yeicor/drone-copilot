"""This is the API that any object detector shares"""

import abc
from dataclasses import dataclass
from typing import List, Callable

import numpy as np


@dataclass
class Rect:
    """A rectangle in 2D space."""

    x_min: float
    """The horizontal start in the range [0, 1], relative of the input size"""

    y_min: float
    """The vertical start in the range [0, 1], relative of the input size"""

    x_max: float
    """The horizontal end in the range [0, 1], relative of the input size"""

    y_max: float
    """The vertical end in the range [0, 1], relative of the input size"""


@dataclass
class Category:
    """A result of a classification task."""

    id: int
    """The unique ID of the category"""

    label: str
    """The display name of the category"""


@dataclass
class Detection:
    """A detected object in an image."""

    bounding_box: Rect
    """The bounding box of the detection (smallest rect that contains the detection)"""

    confidence: float
    """The confidence of the detection, see `categories` for classification confidence"""

    category: Category
    """The category of the found object. It may return always the same category"""

    # TODO: segmentations, features/key points and other kinds of detection metadata


class Detector(abc.ABC):
    """An object detector API that looks for matches in a single image."""

    _loaded = False

    def load(self, callback: Callable[[float], None] = None):
        """Synchronously starts loading the model (if required).

        No other method should be called until this method returns.

        :param callback: a callback that will be called with the progress of the loading [0, 1].
        """
        self._loaded = True
        if callback:
            callback(1)

    def is_loaded(self) -> bool:
        """Returns True if the model is loaded."""
        return self._loaded

    def unload(self):
        """Unloads the model (if required)."""
        self._loaded = False

    @abc.abstractmethod
    def detect(self, img: np.ndarray, min_confidence: float = 0.5, max_results: int = -1) -> List[Detection]:
        """
        :param img: the image where the detector should run in the format [height, width, channels(3)].
            Note that the implementation will resize and crop the image if required.
            It should also adapt the data type, assuming floats to be in the range [0, 1].
        :param min_confidence: the minimum confidence required to return a detection.
        :param max_results: the maximum number of top-scored detection results to return, or -1 for all of them.
        :return: the list of matches found, SORTED by descending detection confidence.
        """
        pass
