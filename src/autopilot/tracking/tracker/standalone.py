from abc import ABC
from typing import Optional, List

import numpy as np

from autopilot.tracking.detector.api import Detection
from autopilot.tracking.tracker.api import Tracker


class StandaloneTracker(Tracker, ABC):
    """Tracker that relies on no detector.
    """

    @property
    def detector(self) -> Optional['Detector']:
        return None  # No detector is used


class DisabledTracker(StandaloneTracker):
    """Tracker that does not track anything. For testing UI only.
    """

    @property
    def name(self) -> str:
        return 'Disabled'

    def track(self, img: np.ndarray, min_confidence: float = 0.5, max_results: int = -1) -> (
            Optional[Detection], List[Detection]):
        return None, []
