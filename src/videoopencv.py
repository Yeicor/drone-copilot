import threading

import cv2
from kivy import Logger
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.uix.image import Image


class VideoOpenCV(Image):
    def __init__(self, src="udp://0.0.0.0:2000"):
        super(VideoOpenCV, self).__init__()
        self.src = src
        t = threading.Thread(target=self.setup_thread, daemon=True)
        t.start()
        self.lock = threading.Lock()

    def setup_thread(self):
        start_time = Clock.time()
        # noinspection PyUnresolvedReferences
        capture = cv2.VideoCapture(self.src)
        Logger.info('OpenCVVideo: Starting video capture in ' + str(Clock.time() - start_time))
        if not capture.isOpened():
            # FIXME: Android can't use VideoCapture (no error found, but stream is instantly closed)
            # TODO: Test other cv2 features on android
            Logger.error("OpenCVVideo: Capture is closed!!")
        else:
            # cv2.namedWindow("CV2 Image")
            self.clock_event = Clock.schedule_interval(self.update, 1.0 / 5.0)
        with self.lock:
            self.capture = capture

    def update(self, dt):
        with self.lock:
            if not self.capture or not self.capture.isOpened():
                return  # Starting up...

        # display image from cam in opencv window
        start_time = Clock.time()
        ret, frame = self.capture.read()
        if frame is None:
            self.clock_event.cancel()
            return  # EOF

        # buf1 = cv2.flip(frame, 0)  # Flip vertically for OpenGL
        buf = frame.tostring()

        # if self.texture is None:
        # noinspection PyArgumentList
        self.texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='bgr')
        self.texture.flip_vertical()
        self.texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte', mipmap_generation=False)
        self.canvas.ask_update()
        Logger.info('Video capture update took ' + str(Clock.time() - start_time))
