from kivy.properties import BooleanProperty

import joystick


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

    def force_pad_x_pos(self, x: float):
        self.ids.pad.center[0] = self.center[0] + x * self.size[0] / 2

    def force_pad_y_pos(self, y: float):
        self.ids.pad.center[1] = self.center[1] + y * self.size[1] / 2

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
