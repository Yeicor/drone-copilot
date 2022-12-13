import numpy as np
from kivy.clock import mainthread
from kivy.core.text import Label as CoreLabel
from kivy.graphics.texture import Texture
from kivy.uix.image import Image


class MyVideo(Image):

    def __init__(self, **kwargs):
        super().__init__(**kwargs, nocache=True, allow_stretch=True)

    def set_frame_text(self, msg: str, **kwargs):
        """Generates a new frame that only contains the given text.

        :param msg: the text message to send to the user. Useful for quick and dirty error messages.
        :param kwargs: the arguments for the text label.
        """
        label = CoreLabel(text=msg, font_size=42, **kwargs)
        # The label is usually not drawn until needed, so force it to draw.
        label.refresh()
        # Now access the texture of the label and use it wherever and however you may please.
        self.texture = label.texture

    @mainthread
    def update_texture(self, frame: np.ndarray):
        """
        Queues an update of the texture on the main UI thread (work should be minimal).
        It also forces to redraw of the widget soon.

        :param frame: the image to update the texture with, as a numpy.ndarray of (width, height, 3) in RGB format.
        """
        # Update the texture with the vertically-flipped next frame and ask to be redrawn
        new_size = tuple(frame.shape[:2])
        if not self.texture or self.texture.size != new_size:  # Create a new texture only if the size changed
            self.texture = Texture.create(size=new_size, colorfmt='rgb', bufferfmt='ubyte', mipmap=False)
            self.texture.flip_vertical()
        self.texture.blit_buffer(frame.flatten(), colorfmt='rgb', bufferfmt='ubyte', mipmap_generation=False)
        self.canvas.ask_update()

    def get_screen_bounds(self) -> (int, int, int, int):
        """Gets the bounds of the rendered texture in the window, in pixels.

        It takes into account the aspect ratio of the video feed and the widget.
        """
        tw, th = self.texture.size
        sw, sh = self.size
        if tw * sh > th * sw:
            # The texture is wider than the widget
            w = sw
            h = w * th / tw
            x = 0
            y = (sh - h) / 2
        else:
            # The texture is taller than (or equal to) the widget
            h = sh
            w = h * tw / th
            y = 0
            x = (sw - w) / 2

        return x, y, w, h
