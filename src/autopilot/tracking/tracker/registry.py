from typing import List

from autopilot.tracking.detector.tflite import TFLiteEfficientDetLiteDetector
from autopilot.tracking.tracker.api import Tracker
from autopilot.tracking.tracker.detectorbased import DetectorBasedTrackerAny
from autopilot.tracking.tracker.standalone import DisabledTracker


def build_registry() -> List[Tracker]:
    return [
        DisabledTracker(),
        DetectorBasedTrackerAny(TFLiteEfficientDetLiteDetector(tfhub_model_override=0)),
    ]
