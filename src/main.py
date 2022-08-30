from kivy.utils import platform

from ui.app import DroneCopilotApp

__version__ = '0.1.0'
if __name__ == '__main__':
    if platform != 'android' and platform != 'ios':
        from kivy.config import Config

        # Dispose of that nasty red dot, required for gestures4kivy. TODO: Use gestures4kivy
        Config.set('input', 'mouse', 'mouse, disable_multitouch')

    DroneCopilotApp().run()
