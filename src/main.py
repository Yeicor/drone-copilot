__version__ = '0.8.0'

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
        import importlib

        # Help the app find resources stored in the PyInstaller bundle
        # noinspection PyProtectedMember
        resource_add_path(os.path.join(sys._MEIPASS))

        # Hide the splash screen
        if '_PYIBoot_SPLASH' in os.environ and importlib.util.find_spec("pyi_splash"):
            import pyi_splash

            pyi_splash.update_text('UI Loaded ...')
            pyi_splash.close()
            Logger.info('Splash screen closed.')

    # if is_production_build:
    #     # By default, increase log level and remove debugging widgets in production builds
    #     if Logger.isEnabledFor(logging.DEBUG):
    #         Logger.setLevel('INFO')

    # Start the main app or the testing sub-apps based on the command line arguments
    arg = sys.argv[1][0].lower() if len(sys.argv) > 1 else "m"  # Default to main app

    if arg == 'm':
        # ===> Start the App <===
        from app.main import App

        App().run()  # The main app

    elif arg == '3':
        # ===> Test rendering a virtual 3D scene <===
        from drone.test.renderer3d.main import Renderer3DTestApp

        Renderer3DTestApp().run()

    elif arg == 'w':
        # ===> Test object detection from webcam <===
        from autopilot.tracking.detector.webcamapp import WebcamDetectorApp

        WebcamDetectorApp().run()

    else:
        Logger.warning("The first argument is the app to run. Valid values are: m, 3, w (see main.py)")
