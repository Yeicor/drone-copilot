from threading import Thread, Event, Lock
from typing import List, Optional

import numpy as np
from kivy import Logger
from kivy.app import App
from kivy.clock import mainthread, Clock
from kivy.core.text import Label as CoreLabel
from kivy.graphics import Color, Rectangle, Line, PopState, PushState
from kivy.properties import ObjectProperty
from kivy.uix.widget import Widget

from autopilot.tracking.detector.api import Detection
from autopilot.tracking.detector.tflite import TFLiteEfficientDetDetector
from autopilot.tracking.tracker.api import Tracker as TrackerAPI
from autopilot.tracking.tracker.simple import SimpleTrackerAny
from ui.video.video import MyVideo


class Tracker(Widget):
    """The UI of the tracker API, letting a drone detect & track, locate in 3D space and follow objects.

    It uses a background thread to actually run the algorithms.

    It does not control the drone, it only provides the information needed to do so (on_track) and renders it."""

    video: MyVideo = ObjectProperty(None, allownone=True)
    """The background video element, used to get the video position and dimensions to apply the overlay."""

    def __init__(self, tracker: TrackerAPI, **kwargs):  # , depth_estimator: DepthEstimator
        super().__init__(**kwargs)
        self._tracker = tracker
        # self._depth_estimator = depth_estimator
        self._thread: Optional[Thread] = None
        self._new_img_event = Event()
        self._new_img_lock = Lock()
        self._img = None
        self._load_progress: Optional[float] = -1
        # Event listeners
        self.register_event_type('on_track')

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
            Logger.info(f'Tracker: {msg}')
            label = CoreLabel(text=msg, font_size=16)
            label.refresh()  # The label is usually not drawn until needed, so force it to draw.

            app = App.get_running_app()
            left_bar = app.ui_el('left_bar')
            top_bar = app.ui_el('top_bar')
            label_pos = (left_bar.x + left_bar.width + 10, top_bar.y - top_bar.height - 10)

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
                             bb.x_min, bb.y_min], width=4 if is_tracked else 2)

                # Render the label
                msg = f'{det.category.label} ({det.confidence * 100:.0f}%)'
                label = CoreLabel(text=msg, font_size=12)
                label.refresh()  # The label is usually not drawn until needed, so force it to draw.
                Rectangle(texture=label.texture, pos=(bb.x_min, bb.y_min), size=label.texture.size)

            PopState()

    def is_running(self) -> bool:
        """Returns whether the background thread is running."""
        return self._thread and self._thread.is_alive()

    def start(self) -> None:
        """Starts the background thread."""
        if self.is_running():
            self.stop()
        Logger.info('Tracker: Loading...')
        if self._load_progress == -1:
            self._load_progress = 0
            self._tracker.load(self._on_load_progress)
        else:
            self._on_load_progress(1)  # Start the thread immediately if the model is already loaded

    def _on_load_progress(self, progress: float):
        if progress < 1:
            self._load_progress = progress
            self._update_ui(None, [])
        else:  # Done loading
            self._load_progress = None
            Logger.info('Tracker: Loaded. Starting...')
            # Create a new thread (as they can't be reused)
            self._thread = Thread(target=self.run, name='Tracker')
            self._thread.start()

    def stop(self):
        """Stops the background thread and waits for it. The thread can be started again."""
        Logger.info('Tracker: Stopping...')
        self._feed(None)
        self._thread.join()
        Clock.schedule_once(lambda dt: self.canvas.clear())  # Clear the canvas after the thread has stopped

    def run(self) -> None:
        """The background thread that runs the tracking algorithm."""
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
            detection, all_detections = self._tracker.track(img)

            # Run any bound event listeners, including the default one which updates the UI
            # NOTE: This runs them on the background thread, blocking further processing until they are done.
            self.dispatch('on_track', detection, all_detections)

            # Compute processing time stats
            processing_time = Clock.time() - start_time
            time_stats = (time_stats[0] + processing_time, time_stats[1] + 1)

            # Log stats every N frames
            if time_stats[1] % 1000 == 0:
                frame_time = time_stats[0] / time_stats[1]
                Logger.info(f'Tracker: Avg frame time: {frame_time:.2f}s ({1.0 / frame_time:.1f} max FPS)')
                # "Moving average", reset counters
                time_stats = (0, 0)


class DefaultTracker(Tracker):
    """An implementation of the Tracker class which selects default algorithms and configurations."""

    def __init__(self, **kwargs):
        super().__init__(SimpleTrackerAny(TFLiteEfficientDetDetector()), **kwargs)
