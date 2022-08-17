import socket
import threading

from kivy import Logger


class VideoProxy(threading.Thread):
    """
    Proxies video data from the udp protocol to the tcp protocol (server with only 1 client).

    This is needed for android, as the udp protocol support of ffmpeg seems broken.

    This will run on its own thread. This has the added benefit of buffering
    the data (until the OS buffers are full), so that the video is not dropped and
    no artifacts are displayed.
    """

    def __init__(self, src_addr=('0.0.0.0', 11111), dst_addr=('127.0.0.1', 0)):
        super().__init__(daemon=True)
        # Bind sockets to input and output
        self.socket_in = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket_in.bind(src_addr)
        self.src_addr = self.socket_in.getsockname()
        self.socket_out = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket_out.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)  # Don't wait before sending data
        self.socket_out.bind(dst_addr)
        self.dst_addr = self.socket_out.getsockname()
        self.socket_out.listen(1)

    # Start the thread that will accept 1 connection and pipe all data
    def run(self):
        out, client_address = self.socket_out.accept()
        Logger.info('VideoProxy: Accepted connection from {}'.format(client_address))
        buf_size = 4096
        buffer = bytearray(buf_size)
        while True:
            read = self.socket_in.recv_into(buffer, buf_size)
            if read <= 0:
                break
            out.sendall(buffer[:read])  # Throws exception on error
