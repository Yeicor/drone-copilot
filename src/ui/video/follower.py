from threading import Thread, Event, Lock
from typing import List, Optional

import numpy as np
from kivy import Logger
from kivy.clock import mainthread, Clock
from kivy.core.text import Label as CoreLabel
from kivy.graphics import Color, Rectangle, Line, PopState, PushState
from kivy.properties import ObjectProperty
from kivy.uix.widget import Widget

from autopilot.follow.detector.api import Detection
from autopilot.follow.detector.tflite import TFLiteEfficientDetDetector
from autopilot.follow.tracker.api import Tracker
from autopilot.follow.tracker.simple import SimpleTrackerAny
from ui.video.video import MyVideo


class Follower(Widget):
    """The UI of the follow API, letting a drone detect & track, locate in 3D space and follow objects.

    It uses a background thread to actually run the algorithms.

    It does not control the drone, it only provides the information needed to do so (on_track) and renders it."""

    video: MyVideo = ObjectProperty(None, allownone=True)
    """The background video element, used to get the video feed and feed it to the follower."""

    def __init__(self, tracker: Tracker, **kwargs):  # , depth_estimator: DepthEstimator
        super().__init__(**kwargs)
        self._tracker = tracker
        # self._depth_estimator = depth_estimator
        self._thread: Optional[Thread] = None
        self._new_img_event = Event()
        self._new_img_lock = Lock()
        self._img = None
        # Event listeners
        self.register_event_type('on_track')

    def feed(self, img: np.ndarray):
        """Feeds the follower with a new image.
        The image may be silently dropped if the follower is busy, in order to keep up to date with the video feed.

        :param img: the image to feed the follower with, in the format [height, width, channels(3)].
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

        # Draw an overlay on the video feed
        self.canvas.clear()
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
                y_max = 1 - bb.y_max  # Flip the y-axis
                y_min = 1 - bb.y_min
                ox, oy = sx + bb.x_min * sw, sy + y_max * sh,
                ow, oh = abs(bb.x_max - bb.x_min) * sw, abs(y_max - y_min) * sh
                Line(points=[ox, oy, ox + ow, oy, ox + ow, oy + oh, ox, oy + oh, ox, oy], width=4 if is_tracked else 2)

                # Render the label
                msg = f'{det.category.label} ({det.confidence * 100:.0f}%)'
                label = CoreLabel(text=msg, font_size=12)
                label.refresh()  # The label is usually not drawn until needed, so force it to draw.
                Rectangle(texture=label.texture, pos=(ox, oy + oh))

            PopState()

    def is_running(self) -> bool:
        """Returns whether the background thread is running."""
        return self._thread and self._thread.is_alive()

    def start(self) -> None:
        """Starts the background thread."""
        if self.is_running():
            self.stop()
        Logger.info('Follower: Starting...')
        # Create a new thread (as they can't be reused)
        self._thread = Thread(target=self.run, name='Follower')
        self._thread.start()

    def stop(self):
        """Stops the background thread and waits for it. The thread can be started again."""
        Logger.info('Follower: Stopping...')
        self._feed(None)
        self._thread.join()

    def run(self) -> None:
        """The background thread that runs the tracking algorithm."""
        processing_time_stats = (0, 0)  # sum, count
        processing_time_l_stats = (0, 0)  # sum, count

        while True:

            # Wait for a new image to be ready
            self._new_img_event.wait()
            self._new_img_event.clear()

            # Start measuring the time it takes to process the image
            start_time = Clock.time()

            # Detect stop condition and copy the new image
            with self._new_img_lock:  # Avoid races with the feed() method
                if self._img is None:
                    break
                img = self._img.copy()  # Avoid blocking or reading new data while processing

            # Run the tracking algorithm
            detection, all_detections = self._tracker.track(img)

            # Store the time it took to process the image internally
            processing_time = Clock.time() - start_time

            # Run any bound event listeners, including the default one which updates the UI
            # NOTE: This runs them on the background thread, blocking further processing until they are done.
            self.dispatch('on_track', detection, all_detections)

            # Store the time it took to process the image including the listeners
            total_time = Clock.time() - start_time

            # Compute processing time stats
            processing_time_stats = (processing_time_stats[0] + processing_time, processing_time_stats[1] + 1)
            processing_time_l_stats = (processing_time_l_stats[0] + total_time, processing_time_l_stats[1] + 1)

            # Log stats every N frames
            if processing_time_stats[1] % 1000 == 0:
                Logger.info(f'Follower: Avg frame time: {processing_time_stats[0] / processing_time_stats[1]:.2f}s, '
                            f'(with listeners: {processing_time_l_stats[0] / processing_time_l_stats[1]:.2f}s)')
                # Moving average, reset counters
                processing_time_stats = (0, 0)
                processing_time_l_stats = (0, 0)


class DefaultFollower(Follower):
    """The default implementation of the Follower class, which uses the default implementations of the tracking and depth
    estimation algorithms."""

    def __init__(self, **kwargs):
        super().__init__(SimpleTrackerAny(TFLiteEfficientDetDetector()), **kwargs)
