from kivy.app import App
from kivy.utils import platform

from ui.video.video import Video
from util import androidhacks
from util.video.proxy import VideoProxy
from util.video.videosource import VideoSource

__version__ = '0.0.2'

if platform != 'android' and platform != 'ios':
    from kivy.config import Config

    # Dispose of that nasty red dot, required for gestures4kivy. TODO: Use gestures4kivy
    Config.set('input', 'mouse', 'mouse, disable_multitouch')


class MyApp(App):

    def build(self):
        self.title = 'Tello Copilot'
        if platform == 'android':
            androidhacks.setup()

        proxy = VideoProxy()
        proxy.start()  # Start the default video proxy (UDP -> TCP)
        video_widget = Video()
        video_source = VideoSource('tcp://{}:{}'.format(proxy.dst_addr[0], proxy.dst_addr[1]))
        video_source.bind(on_video_frame=lambda _, frame: video_widget.update_texture(frame))
        video_source.start()
        return video_widget


if __name__ == '__main__':
    MyApp().run()
