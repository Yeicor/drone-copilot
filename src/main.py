__version__ = '0.5.8'

if __name__ == '__main__':
    import os
    import sys

    from kivy import Logger
    from kivy.utils import platform

    # Identify the build type
    is_pyinstaller_build = hasattr(sys, '_MEIPASS')
    is_mobile_build = platform in ('android', 'ios')
    is_production_build = is_pyinstaller_build or is_mobile_build

    if not is_mobile_build:
        from kivy.config import Config

        # Dispose of that nasty red dot, required for gestures4kivy. TODO: Use gestures4kivy
        Config.set('input', 'mouse', 'mouse, disable_multitouch')

    if is_pyinstaller_build:  # PyInstaller
        from kivy.resources import resource_add_path

        # Help the app find resources stored in the PyInstaller bundle
        # noinspection PyProtectedMember
        resource_add_path(os.path.join(sys._MEIPASS))

        # Help PyInstaller bundle dynamically loaded python modules
        from ui.video.video import MyVideo
        from ui.video.tracker import DefaultTracker
        from ui.util.joystick import MyJoystick
        from ui.util.shadow import *

        _ignore1 = MyVideo
        _ignore2 = DefaultTracker
        _ignore3 = MyJoystick
        _ignore4 = ShadowLabel

    if is_production_build:
        # By default, increase log level and remove debugging widgets in production builds (mobile is always production)
        if Logger.getEffectiveLevel() == 10:  # DEBUG
            Logger.setLevel('INFO')

    # ===> Start the App <===
    #
    from ui.app import App

    App().run()  # The main app

    # ===> Test rendering a virtual 3D scene <===
    #
    # from drone.app import DroneCopilotApp
    #
    # Renderer3DTestApp().run()

    # ===> Test object detection from webcam <===
    #
    # from autopilot.tracking.detector.webcam import WebcamDetectorApp
    #
    # WebcamDetectorApp().run()
