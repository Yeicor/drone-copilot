import abc
from typing import Dict, Optional, List

from kivy.core.window import Keyboard, Window


class Controls(abc.ABC):
    """
    Class for handling the keybindings and gamepad bindings for the app. Note that UI bindings are in the .kv files.
    """

    def __init__(self):
        # Bind all listeners that call parsed actions
        Window.bind(on_key_down=lambda *args: self.on_keyboard(*args, down=True),
                    on_key_up=lambda *args: self.on_keyboard(*(list(args) + [None, None]), down=False),
                    on_joy_axis=lambda *args: self.on_gamepad_axis(*args),
                    # Ignored (for now): on_joy_hat=lambda *args: self.on_gamepad_hat(*args),
                    # Ignored: on_joy_ball=lambda *args: self.on_gamepad_ball(*args),
                    on_joy_button_down=lambda *args: self.on_gamepad_press(*args, down=True),
                    on_joy_button_up=lambda *args: self.on_gamepad_press(*args, down=False))

    # ==================== KEYBOARD / GAMEPAD events (UI events are in the .kv file) ====================
    keyboard_down: Dict[int, bool] = {}

    def on_keyboard(self, _window: any, key: int, _scancode: int, _codepoint: str, _modifiers: List[any], down: bool):
        just_pressed = not self.keyboard_down.get(key, False) and down
        just_released = not down and key in self.keyboard_down
        if down:
            self.keyboard_down[key] = True
        elif key in self.keyboard_down:
            del self.keyboard_down[key]
        # Manage joysticks to control drone movements (only if any change has just been made)
        if just_pressed or just_released:
            joystick_left_x = None  # keep previous value by default
            joystick_left_y = None
            joystick_right_x = None
            joystick_right_y = None
            if key == Keyboard.keycodes['w']:
                joystick_left_y = 1 if down else 0
            elif key == Keyboard.keycodes['s']:
                joystick_left_y = -1 if down else 0
            if key == Keyboard.keycodes['a']:
                joystick_left_x = -1 if down else 0
            elif key == Keyboard.keycodes['d']:
                joystick_left_x = 1 if down else 0
            if key == Keyboard.keycodes['up']:
                joystick_right_y = 1 if down else 0
            elif key == Keyboard.keycodes['down']:
                joystick_right_y = -1 if down else 0
            if key == Keyboard.keycodes['left']:
                joystick_right_x = -1 if down else 0
            elif key == Keyboard.keycodes['right']:
                joystick_right_x = 1 if down else 0
            # Call the action if any joystick has changed
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

    def on_gamepad_axis(self, _window: any, _gamepad: int, axis: int, value: int):
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

    gamepad_down: Dict[int, bool] = {}

    def on_gamepad_press(self, _window: any, _gamepad: int, button: int, down: bool):
        # Logger.debug('DroneCopilotApp: on_gamepad_press: {}, {}, {}'.format(_gamepad, button, down))
        # NOTE: Only XBox 360 controller tested, use a virtual driver if the axis are not the same
        just_pressed = not self.gamepad_down.get(button, False) and down
        if down:
            self.gamepad_down[button] = True
        elif button in self.gamepad_down:
            del self.gamepad_down[button]
        # Trigger actions
        if just_pressed:
            if button == 0:  # A
                self.action_takeoff_land()
            elif button == 1:  # B
                self.action_take_photo()
            elif button == 3:  # Y
                self.action_toggle_tracking()

    # ==================== ACTIONS that should be implemented by subclasses ====================
    @abc.abstractmethod
    def action_joysticks(self, joystick_left_x: Optional[float], joystick_left_y: Optional[float],
                         joystick_right_x: Optional[float], joystick_right_y: Optional[float]):
        """
        Called when the "joysticks" are moved.
        :param joystick_left_x: The X axis of the left joystick, from -1 to 1 (None if not changed).
        :param joystick_left_y: The Y axis of the left joystick, from -1 to 1 (None if not changed).
        :param joystick_right_x: The X axis of the right joystick, from -1 to 1 (None if not changed).
        :param joystick_right_y: The Y axis of the right joystick, from -1 to 1 (None if not changed).
        :return: None
        """
        pass

    def action_takeoff_land(self):
        """
        Called when the takeoff/land action is triggered.
        :return: None
        """
        pass

    def action_toggle_tracking(self, set_enabled: Optional[bool] = None):
        """
        Called when the tracking action is triggered.
        :param set_enabled: If set, force the tracking to be enabled or disabled.
        :return: None
        """
        pass

    def action_take_photo(self):
        """
        Called when the take photo action is triggered.
        :return: None
        """
        pass

    def action_toggle_settings(self, force: Optional[bool] = None, menu: Optional[str] = None):
        """
        Called when the settings action is triggered.
        :param force: If set, force the settings to be shown or hidden.
        :param menu: If set, force the settings to be on this menu.
        :return: None
        """
        pass

    def action_screenshot_app(self):
        """
        Called when the app screenshot action is triggered.
        :return: None
        """
        pass
