from kivy.uix.image import Image


class VideoFfmpeg(Image):
    def __init__(self, source="udp://0.0.0.0:2000"):
        super(VideoFfmpeg, self).__init__()
        # TODO: import av

