import sys
from abc import ABC, abstractmethod
from typing import Optional, List, Callable

import numpy as np

from autopilot.tracking.detector.api import Detection, Detector
from autopilot.tracking.tracker.api import Tracker


class DetectorBasedTracker(Tracker, ABC):
    """A simple tracker that runs a detector on each frame and follows a customizable strategy to track the object."""

    def __init__(self, detector: Detector):
        super().__init__()
        self._detector = detector

    @property
    def detector(self) -> Optional['Detector']:
        return self._detector

    @detector.setter
    def detector(self, detector: 'Detector'):
        self._detector = detector

    def load(self, callback: Callable[[float], None] = None):
        self.detector.load(lambda pr: callback(pr * 0.99))
        super().load(callback)

    def is_loaded(self) -> bool:
        return self.detector.is_loaded() and super().is_loaded()

    def unload(self):
        self.detector.unload()
        super().unload()

    def track(self, img: np.ndarray, min_confidence: float = 0.5) -> (Optional[Detection], List[Detection]):
        all_detections = self.detector.detect(img, min_confidence)
        return self.track_strategy(all_detections), all_detections

    @abstractmethod
    def track_strategy(self, detections: List[Detection]) -> Optional[Detection]:
        """The strategy to follow to track the object.
        :param detections: the list of detections of the current frame.
        :return: the tracked object's detection data or None if the target was not detected.
        """
        pass

    # TODO: Recovery strategy


class DetectorBasedTrackerAny(DetectorBasedTracker):
    """Tracks the object that is detected with the most confidence on the first frame.

    Different filters and weights can be applied to choose the best detection on next frames.
    """

    def __init__(self, detector: Detector, category_filter: Optional[int] = None, same_category_weight: float = 1,
                 confidence_score_weight: float = 1, dist_iou_score_weight: float = 2, min_score: float = 1):
        """
        :param detector: the detector to use.
        :param category_filter: the category to track, or None to track any class.
        :param same_category_weight: the score to add if the tracked and detected object are of same category.
        :param confidence_score_weight: the weight of the confidence in the score of the detection.
        :param dist_iou_score_weight: the weight of the "distance" [0, 1] to a previous detection in the score.
        :param min_score: the minimum score to consider a detection valid.
        """
        super().__init__(detector)
        self.category_filter = category_filter
        self.same_category_weight = same_category_weight
        self.confidence_weight = confidence_score_weight
        self.distance_weight = dist_iou_score_weight
        self.min_score = min_score
        self.tracked = None

    @property
    def name(self) -> str:
        return 'DetectorBasedTrackerAny'

    def track_strategy(self, detections: List[Detection]) -> Optional[Detection]:
        if len(detections) == 0:
            return None
        # The strategy is to maximize the score of the detection
        self.tracked = max(detections, key=lambda d: self.tracking_score(self.tracked, d))
        return self.tracked

    def tracking_score(self, tracked: Optional[Detection], detection: Detection) -> float:
        """A heuristic to score a detection.

        The higher the score, the better the detection.
        """
        # Apply filters
        if self.category_filter is not None and detection.category.id != self.category_filter:
            return -sys.float_info.max
        # Compute score
        score = detection.confidence * self.confidence_weight
        if tracked is not None:
            # Category
            if tracked.category.id == detection.category.id:
                score += self.same_category_weight
            # Bounding box
            bb1 = tracked.bounding_box
            bb2 = detection.bounding_box
            iou = intersection_over_union(
                [bb1.x_min, bb1.y_max, bb1.x_max, bb1.y_min],
                [bb2.x_min, bb2.y_max, bb2.x_max, bb2.y_min]
            )
            score += iou * self.distance_weight
        # Apply minimum score filter
        if score < self.min_score:
            return -sys.float_info.max
        # Return score
        return score


# https://stackoverflow.com/a/64836196
def intersection_over_union(box1, box2):
    # Get coordinates of the intersection
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    # Get the area of intersection rectangle
    intersection = max(0, x2 - x1 + 1) * max(0, y2 - y1 + 1)

    # Get the area of both rectangles
    box1_area = (box1[2] - box1[0] + 1) * (box1[3] - box1[1] + 1)
    box2_area = (box2[2] - box2[0] + 1) * (box2[3] - box2[1] + 1)

    iou = intersection / float(box1_area + box2_area - intersection)

    return iou
