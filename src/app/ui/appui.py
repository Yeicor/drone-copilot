import glob
import logging
from abc import abstractmethod
from typing import Optional

import numpy as np
from PIL import Image
from kivy import Logger
from kivy.app import App
from kivy.clock import Clock, ClockEvent, mainthread
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.uix.settings import Settings
from kivy.uix.widget import Widget

from app.settings.manager import SettingsManager
from app.settings.settings import SettingMetaNumeric
from app.ui.controls import Controls
from app.util.monitor import setup_monitor
from app.util.photo import save_image_to_pictures
from drone.api.drone import Drone
from drone.api.status import Status
from util.filesystem import source


class AppUI(Controls):
    """Manages the main UI of the app, easing its interaction with the logic.

    The main app is expected to inherit from this class, and implement the abstract methods.
    """
    _ui_el_root: Optional[Widget] = None
    _ui_drone: Optional[Drone] = None
    _ui_status_last_battery: float = -1.0
    _ui_resizing: Optional[ClockEvent] = None

    def __init__(self):
        super().__init__()
        # Dynamically resize the UI when the window is resized or the scale is changed
        Window.bind(on_resize=lambda _dt, width, height: self.ui_on_resize(width, height))
        # Settings
        Logger.info('AppUI: UI settings...')
        settings = SettingsManager.instance()
        self.section_name = 'UI'
        settings[self.section_name] = [
            SettingMetaNumeric.create('Scale', 'The scale multiplier of the UI elements', 1.0),
            SettingMetaNumeric.create('Opacity', 'The opacity multiplier of the UI elements', 1.0)
        ]
        settings[self.section_name][0].bind(
            self.section_name, lambda _val: self.ui_on_resize(Window.width, Window.height), False)
        # TODO: Also listen to opacity changes (how to update the UI?)

    @abstractmethod
    def ui_get_or_create_settings(self) -> (Settings, bool):
        """Returns the settings UI of the app, and a boolean indicating whether the settings have just been created."""
        raise NotImplementedError()

    @property
    def ui_scale(self) -> float:
        """The scale of the UI elements."""
        return float(App.get_running_app().config.get(self.section_name, 'scale'))

    @property
    def ui_opacity(self) -> float:
        """The opacity of the UI elements."""
        return float(App.get_running_app().config.get(self.section_name, 'opacity'))

    def ui_build(self) -> Widget:
        """Builds the UI from the source KV files. The returned widget is expected to be the root of the app.

        :return: The root widget of the UI."""
        if self._ui_el_root is not None:
            Logger.warning('AppUI: UI already built.')
            return self._ui_el_root

        # Import the modules, which are classes that represent a part of the UI.
        import app.ui.modules
        _ = app.ui.modules.BottomBar

        # Preload all KV files that are used by the app
        for kv_dep in sorted(glob.glob(source('app', 'ui', 'kv', '**.kv'))):
            Logger.info('AppUI: Preloading KV file: {}'.format(kv_dep))
            Builder.load_file(kv_dep)

        # Load the root widget of the app
        Logger.info('AppUI: Loading main file')
        self._ui_el_root = Builder.load_file(source('app', 'ui', 'appui.kv'))
        Logger.info('AppUI: Main file loaded: %s' % self._ui_el_root)

        # Provide dynamic access (recursively, flattening) to all named widgets in the UI (ui_el_<id> or ui_el(<id>)).
        self._provide_ui_el_access(self._ui_el_root)

        return self._ui_el_root

    def _provide_ui_el_access(self, el: Widget):
        to_process = [el]
        while len(to_process) > 0:
            widget = to_process.pop()
            for name, child in widget.ids.items():
                Logger.debug('AppUI: Found named widget: %s' % name)
                setattr(self, 'ui_el_' + name, child)
                to_process.append(child)

    def ui_el(self, _id: str, _property: Optional[str] = None, _default: any = None) -> Widget:
        """Returns the widget with the given id (or its property if given), or default.

        :param _id: The id of the widget.
        :param _property: The property of the widget to return.
        :param _default: The default value to return if either is set and not found.
        :return: The widget with the given name, or None if not found.
        """
        widget = getattr(self, 'ui_el_' + _id, None)
        if widget is None:
            Logger.warning('AppUI: Widget not found (ok during startup): {}'.format(_id))
            return _default
        if _property is None:
            return widget
        return getattr(widget, _property, _default)

    # ==================================== EVENT HANDLERS ====================================

    @mainthread
    def on_start(self):
        """Called when the app starts."""
        Logger.info('AppUI: on_start()')

        # Make sure that all UI elements are properly in place (solve interdependencies by refreshing layouts)
        self._ui_force_refresh_layouts(1)

        # Enable the performance graph if we are in debug mode
        if Logger.isEnabledFor(logging.DEBUG):  # Can be configured from the settings UI or file!
            setup_monitor(self.ui_el('top_bar'))

        # Before connection: disable most of the UI
        self.ui_el('joystick_left').disabled = True
        self.ui_el('joystick_right').disabled = True
        self.ui_el('takeoff_land_button').disabled = True
        self.ui_el('tracking_button').disabled = True
        self.ui_el('video').set_frame_text('Connecting to the drone...')

    def ui_on_takeoff_request(self):
        """Called when the user requests to takeoff."""
        self.ui_el('joystick_left').disabled = False  # Quickly (also automatic) allow control while taking off
        self.ui_el('joystick_right').disabled = False

    @mainthread
    def _ui_force_refresh_layouts(self, n: int):
        """Forces the UI to re-layout its elements."""
        tmp_widget = Widget(size_hint=(None, None), size=(1, 1))  # Add a temporary widget to force a layout refresh

        def reset_window_size(_ignored):
            self._ui_el_root.remove_widget(tmp_widget)
            if n > 1:  # Recursively refresh layouts until we are done
                Clock.schedule_once(lambda _ignored: self._ui_force_refresh_layouts(n - 1), 0.1)

        self._ui_el_root.add_widget(tmp_widget)
        Clock.schedule_once(reset_window_size, 0)  # Schedule after the current frame

    def ui_on_resize(self, width: int, height: int):
        # After a window resize (including at startup), we need to re-layout the UI elements (to solve internal refs)
        # We use a scheduled event to avoid doing it too often
        if self._ui_resizing is not None:
            self._ui_resizing.cancel()
        self._ui_resizing = Clock.schedule_once(lambda _ignored: self._ui_on_resize(width, height), 0.25)

    def _ui_on_resize(self, width: int, height: int):
        Logger.info('AppUI: Window resized: {}x{}, relocating widgets...'.format(width, height))
        self._ui_resizing = None
        self._ui_force_refresh_layouts(1)

    @mainthread
    def on_drone_connect_result(self, drone: Optional[Drone]):
        self._ui_drone = drone
        if not self._ui_drone:
            self.ui_el('video').set_frame_text(  # TODO: Something nicer
                'CONNECTION TO DRONE FAILED!\nRETRY BY RELOADING THE APP')

    @mainthread
    def on_drone_connected(self, drone: Drone):
        """Called when the drone is connected."""
        Logger.info('AppUI: on_drone_connected()')
        self.ui_el('takeoff_land_button').disabled = False
        self.ui_el('tracking_button').disabled = False

        if len(self._ui_drone.cameras()) > 0:
            self.ui_el('video').set_frame_text('Connecting video...')
        else:
            self.ui_el('video').set_frame_text('No video available')

    @mainthread
    def on_drone_status(self, drone_status: Status):
        # BATTERY
        if self._ui_status_last_battery != drone_status.battery:
            self._ui_status_last_battery = drone_status.battery
            self.ui_el('battery_label').text = '{}%'.format(int(self._ui_status_last_battery * 100))
            Logger.info('DroneCopilotApp: battery: {}%'.format(int(self._ui_status_last_battery * 100)))
        # TEMPERATURE
        if len(drone_status.temperatures) > 0:
            cur_max_temp_c = max(drone_status.temperatures.values()) - 273.15  # Kelvin to Celsius.
            self.ui_el('temperature_label').text = '{:.1f}ºC'.format(cur_max_temp_c)  # TODO: Configure display units
        # SIGNAL
        self.ui_el('signal_label').text = str(int(drone_status.signal_strength * 100)) + '%'
        # HEIGHT
        self.ui_el('height_label').text = '{:.2f}m'.format(drone_status.height)
        # ENABLED UI ELEMENTS AND CONTENTS
        self.ui_el('joystick_left').disabled = not self._ui_drone.status.flying
        self.ui_el('joystick_right').disabled = not self._ui_drone.status.flying
        if self._ui_drone.status.flying:
            self.ui_el('takeoff_land_button').background_color = (1, 1, 0, 1)
            self.ui_el('takeoff_land_button').text = 'Land'  # TODO: Icons?
        else:
            self.ui_el('takeoff_land_button').background_color = (1, 1, 1, 1)
            self.ui_el('takeoff_land_button').text = 'Takeoff'

    @mainthread
    def on_drone_video_frame(self, frame: np.ndarray):
        self.ui_el('video').update_texture(frame)

    @mainthread
    def action_joysticks(self, joystick_left_x: Optional[float], joystick_left_y: Optional[float],
                         joystick_right_x: Optional[float], joystick_right_y: Optional[float]):
        # Update UI to show the current joystick values (only if they are enabled)
        if not self.ui_el('joystick_left').disabled:
            if joystick_left_x is not None:
                self.ui_el('joystick_left').force_pad_x_pos(joystick_left_x)
            if joystick_left_y is not None:
                self.ui_el('joystick_left').force_pad_y_pos(joystick_left_y)
        if not self.ui_el('joystick_right').disabled:
            if joystick_right_x is not None:
                self.ui_el('joystick_right').force_pad_x_pos(joystick_right_x)
            if joystick_right_y is not None:
                self.ui_el('joystick_right').force_pad_y_pos(joystick_right_y)

    def action_toggle_tracking_result(self, now_enabled: bool):
        self.ui_el('tracking_button').background_color = (0, 1, 0, 1) if now_enabled else (1, 1, 1, 1)

    def cur_settings_menu(self) -> Optional[str]:
        settings, just_created = self.ui_get_or_create_settings(can_create=False)
        return settings.interface.menu.spinner.text if settings else None

    @mainthread
    def action_toggle_settings(self, force: Optional[bool] = None, menu: Optional[str] = None):
        Logger.debug('AppUI: action_toggle_settings()')
        settings, just_created = self.ui_get_or_create_settings()
        if just_created:
            # TODO: Automatically add sliders to the interface after each int/float setting with min & max values
            settings.interface.bind(on_close=lambda *_args: self.action_toggle_settings(False))
        if menu:  # HACK: Access internal properties to set the settings panel menu
            settings.interface.menu.spinner.text = menu
        if self.ui_el('right_panel').size_hint_x == 0 or force is True:  # Open the settings
            self.ui_el('right_panel').size_hint_x = 0.5  # TODO: Animation?
            self.ui_el('right_panel').clear_widgets()
            self.ui_el('right_panel').add_widget(settings)
        elif self.ui_el('right_panel').size_hint_x > 0 or force is False:  # Close the settings
            self.ui_el('right_panel').remove_widget(settings)
            self.ui_el('right_panel').size_hint_x = 0

    def action_screenshot_app(self):
        Logger.debug('AppUI: action_screenshot_app()')
        # HACK: Screenshot code as default can't customize the file path properly!
        from kivy.graphics.opengl import glReadPixels, GL_RGB, GL_UNSIGNED_BYTE
        width, height = Window.size
        data = glReadPixels(0, 0, width, height, GL_RGB, GL_UNSIGNED_BYTE)
        img = Image.frombuffer('RGB', (width, height), data).transpose(Image.FLIP_TOP_BOTTOM)
        save_image_to_pictures(img, 'screenshot')
