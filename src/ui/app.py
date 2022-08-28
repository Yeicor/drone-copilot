from typing import Optional, Callable

import numpy as np
from kivy import platform, Logger
from kivy.app import App
from kivy.config import ConfigParser
from kivy.uix.settings import SettingsWithSpinner

from drone.api.drone import Drone
from drone.api.status import Status
from drone.registry import drone_connect_auto
from ui.settings.registry import get_settings_meta, get_settings_defaults
from util import androidhacks


class DroneCopilotApp(App):
    title = 'Drone Copilot'
    settings_cls = SettingsWithSpinner

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Events
        self.register_event_type('on_drone_connected')
        self.register_event_type('on_drone_status')
        self.register_event_type('on_drone_video_frame')
        # Typing
        self.drone: Optional[Drone] = None
        self.listen_status_stop: Optional[Callable[[], None]] = None
        self.status_last_battery = None
        self.listen_video_stop: Optional[Callable[[], None]] = None

    def build(self):
        if platform == 'android':
            androidhacks.setup()

    def on_start(self):
        # Start connecting to the drone
        def on_connect_result(drone: Drone):
            if drone:
                self.dispatch('on_drone_connected', drone)
            else:
                self.root.ids.video.set_frame_text(  # TODO: Something nicer
                    'CONNECTION TO DRONE FAILED!\nRETRY BY RELOADING THE APP')

        self.root.ids.video.set_frame_text('Connecting to the drone...')
        drone_connect_auto(self.config, on_connect_result)

    def on_drone_connected(self, drone: Drone):
        self.drone = drone
        Logger.info('DroneCopilotApp: connected to drone!')
        # Listen for status events
        self.listen_status_stop = self.drone.listen_status(lambda status: self.dispatch('on_drone_status', status))
        # Connect to video camera (if available)
        self.root.ids.video.set_frame_text('Connecting to the drone\'s video feed...')
        cameras = self.drone.cameras()
        if len(cameras) > 0:
            camera = cameras[0]
            resolution = camera.resolutions_video[0] if len(camera.resolutions_video) > 0 else (640, 480)
            self.listen_video_stop = camera.listen_video(
                resolution, lambda frame: self.dispatch('on_drone_video_frame', frame))
        else:
            self.root.ids.video.set_frame_text('No video feed available for this drone, :(')

    def on_drone_status(self, drone_status: Status):
        if self.status_last_battery != drone_status.battery:
            self.status_last_battery = drone_status.battery
            self.root.ids.battery_label.text = '{}%'.format(int(drone_status.battery * 100))
            Logger.info('DroneCopilotApp: battery: {}%'.format(int(drone_status.battery * 100)))

    def on_drone_video_frame(self, frame: np.ndarray):
        self.root.ids.video.update_texture(frame)

    def on_stop(self):
        if self.listen_status_stop:
            self.listen_status_stop()
        if self.listen_video_stop:
            self.listen_video_stop()
        if self.drone:
            del self.drone
        Logger.info('DroneCopilotApp: destroyed')

    def build_settings(self, settings):
        settings.add_json_panel(self.title, self.config, data=get_settings_meta())

    def build_config(self, config: ConfigParser):
        for k, v in get_settings_defaults().items():
            config.setdefaults(k, v)
