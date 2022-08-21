from abc import abstractmethod, ABC
from dataclasses import dataclass
from typing import Callable

import numpy as np


@dataclass
class Camera(ABC):
    """Stores metadata about a camera.
    """

    direction: np.ndarray = np.array([1, 0, 0])  # <- Forward
    """The (approximate) direction of the camera in 3D space (unit vector).
    """
    resolution: (int, int) = (0, 0)
    """The resolution of the camera. (0, 0) if unknown.
    """

    # TODO: possibility to move the camera

    @abstractmethod
    def listen(self, callback: Callable[[np.ndarray], None]) -> Callable[[], None]:
        """Connects to the camera and starts receiving frames on callback.
        Each frame will be a numpy array of shape (width, height, 3) representing the RGB color for each pixel.
        Multiple calls to listen should share the frames, so modifications may be visible to other listeners.
        The callback may be run on the decoding thread, so long-running operations should be moved to another thread.
        Run the returned function to stop listening.
        """
        return lambda: None
