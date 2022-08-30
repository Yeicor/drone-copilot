import time
from typing import Optional, Callable, List

import numpy as np
import plyer
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

    # ==================== boilerplate ====================

    def build(self):
        if platform == 'android':
            androidhacks.setup()
        Window.bind(on_keyboard=lambda *args: self.on_keyboard(*args))

    def build_settings(self, settings):
        settings.add_json_panel(self.title, self.config, data=get_settings_meta())

    def build_config(self, config: ConfigParser):
        for k, v in get_settings_defaults().items():
            config.setdefaults(k, v)

    def register_event_type(self, *args, **kwargs):  # Needed to avoid EventDispatcher warnings
        # noinspection PyUnresolvedReferences
        super(DroneCopilotApp, self).register_event_type(*args, **kwargs)

    def dispatch(self, *args, **kwargs):  # Needed to avoid EventDispatcher warnings
        # noinspection PyUnresolvedReferences
        super(DroneCopilotApp, self).dispatch(*args, **kwargs)

    # ==================== LISTENERS & HANDLERS ====================

    def on_start(self):
        # Start connecting to the drone
        def on_connect_result(drone: Drone):
            if drone:
                self.dispatch('on_drone_connected', drone)
            else:
                self.root.ids.video.set_frame_text(  # TODO: Something nicer
                    'CONNECTION TO DRONE FAILED!\nRETRY BY RELOADING THE APP')

        self.root.ids.joystick_left.disabled = True
        self.root.ids.joystick_right.disabled = True
        self.root.ids.takeoff_land_button.disabled = True
        self.root.ids.video.set_frame_text('Connecting to the drone...')
        drone_connect_auto(self.config, on_connect_result)

    def on_drone_connected(self, drone: Drone):
        self.drone = drone
        Logger.info('DroneCopilotApp: connected to drone!')
        # Update UI
        self.root.ids.takeoff_land_button.disabled = False
        self.root.ids.video.set_frame_text('Connecting to the drone\'s video feed...')
        # Listen for status events
        self.listen_status_stop = self.drone.listen_status(lambda status: self.dispatch('on_drone_status', status))
        # Connect to video camera (if available)
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
        # BATTERY
        if self.status_last_battery != drone_status.battery:
            self.status_last_battery = drone_status.battery
            self.root.ids.battery_label.text = '{}%'.format(int(self.status_last_battery * 100))
            Logger.info('DroneCopilotApp: battery: {}%'.format(int(self.status_last_battery * 100)))
        # TEMPERATURE
        cur_max_temp_c = max(drone_status.temperatures.values()) - 273.15  # Kelvin to Celsius. TODO: Configure units
        if self.status_last_max_temperature != cur_max_temp_c:
            self.status_last_max_temperature = cur_max_temp_c
            self.root.ids.temperature_label.text = '{:.1f}ºC'.format(self.status_last_max_temperature)
            Logger.info('DroneCopilotApp: temperature: {}ºC'.format(self.status_last_max_temperature))
        # ENABLED UI ELEMENTS AND CONTENTS
        self.root.ids.joystick_left.disabled = not self.drone.status.flying
        self.root.ids.joystick_right.disabled = not self.drone.status.flying
        if self.drone.status.flying:
            self.root.ids.takeoff_land_button.text = 'Land'  # TODO: Icons?
        else:
            self.root.ids.takeoff_land_button.text = 'Takeoff'

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
    # noinspection PyUnusedLocal
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
        if joystick_left_x != 0 or joystick_left_y != 0 or joystick_right_x != 0 or joystick_right_y != 0:
            self.action_joysticks(joystick_left_x, joystick_left_y, joystick_right_x, joystick_right_y)
        # Manage takeoff/land shortcut
        if key == Keyboard.keycodes['spacebar']:
            self.action_takeoff_land()
        # Manage right panel shortcuts
        if key == Keyboard.keycodes['p']:
            self.action_take_photo()
        elif key == Keyboard.keycodes['o']:
            self.action_toggle_settings()
        # Undocumented extras
        if key == Keyboard.keycodes['f11']:
            # HACK: Screenshot code as default can't customize the file path properly!
            filename = f'{plyer.storagepath.get_pictures_dir()}/kivy-drone-copilot-screenshot-{time.time()}.png'
            from kivy.graphics.opengl import glReadPixels, GL_RGB, GL_UNSIGNED_BYTE
            width, height = self.root_window.size
            data = glReadPixels(0, 0, width, height, GL_RGB, GL_UNSIGNED_BYTE)
            # noinspection PyProtectedMember
            self.root_window._win.save_bytes_in_png(filename, data, width, height)
            Logger.debug('Window: Screenshot saved at <%s>' % filename)

    # ==================== ACTIONS triggered by events ====================
    def action_joysticks(self, joystick_left_x: Optional[float], joystick_left_y: Optional[float],
                         joystick_right_x: Optional[float], joystick_right_y: Optional[float]):
        Logger.debug('DroneCopilotApp: action_joysticks: {} {} {} {}'.format(
            joystick_left_x, joystick_left_y, joystick_right_x, joystick_right_y))
        if self.drone and self.drone.status.flying:
            speed_m_per_s = 2.0  # TODO: Configurable
            target_speed_to_update = self.drone.target_speed  # Read previous value for partial updates
            if joystick_right_y:
                target_speed_to_update.linear_x = joystick_right_y * speed_m_per_s
            if joystick_right_x:
                target_speed_to_update.linear_y = joystick_right_x * speed_m_per_s
            if joystick_left_y:
                target_speed_to_update.linear_z = -joystick_left_y * speed_m_per_s
            speed_angular = 2.0  # TODO: Configurable
            if joystick_left_x:
                target_speed_to_update.yaw = joystick_left_x * speed_angular
            self.drone.target_speed = target_speed_to_update  # Actually update the target speed

    def action_takeoff_land(self):
        def action_callback(taking_off: bool):
            Logger.info('DroneCopilotApp: action_takeoff_land callback: taking_off={}'.format(taking_off))
            self.root.ids.takeoff_land_button.disabled = False  # Can take off/land again
            if not taking_off:  # Stop control after landing
                self.root.ids.joystick_left.disabled = True
                self.root.ids.joystick_right.disabled = True

        # Logger.debug('DroneCopilotApp: action_takeoff_land')
        if self.drone:
            self.root.ids.takeoff_land_button.disabled = True
            if self.drone.status.flying:  # Land
                self.drone.land(lambda: action_callback(False))
            else:  # Take off
                self.root.ids.joystick_left.disabled = False  # Allow control while taking off
                self.root.ids.joystick_right.disabled = False
                self.drone.takeoff(lambda: action_callback(True))
        else:
            Logger.error('DroneCopilotApp: takeoff/land: no drone connected')

    def action_take_photo(self):
        # Logger.debug('DroneCopilotApp: action_take_photo')
        if self.drone_camera:
            resolution = self.drone_camera.resolutions_photo[0] if len(self.drone_camera.resolutions_photo) > 0 else (
                640, 480)  # TODO: Configurable
            self.listen_video_stop = self.drone_camera.take_photo(
                resolution, lambda frame: self.dispatch('on_drone_photo', frame))
        else:
            # TODO: Unsupported photo message
            Logger.error('DroneCopilotApp: unsupported photo request')

    def action_toggle_settings(self):
        # Logger.debug('DroneCopilotApp: action_toggle_settings')
        if not self.open_settings():
            self.close_settings()
