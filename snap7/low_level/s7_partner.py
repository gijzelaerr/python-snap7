from .s7_protocol import S7Protocol as S7
from .s7_socket import S7Socket
import threading
import time
from typing import Optional, Callable, Any


class S7Partner:
    """
    Native Python implementation of S7 Partner (peer-to-peer communication).
    Based on Sharp7 S7Partner implementation.

    Partners can communicate in a peer-to-peer fashion, where both sides
    have equal rights and can send data asynchronously.
    """

    def __init__(self, active: bool = False):
        """
        Initialize S7 Partner.

        Args:
            active: True if this is the active partner (initiates connection)
        """
        self.socket = S7Socket()
        self.is_active = active
        self.pdu_length = 480
        self.max_pdu_length = 480
        self.pdu = bytearray(2048)

        # Connection parameters
        self.local_ip = "0.0.0.0"
        self.local_port = 102
        self.remote_ip = ""
        self.remote_port = 102
        self.local_tsap = 0x0100
        self.remote_tsap = 0x0200

        # Status
        self._connected = False
        self._running = False
        self._last_error = 0
        self._last_job_result = 0

        # Send/receive buffers
        self.send_buffer = bytearray(2048)
        self.recv_buffer = bytearray(2048)
        self.send_size = 0
        self.recv_size = 0

        # Async operation tracking
        self._async_send_pending = False
        self._async_send_result = 0
        self._async_recv_pending = False
        self._async_recv_result = 0

        # Callbacks
        self.send_callback: Optional[Callable[[Any], None]] = None
        self.recv_callback: Optional[Callable[[Any], None]] = None

        # Thread for async operations
        self._worker_thread: Optional[threading.Thread] = None

        # Timeouts
        self.send_timeout = 2000
        self.recv_timeout = 2000
        self.ping_timeout = 1000

        # Statistics
        self.bytes_sent = 0
        self.bytes_recv = 0
        self.send_errors = 0
        self.recv_errors = 0

    def __del__(self):
        self.stop()
        self.destroy()

    def create(self, active: bool = False) -> int:
        """
        Create/recreate the partner.

        Args:
            active: True if active partner

        Returns:
            Error code (0 = success)
        """
        self.is_active = active
        return 0

    def destroy(self) -> int:
        """
        Destroy the partner and clean up resources.

        Returns:
            Error code (0 = success)
        """
        self.stop()
        return 0

    def start(self) -> int:
        """
        Start the partner.
        For active partners, establishes connection to remote partner.
        For passive partners, listens for incoming connection.

        Returns:
            Error code (0 = success)
        """
        if self._running:
            return 0

        try:
            if self.is_active:
                # Active partner connects to remote
                if not self.remote_ip:
                    return S7.errIsoInvalidParams

                error = self.socket.connect(self.remote_ip, self.remote_port)
                if error != 0:
                    return error

                # Perform ISO connection
                error = self._iso_connect()
                if error != 0:
                    return error

            else:
                # Passive partner binds and waits for connection
                self.socket.create_socket()
                self.socket.bind(self.local_ip, self.local_port)
                # In a full implementation, would need to call listen() and accept()

            self._running = True
            self._connected = True
            return 0

        except Exception:
            self._last_error = S7.errTCPConnectionFailed
            return self._last_error

    def stop(self) -> int:
        """
        Stop the partner and disconnect.

        Returns:
            Error code (0 = success)
        """
        if not self._running:
            return 0

        self._running = False
        self._connected = False

        # Close socket
        self.socket.close()

        # Wait for worker thread
        if self._worker_thread:
            self._worker_thread.join(timeout=2.0)
            self._worker_thread = None

        return 0

    def start_to(self, local_ip: str, remote_ip: str, local_tsap: int = 0x0100, remote_tsap: int = 0x0200) -> int:
        """
        Start and connect to a specific remote partner.

        Args:
            local_ip: Local IP address
            remote_ip: Remote IP address
            local_tsap: Local TSAP
            remote_tsap: Remote TSAP

        Returns:
            Error code (0 = success)
        """
        self.local_ip = local_ip
        self.remote_ip = remote_ip
        self.local_tsap = local_tsap
        self.remote_tsap = remote_tsap
        self.is_active = True
        return self.start()

    def b_send(self) -> int:
        """
        Send data packet synchronously (blocking).

        Returns:
            Error code (0 = success)
        """
        if not self._connected:
            return S7.errTCPNotConnected

        try:
            # Send the data in send_buffer
            error = self.socket.send(self.send_buffer, self.send_size)
            if error == 0:
                self.bytes_sent += self.send_size
            else:
                self.send_errors += 1
            return error
        except Exception:
            self.send_errors += 1
            return S7.errTCPDataSend

    def b_recv(self) -> int:
        """
        Receive data packet synchronously (blocking).

        Returns:
            Error code (0 = success)
        """
        if not self._connected:
            return S7.errTCPNotConnected

        try:
            # Receive data into recv_buffer
            error = self.socket.receive(self.recv_buffer, 0, len(self.recv_buffer))
            if error == 0:
                self.recv_size = len(self.recv_buffer)
                self.bytes_recv += self.recv_size
            else:
                self.recv_errors += 1
            return error
        except Exception:
            self.recv_errors += 1
            return S7.errTCPDataReceive

    def as_b_send(self) -> int:
        """
        Send data packet asynchronously (non-blocking).

        Returns:
            Error code (0 = success)
        """
        if not self._connected:
            return S7.errTCPNotConnected

        if self._async_send_pending:
            return S7.errCliJobPending

        self._async_send_pending = True
        self._async_send_result = 0

        # Start async send in a thread
        thread = threading.Thread(target=self._async_send_worker, daemon=True)
        thread.start()

        return 0

    def _async_send_worker(self):
        """Worker thread for async send operation."""
        try:
            self._async_send_result = self.b_send()
        except Exception:
            self._async_send_result = S7.errTCPDataSend
        finally:
            self._async_send_pending = False
            if self.send_callback:
                try:
                    self.send_callback(self._async_send_result)
                except Exception:
                    pass

    def check_as_b_send_completion(self) -> tuple:
        """
        Check if async send operation is complete.

        Returns:
            Tuple of (status, result)
            status: 0 = complete, 1 = in progress
            result: Error code of the operation
        """
        if self._async_send_pending:
            return (1, 0)  # In progress
        else:
            return (0, self._async_send_result)  # Complete

    def wait_as_b_send_completion(self, timeout: int = 0) -> int:
        """
        Wait for async send operation to complete.

        Args:
            timeout: Timeout in milliseconds (0 = infinite)

        Returns:
            Error code (0 = success)
        """
        start_time = time.time() * 1000
        while self._async_send_pending:
            if timeout > 0 and (time.time() * 1000 - start_time) > timeout:
                return S7.errCliJobTimeout
            time.sleep(0.01)
        return self._async_send_result

    def as_b_recv(self) -> int:
        """
        Receive data packet asynchronously (non-blocking).

        Returns:
            Error code (0 = success)
        """
        if not self._connected:
            return S7.errTCPNotConnected

        if self._async_recv_pending:
            return S7.errCliJobPending

        self._async_recv_pending = True
        self._async_recv_result = 0

        # Start async receive in a thread
        thread = threading.Thread(target=self._async_recv_worker, daemon=True)
        thread.start()

        return 0

    def _async_recv_worker(self):
        """Worker thread for async receive operation."""
        try:
            self._async_recv_result = self.b_recv()
        except Exception:
            self._async_recv_result = S7.errTCPDataReceive
        finally:
            self._async_recv_pending = False
            if self.recv_callback:
                try:
                    self.recv_callback(self._async_recv_result)
                except Exception:
                    pass

    def check_as_b_recv_completion(self) -> tuple:
        """
        Check if async receive operation is complete.

        Returns:
            Tuple of (status, result)
            status: 0 = complete, 1 = in progress
            result: Error code of the operation
        """
        if self._async_recv_pending:
            return (1, 0)  # In progress
        else:
            return (0, self._async_recv_result)  # Complete

    def get_status(self) -> tuple:
        """
        Get partner status.

        Returns:
            Tuple of (connected, running, last_error)
        """
        return (self._connected, self._running, self._last_error)

    def get_last_error(self) -> int:
        """
        Get last error code.

        Returns:
            Error code
        """
        return self._last_error

    def get_stats(self) -> dict:
        """
        Get partner statistics.

        Returns:
            Dictionary with statistics
        """
        return {
            "bytes_sent": self.bytes_sent,
            "bytes_recv": self.bytes_recv,
            "send_errors": self.send_errors,
            "recv_errors": self.recv_errors,
        }

    def get_times(self) -> dict:
        """
        Get timing information.

        Returns:
            Dictionary with timing info
        """
        return {
            "send_timeout": self.send_timeout,
            "recv_timeout": self.recv_timeout,
            "ping_timeout": self.ping_timeout,
        }

    def set_param(self, param_number: int, value: int) -> int:
        """
        Set partner parameter.

        Args:
            param_number: Parameter number
            value: Parameter value

        Returns:
            Error code (0 = success)
        """
        if param_number == S7.p_i32_SendTimeout:
            self.send_timeout = value
            return 0
        elif param_number == S7.p_i32_RecvTimeout:
            self.recv_timeout = value
            return 0
        elif param_number == S7.p_i32_PingTimeout:
            self.ping_timeout = value
            return 0
        elif param_number == S7.p_i32_PDURequest:
            self.max_pdu_length = value
            return 0
        return S7.errCliInvalidParamNumber

    def get_param(self, param_number: int) -> int:
        """
        Get partner parameter.

        Args:
            param_number: Parameter number

        Returns:
            Parameter value
        """
        params = {
            S7.p_i32_SendTimeout: self.send_timeout,
            S7.p_i32_RecvTimeout: self.recv_timeout,
            S7.p_i32_PingTimeout: self.ping_timeout,
            S7.p_i32_PDURequest: self.max_pdu_length,
        }
        return params.get(param_number, 0)

    def set_send_callback(self, callback: Callable[[Any], None]) -> int:
        """
        Set callback for async send completion.

        Args:
            callback: Callback function

        Returns:
            Error code (0 = success)
        """
        self.send_callback = callback
        return 0

    def set_recv_callback(self, callback: Callable[[Any], None]) -> int:
        """
        Set callback for async receive completion.

        Args:
            callback: Callback function

        Returns:
            Error code (0 = success)
        """
        self.recv_callback = callback
        return 0

    def _iso_connect(self) -> int:
        """
        Perform ISO connection handshake.

        Returns:
            Error code (0 = success)
        """
        # Build ISO CR packet
        iso_cr = bytearray(S7.ISO_CR)
        iso_cr[16] = (self.local_tsap >> 8) & 0xFF
        iso_cr[17] = self.local_tsap & 0xFF
        iso_cr[20] = (self.remote_tsap >> 8) & 0xFF
        iso_cr[21] = self.remote_tsap & 0xFF

        # Send ISO CR
        error = self.socket.send(iso_cr, len(iso_cr))
        if error != 0:
            return error

        # Receive ISO CC
        response = bytearray(1024)
        error = self.socket.receive(response, 0, 1024)
        if error != 0:
            return error

        # Check if it's a valid ISO CC
        if len(response) < 22 or response[5] != 0xD0:
            return S7.errIsoConnect

        return 0
