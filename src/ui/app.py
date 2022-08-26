from typing import Type, Optional

from kivy import platform, Logger
from kivy.app import App
from kivy.config import ConfigParser
from kivy.uix.settings import SettingsWithSpinner

from drone.api.drone import Drone
from drone.registry import drone_connect_auto
from ui.settings.registry import get_settings_meta, get_settings_defaults
from util import androidhacks
from util.video import StreamingVideoSource


class DroneCopilotApp(App):
    title = 'Drone Copilot'
    settings_cls = SettingsWithSpinner

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.register_event_type('on_connected')  # Dispatched when we connect to the drone
        # Typing
        self.drone: Optional[Drone] = None
        self.video_source: Optional[StreamingVideoSource] = None

    def build(self):
        if platform == 'android':
            androidhacks.setup()

    def on_start(self):
        # Start connecting to the drone
        def on_connect_result(drone: Drone):
            if drone:
                self.dispatch('on_connected', drone)
            else:
                self.root.ids.video.set_frame_text(  # TODO: Something nicer
                    'CONNECTION TO DRONE FAILED!\nRETRY BY RELOADING THE APP')

        self.root.ids.video.set_frame_text('Connecting to the drone...')
        drone_connect_auto(self.config, on_connect_result)

    def on_connected(self, drone: Drone):
        self.drone = drone
        Logger.info('DroneCopilotApp: connected to drone!')
        # Connect to video camera
        self.root.ids.video.set_frame_text('Connecting to the drone\'s video feed...')
        camera = self.drone.cameras()[0]
        camera.listen_video(camera.resolutions_video[0], lambda frame: self.root.ids.video.update_texture(frame))

    def on_stop(self):
        del self.drone  # Clean up drone connection

    def build_settings(self, settings):
        settings.add_json_panel(self.title, self.config, data=get_settings_meta())

    def build_config(self, config: ConfigParser):
        for k, v in get_settings_defaults().items():
            config.setdefaults(k, v)
