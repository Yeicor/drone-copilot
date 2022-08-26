from __future__ import annotations

import math
import threading
import weakref
from time import sleep
from typing import Callable, Optional, List

from kivy import Logger
from tellopy import Tello
from tellopy._internal.logger import LOG_INFO
from tellopy._internal.protocol import FlightData, LogData

from drone.api.camera import Camera
from drone.api.drone import Drone
from drone.api.linearangular import LinearAngular
from drone.api.status import Status
from drone.tello.camera import TelloCamera


class TelloDrone(Drone):

    @staticmethod
    def connect(url: str, timeout_secs: float, extra: any, callback: Callable[[Optional[TelloDrone]], None]):
        tello = Tello()
        callback_done = []

        def callback_wrapper(_tello: Tello, success: bool):
            if len(callback_done) == 0:  # HACK: aliasing of the outer variable while setting it
                callback_done.append(True)
                if success:
                    drone = TelloDrone(_tello)
                    callback(drone)
                else:  # Timeout connecting to the drone
                    _tello.quit()  # Clean up
                    callback(None)

        # HACK: Use a new thread for the timeout as using the Clock would break if exiting the application
        threading.Thread(target=lambda: sleep(timeout_secs) or callback_wrapper(tello, False)).start()
        tello.subscribe(Tello.EVENT_CONNECTED, lambda **kwargs: callback_wrapper(tello, True))
        tello.connect()

    @staticmethod
    def get_name() -> str:
        return "Tello (native)"

    def __init__(self, tello: Tello):
        super().__init__()
        self._tello = tello
        # Set some default configuration for the drone
        # NOTE that any packet may get lost due to using UDP
        self._tello.set_loglevel(LOG_INFO)
        self._tello.set_exposure(0)
        self._tello.set_video_encoder_rate(4)  # This forces the maximum quality (set to 0 for automatic)
        self._tello.set_alt_limit(30)  # 30m
        self._tello.set_att_limit(15)  # 15deg
        # Listen for status updates and other events
        self._tello.subscribe(Tello.EVENT_FLIGHT_DATA, lambda **kwargs: self._on_flight_data(kwargs['data']))
        self._tello.subscribe(Tello.EVENT_LOG_DATA, lambda **kwargs: self._on_log_data(kwargs['data']))
        # Predefined set of cameras
        self._cameras = [TelloCamera(self, self._tello)]
        # Finalizer (in case the user forgets to call del)
        weakref.finalize(self, self.__del__)

    def __del__(self):
        self._tello.quit()

    def takeoff(self, callback: Callable[[bool], None]):
        # TODO: Check status
        self._tello.takeoff()
        callback(True)

    def land(self, callback: Callable[[bool], None]):
        # TODO: Check status
        self._tello.land()
        callback(True)

    def set_speed(self, speed: LinearAngular):
        def speed_to_stick(_speed: float) -> float:
            """Converts a speed in m/s to a stick value [-1.0, 1.0].
            """
            _speed_sigmoid = 1 / (1 + math.exp(-_speed))
            return _speed_sigmoid * 2 - 1  # TODO: Customize the curve for closer to reality speeds

        # Convert data to joystick format
        self._tello.left_x = speed_to_stick(speed.yaw)  # TODO: Different function for angles
        self._tello.left_y = speed_to_stick(-speed.linear_z)
        self._tello.right_x = speed_to_stick(speed.linear_y)
        self._tello.right_y = speed_to_stick(speed.linear_x)
        # Data will be sent automatically on the next tick (internal Tello thread)

    def _on_flight_data(self, data: FlightData):
        Logger.info(f"Tello _on_flight_data: {data}")

    def _on_log_data(self, data: LogData):
        Logger.info(f"Tello _on_log_data: {data}")

    @property
    def status(self) -> Status:
        pass

    def status_listen(self, callback: Callable[[Status], None]) -> Callable[[], None]:
        pass

    def cameras(self) -> List[Camera]:
        return self._cameras
