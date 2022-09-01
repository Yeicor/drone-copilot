from typing import Callable

import numpy as np
from kivy.app import App
from kivy.clock import Clock, mainthread
from kivy3 import Geometry, Object3D, Mesh

from drone.api.camera import Camera
from drone.test.renderer3d.renderer import MySceneRenderer


class TestCamera(Camera):
    _renderer = MySceneRenderer()

    def __init__(self) -> None:
        super().__init__()

    @mainthread
    def setup(self):
        # HACK: We need to render to the main app, but we do it offscreen to avoid showing it
        self._renderer.pos_hint = {'x': 1, 'y': 0}
        self._renderer.size_hint = (None, None)  # Size is set manually
        App.get_running_app().root.add_widget(self._renderer)

    def scene_geoms(self) -> [Geometry]:
        to_process = [self._renderer.scene]
        geoms = []
        while to_process:
            obj = to_process.pop()
            if isinstance(obj, Object3D):
                to_process.extend(obj.children)
            if isinstance(obj, Mesh):
                geoms.append(obj.geometry)
        return geoms

    def render_frame(self, callback: Callable[[np.ndarray], None] = None):
        """Renders a new frame and calls the callback with the result.
        """
        return self._renderer.queue_render(
            lambda: Clock.schedule_once(lambda dt: callback(self._renderer.last_frame()), 0))

    def take_photo(self, resolution: (int, int), callback: Callable[[np.ndarray], None]):
        # NOTE: resolution is ignored, for photos, only videos modify the resolution (to avoid clashes)
        self.render_frame(callback)

    def listen_video(self, resolution: (int, int), callback: Callable[[np.ndarray], None]) -> Callable[[], None]:
        self._renderer.size = resolution if resolution[0] != 0 and resolution[1] != 0 else (640, 480)
        # TODO: Optimize (share frames) for multiple video listeners!
        ev = Clock.schedule_interval(lambda dt: self.render_frame(callback), 0)
        return ev.cancel
