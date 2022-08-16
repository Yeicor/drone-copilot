from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.utils import platform

from android_permissions import AndroidPermissions
from applayout import AppLayout

__version__ = '0.0.1'

if platform == 'android':
    from jnius import autoclass
    from android.runnable import run_on_ui_thread
    from android import mActivity

    View = autoclass('android.view.View')


    @run_on_ui_thread
    def hide_landscape_status_bar(instance, width, height):
        # width,height gives false layout events, on pinch/spread 
        # so use Window.width and Window.height
        if Window.width > Window.height:
            # Hide status bar
            option = View.SYSTEM_UI_FLAG_FULLSCREEN
        else:
            # Show status bar 
            option = View.SYSTEM_UI_FLAG_VISIBLE
        mActivity.getWindow().getDecorView().setSystemUiVisibility(option)
elif platform != 'ios':
    # Dispose of that nasty red dot, required for gestures4kivy.
    from kivy.config import Config

    Config.set('input', 'mouse', 'mouse, disable_multitouch')


class MyApp(App):

    def build(self):
        self.started = False
        if platform == 'android':
            Window.bind(on_resize=hide_landscape_status_bar)
        self.layout = AppLayout()
        return self.layout

    def on_start(self):
        self.dont_gc = AndroidPermissions(self.start_app)

    def start_app(self):
        self.dont_gc = None
        # Can't connect camera till after on_start()
        Clock.schedule_once(self.connect_camera)

    def connect_camera(self, dt):
        self.layout.detect.connect_camera(enable_analyze_pixels=True)

    def on_stop(self):
        self.layout.detect.disconnect_camera()


if __name__ == '__main__':
    MyApp().run()
