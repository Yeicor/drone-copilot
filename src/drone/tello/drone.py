from __future__ import annotations

import math
import threading
import weakref
from time import sleep
from typing import Callable, Optional, List

from kivy.clock import Clock
from tellopy import Tello
from tellopy._internal.logger import LOG_INFO
from tellopy._internal.protocol import FlightData, LogData

from drone.api.camera import Camera
from drone.api.drone import Drone
from drone.api.linearangular import LinearAngular
from drone.api.status import Status
from drone.tello.camera import TelloCamera
from drone.tello.status import TelloStatus


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
        self._tello.set_exposure(0)  # Automatic
        self._tello.set_video_encoder_rate(0)  # Automatic
        # self._tello.set_alt_limit(30)  # 30m?
        # self._tello.set_att_limit(15)  # 15deg?
        self._tello.fast_mode = False
        # Listen for status updates and other events
        self._tello.subscribe(Tello.EVENT_FLIGHT_DATA, lambda **kwargs: self._on_flight_data(kwargs['data']))
        self._tello.subscribe(Tello.EVENT_LOG_DATA, lambda **kwargs: self._on_log_data(kwargs['data']))
        # Predefined set of cameras
        self._cameras = [TelloCamera(self, self._tello)]
        # Status data
        self.last_flight_data: Optional[FlightData] = None
        self.last_log_data: Optional[LogData] = None
        self.status_listeners: List[Callable[[Status], None]] = []
        # Finalizer (in case the user forgets to call del)
        weakref.finalize(self, self.__del__)

    def __del__(self):
        del self._cameras
        self._tello.quit()

    def takeoff(self, callback: Callable[[bool], None]):
        # TODO: Check status
        self._tello.takeoff()

        # HACK: Wait for takeoff to complete
        # TODO: Check status to see if it's actually taken off and run the callback just as it frees controls
        Clock.schedule_once(lambda dt: callback(True), 2.5)

    def land(self, callback: Callable[[bool], None]):
        # TODO: Check status
        self._tello.land()

        # HACK: Wait for land to complete
        # TODO: Check status to see if it's actually taken off and run the callback just as it frees controls
        Clock.schedule_once(lambda dt: callback(True), 5.0)

    @staticmethod
    def _speed_linear_to_stick(speed: float) -> float:
        """Converts a speed in m/s to a stick value [-1.0, 1.0].
        """
        _speed_sigmoid = 1 / (1 + math.exp(-speed))
        return _speed_sigmoid * 2 - 1  # TODO: Customize the curve for closer to reality speeds

    @staticmethod
    def _stick_to_speed_linear(stick: float) -> float:
        """Converts a stick value [-1.0, 1.0] to a speed in m/s.
        """
        stick_sigmoid = (stick + 1) / 2
        return math.log(stick_sigmoid / (1 - stick_sigmoid))

    _speed_angular_to_stick = _speed_linear_to_stick  # TODO: Customize the curve for closer to reality speeds
    _stick_to_speed_angular = _stick_to_speed_linear

    @property
    def target_speed(self) -> LinearAngular:
        res = LinearAngular()
        # Convert from joystick format
        res.linear_x = self._stick_to_speed_linear(self._tello.right_y)
        res.linear_y = self._stick_to_speed_linear(self._tello.right_y)
        res.linear_z = self._stick_to_speed_linear(self._tello.right_y)
        res.yaw = self._stick_to_speed_angular(self._tello.right_y)
        return res

    @target_speed.setter
    def target_speed(self, speed: LinearAngular):
        # Convert data to joystick format
        self._tello.left_x = self._speed_angular_to_stick(speed.yaw)  # TODO: Different function for angles
        self._tello.left_y = self._speed_linear_to_stick(-speed.linear_z)
        self._tello.right_x = self._speed_linear_to_stick(speed.linear_y)
        self._tello.right_y = self._speed_linear_to_stick(speed.linear_x)
        # Data will be sent automatically on the next tick (internal Tello thread)

    def _on_flight_data(self, data: FlightData):
        # Logger.info(f"Tello _on_flight_data: {data}")
        self.last_flight_data = data
        for listener in self.status_listeners:
            listener(self.status)

    def _on_log_data(self, data: LogData):
        # Logger.info(f"Tello _on_log_data: {data}")
        self.last_log_data = data
        for listener in self.status_listeners:
            listener(self.status)

    @property
    def status(self) -> Status:
        return TelloStatus(self.last_flight_data, self.last_log_data)  # TODO: deep copy as this is internally aliased?

    def listen_status(self, callback: Callable[[Status], None]) -> Callable[[], None]:
        self.status_listeners.append(callback)
        return lambda: self.status_listeners.remove(callback)

    def cameras(self) -> List[Camera]:
        return self._cameras
