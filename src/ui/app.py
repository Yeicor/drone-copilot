import glob
import logging
from typing import Optional, Callable, List

import numpy as np
from PIL import Image
from kivy import platform, Logger
from kivy.app import App as KivyApp
from kivy.clock import mainthread
from kivy.config import ConfigParser
from kivy.lang import Builder
from kivy.uix.settings import SettingsWithSpinner

from autopilot.tracking.detector.api import Detection
from drone.api.camera import Camera
from drone.api.drone import Drone
from drone.api.status import Status
from drone.registry import drone_connect_auto
from ui.controls import Controls
from ui.settings.registry import get_settings_meta, get_settings_defaults
from ui.util.monitor import setup_monitor
from ui.util.photo import save_image_to_pictures
# noinspection PyUnresolvedReferences
from util import androidhacks


class App(KivyApp, Controls):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Setup
        self.title = 'Drone Copilot'
        self.icon = '../assets/other/icon.png'
        self.kv_file = 'ui/app.kv'
        self.settings_cls = SettingsWithSpinner
        # Preload all KV files that are used by the app
        for kv_dep in sorted(glob.glob('ui/kv/*.kv')):
            Logger.info('DroneCopilotApp: Preloading KV file: {}'.format(kv_dep))
            Builder.load_file(kv_dep)
        # Events
        self.register_event_type('on_drone_connected')
        self.register_event_type('on_drone_status')
        self.register_event_type('on_drone_video_frame')
        self.register_event_type('on_drone_photo')
        self.register_event_type('on_drone_tracker_update')
        # Typing
        self._drone: Optional[Drone] = None
        self._listen_status_stop: Optional[Callable[[], None]] = None
        self._status_last_battery: float = -1.0
        self._listen_video_stop: Optional[Callable[[], None]] = None
        self._drone_cameras: Optional[List[Camera]] = None
        self._drone_camera: Optional[Camera] = None
        self._my_app_settings: Optional[SettingsWithSpinner] = None  # Cached settings

    # ==================== "boilerplate" ====================

    @property
    def name(self):
        return 'drone_copilot'  # No spaces, no special characters

    def on_config_change(self, *args):
        Logger.info('TODO: DroneCopilotApp: config changed: %s' % (args,))

    def build_settings(self, settings):
        for title, data in get_settings_meta().items():
            settings.add_json_panel(title, self.config, data=data)

    def build_config(self, config: ConfigParser):
        for k, v in get_settings_defaults().items():
            config.setdefaults(k, v)

    # ==================== LISTENERS & HANDLERS ====================
    def on_start(self):
        Logger.info('DroneCopilotApp: on_start()')

        if platform == 'android':
            androidhacks.setup()

        if Logger.isEnabledFor(logging.DEBUG):  # Can be configured from the settings UI or file!
            setup_monitor(self.root.ids.top_bar)

        # Start connecting to the drone
        # TODO: More interactive UI for initial connection

        @mainthread
        def on_connect_result(drone: Drone):
            if drone:
                self.dispatch('on_drone_connected', drone)
            else:
                self.root.ids.video.set_frame_text(  # TODO: Something nicer
                    'CONNECTION TO DRONE FAILED!\nRETRY BY RELOADING THE APP')

        self.root.ids.joystick_left.disabled = True
        self.root.ids.joystick_right.disabled = True
        self.root.ids.takeoff_land_button.disabled = True
        self.root.ids.tracking_button.disabled = True
        self.root.ids.video.set_frame_text('Connecting to the drone...')
        drone_connect_auto(self.config, on_connect_result)

    @mainthread
    def on_drone_connected(self, drone: Drone):
        self._drone = drone
        Logger.info('DroneCopilotApp: connected to drone!')
        # Update UI
        self.root.ids.takeoff_land_button.disabled = False
        self.root.ids.tracking_button.disabled = False
        self.root.ids.video.set_frame_text('Connecting to the drone\'s video feed...')
        # Listen for events
        self._listen_status_stop = self._drone.listen_status(lambda status: self.dispatch('on_drone_status', status))
        self.root.ids.tracker.bind(on_track=lambda *args: self.dispatch('on_drone_tracker_update', *args[1:]))
        # Connect to video camera (if available)
        self._drone_cameras = self._drone.cameras()
        if len(self._drone_cameras) > 0:
            self._drone_camera = self._drone_cameras[0]  # TODO: Configurable
            # TODO: Multi-camera views!
            resolution = self._drone_camera.resolutions_video[0] \
                if len(self._drone_camera.resolutions_video) > 0 else (640, 480)  # TODO: Configurable
            self._listen_video_stop = self._drone_camera.listen_video(
                resolution, lambda frame: self.dispatch('on_drone_video_frame', frame))
        else:
            self.root.ids.video.set_frame_text('No video feed available for this drone, :(')

    @mainthread
    def on_drone_status(self, drone_status: Status):
        # Logger.debug('DroneCopilotApp: STATUS: {}'.format(str(drone_status)))
        # BATTERY
        if self._status_last_battery != drone_status.battery:
            self._status_last_battery = drone_status.battery
            self.root.ids.battery_label.text = '{}%'.format(int(self._status_last_battery * 100))
            Logger.info('DroneCopilotApp: battery: {}%'.format(int(self._status_last_battery * 100)))
        # TEMPERATURE
        if len(drone_status.temperatures) > 0:
            cur_max_temp_c = max(drone_status.temperatures.values()) - 273.15  # Kelvin to Celsius.
            self.root.ids.temperature_label.text = '{:.1f}ºC'.format(cur_max_temp_c)  # TODO: Configure display units
        # SIGNAL
        self.root.ids.signal_label.text = str(int(drone_status.signal_strength * 100)) + '%'
        # HEIGHT
        self.root.ids.height_label.text = '{:.2f}m'.format(drone_status.height)
        # ENABLED UI ELEMENTS AND CONTENTS
        self.root.ids.joystick_left.disabled = not self._drone.status.flying
        self.root.ids.joystick_right.disabled = not self._drone.status.flying
        if self._drone.status.flying:
            self.root.ids.takeoff_land_button.text = 'Land'  # TODO: Icons?
        else:
            self.root.ids.takeoff_land_button.text = 'Takeoff'

    @mainthread
    def on_drone_video_frame(self, frame: np.ndarray):
        self.root.ids.video.update_texture(frame)
        if self.root.ids.tracker.is_running():  # Also update the tracker's frame, if it's running
            # AI algorithms actually want the image in height x width x channels format, not width x height x channels
            # TODO: why is this needed???! (test-only?)
            width, height, channels = frame.shape
            reshape = frame.ravel(order='K').reshape((height, width, channels))
            self.root.ids.tracker.feed(reshape)

    # noinspection PyMethodMayBeStatic
    def on_drone_photo(self, frame: np.ndarray):
        Logger.info('DroneCopilotApp: received photo frame')
        save_image_to_pictures(Image.fromarray(frame, 'RGB'), 'picture')

    def on_drone_tracker_update(self, detection: Optional[Detection], all_detections: List[Detection]):
        # Logger.info('DroneCopilotApp: received tracker results')
        pass

    def on_stop(self):
        Logger.info('DroneCopilotApp: on_stop()')
        if self._listen_status_stop:
            self._listen_status_stop()
        if self.root.ids.tracker.is_running():
            self.root.ids.tracker.stop()
        if self._listen_video_stop:
            self._listen_video_stop()
        if self._drone:
            del self._drone
        Logger.info('DroneCopilotApp: destroyed')

    # ==================== ACTIONS triggered by UI/keyboard/gamepad events ====================
    def action_joysticks(self, joystick_left_x: Optional[float], joystick_left_y: Optional[float],
                         joystick_right_x: Optional[float], joystick_right_y: Optional[float]):
        # Logger.debug('DroneCopilotApp: action_joysticks: {} {} {} {}'.format(
        #     joystick_left_x, joystick_left_y, joystick_right_x, joystick_right_y))

        if self._drone and self._drone.status.flying:
            # Update UI to show the current joystick values (only if they are enabled)
            if joystick_left_x is not None:
                self.root.ids.joystick_left.force_pad_x_pos(joystick_left_x)
            if joystick_left_y is not None:
                self.root.ids.joystick_left.force_pad_y_pos(joystick_left_y)
            if joystick_right_x is not None:
                self.root.ids.joystick_right.force_pad_x_pos(joystick_right_x)
            if joystick_right_y is not None:
                self.root.ids.joystick_right.force_pad_y_pos(joystick_right_y)

            # Actually apply them to the drone
            max_speed_m_per_s = 1.5  # TODO: Configurable
            target_speed_to_update = self._drone.target_speed
            if joystick_right_y is not None:
                target_speed_to_update.linear_local_x = joystick_right_y * max_speed_m_per_s
            if joystick_right_x is not None:
                target_speed_to_update.linear_local_y = joystick_right_x * max_speed_m_per_s
            if joystick_left_y is not None:
                target_speed_to_update.linear_local_z = -joystick_left_y * max_speed_m_per_s
            max_speed_angular = 1.0  # TODO: Configurable
            if joystick_left_x is not None:
                target_speed_to_update.yaw = joystick_left_x * max_speed_angular
            self._drone.target_speed = target_speed_to_update  # Actually update the target speed

    def action_takeoff_land(self):
        def action_callback(taking_off: bool, success: bool):
            Logger.info('DroneCopilotApp: action_takeoff_land callback: taking_off={}, success={}'.format(
                taking_off, success))

        # Logger.debug('DroneCopilotApp: action_takeoff_land')
        if self._drone:
            if self._drone.status.flying:  # Land
                self._drone.land(lambda success: action_callback(False, success))
            else:  # Take off
                self.root.ids.joystick_left.disabled = False  # Quickly (also automatic) allow control while taking off
                self.root.ids.joystick_right.disabled = False
                self._drone.takeoff(lambda success: action_callback(True, success))
        else:
            Logger.error('DroneCopilotApp: takeoff/land: no drone connected')

    def action_toggle_tracking(self, set_enabled: Optional[bool] = None):
        # Logger.debug('DroneCopilotApp: action_toggle_tracking: {}'.format(set_enabled))

        # Check if tracking is enabled
        was_enabled = self.root.ids.tracker.is_running()
        if set_enabled is None:
            set_enabled = not was_enabled
        elif set_enabled == was_enabled:
            return  # Nothing to do

        # Actually start/stop the tracking
        if set_enabled:
            self.root.ids.tracker.start()
        else:
            self.root.ids.tracker.stop()

        # Update the UI
        self.root.ids.tracking_button.text = 'Tracking (enabled)' if set_enabled else 'Tracking (disabled)'

    def action_take_photo(self):
        # Logger.debug('DroneCopilotApp: action_take_photo')
        if self._drone_camera:
            resolution = self._drone_camera.resolutions_photo[0] if len(self._drone_camera.resolutions_photo) > 0 else (
                640, 480)  # TODO: Configurable
            self._listen_video_stop = self._drone_camera.take_photo(
                resolution, lambda frame: self.dispatch('on_drone_photo', frame))
        else:
            # TODO: Unsupported photo message
            Logger.error('DroneCopilotApp: unsupported photo request')

    def action_toggle_settings(self, force_show: bool = False, menu: Optional[str] = None):
        # Logger.debug('DroneCopilotApp: action_toggle_settings')
        if not self._my_app_settings:
            self._my_app_settings = self.create_settings()
            self._my_app_settings.bind(on_close=lambda _ignore: self.action_toggle_settings())
        if menu:  # HACK: Access internal properties to set the settings panel menu
            self._my_app_settings.interface.menu.spinner.text = menu
        if self.root.ids.right_panel.size_hint_x == 0:  # Open the settings
            self.root.ids.right_panel.size_hint_x = 0.5  # TODO: Animation?
            self.root.ids.right_panel.add_widget(self._my_app_settings)
        else:  # Close the settings
            self.root.ids.right_panel.remove_widget(self._my_app_settings)
            self.root.ids.right_panel.size_hint_x = 0
            if force_show:
                self.action_toggle_settings()  # Call it again to open it properly

    def action_screenshot_app(self):
        # HACK: Screenshot code as default can't customize the file path properly!
        from kivy.graphics.opengl import glReadPixels, GL_RGB, GL_UNSIGNED_BYTE
        width, height = self.root_window.size
        data = glReadPixels(0, 0, width, height, GL_RGB, GL_UNSIGNED_BYTE)
        img = Image.frombuffer('RGB', (width, height), data).transpose(Image.FLIP_TOP_BOTTOM)
        save_image_to_pictures(img, 'screenshot')
