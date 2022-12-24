from typing import List

from autopilot.tracking.detector.api import Detector
from autopilot.tracking.detector.tflite import TFLiteEfficientDetLiteDetector, TFLiteYoloV5Detector


def build_registry() -> List[Detector]:
    return [
        TFLiteEfficientDetLiteDetector(tfhub_model_override=0),
        TFLiteEfficientDetLiteDetector(tfhub_model_override=1),
        TFLiteEfficientDetLiteDetector(tfhub_model_override=2),
        TFLiteEfficientDetLiteDetector(tfhub_model_override=3),
        TFLiteEfficientDetLiteDetector(tfhub_model_override=-1),  # 3x
        TFLiteEfficientDetLiteDetector(tfhub_model_override=4),
        TFLiteYoloV5Detector(),
        # TODO: Implement more detectors (https://tfhub.dev/s?deployment-format=lite&module-type=image-object-detection)
    ]
