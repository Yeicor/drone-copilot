from abc import abstractmethod, ABC
from typing import Dict

from drone.api.linearangular import LinearAngular


class Status(ABC):
    """Read-only status of the drone.
    See :class:`drone.Drone` for unit and axes details.
    Properties of this class may be lazily computed.
    """

    @property
    @abstractmethod
    def battery(self) -> float:
        """The battery level of the drone as a float between 0 and 1.
        This should be regularly checked and a safety protocol implemented if it is low.
        """
        return 1.0

    @property
    @abstractmethod
    def signal_strength(self) -> float:
        """The signal strength of the connection to the drone as a float between 0 and 1.
        This should be regularly checked and a safety protocol implemented if it is low.
        """
        return 1.0

    @property
    @abstractmethod
    def temperatures(self) -> Dict[str, float]:
        """The temperatures of the different components of the drone, as key-values indexed by name.
        This should be regularly checked and a safety protocol implemented if any value is too high.
        """
        return {}

    @property
    @abstractmethod
    def flying(self) -> bool:
        """Whether the drone is currently flying.
        """
        return False

    @property
    @abstractmethod
    def height(self) -> float:
        """The height of the drone above the ground.
        This may be different from the -position.z value as the ground level may change, unlike the takeoff position.
        This is only available if a Time-Of-Flight sensor is present. Otherwise, it will be set to a negative number.
        """
        return -1.0

    @property
    @abstractmethod
    def position_attitude(self) -> LinearAngular:
        """The position and attitude of the drone on 3D space, relative to the pre-takeoff position and rotation.

        Only high-end drones may have a position, and it may be very inaccurate.
        If only a barometer is present, only the Z value will be set to the -altitude.

        The attitude consists of yaw, pitch and roll.

        Any unsupported value will be set to `0`.
        """
        return LinearAngular()

    @property
    @abstractmethod
    def velocity(self) -> LinearAngular:
        """The speed of the drone. See :class:`LinearAngular` for more details.
        """
        return LinearAngular()

    @property
    @abstractmethod
    def acceleration(self) -> LinearAngular:
        """The acceleration experienced by the drone, including gravity.
        """
        return LinearAngular()
