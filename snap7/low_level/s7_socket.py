import socket
import time

from snap7.low_level.s7_protocol import S7Protocol as S7


class S7Socket:
    def __init__(self):
        self.TCPSocket: socket.socket | None = None
        self._ReadTimeout : int = 2000
        self._WriteTimeout : int = 2000
        self._ConnectTimeout : int= 1000
        self._LastError = 0

    def __del__(self):
        self.close()

    def close(self):
        if self.TCPSocket is not None:
            self.TCPSocket.close()
            self.TCPSocket = None

    def create_socket(self):
        self.TCPSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
        # Important to set TCP_NODELAY to avoid delays in the communication with the PLC
        self.TCPSocket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.TCPSocket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

    def bind(self, ip, tcp_port):
        self.TCPSocket.bind((ip, tcp_port))

    def tcp_ping(self, host, port):
        """
        From Davide Nardella notes on Snap7 if you can ping the PLC you can connect to it
        :param host: IP address of the Host
        :param port: TCP port of the Port
        """
        ping_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
        ping_socket.settimeout(self._ConnectTimeout / 1000.0)
        try:
            ping_socket.connect((host, port))
        except socket.error:
            self._LastError = S7.errTCPConnectionFailed
        finally:
            ping_socket.close()

    def connect(self, host, port):
        if self.connected:
            # Already connected
            return 0

        self.tcp_ping(host, port)
        if self._LastError != 0:
            return self._LastError
        try:
            self.create_socket()
            self.TCPSocket.connect((host, port))
        except socket.error:
            self._LastError = S7.errTCPConnectionFailed
            return self._LastError
        return 0

    def wait_for_data(self, size, timeout):
        expired = False
        elapsed = time.time()
        self._LastError = 0
        try:
            size_avail = self.TCPSocket.recv(4096, socket.MSG_PEEK)
            while len(size_avail) < size and not expired:
                time.sleep(0.002)
                size_avail = self.TCPSocket.recv(4096, socket.MSG_PEEK)
                expired = (time.time() - elapsed) * 1000 > timeout
                if expired and len(size_avail) > 0:
                    try:
                        self.TCPSocket.recv(len(size_avail))
                    except socket.error:
                        pass
        except socket.error:
            self._LastError = S7.errTCPDataReceive
        if expired:
            self._LastError = S7.errTCPDataReceive
        return self._LastError

    def receive(self, buffer, start, size):
        bytes_read = 0
        self._LastError = self.wait_for_data(size, self._ReadTimeout)
        if self._LastError == 0:
            try:
                bytes_read = self.TCPSocket.recv_into(memoryview(buffer)[start : start + size])
            except socket.error:
                self._LastError = S7.errTCPDataReceive
            if bytes_read == 0:
                self._LastError = S7.errTCPDataReceive
                self.close()
        return self._LastError

    def send(self, buffer, size):
        self._LastError = 0
        try:
            bytes_sent = self.TCPSocket.send(buffer[:size])
        except socket.error:
            self._LastError = S7.errTCPDataSend
            self.close()

        return self._LastError


    @property
    def connected(self):
        return self.TCPSocket is not None and self.TCPSocket.fileno() != -1

    @property
    def read_timeout(self):
        return self._ReadTimeout

    @read_timeout.setter
    def read_timeout(self, value):
        self._ReadTimeout = value

    @property
    def write_timeout(self):
        return self._WriteTimeout

    @write_timeout.setter
    def write_timeout(self, value):
        self._WriteTimeout = value

    @property
    def connect_timeout(self):
        return self._ConnectTimeout

    @connect_timeout.setter
    def connect_timeout(self, value):
        self._ConnectTimeout = value
