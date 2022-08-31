import numpy as np
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.floatlayout import FloatLayout

from drone.test.renderer3d.renderer import MySceneRenderer


class TestApp(App):

    def build(self):
        root_widget = FloatLayout()
        renderer = MySceneRenderer()
        root_widget.add_widget(renderer)
        renderer.do_render()
        Clock.schedule_once(lambda _: print(np.count_nonzero(renderer.get_last_render_array())), 2.5)
        return root_widget


if __name__ == '__main__':
    TestApp().run()
