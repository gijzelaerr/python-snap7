from .s7_protocol import S7Protocol as S7
from .s7_socket import S7Socket
import socket
import threading
import time
from typing import Dict, Optional, Callable, Any


class S7Server:
    """
    Native Python implementation of S7 Server (PLC simulator).
    Based on Sharp7 S7Server implementation.
    """

    def __init__(self):
        self.socket = S7Socket()
        self.listen_socket: Optional[socket.socket] = None
        self.pdu_length = 480
        self.max_pdu_length = 480
        self.db_count = 0
        self.db_limit = 100
        self.pdu = bytearray(2048)
        self.cpu_state: int = S7.S7CpuStatusRun
        self.server_status: int = 0  # 0 = stopped, 1 = running
        self.clients_count: int = 0

        # Memory areas storage
        self.memory_areas: Dict[tuple, bytearray] = {}  # Key: (area_code, index)

        # Event callback
        self.event_callback: Optional[Callable[[Any], None]] = None

        # Server thread
        self._running = False
        self._server_thread: Optional[threading.Thread] = None
        self._client_threads: list = []

        # Last error
        self._last_error = 0

    def __del__(self):
        self.stop()

    def register_area(self, area_code: int, index: int, data: bytearray) -> int:
        """
        Register a memory area with the server.

        Args:
            area_code: Area code (DB, M, I, Q, etc.)
            index: Area index (e.g., DB number)
            data: Data buffer for this area

        Returns:
            Error code (0 = success)
        """
        self.memory_areas[(area_code, index)] = data
        return 0

    def unregister_area(self, area_code: int, index: int) -> int:
        """
        Unregister a memory area from the server.

        Args:
            area_code: Area code
            index: Area index

        Returns:
            Error code (0 = success)
        """
        key = (area_code, index)
        if key in self.memory_areas:
            del self.memory_areas[key]
            return 0
        return S7.errCliItemNotAvailable

    def start(self, ip: str = "0.0.0.0", tcp_port: int = 102) -> int:
        """
        Start the server.

        Args:
            ip: IP address to bind to
            tcp_port: TCP port to bind to

        Returns:
            Error code (0 = success)
        """
        if self._running:
            return 0

        try:
            self.listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.listen_socket.bind((ip, tcp_port))
            self.listen_socket.listen(5)
            self.listen_socket.settimeout(1.0)  # Non-blocking with timeout

            self._running = True
            self.server_status = 1

            # Start server thread
            self._server_thread = threading.Thread(target=self._server_loop, daemon=True)
            self._server_thread.start()

            return 0
        except Exception:
            self._last_error = S7.errTCPSocketCreation
            return self._last_error

    def stop(self) -> int:
        """
        Stop the server.

        Returns:
            Error code (0 = success)
        """
        if not self._running:
            return 0

        self._running = False
        self.server_status = 0

        # Close listen socket
        if self.listen_socket:
            try:
                self.listen_socket.close()
            except Exception:
                pass
            self.listen_socket = None

        # Wait for server thread
        if self._server_thread:
            self._server_thread.join(timeout=2.0)
            self._server_thread = None

        return 0

    def get_status(self) -> tuple:
        """
        Get server status.

        Returns:
            Tuple of (server_status, cpu_status, clients_count)
        """
        return (self.server_status, self.cpu_state, self.clients_count)

    def set_cpu_status(self, status: int) -> int:
        """
        Set CPU status.

        Args:
            status: CPU status (Run/Stop)

        Returns:
            Error code (0 = success)
        """
        self.cpu_state = status
        return 0

    def set_event_callback(self, callback: Callable[[Any], None]) -> int:
        """
        Set event callback function.

        Args:
            callback: Callback function

        Returns:
            Error code (0 = success)
        """
        self.event_callback = callback
        return 0

    def get_param(self, param_number: int) -> int:
        """
        Get server parameter.

        Args:
            param_number: Parameter number

        Returns:
            Parameter value
        """
        params = {
            S7.p_i32_PDURequest: self.max_pdu_length,
        }
        return params.get(param_number, 0)

    def set_param(self, param_number: int, value: int) -> int:
        """
        Set server parameter.

        Args:
            param_number: Parameter number
            value: Parameter value

        Returns:
            Error code (0 = success)
        """
        if param_number == S7.p_i32_PDURequest:
            self.max_pdu_length = value
            return 0
        return S7.errCliInvalidParamNumber

    def _server_loop(self):
        """Main server loop to accept client connections."""
        while self._running:
            try:
                client_socket, address = self.listen_socket.accept()
                self.clients_count += 1

                # Handle client in a separate thread
                client_thread = threading.Thread(target=self._handle_client, args=(client_socket, address), daemon=True)
                client_thread.start()
                self._client_threads.append(client_thread)

            except socket.timeout:
                continue
            except Exception:
                if self._running:
                    time.sleep(0.1)

    def _handle_client(self, client_socket: socket.socket, address: tuple):
        """
        Handle a client connection.

        Args:
            client_socket: Client socket
            address: Client address
        """
        try:
            # Basic client handling - accept ISO connection, negotiate PDU
            # This is a simplified implementation
            client_socket.settimeout(5.0)

            # Read ISO CR (Connection Request)
            data = client_socket.recv(1024)
            if len(data) > 0:
                # Send ISO CC (Connection Confirm)
                # Simplified - just echo back with CC type
                if len(data) >= 22 and data[5] == 0xE0:  # CR packet
                    response = bytearray(data)
                    response[5] = 0xD0  # Change to CC
                    client_socket.send(response)

                    # Handle S7 communication
                    while self._running:
                        try:
                            request = client_socket.recv(2048)
                            if len(request) == 0:
                                break

                            # Process S7 request and send response
                            response = self._process_request(request)
                            if response:
                                client_socket.send(response)
                        except socket.timeout:
                            continue
                        except Exception:
                            break
        except Exception:
            pass
        finally:
            try:
                client_socket.close()
            except Exception:
                pass
            self.clients_count -= 1

    def _process_request(self, request: bytearray) -> Optional[bytearray]:
        """
        Process an S7 request and generate response.

        Args:
            request: Request data

        Returns:
            Response data or None
        """
        # This is a simplified implementation
        # A full implementation would parse the request and handle:
        # - Read/write operations
        # - Start/stop PLC
        # - Get CPU info
        # etc.

        # For now, just return a simple ACK
        return None

    def get_last_error(self) -> int:
        """
        Get last error code.

        Returns:
            Error code
        """
        return self._last_error
