from autopilot.tracking.detector.tflite import TFLiteEfficientDetDetector, TFLiteYoloV5Detector

registry = [
    TFLiteEfficientDetDetector(),
    TFLiteYoloV5Detector(),
    # Add your detector here
]
