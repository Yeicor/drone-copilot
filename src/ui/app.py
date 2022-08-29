import time
from typing import Optional, Callable, List

import numpy as np
from kivy import platform, Logger
from kivy.app import App
from kivy.config import ConfigParser
from kivy.uix.settings import SettingsWithSpinner

from drone.api.camera import Camera
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
        self.register_event_type('on_drone_photo_request')
        self.register_event_type('on_drone_photo')
        # Typing
        self.drone: Optional[Drone] = None
        self.listen_status_stop: Optional[Callable[[], None]] = None
        self.status_last_battery: float = -1.0
        self.status_last_max_temperature: float = -1.0
        self.listen_video_stop: Optional[Callable[[], None]] = None
        self.drone_cameras: Optional[List[Camera]] = None
        self.drone_camera: Optional[Camera] = None

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
        self.drone_cameras = self.drone.cameras()
        if len(self.drone_cameras) > 0:
            self.drone_camera = self.drone_cameras[0]  # TODO: Configurable
            # TODO: Multi-camera views!
            resolution = self.drone_camera.resolutions_video[0] if len(self.drone_camera.resolutions_video) > 0 else (
                640, 480)  # TODO: Configurable
            self.listen_video_stop = self.drone_camera.listen_video(
                resolution, lambda frame: self.dispatch('on_drone_video_frame', frame))
        else:
            self.root.ids.video.set_frame_text('No video feed available for this drone, :(')

    def on_drone_status(self, drone_status: Status):
        Logger.info('DroneCopilotApp: STATUS: {}'.format(str(drone_status)))
        if self.status_last_battery != drone_status.battery:
            self.status_last_battery = drone_status.battery
            self.root.ids.battery_label.text = '{}%'.format(int(self.status_last_battery * 100))
            Logger.info('DroneCopilotApp: battery: {}%'.format(int(self.status_last_battery * 100)))
        cur_max_temp_c = max(drone_status.temperatures.values()) - 273.15  # Kelvin to Celsius. TODO: Configure units
        if self.status_last_max_temperature != cur_max_temp_c:
            self.status_last_max_temperature = cur_max_temp_c
            self.root.ids.temperature_label.text = '{:.1f}ºC'.format(self.status_last_max_temperature)
            Logger.info('DroneCopilotApp: temperature: {}ºC'.format(self.status_last_max_temperature))

    def on_drone_video_frame(self, frame: np.ndarray):
        self.root.ids.video.update_texture(frame)

    def on_drone_photo_request(self):
        if self.drone_camera:
            resolution = self.drone_camera.resolutions_photo[0] if len(self.drone_camera.resolutions_photo) > 0 else (
                640, 480)  # TODO: Configurable
            self.listen_video_stop = self.drone_camera.take_photo(
                resolution, lambda frame: self.dispatch('on_drone_photo', frame))
        else:
            # TODO: Unsupported photo message
            Logger.error('DroneCopilotApp: unsupported photo request')

    def on_drone_photo(self, frame: np.ndarray):
        Logger.info('DroneCopilotApp: received photo frame')
        self.root.ids.video.update_texture(frame)
        time.sleep(2)  # TODO: Save it somewhere (configurable)

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
