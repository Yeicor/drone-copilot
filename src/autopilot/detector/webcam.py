"""Test new object detectors directly using your webcam for development."""

import time

import numpy as np
from camera4kivy import Preview
from kivy.app import App
from kivy.clock import mainthread
from kivy.core.text import Label as CoreLabel
from kivy.graphics import Color, Line, Rectangle
from kivy.metrics import dp, sp

from autopilot.detector.tflite import TFLiteEfficientDetDetector


class WebcamDetectorApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.preview = WebcamDetector(TFLiteEfficientDetDetector())

    def build(self):
        return self.preview

    def on_start(self):
        self.preview.connect_camera(enable_analyze_pixels=True)

    def on_stop(self):
        self.preview.disconnect_camera()


class WebcamDetector(Preview):
    def __init__(self, detector, **kwargs):
        super().__init__(**kwargs)
        self.detector = detector
        self.classified = []
        # Get the required analyze resolution from the detector, a 2 element list.
        # as a consequence, scale will be a 2 element list
        self.auto_analyze_resolution = self.detector.input_size
        self.start_time = time.time()

    ####################################
    # Analyze a Frame - NOT on UI Thread
    ####################################

    def analyze_pixels_callback(self, pixels, image_size, image_pos,
                                image_scale, mirror):
        # Convert pixels to numpy rgb
        rgba = np.fromstring(pixels, np.uint8).reshape((image_size[1], image_size[0], 4))
        rgb = rgba[:, :, :3]
        # detect
        detections = self.detector.detect(rgb)
        now = time.time()
        fps = 0
        if now - self.start_time:
            fps = 1 / (now - self.start_time)
        self.start_time = now
        found = []
        for detection in detections:
            # Bounding box, pixels coordinates
            x = detection.bounding_box.left
            y = detection.bounding_box.top
            w = detection.bounding_box.right - x
            h = detection.bounding_box.bottom - y

            # Map tflite style coordinates to Kivy Preview coordinates
            y = max(image_size[1] - y - h, 0)
            if mirror:
                x = max(image_size[0] - x - w, 0)

            # Map Analysis Image coordinates to Preview coordinates
            # image_scale is a list because we used self.auto_analyze_resolution
            x = round(x * image_scale[0] + image_pos[0])
            y = round(y * image_scale[1] + image_pos[1])
            w = round(w * image_scale[0])
            h = round(h * image_scale[1])

            # Category text for canvas
            category = detection.category
            class_name = category.label
            probability = round(detection.confidence, 2)
            result_text = class_name + ' [{:.2f}]'.format(probability)
            label = CoreLabel(font_size=sp(20))
            label.text = result_text
            label.refresh()

            # Thread safe result
            found.append({'x': x, 'y': y, 'w': w, 'h': h, 't': label.texture})
        self.make_thread_safe(list(found))  # A COPY of the list

    @mainthread
    def make_thread_safe(self, found):
        self.classified = found

    ################################
    # Canvas Update  - on UI Thread
    ################################

    def canvas_instructions_callback(self, texture, tex_size, tex_pos):
        # Add the analysis annotations
        Color(0, 1, 0, 1)
        for r in self.classified:
            # Draw box
            Line(rectangle=(r['x'], r['y'], r['w'], r['h']), width=dp(1.5))
            # Draw text
            Rectangle(size=r['t'].size,
                      pos=[r['x'] + dp(10), r['y'] + dp(10)],
                      texture=r['t'])
