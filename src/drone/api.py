import typing
from dataclasses import dataclass


@dataclass
class CameraMetadata:
    # noinspection PyUnresolvedReferences
    """
    Stores metadata about a camera.

    Attributes:
        direction: The (approximate) direction of the camera in 3D space (unit vector).
        resolution: The resolution of the camera. (0, 0) if unknown.
    """

    direction: (float, float, float)
    resolution: (int, int) = (0, 0)
    # TODO: possibility to move the camera


class Drone:
    """
    The base class that all drones must inherit from.

    This specifies the core functionality that all drones must have, like querying the battery or setting its 3D speed.

    Unless otherwise specified, all methods use SI units (meters, seconds, radians, etc.).

    Following the convention the Coordinate Systems for Modeling, X+ is forward, Y+ is right and Z+ is down.
    """

    def __init__(self):
        pass

    # noinspection PyMethodMayBeStatic
    def get_name(self) -> str:
        """
        Returns the display name of the drone.
        It may be just the model name, or something else.
        """
        return "UnnamedDrone"

    def get_battery(self) -> float:
        """
        Returns the battery level of the drone as a float between 0 and 1.
        This should be regularly checked and a safety protocol implemented if the battery level is low.
        """
        pass

    def takeoff(self, callback: typing.Callable[[bool], None]):
        """
        Sends the command to take off the drone and returns "immediately".
        It will run the callback when/if the takeoff is complete, with a boolean indicating success.
        """
        pass

    def land(self, callback: typing.Callable[[bool], None]):
        """
        Sends the command to land the drone and returns "immediately".
        It will run the callback when/if the landing is complete, with a boolean indicating success.
        """
        pass

    def set_speed(self, x: float, y: float, z: float, yaw: float):
        """
        Sets the speed of the drone in 3D space. x, y, z and yaw are floats in SI units.
        The drone must be flying for this to have any effect.
        The drone may take some time to reach the new speed, but will accept more speed commands meanwhile.
        If the drone cannot go that fast, it will go as fast as possible.
        """
        pass

    # noinspection PyMethodMayBeStatic
    def cameras(self) -> typing.List[CameraMetadata]:
        """Returns a list of CameraMetadata objects for each camera on the drone."""
        return []

    # noinspection PyMethodMayBeStatic
    def camera_connect(self, n: int):
        """Connects to the given camera and starts returning image data."""
        return []
