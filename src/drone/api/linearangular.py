from dataclasses import dataclass

import numpy as np


@dataclass
class LinearAngular:
    """Holds/sets the position+angle/velocity/acceleration of a drone.
    See :class:`drone.Drone` for unit and axes details.
    """

    linear: np.ndarray = np.zeros(3)
    """The linear ***** of the drone.
    """

    angular: np.ndarray = np.zeros(3)
    """The angular ***** of the drone (yaw, pitch and roll). 
    The pitch and roll values may be ignored if unsupported.
    """
