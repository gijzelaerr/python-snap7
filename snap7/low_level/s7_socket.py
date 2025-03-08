import socket
import time


class S7Socket:
    def __init__(self):
        self.TCPSocket = None
        self._ReadTimeout = 2000
        self._WriteTimeout = 2000
        self._ConnectTimeout = 1000
        self.LastError = 0

    def __del__(self):
        self.close()

    def close(self):
        if self.TCPSocket is not None:
            self.TCPSocket.close()
            self.TCPSocket = None

    def create_socket(self):
        self.TCPSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
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
        ping_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ping_socket.settimeout(self._ConnectTimeout / 1000.0)
        try:
            ping_socket.connect((host, port))
        except socket.error:
            self.LastError = "errTCPConnectionFailed"
        finally:
            ping_socket.close()

    def connect(self, host, port):
        self.LastError = 0
        if not self.connected:
            self.tcp_ping(host, port)
            if self.LastError == 0:
                try:
                    self.create_socket()
                    self.TCPSocket.connect((host, port))
                except socket.error:
                    self.LastError = "errTCPConnectionFailed"
        return self.LastError

    def wait_for_data(self, size, timeout):
        expired = False
        elapsed = time.time()
        self.LastError = 0
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
            self.LastError = "errTCPDataReceive"
        if expired:
            self.LastError = "errTCPDataReceive"
        return self.LastError

    def receive(self, buffer, start, size):
        bytes_read = 0
        self.LastError = self.wait_for_data(size, self._ReadTimeout)
        if self.LastError == 0:
            try:
                bytes_read = self.TCPSocket.recv_into(memoryview(buffer)[start : start + size])
            except socket.error:
                self.LastError = "errTCPDataReceive"
            if bytes_read == 0:
                self.LastError = "errTCPDataReceive"
                self.close()
        return self.LastError

    def send(self, buffer, size):
        self.LastError = 0
        try:
            bytes_sent = self.TCPSocket.send(buffer[:size])
        except socket.error:
            self.LastError = "errTCPDataSend"
            self.close()
        return self.LastError

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
