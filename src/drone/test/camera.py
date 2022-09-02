from typing import Callable

import numpy as np
from kivy import Logger
from kivy.app import App
from kivy.clock import Clock, mainthread
from kivy3 import Geometry, Object3D, Mesh, Face3

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
        self._renderer.size = (512, 512)
        App.get_running_app().root.add_widget(self._renderer)

    def scene_geoms(self) -> [Geometry]:
        to_process = [self._renderer.scene]
        geoms = []
        while to_process:
            obj = to_process.pop()
            if isinstance(obj, Object3D):
                to_process.extend(obj.children)
            if isinstance(obj, Mesh):
                if isinstance(obj.geometry, Geometry):
                    if len(obj.geometry.faces) > 0 and isinstance(obj.geometry.faces[0], Face3):
                        if len(obj.geometry.faces) < 256:
                            geoms.append(obj.geometry)
                        else:
                            Logger.warn('Skipping collision detection for mesh with %d faces', len(obj.geometry.faces))
        return geoms

    def render_frame(self, callback: Callable[[np.ndarray], None] = None):
        """Renders a new frame and calls the callback with the result.
        """
        return self._renderer.queue_render(lambda: callback(self._renderer.last_frame()))

    def take_photo(self, resolution: (int, int), callback: Callable[[np.ndarray], None]):
        # NOTE: resolution is ignored, for photos, only videos modify the resolution (to avoid clashes)
        self.render_frame(callback)

    def listen_video(self, resolution: (int, int), callback: Callable[[np.ndarray], None]) -> Callable[[], None]:
        # self._renderer.size = resolution if resolution[0] != 0 and resolution[1] != 0 else (800, 600)
        # TODO: Optimize (share frames) for multiple video listeners!
        ev = Clock.schedule_interval(lambda dt: self.render_frame(callback), 0)
        return ev.cancel
