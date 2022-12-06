import logging
from typing import Optional, Callable, List, Dict

import numpy as np
from PIL import Image
from kivy import platform, Logger
from kivy.app import App
from kivy.clock import mainthread
from kivy.config import ConfigParser
from kivy.core.window import Window, Keyboard
from kivy.modules import monitor
from kivy.uix.settings import SettingsWithSpinner

from drone.api.camera import Camera
from drone.api.drone import Drone
from drone.api.status import Status
from drone.registry import drone_connect_auto
from ui.settings.registry import get_settings_meta, get_settings_defaults
from ui.util.photo import save_image_to_pictures
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
        self.listen_video_stop: Optional[Callable[[], None]] = None
        self.drone_cameras: Optional[List[Camera]] = None
        self.drone_camera: Optional[Camera] = None

    # ==================== "boilerplate" ====================
    def build(self):
        if platform == 'android':
            androidhacks.setup()
        Window.bind(on_key_down=lambda *args: self.on_keyboard(*args, down=True),
                    on_key_up=lambda *args: self.on_keyboard(*(list(args) + [None, None]), down=False),
                    on_joy_axis=lambda *args: self.on_gamepad_axis(*args),
                    # Ignored (for now): on_joy_hat=lambda *args: self.on_gamepad_hat(*args),
                    # Ignored: on_joy_ball=lambda *args: self.on_gamepad_ball(*args),
                    on_joy_button_down=lambda *args: self.on_gamepad_press(*args, down=True),
                    on_joy_button_up=lambda *args: self.on_gamepad_press(*args, down=False))

        if Logger.isEnabledFor(logging.DEBUG):  # Can be configured from the settings UI or file!
            self.setup_monitor()

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

    def setup_monitor(self):
        app = self

        def monitor_x_offset():
            return Window.width * 1 / 4

        def update_stats_hack(win, ctx, *largs):
            ctx.stats = ctx.stats[1:] + [monitor._statsinput]
            monitor._statsinput = 0
            m = max(1., monitor._maxinput)
            for i, x in enumerate(ctx.stats):
                ctx.statsr[i].size = (4, ctx.stats[i] / m * 20)
                ctx.statsr[i].pos = (monitor_x_offset() + win.width - 64 * 4 + i * 4, win.height - 25)

        def _update_monitor_canvas_hack(win, ctx, *largs):
            with win.canvas.after:
                ctx.overlay.pos = (monitor_x_offset(), win.height - 25)
                ctx.overlay.size = (win.width, 25)
                ctx.rectangle.pos = (monitor_x_offset() + 5, win.height - 20)

        monitor.update_stats = update_stats_hack
        monitor._update_monitor_canvas = _update_monitor_canvas_hack

        class FakeWindow(object):
            def __init__(self):
                pass

            @property
            def width(self):
                return Window.width / 2

            @property
            def height(self):
                return Window.height

            @property
            def canvas(self):
                return app.root.ids.top_panel.canvas

            def bind(self, *args, **kwargs):
                return Window.bind(*args, **kwargs)

        monitor.start(FakeWindow(), self.root.ids.top_panel)
        _update_monitor_canvas_hack(FakeWindow(), self.root.ids.top_panel)

    # ==================== LISTENERS & HANDLERS ====================
    def on_start(self):
        # Start connecting to the drone
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
        # Logger.debug('DroneCopilotApp: STATUS: {}'.format(str(drone_status)))
        # BATTERY
        if self.status_last_battery != drone_status.battery:
            self.status_last_battery = drone_status.battery
            self.root.ids.battery_label.text = '{}%'.format(int(self.status_last_battery * 100))
            Logger.info('DroneCopilotApp: battery: {}%'.format(int(self.status_last_battery * 100)))
        # TEMPERATURE
        if len(drone_status.temperatures) > 0:
            cur_max_temp_c = max(drone_status.temperatures.values()) - 273.15  # Kelvin to Celsius.
            self.root.ids.temperature_label.text = '{:.1f}ºC'.format(cur_max_temp_c)  # TODO: Configure display units
        # SIGNAL
        self.root.ids.signal_label.text = str(int(drone_status.signal_strength * 100)) + '%'
        # HEIGHT
        self.root.ids.height_label.text = '{:.2f}m'.format(drone_status.height)
        # ENABLED UI ELEMENTS AND CONTENTS
        self.root.ids.joystick_left.disabled = not self.drone.status.flying
        self.root.ids.joystick_right.disabled = not self.drone.status.flying
        if self.drone.status.flying:
            self.root.ids.takeoff_land_button.text = 'Land'  # TODO: Icons?
        else:
            self.root.ids.takeoff_land_button.text = 'Takeoff'

    def on_drone_video_frame(self, frame: np.ndarray):
        self.root.ids.video.update_texture(frame)
        if self.root.ids.follower.is_running():  # Also update the follower's frame, if it's running
            # AI algorithms actually want the image in height x width x channels format, not width x height x channels
            # TODO: why is this needed???! (test-only?)
            width, height, channels = frame.shape
            reshape = frame.ravel(order='K').reshape((height, width, channels))
            self.root.ids.follower.feed(reshape)

    def on_drone_photo(self, frame: np.ndarray):
        Logger.info('DroneCopilotApp: received photo frame')
        save_image_to_pictures(Image.fromarray(frame, 'RGB'), 'picture')

    def on_stop(self):
        if self.listen_status_stop:
            self.listen_status_stop()
        if self.root.ids.follower.is_running():
            self.root.ids.follower.stop()
        if self.listen_video_stop:
            self.listen_video_stop()
        if self.drone:
            del self.drone
        Logger.info('DroneCopilotApp: destroyed')

    # ==================== KEYBOARD / GAMEPAD events (UI events are in the .kv file) ====================
    on_keyboard_already_pressed: Dict[int, bool] = {}

    # noinspection PyUnusedLocal
    def on_keyboard(self, window: any, key: int, scancode: int, codepoint: str, modifiers: List[any], down: bool):
        just_pressed = not self.on_keyboard_already_pressed.get(key, False) and down
        if down:
            self.on_keyboard_already_pressed[key] = True
        else:
            del self.on_keyboard_already_pressed[key]
        # Manage joysticks to control drone movements
        if just_pressed or not down:  # Less useless action_joysticks calls
            joystick_left_x = None  # keep by default
            joystick_left_y = None
            joystick_right_x = None
            joystick_right_y = None
            if key == Keyboard.keycodes['w'] and down:
                joystick_left_y = 1
            elif key == Keyboard.keycodes['s'] and down:
                joystick_left_y = -1
            elif (key == Keyboard.keycodes['w'] or key == Keyboard.keycodes['s']) and not down:
                joystick_left_y = 0
            if key == Keyboard.keycodes['a'] and down:
                joystick_left_x = -1
            elif key == Keyboard.keycodes['d'] and down:
                joystick_left_x = 1
            elif (key == Keyboard.keycodes['a'] or key == Keyboard.keycodes['d']) and not down:
                joystick_left_x = 0
            if key == Keyboard.keycodes['up'] and down:
                joystick_right_y = 1
            elif key == Keyboard.keycodes['down'] and down:
                joystick_right_y = -1
            elif (key == Keyboard.keycodes['up'] or key == Keyboard.keycodes['down']) and not down:
                joystick_right_y = 0
            if key == Keyboard.keycodes['left'] and down:
                joystick_right_x = -1
            elif key == Keyboard.keycodes['right'] and down:
                joystick_right_x = 1
            elif (key == Keyboard.keycodes['left'] or key == Keyboard.keycodes['right']) and not down:
                joystick_right_x = 0
            # FIXME: Normalize when 2 directions are enabled at the same time.
            if joystick_left_x is not None or joystick_left_y is not None or \
                    joystick_right_x is not None or joystick_right_y is not None:
                self.action_joysticks(joystick_left_x, joystick_left_y, joystick_right_x, joystick_right_y)
        # Manage takeoff/land shortcut
        if just_pressed and key == Keyboard.keycodes['spacebar']:
            self.action_takeoff_land()
        # Manage tracking shortcut
        if just_pressed and key == Keyboard.keycodes['t']:
            self.action_toggle_tracking()
        # Manage right panel shortcuts
        if just_pressed and key == Keyboard.keycodes['p']:
            self.action_take_photo()
        elif just_pressed and key == Keyboard.keycodes['o']:
            self.action_toggle_settings()
        # Undocumented extras
        if just_pressed and key == Keyboard.keycodes['f11']:
            self.action_screenshot_app()

    def on_gamepad_axis(self, window: any, gamepad: int, axis: int, value: int):
        # Logger.debug('DroneCopilotApp: on_gamepad_axis: {} -> {}'.format(axis, value))
        # NOTE: Only XBox 360 controller tested, use a virtual driver if the axis are not the same
        if axis == 0:  # Left stick X
            self.action_joysticks(value / 32768, None, None, None)
        elif axis == 1:  # Left stick Y
            self.action_joysticks(None, -value / 32768, None, None)
        elif axis == 3:  # Right stick X
            self.action_joysticks(None, None, value / 32768, None)
        elif axis == 4:  # Right stick Y
            self.action_joysticks(None, None, None, -value / 32768)

    def on_gamepad_press(self, window: any, gamepad: int, button: int, down: bool):
        # Logger.debug('DroneCopilotApp: on_gamepad_press: {}, {}, {}'.format(gamepad, button, down))
        if button == 3 and down:  # Y
            self.action_takeoff_land()
        elif button == 1 and down:  # B
            self.action_take_photo()

    # ==================== ACTIONS triggered by events ====================
    def action_joysticks(self, joystick_left_x: Optional[float], joystick_left_y: Optional[float],
                         joystick_right_x: Optional[float], joystick_right_y: Optional[float]):
        # Logger.debug('DroneCopilotApp: action_joysticks: {} {} {} {}'.format(
        #     joystick_left_x, joystick_left_y, joystick_right_x, joystick_right_y))

        if self.drone and self.drone.status.flying:
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
            target_speed_to_update = self.drone.target_speed
            if joystick_right_y is not None:
                target_speed_to_update.linear_local_x = joystick_right_y * max_speed_m_per_s
            if joystick_right_x is not None:
                target_speed_to_update.linear_local_y = joystick_right_x * max_speed_m_per_s
            if joystick_left_y is not None:
                target_speed_to_update.linear_local_z = -joystick_left_y * max_speed_m_per_s
            max_speed_angular = 0.5  # TODO: Configurable
            if joystick_left_x is not None:
                target_speed_to_update.yaw = joystick_left_x * max_speed_angular
            self.drone.target_speed = target_speed_to_update  # Actually update the target speed

    def action_takeoff_land(self):
        def action_callback(taking_off: bool, success: bool):
            Logger.info('DroneCopilotApp: action_takeoff_land callback: taking_off={}, success={}'.format(
                taking_off, success))

        # Logger.debug('DroneCopilotApp: action_takeoff_land')
        if self.drone:
            if self.drone.status.flying:  # Land
                self.drone.land(lambda success: action_callback(False, success))
            else:  # Take off
                self.root.ids.joystick_left.disabled = False  # Quickly (also automatic) allow control while taking off
                self.root.ids.joystick_right.disabled = False
                self.drone.takeoff(lambda success: action_callback(True, success))
        else:
            Logger.error('DroneCopilotApp: takeoff/land: no drone connected')

    def action_toggle_tracking(self, set_enabled: Optional[bool] = None):
        # Logger.debug('DroneCopilotApp: action_toggle_tracking: {}'.format(set_enabled))

        # Check if tracking is enabled
        was_enabled = self.root.ids.follower.is_running()
        if set_enabled is None:
            set_enabled = not was_enabled
        elif set_enabled == was_enabled:
            return  # Nothing to do

        # Actually start/stop the tracking
        if set_enabled:
            self.root.ids.follower.start()
        else:
            self.root.ids.follower.stop()

        # Update the UI
        self.root.ids.tracking_button.text = 'Tracking (enabled)' if set_enabled else 'Tracking (disabled)'

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

    def action_screenshot_app(self):
        # HACK: Screenshot code as default can't customize the file path properly!
        from kivy.graphics.opengl import glReadPixels, GL_RGB, GL_UNSIGNED_BYTE
        width, height = self.root_window.size
        data = glReadPixels(0, 0, width, height, GL_RGB, GL_UNSIGNED_BYTE)
        img = Image.frombuffer('RGB', (width, height), data).transpose(Image.FLIP_TOP_BOTTOM)
        save_image_to_pictures(img, 'screenshot')
