import cv2
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.uix.image import Image


# noinspection PyUnresolvedReferences
class Video(Image):

    def __init__(self):
        super(Video, self).__init__()
        # TODO: Android fix for:
        self.capture = cv2.VideoCapture(
            "https://jsoncompare.org/LearningContainer/SampleFiles/Video/MP4/sample-mp4-file.mp4")
        # cv2.namedWindow("CV2 Image")
        self.clock_event = Clock.schedule_interval(self.update, 1.0 / 33.0)

    def update(self, dt):
        # display image from cam in opencv window
        ret, frame = self.capture.read()
        if frame is None:
            self.clock_event.cancel()
            return  # EOF

        buf1 = cv2.flip(frame, 0)  # Flip vertically for OpenGL
        buf = buf1.tostring()

        if self.texture is None:
            # noinspection PyArgumentList
            self.texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='bgr')
        self.texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
        self.canvas.ask_update()
