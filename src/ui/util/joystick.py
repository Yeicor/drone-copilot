import importlib

from kivy.properties import BooleanProperty

joystick = importlib.import_module("kivy-joystick")


class MyJoystick(joystick.Joystick):
    disabled = BooleanProperty(False)

    def __init__(self, **kwargs):
        super(MyJoystick, self).__init__(**kwargs)

    def on_disabled(self, *args):
        if self.disabled:
            self.default_pad_background_color = self.pad_background_color  # (copied)
            self.pad_background_color = [0.4, 0.1, 0.1, 1]
            self.center_pad()  # Reset to (0, 0)
        else:
            self.pad_background_color = self.default_pad_background_color
        self._update_pad()  # Update colors

    def on_touch_down(self, touch):
        if self.disabled:
            return
        return super(MyJoystick, self).on_touch_down(touch)

    def on_touch_move(self, touch):
        if self.disabled:
            return
        return super(MyJoystick, self).on_touch_move(touch)

    def on_touch_up(self, touch):
        if self.disabled:
            return
        return super(MyJoystick, self).on_touch_up(touch)
