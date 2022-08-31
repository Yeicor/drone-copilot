import os

import numpy as np
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.floatlayout import FloatLayout

from drone.test.renderer3d.renderer import MySceneRenderer


class Renderer3DTestApp(App):

    def build(self):
        root_widget = FloatLayout()
        renderer = MySceneRenderer()
        root_widget.add_widget(renderer)
        renderer.queue_render(lambda: Clock.schedule_once(lambda _: print(
            'Non-zero pixels in the rendered frame:', np.count_nonzero(renderer.last_frame())), -1))
        return root_widget


if __name__ == '__main__':
    os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../..'))
    Renderer3DTestApp().run()
