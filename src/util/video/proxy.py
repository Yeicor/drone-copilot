import socket
import threading
import time
import weakref

from kivy import Logger


class VideoProxy(threading.Thread):
    """
    Proxies video data from the udp protocol to the tcp protocol (server with only 1 client).

    This is needed for android, as the udp protocol support of ffmpeg seems broken.

    This will run on its own thread. This has the added benefit of buffering
    the data (until the OS buffers are full), so that the video is not dropped and
    no artifacts are displayed.
    """

    def __init__(self, src_addr=('0.0.0.0', 11111), dst_addr=('127.0.0.1', 0), *args, **kwargs):
        super().__init__(*args, **kwargs, daemon=True)
        # Bind sockets to input and output
        self.socket_in = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket_in.bind(src_addr)
        self.src_addr = self.socket_in.getsockname()
        self.socket_out = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket_out.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)  # Don't wait before sending data
        self.socket_out.bind(dst_addr)
        self.dst_addr = self.socket_out.getsockname()
        self.socket_out.listen(1)
        # Synchronization
        self.closing = False
        # Finalizer (in case the user forgets to call del)
        weakref.finalize(self, self.__del__)

    def run(self):
        """
        Start the thread that will accept 1 connection (repeatedly) and pipe all input data to the connection.
        """
        while not self.closing:
            out, client_address = self.socket_out.accept()
            Logger.info('VideoProxy: Accepted connection from {}'.format(client_address))
            buf_size = 4096
            buffer = bytearray(buf_size)
            try:
                self.socket_in.settimeout(5.0)  # Make sure that we check the exit flag once in a while
                while not self.closing:
                    try:
                        read = self.socket_in.recv_into(buffer, buf_size)
                    except socket.timeout:
                        if self.closing:
                            break
                        continue
                    if read <= 0:
                        break
                    out.sendall(buffer[:read])  # Throws exception on error
            except Exception as e:
                Logger.info('VideoProxy: I/O error: {}, waiting for a new connection'.format(e))

        # Notify that we finished
        self.closing = None

    def __del__(self):
        """Cleans up the resources.
        """
        # Wait for the video thread to stop (ugly and possibly racy)
        if self.closing is not None:
            Logger.info('VideoProxy: waiting for thread to stop')
            self.closing = True
            while self.closing is not None:
                time.sleep(0.01)
            Logger.info('VideoProxy: thread stopped')

        self.socket_in.close()
        self.socket_out.close()
        Logger.info('VideoProxy: released')
