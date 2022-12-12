import numpy as np
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout

from drone.test.renderer3d.renderer import MySceneRenderer


class Renderer3DTestApp(App):

    def build(self):
        root_widget = FloatLayout()
        renderer = MySceneRenderer()
        root_widget.add_widget(renderer)
        renderer.queue_render(lambda: print('Non-zero pixels in the rendered frame:',
                                            np.count_nonzero(renderer.last_frame())))
        return root_widget


if __name__ == '__main__':
    Renderer3DTestApp().run()
