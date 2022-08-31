from kivy.lang import Builder
from kivy.properties import ListProperty, NumericProperty
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.label import Label


def _shadow_code(size='size'):
    return f'''
    canvas.before:
        Color:
            rgba: root.shadow_tint

        Rectangle:
            pos:
                int(self.center_x - self.{size}[0] / 2.),\
                int(self.center_y - self.{size}[1] / 2.)

            size: [d*self.shadow_scale for d in root.{size}]
            texture: root.texture

        Color:  # Reset color
            rgba: root.color
'''


Builder.load_string(f'''
<ShadowLabel>: {_shadow_code('texture_size')}
<ShadowButton>: {_shadow_code('texture_size')}
<ShadowImage>: {_shadow_code()}
''')


class ShadowLabel(Label):
    shadow_scale = NumericProperty(1.1)
    shadow_tint = ListProperty([0, 0, 0, 1])


class ShadowButton(Button, ShadowLabel):
    shadow_scale = NumericProperty(1.1)
    shadow_tint = ListProperty([0, 0, 0, 1])


class ShadowImage(Image):
    """NOTE: Does not keep aspect ratio!
    """
    shadow_scale = NumericProperty(1.025)
    shadow_tint = ListProperty([0, 0, 0, 1])
