import os
import sys

from kivy.resources import resource_add_path
from kivy.utils import platform

from ui.app import DroneCopilotApp

__version__ = '0.2.4'

if __name__ == '__main__':
    if platform != 'android' and platform != 'ios':
        from kivy.config import Config

        # Dispose of that nasty red dot, required for gestures4kivy. TODO: Use gestures4kivy
        Config.set('input', 'mouse', 'mouse, disable_multitouch')

    if hasattr(sys, '_MEIPASS'):  # PyInstaller
        resource_add_path(os.path.join(sys._MEIPASS))
        # Help PyInstaller find the data files
        from ui.video.video import MyVideo
        from ui.util.joystick import MyJoystick
        _ignore1 = MyVideo
        _ignore2 = MyJoystick
        # TODO: add more imports here (rename kivy-joystick to a valid name!)

    DroneCopilotApp().run()  # The main app
    # Renderer3DTestApp().run()  # Test rendering a virtual 3D scene
