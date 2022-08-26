from typing import Callable, Optional

import cv2
import numpy as np
from kivy import Logger
from tellopy import Tello

from drone.api.camera import Camera
from util.video import StreamingVideoSource


class TelloCamera(Camera):  # TODO: Threadsafe implementation
    direction = np.array([1, 0, 0])
    resolutions_video = [
        (960, 720),
        (1280, 720),  # zoomed, but more pixels
    ]
    resolutions_photo = [(2592, 1936)]  # 5MP photos!

    def __init__(self, drone: 'TelloDrone', tello: Tello):
        self.drone = drone
        self.tello = tello
        # Photo
        self.listeners_photo: [Callable[[np.ndarray], None]] = []
        # Video
        self.listeners_video: [Callable[[np.ndarray], None]] = []
        self.decoder: Optional[StreamingVideoSource] = None
        # Configure tello listeners
        self.tello.subscribe(Tello.EVENT_FILE_RECEIVED, lambda **kwargs: self._on_photo_jpeg_bytes(kwargs['data']))
        self.tello.subscribe(Tello.EVENT_VIDEO_FRAME, lambda **kwargs: self._on_video_data_h264_bytes(kwargs['data']))
        self.tello.video_enabled = False

    def take_photo(self, resolution: (int, int), callback: Callable[[np.ndarray], None]):
        if len(self.listeners_photo) == 0:
            self.tello.take_picture()
        self.listeners_photo.append(callback)  # Register the new listener

    def _listen_stop_photo(self, callback: Callable[[np.ndarray], None]):
        self.listeners_photo.remove(callback)

    def _on_photo_jpeg_bytes(self, data: bytes):
        if len(self.listeners_photo) == 0:
            Logger.warn('Unexpected photo received with no listeners')
            return
        # Decode the JPEG image to a numpy array
        frame = cv2.imdecode(np.fromstring(data, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
        # Notify all listeners
        for listener in self.listeners_photo:
            listener(frame)

    def listen_video(self, resolution: (int, int), callback: Callable[[np.ndarray], None]) -> Callable[[], None]:
        # First listener sets up the shared video decoder
        if len(self.listeners_video) == 0:
            self.decoder = StreamingVideoSource()
            self.decoder.start()

            # Connect each frame decoded to notifying all listeners
            def on_video_frame(_ignore, frame: np.ndarray):
                for listener in self.listeners_video:
                    listener(frame)

            self.decoder.bind(on_video_frame=on_video_frame)

        self.listeners_video.append(callback)  # Register the new listener
        self.tello.start_video()  # Just sends another PPS/SPS pair to let clients start processing frames

        # Return the callable that removes this listener
        return lambda: self._listen_stop_video(callback)

    def _listen_stop_video(self, callback: Callable[[np.ndarray], None]):
        self.listeners_video.remove(callback)

        # The last listener cleans up the video decoder and starts ignoring any future video packets
        if len(self.listeners_video) == 0:
            del self.decoder
            self.tello.video_enabled = False

    def _on_video_data_h264_bytes(self, data: bytes):
        if len(self.listeners_video) == 0:
            Logger.warn('Unexpected frame data received with no listeners')
            return
        self.decoder.feed(data)

    def __del__(self):  # Clean up resources
        for listener in self.listeners_photo:
            self._listen_stop_photo(listener)
        for listener in self.listeners_video:
            self._listen_stop_video(listener)
