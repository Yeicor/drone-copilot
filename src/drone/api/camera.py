from abc import abstractmethod, ABC
from dataclasses import dataclass, field
from typing import Callable, List, Tuple

import numpy as np


@dataclass
class Camera(ABC):
    """Stores metadata about a camera.
    """

    direction: np.ndarray = np.array([1, 0, 0])  # <- Forward
    """The (approximate) direction of the camera in 3D space (unit vector).
    """
    resolutions_video: List[Tuple[int, int]] = field(default_factory=list)
    """The available video resolutions of the camera. [] if unknown.
    """
    resolutions_photo: List[Tuple[int, int]] = field(default_factory=list)
    """The available photo resolutions of the camera. [] if unknown.
    """

    # TODO: possibility to move the camera

    @abstractmethod
    def listen_video(self, resolution: (int, int), callback: Callable[[np.ndarray], None]) -> Callable[[], None]:
        """Connects to the camera and starts receiving frames on callback. It returns "immediately".
        Each frame will be a numpy array of shape (width, height, 3) representing the RGB color for each pixel.
        Multiple calls to listen should share the frames, so modifications may be visible to other listeners.
        The callback may be run on the decoding thread, so long-running operations should be moved to another thread.
        Run the returned function to stop listening.

        :param resolution: the requested resolution to use for the video stream (only a hint).
        :param callback: the function to call with each video frame.
        :return: a function to stop listening.
        """
        return lambda: None

    @abstractmethod
    def take_photo(self, resolution: (int, int), callback: Callable[[np.ndarray], None]):
        """Takes a photo with the camera and returns it on callback. It returns "immediately".
        It may freeze the video or not work if already listening for video

        :param resolution: the requested resolution to use for the photo (only a hint).
        :param callback: the function to call with the photo.
        """
        return lambda: None
