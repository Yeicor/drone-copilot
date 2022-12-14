from threading import Thread, Event, Lock
from typing import List, Optional

import numpy as np
from kivy import Logger
from kivy.app import App
from kivy.clock import mainthread, Clock
from kivy.core.text import Label as CoreLabel
from kivy.graphics import Color, Rectangle, Line, PopState, PushState
from kivy.metrics import pt
from kivy.properties import ObjectProperty
from kivy.uix.widget import Widget

from app.settings.manager import SettingsManager
from app.settings.settings import SettingMetaOptions, SettingMetaNumeric
from app.video.video import MyVideo
from autopilot.tracking.detector.api import Detection
from autopilot.tracking.detector.registry import build_registry as detector_registry
from autopilot.tracking.tracker.api import Tracker as TrackerAPI
from autopilot.tracking.tracker.registry import build_registry as tracker_registry


class Tracker(Widget):
    """The UI of the tracker API, letting a drone detect & track, locate in 3D space and follow objects.

    It uses a background thread to actually run the algorithms.

    It does not control the drone, it only provides the information needed to do so (on_track) and renders it."""

    video: MyVideo = ObjectProperty(None, allownone=True)
    """The background video element, used to get the video position and dimensions to apply the overlay."""
    _section_name = 'Tracker'
    """The section name for settings"""

    def __init__(self, tracker: TrackerAPI = None, **kwargs):  # , depth_estimator: DepthEstimator
        super().__init__(**kwargs)
        # self._depth_estimator = depth_estimator
        self._thread: Optional[Thread] = None
        self._thread_lock = Lock()
        self._new_img_event = Event()
        self._new_img_lock = Lock()
        self._img = None
        self._load_progress: Optional[float] = None
        # Events
        self.register_event_type('on_track')
        # Settings
        self.detector_registry = detector_registry()
        self.tracker_registry = tracker_registry()
        self._tracker = tracker or self.tracker_registry[0]
        if self._tracker.detector:
            self._tracker.detector.selected(True)
        self.rebuild_settings(True)

    def rebuild_settings(self, first_time: bool = False):
        settings = SettingsManager.instance()

        # Tracker settings
        tracker_names = [tr.name for tr in self.tracker_registry]
        tracker_selector = SettingMetaOptions.create(
            'Tracker', 'The tracker implementation', tracker_names, tracker_names[0])
        if first_time:
            tracker_selector.bind(self._section_name, self._on_change_tracker_tracker, True)
        current_settings = [tracker_selector]

        # Detector settings (if any)
        if self.tracker is not None and self.tracker.detector is not None:
            detector_names = [det.name for det in self.detector_registry]
            detector_selector = SettingMetaOptions.create(
                'Detector', 'The object detector model to use', detector_names, detector_names[0])
            current_settings += [detector_selector]
            if first_time:
                detector_selector.bind(self._section_name, self._on_change_tracker_detector, True)

        # Common detector/tracker settings (read from the tracker thread on each frame)
        current_settings += [
            SettingMetaNumeric.create('Confidence', 'The minimum confidence to detect/track', 0.5),
            SettingMetaNumeric.create('Max results', 'The maximum number of objects to detect', -1),
        ]

        # Update the settings and force refresh their UI
        settings[self._section_name] = current_settings

    def _on_change_tracker_tracker(self, tracker: str):
        Logger.info('Tracker: on_change_tracker_tracker: %s' % tracker)
        previous_detector = self.tracker.detector
        self.tracker = [tr for tr in self.tracker_registry if tr.name == tracker][0]
        if previous_detector is not None and self.tracker.detector is None:
            previous_detector.selected(False)
        elif previous_detector is None and self.tracker.detector is not None:
            self.tracker.detector.selected(True)
        self.rebuild_settings()

    def _on_change_tracker_detector(self, tracker: str):
        Logger.info('Tracker: on_change_tracker_detector_settings: %s' % tracker)
        new_detector = [det for det in self.detector_registry if det.name == tracker][0]
        if self.tracker.detector:  # If the current tracker supports a detector
            self.tracker.detector.selected(False)
            self.tracker.detector = new_detector
            self.tracker.detector.selected(True)

    @property
    def tracker(self):
        return self._tracker

    @tracker.setter
    def tracker(self, tracker: TrackerAPI):
        """Sets the tracker implementation."""
        is_running = self.is_running()
        if is_running:
            self.stop()
        self._tracker = tracker
        if is_running:
            self.start()

    def feed(self, img: np.ndarray):
        """Feeds the tracker with a new image.
        The image may be silently dropped if the tracker is busy, in order to keep up to date with the video feed.

        :param img: the image to feed the tracker with, in the format [height, width, channels(3)].
            Note that the implementation will resize and crop the image if required.
            It should also adapt the data type, assuming floats to be in the range [0, 1].
        """
        self._feed(img)

    def _feed(self, img: Optional[np.ndarray]):
        with self._new_img_lock:
            self._img = img
        self._new_img_event.set()

    def on_touch_down(self, touch):
        return super().on_touch_down(touch)  # Passthrough the event to child widgets
        # TODO: Receive wanted object to track from UI (click on any rectangle)

    def on_track(self, detection: Optional[Detection], all_detections: List[Detection]):
        """Event listener for when a new detection is made."""
        self._update_ui(detection, all_detections)

    @mainthread
    def _update_ui(self, detection: Optional[Detection], all_detections: List[Detection]):
        """Adds an overlay to the video feed to show the tracked object.

        Called when a new frame has been processed and the UI should be updated.

        :param detection: the tracked object or None if no object was detected.
        :param all_detections: the list of all detections.
        """

        # Clear the canvas
        self.canvas.ask_update()
        self.canvas.clear()

        # If we are loading the model, show a progress bar
        if self._load_progress is not None:
            msg = f'Loading tracker... {self._load_progress * 100:.0f}%'
            label = CoreLabel(text=msg, font_size=pt(16))
            label.refresh()  # The label is usually not drawn until needed, so force it to draw.

            app = App.get_running_app()
            left_bar = app.ui_el('left_bar')
            top_bar = app.ui_el('top_bar')
            label_pos = (left_bar.x + left_bar.width + pt(4), top_bar.y - top_bar.height - pt(16) + pt(4))

            with self.canvas:
                Color(1, 0, 0, 1)
                Rectangle(texture=label.texture, pos=label_pos, size=label.texture.size)
            return

        # Draw an overlay on the video feed
        sx, sy, sw, sh = self.video.get_screen_bounds()
        with self.canvas:
            PushState()

            for det in all_detections:
                is_tracked = det == detection
                if is_tracked:
                    Color(1, 1, 0, 1)
                else:
                    Color(0, 1, 0, 1)

                # Render the bounding box
                bb = det.bounding_box
                # Flip the y coordinates
                bb.y_min = 1 - bb.y_min
                bb.y_max = 1 - bb.y_max
                # Convert bounding box to screen pixel coordinates
                bb.x_min = bb.x_min * sw + sx
                bb.x_max = bb.x_max * sw + sx
                bb.y_min = bb.y_min * sh + sy
                bb.y_max = bb.y_max * sh + sy
                # Draw the bounding box
                Line(points=[bb.x_min, bb.y_min, bb.x_max, bb.y_min, bb.x_max, bb.y_max, bb.x_min, bb.y_max,
                             bb.x_min, bb.y_min], width=pt(2 if is_tracked else 1))

                # Render the label
                msg = f'{det.category.label} ({det.confidence * 100:.0f}%)'
                label = CoreLabel(text=msg, font_size=pt(16))
                label.refresh()  # The label is usually not drawn until needed, so force it to draw.
                Rectangle(texture=label.texture, pos=(bb.x_min + pt(4), bb.y_min - pt(16 + 4)), size=label.texture.size)

            PopState()

    def is_running(self, __lock: bool = True) -> bool:
        """Returns whether the background thread is running."""
        if __lock:
            with self._thread_lock:
                return self._thread is not None
        else:
            return self._thread is not None

    def start(self) -> None:
        with self._thread_lock:
            """Starts the background thread."""
            if self.is_running(False):
                self.stop()
            # Start the thread
            self._thread = Thread(target=self._bg_thread)
            self._thread.start()

    def stop(self) -> None:
        """Stops the background thread and waits for it. The thread can be started again."""
        with self._thread_lock:
            if not self.is_running(False):
                return
            self._feed(None)
            self._thread.join()
            self._thread = None
            Clock.schedule_once(lambda dt: self.canvas.clear())  # Clear the canvas after the thread has stopped

    def _bg_thread(self) -> None:
        """The background thread that runs the tracking algorithm."""
        Logger.info('Tracker: _bg_thread() started')

        if not self._tracker.is_loaded():
            def _on_load_progress(progress: Optional[float]):
                self._load_progress = progress
                self._update_ui(None, [])

            Logger.info('Tracker: Loading...')
            _on_load_progress(0)
            self._tracker.load(_on_load_progress)
            _on_load_progress(None)  # finished loading

        time_stats = (0, 0)  # sum, count

        while True:
            # Wait for a new image to be ready
            self._new_img_event.wait()
            self._new_img_event.clear()
            start_time = Clock.time()

            # Detect stop condition and copy the new image
            with self._new_img_lock:  # Avoid races with the feed() method
                if self._img is None:
                    break
                img = self._img.copy()  # Avoid blocking or reading new data while processing

            # Run the tracking algorithm
            confidence = float(App.get_running_app().config.get(self._section_name, 'confidence'))
            max_results = int(App.get_running_app().config.get(self._section_name, 'max_results'))
            detection, all_detections = self._tracker.track(img, confidence, max_results)

            # Run any bound event listeners, including the default one which updates the UI
            # NOTE: This runs them on the background thread, blocking further processing until they are done.
            self.dispatch('on_track', detection, all_detections)

            # Compute processing time stats
            processing_time = Clock.time() - start_time
            time_stats = (time_stats[0] + processing_time, time_stats[1] + 1)

            # Log stats every N frames
            if time_stats[1] % 100 == 0:
                frame_time = time_stats[0] / time_stats[1]
                Logger.info(f'Tracker: Avg frame time: {frame_time:.3f}s ({1.0 / frame_time:.1f} max FPS)')
                # "Moving average", reset counters
                time_stats = (0, 0)

        if self._tracker.is_loaded():
            Logger.info('Tracker: Unloading...')
            self._tracker.unload()
        Logger.info('Tracker: _bg_thread() stopped')
