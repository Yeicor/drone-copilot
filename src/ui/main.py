from typing import Optional, Callable, List

import numpy as np
from PIL import Image
from kivy import platform, Logger
from kivy.app import App as KivyApp
from kivy.config import ConfigParser
from kivy.uix.settings import SettingsWithSpinner, Settings

from autopilot.tracking.detector.api import Detection
from drone.api.camera import Camera
from drone.api.drone import Drone
from drone.api.status import Status
from drone.registry import drone_connect_auto
from ui.app.ui import AppUI
from ui.settings.registry import get_settings_meta, get_settings_defaults
from ui.util.photo import save_image_to_pictures
from ui.video.tracker import Tracker
from util.androidhacks import setup as androidhacks_setup


class App(KivyApp, AppUI):
    """Contains the core logic of the Drone Copilot application, leaving UI and controls to superclasses."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Setup
        self.title = 'Drone Copilot'
        self.icon = 'assets/other/icon.png'
        self.settings_cls = SettingsWithSpinner
        # Events
        self.register_event_type('on_drone_connected')
        self.register_event_type('on_drone_status')
        self.register_event_type('on_drone_video_frame')
        self.register_event_type('on_drone_photo')
        self.register_event_type('on_drone_tracker_update')
        # Types
        self._drone: Optional[Drone] = None
        self._tracker: Optional[Tracker] = None
        self._listen_status_stop: Optional[Callable[[], None]] = None
        self._listen_video_stop: Optional[Callable[[], None]] = None
        self._drone_cameras: Optional[List[Camera]] = None
        self._drone_camera: Optional[Camera] = None
        self._my_app_settings: Optional[SettingsWithSpinner] = None  # Cached settings

    # ==================== "boilerplate" ====================

    @property
    def name(self):
        return 'drone_copilot'  # No spaces, no special characters

    def build_settings(self, settings):
        for title, data in get_settings_meta().items():
            settings.add_json_panel(title, self.config, data=data)

    def build_config(self, config: ConfigParser):
        for k, v in get_settings_defaults().items():
            config.setdefaults(k, v)

    def on_config_change(self, *args):
        Logger.info('DroneCopilotApp: TODO: config changed: %s' % (args,))

    def load_kv(self, filename=None):
        # Use AppUI to load the root widget, instead of KivyApp
        Logger.info('DroneCopilotApp: load_kv()')
        self.root = self.ui_build()
        return True

    # ==================== UI method implementations ====================

    def ui_get_or_create_settings(self) -> (Settings, bool):
        created = False
        if not self._my_app_settings:
            self._my_app_settings = self.create_settings()
            created = True
        return self._my_app_settings, created

    @property
    def ui_scale(self) -> float:
        return float(self.config.get('ui', 'scale'))

    @property
    def ui_opacity(self) -> float:
        return float(self.config.get('ui', 'opacity'))

    # ==================== LISTENERS & HANDLERS ====================
    def on_start(self):
        AppUI.on_start(self)  # Call the parent method
        Logger.info('DroneCopilotApp: on_start()')

        # UI Shortcuts
        self._tracker = self.ui_el('tracker')

        if platform == 'android':
            androidhacks_setup()

        # Start connecting to the drone
        # TODO: More interactive UI for initial connection
        drone_connect_auto(self.config, lambda drone: AppUI.on_drone_connect_result(self, drone) or (
            self.dispatch('on_drone_connected', drone) if drone else None))

    def on_drone_connected(self, drone: Drone):
        AppUI.on_drone_connected(self, drone)  # Call the parent method
        Logger.info('DroneCopilotApp: on_drone_connected()')
        self._drone = drone

        # Start listening for events
        self._listen_status_stop = self._drone.listen_status(lambda status: self.dispatch('on_drone_status', status))
        self._tracker.bind(on_track=lambda *args: self.dispatch('on_drone_tracker_update', *args[1:]))

        # Connect to video camera (if available)
        self._drone_cameras = self._drone.cameras()
        if len(self._drone_cameras) > 0:
            self._drone_camera = self._drone_cameras[0]  # TODO: Configurable
            # TODO: Multi-camera views!
            resolution = self._drone_camera.resolutions_video[0] \
                if len(self._drone_camera.resolutions_video) > 0 else (640, 480)  # TODO: Configurable
            self._listen_video_stop = self._drone_camera.listen_video(
                resolution, lambda frame: self.dispatch('on_drone_video_frame', frame))

    def on_drone_status(self, drone_status: Status):
        AppUI.on_drone_status(self, drone_status)  # Call the parent method
        # Logger.info('DroneCopilotApp: on_drone_status(%s)' % drone_status)

    def on_drone_video_frame(self, frame: np.ndarray):
        AppUI.on_drone_video_frame(self, frame)  # Call the parent method
        # Logger.info('DroneCopilotApp: on_drone_video_frame(%s)' % frame)
        if self._tracker.is_running():  # Also update the tracker's frame, if it's running
            # AI algorithms actually want the image in height x width x channels format, not width x height x channels
            # TODO: why is this needed???! (test-only?)
            width, height, channels = frame.shape
            reshape = frame.ravel(order='K').reshape((height, width, channels))
            self._tracker.feed(reshape)

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
        if self._tracker.is_running():
            self._tracker.stop()
        if self._listen_video_stop:
            self._listen_video_stop()
        if self._drone:
            del self._drone
        Logger.info('DroneCopilotApp: destroyed')

    # ==================== ACTIONS triggered by UI/keyboard/gamepad events ====================
    def action_joysticks(self, joystick_left_x: Optional[float], joystick_left_y: Optional[float],
                         joystick_right_x: Optional[float], joystick_right_y: Optional[float]):
        AppUI.action_joysticks(self, joystick_left_x, joystick_left_y, joystick_right_x, joystick_right_y)
        # Logger.debug('DroneCopilotApp: action_joysticks: {} {} {} {}'.format(
        #     joystick_left_x, joystick_left_y, joystick_right_x, joystick_right_y))

        if self._drone and self._drone.status.flying:
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
                self.ui_on_takeoff_request()
                self._drone.takeoff(lambda success: action_callback(True, success))
        else:
            Logger.error('DroneCopilotApp: takeoff/land: no drone connected')

    def action_toggle_tracking(self, set_enabled: Optional[bool] = None):
        # Logger.debug('DroneCopilotApp: action_toggle_tracking: {}'.format(set_enabled))

        # Check if tracking is enabled
        was_enabled = self._tracker.is_running()
        if set_enabled is None:
            set_enabled = not was_enabled
        elif set_enabled == was_enabled:
            return  # Nothing to do

        # Actually start/stop the tracking
        if set_enabled:
            self._tracker.start()
        else:
            self._tracker.stop()

        # Update the UI
        AppUI.action_toggle_tracking_result(self, set_enabled)

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
