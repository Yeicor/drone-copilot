"""
A FPS / frame time monitor, for debugging purposes.
"""
from kivy.core.window import Window
from kivy.modules import monitor
from kivy.uix.widget import Widget


def setup_monitor(parent_widget: Widget):
    def monitor_x_offset():
        return Window.width * 1 / 4

    # noinspection PyProtectedMember
    def update_stats_hack(win, ctx, _ignored):
        ctx.stats = ctx.stats[1:] + [monitor._statsinput]
        monitor._statsinput = 0
        m = max(1., monitor._maxinput)
        for i, x in enumerate(ctx.stats):
            ctx.statsr[i].size = (4, ctx.stats[i] / m * 20)
            ctx.statsr[i].pos = (monitor_x_offset() + win.width - 64 * 4 + i * 4, win.height - 25)

    def _update_monitor_canvas_hack(win, ctx, *_args):
        with win.canvas.after:
            ctx.overlay.pos = (monitor_x_offset(), win.height - 25)
            ctx.overlay.size = (win.width, 25)
            ctx.rectangle.pos = (monitor_x_offset() + 5, win.height - 20)

    monitor.update_stats = update_stats_hack
    monitor._update_monitor_canvas = _update_monitor_canvas_hack

    class FakeWindow(object):
        def __init__(self):
            pass

        @property
        def width(self):
            return Window.width / 2

        @property
        def height(self):
            return Window.height

        @property
        def canvas(self):
            return parent_widget.canvas

        def bind(self, *args, **kwargs):
            return Window.bind(*args, **kwargs)

    monitor.start(FakeWindow(), parent_widget)

    # Do an initial call to the hack to set the location of the monitor
    _update_monitor_canvas_hack(Window, parent_widget)
