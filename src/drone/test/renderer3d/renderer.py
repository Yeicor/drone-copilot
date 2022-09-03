"""
This shows the 3D viewer of the scene in a single app
"""
import os.path
from typing import Callable, Optional

import numpy as np
from kivy import Logger
from kivy.clock import mainthread
from kivy3 import Renderer, PerspectiveCamera

from drone.test.renderer3d.scene import load_scene


class MySceneRenderer(Renderer):
    """Loads and renders the scene. Check out queue_render() for rendering to a np.ndarray.
    """

    def __init__(self, **kwargs):
        super().__init__(shader_file=os.path.join(os.path.dirname(__file__), 'default.glsl'), **kwargs)
        self.set_clear_color((0.3, 0.5, 0.8, 1.0))
        self.bind(size=self._adjust_aspect)
        self.scene = load_scene()  # will take a couple of seconds to load, it should be moved to another thread
        self.camera = PerspectiveCamera(75, 1, 0.01, 1000)
        self.queue_render_callback = None
        # Set up the future renders (compile the whole scene into static render instructions)
        self.render(self.scene, self.camera)

    def _adjust_aspect(self, _inst, _val):
        aspect = self.size[0] / float(self.size[1])
        self.camera.aspect = aspect
        # Logger.warn('Renderer: aspect ratio adjusted to %s (size changed to %s)' % (aspect, rsize))

    @mainthread
    def queue_render(self, callback: Optional[Callable[[], None]] = None):
        """Asks for another render to be done.
        This should be done after a change to the scene or the camera, and is done automatically after resizing.

        :param callback: a callback to be called after the render is done, useful for reading the rendered array.
        """
        if self.queue_render_callback is None:  # Don't overload rendering if the device is not fast enough
            self.queue_render_callback = callback
            self.canvas.ask_update()  # Not forcing the render! Only rescaling does it.
            if self.pos[0] % 2 == 0:  # force a rerender, the ugly way ;)
                self.pos[0] += 1
            else:
                self.pos[0] -= 1
        else:
            Logger.warn('Renderer: render already queued, skipping to avoid freezes')

    def _reset_gl_context(self, *args):
        """Called at the end of each render
        """
        super(MySceneRenderer, self)._reset_gl_context(*args)
        if self.queue_render_callback:
            self.queue_render_callback()
            self.queue_render_callback = None

    def last_frame(self) -> np.ndarray:
        """Reads the last rendered array. This may be a bit slow (because we are reading an OpenGL FBO to the CPU).
        :return: np.ndarray of RGB values (shape: (width, height, 3))
        """
        pixels = self.fbo.texture.pixels
        width, height = self.size
        rgb_frame: np.ndarray = np.frombuffer(pixels, dtype=np.uint8).reshape((width, height, 4))
        rgb_frame = rgb_frame[:, :, :3]  # RGBA -> RGB
        rgb_frame = np.flip(rgb_frame, axis=0)  # flip the frame vertically
        # Weird HACK: if resolution is not square, pixels are not aligned correctly
        if width != height:
            aspect_1 = width / height
            min_size = min(width, height)
            if height > width:
                aspect_1 = 1 / aspect_1
            if aspect_1 != int(aspect_1):  # FIXME: most resolutions are broken!
                Logger.warn('Renderer: non-multiple width and height (those that don\'t validate '
                            'width = n * height or height = n * width where n is an integer) are broken!')
            else:
                rgb_frame = rgb_frame.reshape((min_size, int(aspect_1), min_size, 3))
                hacky_flip = rgb_frame[:, ::-1, :, :]
                rgb_frame = hacky_flip.reshape((width, height, 3))

        return rgb_frame