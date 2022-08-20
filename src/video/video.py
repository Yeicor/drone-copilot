import threading
import time

import ffpyplayer
import numpy as np
from ffpyplayer.player import MediaPlayer
from kivy import Logger
from kivy.clock import Clock, mainthread
from kivy.event import EventDispatcher
from kivy.graphics.texture import Texture
from kivy.uix.image import Image


class Video(Image, EventDispatcher):  # TODO: Take ideas from VideoFFPy (e.g. yuv420p rendering through shader!)
    def __init__(self, src="udp://0.0.0.0:2000", **kwargs):
        """
        Create a video player that plays the given source file/URL.
        This is intended for live video streams, and will speed up the video playback to catch up.

        :param src: The source of the video stream.
        """
        super(Video, self).__init__(**kwargs)
        self.src = src
        self.stats_frame_time = 0
        self.stats_frame_time_counter = 0
        self.player = None
        self.clock_event = None
        # noinspection PyUnresolvedReferences
        ffpyplayer.tools.emit_library_info()
        self.register_event_type('on_video_frame')
        t = threading.Thread(target=self.video_thread, daemon=True)
        t.start()

    def video_thread(self):
        start_time = Clock.time()

        # noinspection PyUnresolvedReferences,PyArgumentList
        self.player = MediaPlayer(self.src, ff_opts={  # TODO: configure more ffmpeg options
            'framedrop': True, 'stats': True, 'fast': True, 'an': True,
            # Apply a video filter to speed up the playback as long as more frames are available, to catch up to live source.
            'vf': ['setpts=0.9*PTS'],  # NOTE: video filters can be changed at runtime, for dynamic effects
        })
        self.player.set_output_pix_fmt('rgb24')  # Should be the default, but just in case
        Logger.info('Video: initialization (network + codec probing) took ' + str(Clock.time() - start_time))

        # Start reading video frames and sending them to the main thread
        while True:
            # Read frame from source
            start_time = Clock.time()
            frame, val = self.player.get_frame()  # FIXME: Catchup to the latest frame!
            if val == 'eof':
                self.clock_event.cancel()
                break  # EOF todo: notify/handle this
            elif frame is None:
                time.sleep(0.01)  # FIXME: Better solution than this to wait between frames?
                continue  # No new frame yet

            # Convert frame to np.ndarray of (width, height, 3)
            frame_size = frame[0].get_size()
            frame = np.array(frame[0].to_memoryview()[0]).reshape((frame_size[0], frame_size[1], 3))

            # Run all listeners before publishing the frame. Bind is applied in reverse order.
            # They may modify the frame in-place, but should do long-running operations in a separate thread.
            self.dispatch('on_video_frame', frame)

            # Update and report stats
            self.stats_frame_time = (Clock.time() - start_time) * 0.5 + self.stats_frame_time * 0.5
            self.stats_frame_time_counter += 1
            if self.stats_frame_time_counter % 1000 == 0:
                Logger.info('Video: frame time: ' + str(self.stats_frame_time))
                self.stats_frame_time_counter = 0

    def on_video_frame(self, frame: np.ndarray):
        """
        Event handler for the on_video_frame event. This is the last one to be called and will render the frame.

        :param frame: the image to update the texture with, as a numpy.ndarray of (width, height, 3) in RGB format.
        """
        self.update_texture(frame)

    @mainthread
    def update_texture(self, frame: np.ndarray):
        """
        Queues an update of the texture on the main UI thread (work should be minimal).
        It also forces to redraw of the widget soon.

        :param frame: the image to update the texture with, as a numpy.ndarray of (width, height, 3) in RGB format.
        """
        # Update the texture with the vertically-flipped next frame and ask to be redrawn
        if self.texture is None:
            # noinspection PyArgumentList
            self.texture = Texture.create(size=(frame.shape[0], frame.shape[1]), colorfmt='rgb')
            self.texture.flip_vertical()
        self.texture.blit_buffer(np.ravel(frame), colorfmt='rgb', bufferfmt='ubyte', mipmap_generation=False)
        self.canvas.ask_update()

    def __del__(self):  # FIXME: races with the thread
        if self.clock_event:
            self.clock_event.cancel()
        if self.player:
            self.player.close_player()
        Logger.info('Video: released')
