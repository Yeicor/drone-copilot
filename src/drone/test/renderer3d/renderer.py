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
        self.set_clear_color((0.3, 0.5, 0.8, 1.0))  # background color: sky blue
        self.bind(size=self._adjust_aspect)  # adjust camera aspect ratio when window size changes
        self.scene = load_scene()  # will take a couple of seconds to load, it should be moved to another thread
        self.camera = PerspectiveCamera(75, 1, 0.01, 1000)
        self.queue_render_callback = None
        # Set up the future renders (compile the whole scene into static render instructions)
        self.render(self.scene, self.camera)

    def _adjust_aspect(self, _inst, _val):
        aspect = self.size[0] / float(self.size[1])
        self.camera.aspect = aspect
        Logger.warn('Renderer: aspect ratio adjusted to %s (size changed to %s)' % (aspect, self.size))

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
        height, width = self.fbo.texture.height, self.fbo.texture.width
        rgb_frame = np.frombuffer(self.fbo.texture.pixels, np.uint8)
        rgb_frame = rgb_frame.reshape((height, width, 4))
        rgb_frame = rgb_frame[:, :, :3]  # RGBA -> RGB
        rgb_frame = rgb_frame[::-1, :, :]  # flip vertically
        rgb_frame = np.transpose(rgb_frame, (1, 0, 2))  # Convert height x width x 3 to width x height x 3
        rgb_frame = rgb_frame.ravel(order='K').reshape((width, height, 3))  # TODO: why is this needed???!
        return rgb_frame
