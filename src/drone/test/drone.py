from __future__ import annotations

import threading
from time import sleep
from typing import Callable, Optional, List

from drone.api.camera import Camera
from drone.api.drone import Drone
from drone.api.linearangular import LinearAngular
from drone.api.status import Status


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

    def __del__(self):
        pass

    def takeoff(self, callback: Callable[[bool], None]):
        pass

    def land(self, callback: Callable[[bool], None]):
        pass

    @property
    def target_speed(self) -> LinearAngular:
        return super(TestDrone, self).target_speed

    @target_speed.setter
    def target_speed(self, speed: LinearAngular):
        pass

    @property
    def status(self) -> Status:
        return super(TestDrone, self).status

    def listen_status(self, callback: Callable[[Status], None]) -> Callable[[], None]:
        return super(TestDrone, self).listen_status(callback)

    def cameras(self) -> List[Camera]:
        return []
