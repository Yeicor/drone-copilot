from typing import Callable

import numpy as np
from kivy import Logger
from kivy.app import App
from kivy.clock import Clock, mainthread
from kivy.uix.layout import Layout
from kivy.uix.widget import Widget

from drone.api.camera import Camera
from drone.test.renderer3d.collision import raycast_scene
from drone.test.renderer3d.renderer import MySceneRenderer


def _convert_vector(ray_dir: np.ndarray, negate_z: bool = True) -> np.ndarray:
    """It will convert the drone's coordinate system to the internal one (OpenGL). It will clone the vector
    """
    ray_dir = np.array([ray_dir[0], -ray_dir[2] if negate_z else ray_dir[2], ray_dir[1]])
    return ray_dir


class TestCamera(Camera):
    _renderer = MySceneRenderer()

    def __init__(self) -> None:
        super().__init__()
        self.resolutions_video = [(640, 480)]
        self.resolutions_photo = [(640, 480)]

    @mainthread
    def setup(self):
        # HACK: Attach ourselves to the app to force offscreen rendering
        # - Find a suitable widget to attach to (not a layout that will change the size of our widget)
        def invalid_parent(parent: Widget) -> bool:
            return isinstance(parent, Layout)

        possible_parent_queue = [App.get_running_app().root]
        cur_parent = possible_parent_queue.pop()
        while invalid_parent(cur_parent):
            possible_parent_queue.extend(cur_parent.children)
            if len(possible_parent_queue) == 0:
                raise RuntimeError('Unable to automatically find a suitable parent widget for the offscreen renderer')
            cur_parent = possible_parent_queue.pop()

        Logger.info('TestCamera: Chose parent %s to attach the hacky offscreen renderer' % cur_parent)
        self._renderer.size = self.resolutions_video[0]
        cur_parent.add_widget(self._renderer)

    def raycast(self, ray_origin: np.ndarray, ray_dir: np.ndarray) -> float:
        """Returns the distance to the closest object in the scene that collides with the given ray. -1 on no collision.
        """
        # Negate Z and swap YZ (convert drone to OpenGL coordinates), cloning to avoid aliasing
        ray_origin = _convert_vector(ray_origin)
        ray_dir = _convert_vector(ray_dir)
        return raycast_scene(ray_origin, ray_dir, self._renderer.scene)

    # noinspection PyUnresolvedReferences
    def on_status_update(self, status: 'TestStatus'):
        # Update the camera position
        pos = _convert_vector(status.position_attitude.linear_local)
        look_at_dir = _convert_vector(status.position_attitude.angular_vector, negate_z=False)
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
        # TODO: Optimize (share frames) for multiple video listeners!
        ev = Clock.schedule_interval(lambda dt: self._render_frame(callback), 1 / 30)  # 30 FPS for better performance
        return ev.cancel
