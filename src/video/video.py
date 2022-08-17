import threading

import ffpyplayer
from ffpyplayer.player import MediaPlayer
from kivy import Logger
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.uix.image import Image


class Video(Image):  # TODO: Take ideas from VideoFFPy (e.g. yuv420p rendering through shader!)
    def __init__(self, src="udp://0.0.0.0:2000", fmt=None, **kwargs):
        super(Video, self).__init__(**kwargs)
        self.src = src
        self.fmt = fmt
        self.stats_frame_time = 0
        self.stats_frame_time_counter = 0
        # noinspection PyUnresolvedReferences
        ffpyplayer.tools.emit_library_info()
        t = threading.Thread(target=self.setup_thread, daemon=True)
        t.start()

    def setup_thread(self):
        start_time = Clock.time()

        # noinspection PyUnresolvedReferences,PyArgumentList
        self.player = MediaPlayer(self.src, ff_opts={  # TODO: configure ffmpeg options
            'framedrop': True, 'stats': True, 'fast': True,  # 'f': self.fmt,
        })
        self.player.set_output_pix_fmt('rgb24')  # Should be the default, but just in case
        Logger.info('Video: initialization (network + codec probing) took ' + str(Clock.time() - start_time))

        # Schedule updating the texture
        video_fps = 30 * 1.25  # Mitigate lag, at the cost of more CPU usage
        self.clock_event = Clock.schedule_interval(self.update, 1.0 / video_fps)

    def update(self, dt):
        # Read frame from source
        start_time = Clock.time()
        frame, val = self.player.get_frame()  # FIXME: Catchup to the latest frame!
        if val == 'eof':
            self.clock_event.cancel()
            return  # EOF todo: notify/handle this
        elif frame is None:
            return  # No new frame yet

        # Convert frame to flat array
        frame_shape = frame[0].get_size()
        frame = frame[0].to_memoryview()[0]

        # Update the texture with the vertically-flipped next frame and ask to be redrawn
        if self.texture is None:
            # noinspection PyArgumentList
            self.texture = Texture.create(size=(frame_shape[0], frame_shape[1]), colorfmt='rgb')
            self.texture.flip_vertical()
        self.texture.blit_buffer(frame, colorfmt='rgb', bufferfmt='ubyte', mipmap_generation=False)
        self.canvas.ask_update()

        self.stats_frame_time = (Clock.time() - start_time) * 0.5 + self.stats_frame_time * 0.5
        self.stats_frame_time_counter += 1
        if self.stats_frame_time_counter % 1000 == 0:
            Logger.info('Video: frame time: ' + str(self.stats_frame_time))
            self.stats_frame_time_counter = 0

    def __del__(self):  # FIXME: races with the thread
        if self.clock_event:
            self.clock_event.cancel()
        if self.player:
            self.player.close_player()
        Logger.info('Video: released')
