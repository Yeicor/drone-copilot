import socket
import threading
import time
import weakref

import numpy as np
from ffpyplayer.player import MediaPlayer
from ffpyplayer.tools import emit_library_info
from kivy import Logger
from kivy.clock import Clock
from kivy.event import EventDispatcher


class StreamingVideoSource(threading.Thread, EventDispatcher):
    """This class provides a simple way to decode any streaming video source into python arrays for each (video) frame.

    Call `start()` to start the video thread and produce on_video_frame events after `feed()` ing data.
    See :func:`util.video.StreamingVideoSource.on_video_frame` for more details.
    """

    # TODO: Take ideas from VideoFFPy (e.g. yuv420p rendering through shader!)

    def __init__(self, playback_speed=1.0):
        """
        Set up the :class:`Video` player.

        :param playback_speed: The speed to play the video at. Useful to catch up to livestreams.
        """
        super(StreamingVideoSource, self).__init__(daemon=False)
        # Parameters
        self.playback_speed = playback_speed
        # Events
        self.register_event_type('on_video_frame')

        # Register a socket to feed data to the video decoder
        self.socket_out = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket_out.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)  # Don't wait before sending data
        self.socket_out.bind(('127.0.0.1', 0))  # Any local port
        sockname = self.socket_out.getsockname()
        self.socket_address = 'tcp://' + str(sockname[0]) + ":" + str(sockname[1])
        self.socket_out.listen(1)
        # Start the video decoder and connect it to the socket
        # noinspection PyUnresolvedReferences,PyArgumentList
        self.player = MediaPlayer(self.socket_address, ff_opts={  # TODO: configure more ffmpeg options
            'framedrop': True, 'stats': True, 'fast': True, 'an': True,
            # Apply a video filter to catch up to live source as long as more frames are available.
            'vf': ['setpts=' + str(1 / self.playback_speed) + '*PTS'],
        })
        self.player.set_output_pix_fmt('rgb24')  # Should be the default, but just in case
        self.closing = False
        # Accept the connection (should be queued) from the video decoder to be able to feed data
        self.out, client_address = self.socket_out.accept()
        # Stats & debug
        self.stats_frame_time = 0
        self.stats_frame_time_counter = 0
        emit_library_info()
        # Finalizer (in case the user forgets to call del)
        weakref.finalize(self, self.__del__)

    def feed(self, bs: bytes):
        """Provides the given video source bytes to the decoder, that will produce events when each frame is available.

        :param bs: the next block of data to decode
        """
        self.out.sendall(bs)

    def run(self):
        """The video thread that produces frame events. Call start() to start this thread.
        """

        # Start reading video frames and sending them to the main thread
        while not self.closing:
            # Read frame from source
            start_time = Clock.time()
            frame, val = self.player.get_frame()  # FIXME: Catchup to the latest frame!
            if val == 'eof':
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
                Logger.info('Video: Total EMA frame time: ' + str(self.stats_frame_time))
                self.stats_frame_time_counter = 0

        # Inform that the thread finished
        self.closing = None

    def on_video_frame(self, frame: np.ndarray):
        """
        This is the event that is dispatched when a new frame should be displayed. You can override this method to
        do something with the frame, but for external listeners, you should use `bind('on_video_frame', callback)`.

        Note that this event is dispatched from the video thread, so you should not do long-running operations in it.

        :param frame: the numpy.ndarray that represents the frame with a shape of (width, height, 3) representing
        the red, green and blue channels for each pixel.
        """
        pass

    def __del__(self):
        """Cleans up the resources.
        """
        # Wait for the video thread to stop (ugly and possibly racy)
        if self.closing is not None:
            Logger.info('Video: waiting for thread to stop')
            self.closing = True
            while self.closing is not None:
                time.sleep(0.01)
            Logger.info('Video: thread stopped')

        # Clean up the video player
        if self.player:
            self.player.close_player()
        Logger.info('Video: released')
