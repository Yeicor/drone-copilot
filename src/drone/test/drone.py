from __future__ import annotations

import threading
from time import sleep
from typing import Callable, Optional, List

import numpy as np
from kivy import Logger
from kivy.clock import Clock

from drone.api.camera import Camera
from drone.api.drone import Drone
from drone.api.linearangular import LinearAngular
from drone.api.status import Status
from drone.test.camera import TestCamera
from drone.test.status import TestStatus


class TestDrone(Drone):
    """The driver implementation for controlling a test drone in a virtual environment. Useful for development.
    """

    @staticmethod
    def connect(url: str, timeout_secs: float, extra: any, callback: Callable[[Optional[TestDrone]], None]):
        # Start a new thread to "connect" to the drone (as it may take a little while for other drones)
        threading.Thread(target=lambda: sleep(0.1) or callback(TestDrone())).start()

    @staticmethod
    def get_name() -> str:
        return "TestVirtualDrone"

    def __init__(self):
        super().__init__()
        self._camera = TestCamera()
        self._camera.setup()
        self._status = TestStatus(camera=self._camera)
        self._status.start_updates()
        self._status_listeners: List[Callable[[Status], None]] = [lambda s: self._camera.on_status_update(s)]
        self._status.bind(on_update=lambda _: [listener(self._status) for listener in self._status_listeners])

    def __del__(self):
        pass

    def takeoff(self, callback: Callable[[bool], None]):
        # Slowly rise, wait 2 seconds, stop and run the callback
        self.target_speed = LinearAngular(linear_local=np.array([0, 0, -0.5]))
        Logger.info("TestDrone: Taking off")

        def callback_wrapper(_dt: float):
            self.target_speed = LinearAngular(linear_local=np.array([0, 0, 0]))
            Logger.info("TestDrone: Takeoff complete")
            callback(True)

        Clock.schedule_once(callback_wrapper, 2.0)

    def land(self, callback: Callable[[bool], None]):
        # Slowly fall down until we reach the ground, stop and run the callback
        ev = []

        def protocol(_dt: float):
            if self._status.flying:  # Force the drone to land by always setting the speed
                self.target_speed = LinearAngular(linear_local=np.array([0, 0, 0.5]), angular=np.array([0, 0, 0]))
            else:
                self.target_speed = LinearAngular(linear_local=np.array([0, 0, 0]))
                callback(True)
                ev[0].cancel()

        if self._status.height > 0.0:
            Logger.info("TestDrone: Landing")
            ev.append(Clock.schedule_interval(protocol, 0.1))
        else:
            Logger.warn("TestDrone: Cannot land, you have no ground below!")
            callback(False)

    @property
    def target_speed(self) -> LinearAngular:
        return self._status.velocity

    @target_speed.setter
    def target_speed(self, speed: LinearAngular):
        self._status._velocity = speed

    @property
    def status(self) -> Status:
        return self._status

    def listen_status(self, callback: Callable[[Status], None]) -> Callable[[], None]:
        self._status_listeners.append(callback)
        return lambda: self._status_listeners.remove(callback)

    def cameras(self) -> List[Camera]:
        return [self._camera]
