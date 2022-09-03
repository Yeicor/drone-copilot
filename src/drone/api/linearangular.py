from dataclasses import dataclass

import numpy as np


@dataclass
class LinearAngular(object):
    """Holds/sets the position+angle/velocity/acceleration of a drone.
    See :class:`drone.api.drone.Drone` for unit and axes details.
    """

    linear_local: np.ndarray = np.zeros(3)
    """The linear ***** of the drone.
    """

    angular: np.ndarray = np.zeros(3)
    """The angular ***** of the drone. 
    The pitch and roll values may be ignored if unsupported.
    """

    # Utilities to access data above

    @property
    def linear_local_x(self) -> float:
        return self.linear_local[0]

    @linear_local_x.setter
    def linear_local_x(self, value: float):
        self.linear_local = np.array(
            [value, self.linear_local_y, self.linear_local_z])  # TODO: Why does this require a copy?

    @property
    def linear_local_y(self) -> float:
        return self.linear_local[1]

    @linear_local_y.setter
    def linear_local_y(self, value: float):
        self.linear_local = np.array([self.linear_local_x, value, self.linear_local_z])

    @property
    def linear_local_z(self) -> float:
        return self.linear_local[2]

    @linear_local_z.setter
    def linear_local_z(self, value: float):
        self.linear_local = np.array([self.linear_local_x, self.linear_local_y, value])

    def linear_abs(self, attitude: np.ndarray) -> np.ndarray:
        from kivy.graphics.transformation import Matrix
        m = Matrix()
        m = m.rotate(attitude[2], 0, 0, 1)  # Yaw
        m = m.rotate(attitude[1], 1, 0, 0)  # Pitch
        m = m.rotate(attitude[0], 0, 1, 0)  # Roll
        return np.array(m.transform_point(*self.linear_local))

    @property
    def roll(self) -> float:
        return self.angular[0]

    @roll.setter
    def roll(self, value: float):
        self.angular = np.array([value, self.pitch, self.yaw])

    @property
    def pitch(self) -> float:
        return self.angular[1]

    @pitch.setter
    def pitch(self, value: float):
        self.angular = np.array([self.roll, value, self.yaw])

    @property
    def yaw(self) -> float:
        return self.angular[2]

    @yaw.setter
    def yaw(self, value: float):
        self.angular = np.array([self.roll, self.pitch, value])

    @property
    def angular_vector(self) -> np.ndarray:
        """Converts the angles to a direction unit vector that points to the new forward
        """
        return np.array([
            np.cos(self.yaw) * np.cos(self.pitch),
            np.sin(self.yaw) * np.cos(self.pitch),
            np.sin(self.pitch)
        ])
