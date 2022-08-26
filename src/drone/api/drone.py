from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable, List, Optional, Type

from drone.api.camera import Camera
from drone.api.linearangular import LinearAngular
from drone.api.status import Status


class Drone(ABC):
    """The Abstract Base Class that all drones must inherit from.

    This specifies the core functionality that all drones must have, like querying the battery or setting its 3D speed.

    Unless otherwise specified, all methods use SI units (meters, seconds, radians, etc.).

    Following the convention the Coordinate Systems for Modeling, X+ is forward, Y+ is right and Z+ is down.
    Furthermore, yaw is the rotation around the Z axis (positive is moving the front-side right),
    pitch is the rotation around the Y axis (positive is moving the front-side up), and
    roll is the rotation around the X axis (positive is moving the right-side up).
    """

    @staticmethod
    def connect(url: str, timeout_secs: float, extra: any, callback: Callable[[Optional[Type[Drone]]], None]):
        """Connects to the drone, returning "immediately". Remember to delete this object for disconnection!

        :param url: the URL of the drone (if applicable).
        :param timeout_secs: the maximum amount of time to wait for the drone to connect.
        :param extra: any drone-specific data required for setup (check docs).
        :param callback: a callback function that is called when the drone is connected (or the connection fails).
        """
        pass

    @staticmethod
    def get_name() -> str:
        """Returns the display name of the drone.
        It may be just the model name, or something else.
        """
        return "UnnamedDrone"

    @property
    @abstractmethod
    def status(self) -> Status:
        """Accesses the last status report of the drone.
        """
        return Status()

    @abstractmethod
    def status_listen(self, callback: Callable[[Status], None]) -> Callable[[], None]:
        """Receives status updates executing callback as soon as they are provided by the drone.
        Multiple calls to status_listen should share the data, reducing the load of the drone manager.
        The callback may be run on the status thread, so long-running operations should be moved to another thread.
        """
        return lambda: None

    @abstractmethod
    def takeoff(self, callback: Callable[[bool], None]):
        """Sends the command to take off the drone and returns "immediately".
        It will run the callback when/if the takeoff is complete, with a boolean indicating success.
        """
        pass

    @abstractmethod
    def land(self, callback: Callable[[bool], None]):
        """Sends the command to land the drone and returns "immediately".
        It will run the callback when/if the landing is complete, with a boolean indicating success.
        """
        pass

    @abstractmethod
    def set_speed(self, speed: LinearAngular):
        """Sets the speed of the drone in 3D space and returns "immediately".
        The drone must be flying for this to have any effect.
        The drone may take some time to reach the new speed, but will accept more speed commands meanwhile.
        If the drone cannot go that fast, it will go as fast as possible.
        """
        pass

    @abstractmethod
    def cameras(self) -> List[Camera]:
        """Returns a list of Camera objects for each camera on the drone.
        These contain metadata and may be used to connect to the live feed.
        """
        return []
