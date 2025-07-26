from .s7_protocol import S7Protocol
from .s7_socket import S7Socket


class S7Server:
    def __init__(self):
        self.socket = S7Socket()
        self.pdu_length = 2048
        self.db_count = 0
        self.db_limit = 0
        self.pdu = bytearray(2048)  # Assuming max PDU size
        self.cpu_state : int = S7Protocol.S7CpuStatusRun

    def __del__(self):
        self.socket.close()


    def start(self, ip: str = "0.0.0.0" , tcp_port: int = 102):
        """
        Start the server.
        :param ip: IP address to bind to
        :param tcp_port: TCP port to bind to
        """
        self.socket.create_socket()
        self.socket.bind(ip, tcp_port)

    def stop(self) -> bool:
        self.socket.close()
        return True


