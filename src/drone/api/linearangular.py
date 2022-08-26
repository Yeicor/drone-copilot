from dataclasses import dataclass

import numpy as np


@dataclass
class LinearAngular:
    """Holds/sets the position+angle/velocity/acceleration of a drone.
    See :class:`drone.api.drone.Drone` for unit and axes details.
    """

    linear: np.ndarray = np.zeros(3)
    """The linear ***** of the drone.
    """

    angular: np.ndarray = np.zeros(3)
    """The angular ***** of the drone (yaw, pitch and roll). 
    The pitch and roll values may be ignored if unsupported.
    """

    # Utilities to access data above

    @property
    def linear_x(self) -> float:
        return self.linear[0]

    @linear_x.setter
    def linear_x(self, value: float):
        self.linear[0] = value

    @property
    def linear_y(self) -> float:
        return self.linear[1]

    @linear_y.setter
    def linear_y(self, value: float):
        self.linear[1] = value

    @property
    def linear_z(self) -> float:
        return self.linear[2]

    @linear_z.setter
    def linear_z(self, value: float):
        self.linear[2] = value

    @property
    def roll(self) -> float:
        return self.angular[0]

    @roll.setter
    def roll(self, value: float):
        self.angular[0] = value

    @property
    def pitch(self) -> float:
        return self.angular[1]

    @pitch.setter
    def pitch(self, value: float):
        self.angular[1] = value

    @property
    def yaw(self) -> float:
        return self.angular[2]

    @yaw.setter
    def yaw(self, value: float):
        self.angular[2] = value
