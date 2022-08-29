from kivy.lang import Builder
from kivy.properties import ListProperty, NumericProperty
from kivy.uix.button import Button
from kivy.uix.label import Label

Builder.load_string('''
<ShadowLabel>:
    canvas.before:
        Color:
            rgba: root.shadow_tint

        Rectangle:
            pos:
                int(self.center_x - self.texture_size[0] / 2.),\
                int(self.center_y - self.texture_size[1] / 2.)

            size: [d*self.shadow_scale for d in root.texture_size]
            texture: root.texture

        Color:  # Reset color
            rgba: root.color

<ShadowButton>:
    canvas.before:
        Color:
            rgba: root.shadow_tint

        Rectangle:
            pos:
                int(self.center_x - self.texture_size[0] / 2.),\
                int(self.center_y - self.texture_size[1] / 2.)

            size: [d*self.shadow_scale for d in root.texture_size]
            texture: root.texture

        Color:  # Reset color
            rgba: root.color
''')


class ShadowLabel(Label):
    shadow_scale = NumericProperty(1.1)
    shadow_tint = ListProperty([0, 0, 0, 1])


class ShadowButton(Button, ShadowLabel):
    shadow_scale = NumericProperty(1.1)
    shadow_tint = ListProperty([0, 0, 0, 1])
