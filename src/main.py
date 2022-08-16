import os

import numpy as np
from kivy import Logger
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label

from model import TensorFlowModel
from video import Video

__version__ = '0.0.1'


class MyApp(App):

    def build(self):
        self.title = 'Tello Copilot'

        root = BoxLayout(orientation='vertical')

        root.add_widget(Video())

        # TensorsFlow demo
        start_time = Clock.time()
        model = TensorFlowModel()
        model.load(os.path.join(os.getcwd(), 'model.tflite'))
        Logger.info('TensorFlowModel load in ' + str(Clock.time() - start_time))
        np.random.seed(42)
        x = np.array(np.random.random_sample((1, 28, 28)), np.float32)
        y = model.pred(x)
        Logger.info('TensorFlowModel prediction in ' + str(Clock.time() - start_time))
        # result should be
        # 0.01647118,  1.0278152 , -0.7065112 , -1.0278157 ,  0.12216613,
        # 0.37980393,  0.5839217 , -0.04283606, -0.04240461, -0.58534086
        root.add_widget(Label(text=f'{y}', text_size=(None, 100)))

        return root


if __name__ == '__main__':
    MyApp().run()
