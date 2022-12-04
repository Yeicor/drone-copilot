__version__ = '0.3.11'

if __name__ == '__main__':
    import os
    import sys

    from kivy.resources import resource_add_path
    from kivy.utils import platform

    if platform != 'android' and platform != 'ios':
        from kivy.config import Config

        # Dispose of that nasty red dot, required for gestures4kivy. TODO: Use gestures4kivy
        Config.set('input', 'mouse', 'mouse, disable_multitouch')

    if hasattr(sys, '_MEIPASS'):  # PyInstaller
        resource_add_path(os.path.join(sys._MEIPASS))
        # Help PyInstaller find the data files
        from ui.video.video import MyVideo
        from ui.util.joystick import MyJoystick
        from ui.util.shadow import *

        _ignore1 = MyVideo
        _ignore2 = MyJoystick
        _ignore3 = ShadowLabel

    # ===> Start the App <===
    #
    # from ui.app import DroneCopilotApp
    #
    # DroneCopilotApp().run()  # The main app

    # ===> Test rendering a virtual 3D scene <===
    #
    # from drone.app import DroneCopilotApp
    #
    # Renderer3DTestApp().run()

    # ===> Test object detection from webcam <===
    #
    from autopilot.detector.webcam import WebcamDetectorApp

    WebcamDetectorApp().run()
