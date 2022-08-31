"""
This shows the 3D viewer of the scene in a single app
"""
import os.path
from typing import Callable, Optional

import numpy as np
from kivy3 import Renderer, PerspectiveCamera

from drone.test.renderer3d.scene import load_scene


class MySceneRenderer(Renderer):
    """Loads and renders the scene.

    Interesting utilities are do_render() and get_last_render_array().
    """

    def __init__(self, **kwargs):
        super().__init__(shader_file=os.path.join(os.path.dirname(__file__), 'default.glsl'), **kwargs)
        self.set_clear_color((0.3, 0.5, 0.8, 1.0))
        self.bind(size=self._adjust_aspect)
        self.scene = load_scene()  # will take a couple of seconds to load
        self.camera = PerspectiveCamera(75, 1, 0.01, 1000)
        self.queue_render_callback = None

    def _adjust_aspect(self, inst, val):
        rsize = self.size
        aspect = rsize[0] / float(rsize[1])
        self.camera.aspect = aspect

    def queue_render(self, callback: Optional[Callable[[], None]] = None):
        """Asks for another render to be done.
        This should be done after a change to the scene or the camera, and is done automatically after resizing.

        :param callback: a callback to be called after the render is done, useful for reading the rendered array.
        """
        self.queue_render_callback = callback
        self.render(self.scene, self.camera)

    def _reset_gl_context(self, *args):
        """Called at the end of each render
        """
        super(MySceneRenderer, self)._reset_gl_context(*args)
        if self.queue_render_callback:
            self.queue_render_callback()
            self.queue_render_callback = None

    def last_frame(self) -> np.ndarray:
        """Reads the last rendered array. This may be a bit slow.
        :return: np.ndarray of RGB values (shape: (width, height, 3))
        """
        rgba_frame = np.frombuffer(self.fbo.pixels, dtype=np.uint8).reshape((self.fbo.size[1], self.fbo.size[0], 4))
        return rgba_frame[:, :, :3]  # RGB frame
