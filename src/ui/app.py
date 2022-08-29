import time
from typing import Optional, Callable, List

import numpy as np
from kivy import platform, Logger
from kivy.app import App
from kivy.config import ConfigParser
from kivy.core.window import Window, Keyboard
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
        self.register_event_type('on_drone_photo')
        # Typing
        self.drone: Optional[Drone] = None
        self.listen_status_stop: Optional[Callable[[], None]] = None
        self.status_last_battery: float = -1.0
        self.status_last_max_temperature: float = -1.0
        self.listen_video_stop: Optional[Callable[[], None]] = None
        self.drone_cameras: Optional[List[Camera]] = None
        self.drone_camera: Optional[Camera] = None

    # ==================== BUILD boilerplate ====================

    def build(self):
        if platform == 'android':
            androidhacks.setup()
        Window.bind(on_keyboard=lambda *args: self.on_keyboard(*args))

    def build_settings(self, settings):
        settings.add_json_panel(self.title, self.config, data=get_settings_meta())

    def build_config(self, config: ConfigParser):
        for k, v in get_settings_defaults().items():
            config.setdefaults(k, v)

    # ==================== LISTENERS & HANDLERS ====================

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
            self.update_takeoff_button()  # HACK: regularly update takeoff button, but not too much
        cur_max_temp_c = max(drone_status.temperatures.values()) - 273.15  # Kelvin to Celsius. TODO: Configure units
        if self.status_last_max_temperature != cur_max_temp_c:
            self.status_last_max_temperature = cur_max_temp_c
            self.root.ids.temperature_label.text = '{:.1f}ºC'.format(self.status_last_max_temperature)
            Logger.info('DroneCopilotApp: temperature: {}ºC'.format(self.status_last_max_temperature))

    def on_drone_video_frame(self, frame: np.ndarray):
        self.root.ids.video.update_texture(frame)

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

    # ==================== KEYBOARD / GAMEPAD events ====================
    def on_keyboard(self, instance, key, scancode, codepoint, modifiers):  # TODO: on_gamepad!
        # Manage joysticks to control drone movements
        joystick_left_x = 0
        joystick_left_y = 0
        joystick_right_x = 0
        joystick_right_y = 0
        if key == Keyboard.keycodes['w']:
            joystick_left_y = 1
        elif key == Keyboard.keycodes['s']:
            joystick_left_y = -1
        if key == Keyboard.keycodes['a']:
            joystick_left_x = -1
        elif key == Keyboard.keycodes['d']:
            joystick_left_x = 1
        if key == Keyboard.keycodes['up']:
            joystick_right_y = 1
        elif key == Keyboard.keycodes['down']:
            joystick_right_y = -1
        if key == Keyboard.keycodes['left']:
            joystick_right_x = -1
        elif key == Keyboard.keycodes['right']:
            joystick_right_x = 1
        self.action_joysticks(joystick_left_x, joystick_left_y, joystick_right_x, joystick_right_y)
        # Manage takeoff/land shortcut
        if key == Keyboard.keycodes['spacebar']:
            self.action_takeoff_land()
        # Manage right panel shortcuts
        if key == Keyboard.keycodes['p']:
            self.action_request_photo()
        elif key == Keyboard.keycodes['o']:
            self.action_open_close_settings()
        # Undocumented extras
        if key == Keyboard.keycodes['f11']:
            self.root_window.screenshot()

    # ==================== ACTIONS triggered by events ====================
    def action_joysticks(self, joystick_left_x: Optional[float], joystick_left_y: Optional[float],
                         joystick_right_x: Optional[float], joystick_right_y: Optional[float]):
        if self.drone and self.drone.status.flying:
            speed_m_per_s = 0.5  # TODO: Configurable
            if joystick_right_y:
                self.drone.target_speed.linear_x = joystick_right_y * speed_m_per_s
            if joystick_right_x:
                self.drone.target_speed.linear_y = joystick_right_x * speed_m_per_s
            if joystick_left_y:
                self.drone.target_speed.linear_z = -joystick_left_y * speed_m_per_s
            speed_angular = 0.5  # TODO: Configurable
            if joystick_left_x:
                self.drone.target_speed.yaw = joystick_left_x * speed_angular

    def action_takeoff_land(self):
        if self.drone:
            if self.drone.status.flying:
                self.drone.land(lambda: self.update_takeoff_button())
            else:
                self.drone.takeoff(lambda: self.update_takeoff_button())
        else:
            Logger.error('DroneCopilotApp: takeoff/land: no drone connected')

    def action_request_photo(self):
        if self.drone_camera:
            resolution = self.drone_camera.resolutions_photo[0] if len(self.drone_camera.resolutions_photo) > 0 else (
                640, 480)  # TODO: Configurable
            self.listen_video_stop = self.drone_camera.take_photo(
                resolution, lambda frame: self.dispatch('on_drone_photo', frame))
        else:
            # TODO: Unsupported photo message
            Logger.error('DroneCopilotApp: unsupported photo request')

    def action_open_close_settings(self):
        if not self.open_settings():
            self.close_settings()

    def update_takeoff_button(self):
        if self.drone and self.drone.status.flying:
            self.root.ids.takeoff_land_button.text = 'Land'
        else:
            self.root.ids.takeoff_land_button.text = 'Takeoff'
