from kivy.app import App
from kivy.core.window import Window
from kivy.utils import platform

# from android_permissions import AndroidPermissions
# from applayout import AppLayout

__version__ = '0.0.1'

from videoopencv import VideoOpenCV

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
    from kivy.config import Config

    # Dispose of that nasty red dot, required for gestures4kivy.
    Config.set('input', 'mouse', 'mouse, disable_multitouch')


class MyApp(App):

    def build(self):
        self.title = 'Tello Copilot'
        if platform == 'android':
            Window.bind(on_resize=hide_landscape_status_bar)
        return VideoOpenCV()


if __name__ == '__main__':
    MyApp().run()
