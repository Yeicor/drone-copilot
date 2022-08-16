import cv2
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.uix.image import Image
from kivy import Logger


# noinspection PyUnresolvedReferences
class Video(Image):

    def __init__(self):
        super(Video, self).__init__()
        # TODO: Android fix for:
        start_time = Clock.time()
        self.capture = cv2.VideoCapture(
            "https://jsoncompare.org/LearningContainer/SampleFiles/Video/MP4/sample-mp4-file.mp4")
        Logger.info('Starting video capture in ' + str(Clock.time() - start_time))
        # cv2.namedWindow("CV2 Image")
        self.clock_event = Clock.schedule_interval(self.update, 1.0 / 33.0)

    def update(self, dt):
        # display image from cam in opencv window
        start_time = Clock.time()
        ret, frame = self.capture.read()
        if frame is None:
            self.clock_event.cancel()
            return  # EOF

        # buf1 = cv2.flip(frame, 0)  # Flip vertically for OpenGL
        buf = frame.tostring()

        if self.texture is None:
            # noinspection PyArgumentList
            self.texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='bgr')
            self.texture.flip_vertical()
        self.texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte', mipmap_generation=False)
        self.canvas.ask_update()
        Logger.info('Video capture update took ' + str(Clock.time() - start_time))
