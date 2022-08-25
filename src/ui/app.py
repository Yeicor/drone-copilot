from kivy import platform, Logger
from kivy.app import App
from kivy.config import ConfigParser
from kivy.uix.settings import SettingsWithSpinner

from ui.settings.registry import get_settings_meta, get_settings_defaults
from util import androidhacks
from util.video.proxy import VideoProxy
from util.video.videosource import VideoSource


class DroneCopilotApp(App):
    title = 'Drone Copilot'
    settings_cls = SettingsWithSpinner

    # Typing
    proxy: VideoProxy
    video_source: VideoSource

    def build(self):
        if platform == 'android':
            androidhacks.setup()

    def on_start(self):
        # Connect to video through a proxy
        Logger.info('DroneCopilotApp: Connecting to video')
        self.proxy = VideoProxy()
        self.proxy.start()  # Start the default video proxy (UDP -> TCP)
        self.video_source = VideoSource('tcp://{}:{}'.format(self.proxy.dst_addr[0], self.proxy.dst_addr[1]))
        self.video_source.bind(on_video_frame=lambda _, frame: self.root.ids.video.update_texture(frame))
        self.video_source.start()

    def on_stop(self):
        del self.video_source
        del self.proxy

    def build_settings(self, settings):
        settings.add_json_panel(self.title, self.config, data=get_settings_meta())

    def build_config(self, config: ConfigParser):
        for k, v in get_settings_defaults().items():
            config.setdefaults(k, v)
