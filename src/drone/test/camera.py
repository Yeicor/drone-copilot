from typing import Callable

import numpy as np
from kivy.app import App
from kivy.clock import Clock, mainthread

from drone.api.camera import Camera
from drone.test.renderer3d.collision import raycast_scene
from drone.test.renderer3d.renderer import MySceneRenderer


class TestCamera(Camera):
    _renderer = MySceneRenderer()

    def __init__(self) -> None:
        super().__init__()

    @mainthread
    def setup(self):
        # HACK: We need to render to the main app, but we do it offscreen to avoid showing it
        self._renderer.pos_hint = {'x': 2, 'y': 0}
        self._renderer.size_hint = (None, None)  # Size is set manually
        self._renderer.size = (512, 512)
        App.get_running_app().root.add_widget(self._renderer)

    def raycast(self, pos: np.ndarray, dir: np.ndarray) -> float:
        """Returns the distance to the closest object in the scene that collides with the given ray. -1 on no collision.
        It will convert the drone's coordinate system to the internal one (OpenGL).
        """
        # Negate Z and swap YZ (convert drone to OpenGL coordinates)
        pos[1], pos[2] = pos[2], -pos[1]
        dir[1], dir[2] = dir[2], -dir[1]
        return raycast_scene(pos, dir, self._renderer.scene)

    def _render_frame(self, callback: Callable[[np.ndarray], None] = None):
        """Renders a new frame and calls the callback with the result.
        """
        return self._renderer.queue_render(lambda: callback(self._renderer.last_frame()))

    def take_photo(self, resolution: (int, int), callback: Callable[[np.ndarray], None]):
        # NOTE: resolution is ignored, for photos, only videos modify the resolution (to avoid clashes)
        self._render_frame(callback)

    def listen_video(self, resolution: (int, int), callback: Callable[[np.ndarray], None]) -> Callable[[], None]:
        # self._renderer.size = resolution if resolution[0] != 0 and resolution[1] != 0 else (800, 600)
        # TODO: Optimize (share frames) for multiple video listeners!
        ev = Clock.schedule_interval(lambda dt: self._render_frame(callback), 0)
        return ev.cancel
