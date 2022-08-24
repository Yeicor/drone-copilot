import numpy as np
from kivy.clock import mainthread
from kivy.graphics.texture import Texture
from kivy.uix.image import Image


class MyVideo(Image):

    def __init__(self, **kwargs):
        super().__init__(**kwargs, nocache=True, allow_stretch=True)

    @mainthread
    def update_texture(self, frame: np.ndarray):
        """
        Queues an update of the texture on the main UI thread (work should be minimal).
        It also forces to redraw of the widget soon.

        :param frame: the image to update the texture with, as a numpy.ndarray of (width, height, 3) in RGB format.
        """
        # Update the texture with the vertically-flipped next frame and ask to be redrawn
        if self.texture is None:
            self.texture = Texture.create(size=(frame.shape[0], frame.shape[1]), colorfmt='rgb')
            self.texture.flip_vertical()
        self.texture.blit_buffer(np.ravel(frame), colorfmt='rgb', bufferfmt='ubyte', mipmap_generation=False)
        self.canvas.ask_update()
