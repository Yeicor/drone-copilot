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

    def _convert_vector(self, ray_dir: np.ndarray, negate_z: bool = True) -> np.ndarray:
        """It will convert the drone's coordinate system to the internal one (OpenGL). It will clone the vector
        """
        ray_dir = np.array([ray_dir[0], -ray_dir[2] if negate_z else ray_dir[2], ray_dir[1]])
        return ray_dir

    def raycast(self, ray_origin: np.ndarray, ray_dir: np.ndarray) -> float:
        """Returns the distance to the closest object in the scene that collides with the given ray. -1 on no collision.
        """
        # Negate Z and swap YZ (convert drone to OpenGL coordinates), cloning to avoid aliasing
        ray_origin = self._convert_vector(ray_origin)
        ray_dir = self._convert_vector(ray_dir)
        return raycast_scene(ray_origin, ray_dir, self._renderer.scene)

    # noinspection PyUnresolvedReferences
    def on_status_update(self, status: 'TestStatus'):
        # Update the camera position
        pos = self._convert_vector(status.position_attitude.linear_local)
        look_at_dir = self._convert_vector(status.position_attitude.angular_vector, negate_z=False)
        self._renderer.camera.pos = pos
        # Note that roll won't work as the up vector is fixed (it does not matter as yaw is the only one used for now)
        self._renderer.camera.look_at(pos + look_at_dir)

    def _render_frame(self, callback: Callable[[np.ndarray], None] = None):
        """Renders a new frame and calls the callback with the result.
        """
        return self._renderer.queue_render(lambda: Clock.schedule_once(
            lambda dt: callback(self._renderer.last_frame()), -1))

    def take_photo(self, resolution: (int, int), callback: Callable[[np.ndarray], None]):
        # NOTE: resolution is ignored, for photos, only videos modify the resolution (to avoid clashes)
        self._render_frame(callback)

    def listen_video(self, resolution: (int, int), callback: Callable[[np.ndarray], None]) -> Callable[[], None]:
        # self._renderer.size = resolution if resolution[0] != 0 and resolution[1] != 0 else (800, 600)
        # TODO: Optimize (share frames) for multiple video listeners!
        ev = Clock.schedule_interval(lambda dt: self._render_frame(callback), 1 / 30)  # 30 FPS for now for performance
        return ev.cancel
