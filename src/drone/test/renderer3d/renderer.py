"""
This shows the 3D viewer of the scene in a single app
"""
import numpy as np
from kivy3 import Renderer, PerspectiveCamera

from drone.test.renderer3d.scene import load_scene


class MySceneRenderer(Renderer):
    """Loads and renders the scene.

    Interesting utilities are do_render() and get_last_render_array().
    """

    def __init__(self, **kwargs):
        super().__init__(shader_file='default.glsl', **kwargs)
        self.bind(size=self._adjust_aspect)
        self.scene = load_scene()  # will take a couple of seconds to load
        self.camera = PerspectiveCamera(75, 1, 1, 1000)

    def _adjust_aspect(self, inst, val):
        rsize = self.size
        aspect = rsize[0] / float(rsize[1])
        self.camera.aspect = aspect

    def do_render(self):
        self.render(self.scene, self.camera)

    def get_last_render_array(self) -> np.ndarray:
        """Returns the last rendered array. Note that renders are delayed after a do_render call.
        :return: np.ndarray of RGB values (shape: (width, height, 3))
        """
        rgba_frame = np.frombuffer(self.fbo.pixels, dtype=np.uint8).reshape((self.fbo.size[1], self.fbo.size[0], 4))
        return rgba_frame[:, :, :3]  # RGB frame
