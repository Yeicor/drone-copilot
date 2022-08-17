from kivy.app import App
from kivy.utils import platform

import androidhacks
from video.proxy import VideoProxy
from video.video import Video

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
        return Video('tcp://{}:{}'.format(proxy.dst_addr[0], proxy.dst_addr[1]))


if __name__ == '__main__':
    MyApp().run()
