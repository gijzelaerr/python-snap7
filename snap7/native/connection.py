"""
ISO on TCP connection management (RFC 1006).

Implements TPKT (Transport Service on top of TCP) and COTP (Connection Oriented
Transport Protocol) layers for S7 communication.
"""

import socket
import struct
import logging
from typing import Optional

from .errors import S7ConnectionError, S7TimeoutError

logger = logging.getLogger(__name__)


class ISOTCPConnection:
    """
    ISO on TCP connection implementation.
    
    Handles the transport layer for S7 communication including:
    - TCP socket management
    - TPKT framing (RFC 1006)
    - COTP connection setup and data transfer
    - PDU size negotiation
    """
    
    # COTP PDU types
    COTP_CR = 0xE0    # Connection Request
    COTP_CC = 0xD0    # Connection Confirm  
    COTP_DR = 0x80    # Disconnect Request
    COTP_DC = 0xC0    # Disconnect Confirm
    COTP_DT = 0xF0    # Data Transfer
    COTP_ED = 0x10    # Expedited Data
    COTP_AK = 0x60    # Data Acknowledgment
    COTP_EA = 0x20    # Expedited Acknowledgment
    COTP_RJ = 0x50    # Reject
    COTP_ER = 0x70    # Error
    
    def __init__(self, host: str, port: int = 102, 
                 local_tsap: int = 0x0100, remote_tsap: int = 0x0102):
        """
        Initialize ISO TCP connection.
        
        Args:
            host: Target PLC IP address
            port: TCP port (default 102 for S7)
            local_tsap: Local Transport Service Access Point
            remote_tsap: Remote Transport Service Access Point
        """
        self.host = host
        self.port = port
        self.local_tsap = local_tsap
        self.remote_tsap = remote_tsap
        self.socket: Optional[socket.socket] = None
        self.connected = False
        self.pdu_size = 240  # Default PDU size, negotiated during connection
        self.timeout = 5.0   # Default timeout in seconds
        
        # Connection parameters
        self.src_ref = 0x0001  # Source reference
        self.dst_ref = 0x0000  # Destination reference (assigned by peer)
        
    def connect(self, timeout: float = 5.0) -> None:
        """
        Establish ISO on TCP connection.
        
        Args:
            timeout: Connection timeout in seconds
        """
        self.timeout = timeout
        
        try:
            # Step 1: TCP connection
            self._tcp_connect()
            
            # Step 2: ISO connection (COTP handshake)
            self._iso_connect()
            
            self.connected = True
            logger.info(f"Connected to {self.host}:{self.port}, PDU size: {self.pdu_size}")
            
        except Exception as e:
            self.disconnect()
            if isinstance(e, (S7ConnectionError, S7TimeoutError)):
                raise
            else:
                raise S7ConnectionError(f"Connection failed: {e}")
    
    def disconnect(self) -> None:
        """Disconnect from S7 device."""
        if self.socket:
            try:
                if self.connected:
                    # Send COTP disconnect request
                    self._send_cotp_disconnect()
                self.socket.close()
            except Exception:
                pass  # Ignore errors during disconnect
            finally:
                self.socket = None
                self.connected = False
                logger.info(f"Disconnected from {self.host}:{self.port}")
    
    def send_data(self, data: bytes) -> None:
        """
        Send data over ISO connection.
        
        Args:
            data: S7 PDU data to send
        """
        if not self.connected:
            raise S7ConnectionError("Not connected")
            
        # Wrap data in COTP Data Transfer PDU
        cotp_data = self._build_cotp_dt(data)
        
        # Wrap in TPKT frame
        tpkt_frame = self._build_tpkt(cotp_data)
        
        # Send over TCP
        try:
            self.socket.sendall(tpkt_frame)
            logger.debug(f"Sent {len(tpkt_frame)} bytes")
        except socket.error as e:
            raise S7ConnectionError(f"Send failed: {e}")
    
    def receive_data(self) -> bytes:
        """
        Receive data from ISO connection.
        
        Returns:
            S7 PDU data
        """
        if not self.connected:
            raise S7ConnectionError("Not connected")
            
        try:
            # Receive TPKT header (4 bytes)
            tpkt_header = self._recv_exact(4)
            
            # Parse TPKT header
            version, reserved, length = struct.unpack('>BBH', tpkt_header)
            
            if version != 3:
                raise S7ConnectionError(f"Invalid TPKT version: {version}")
                
            # Receive remaining data
            remaining = length - 4
            if remaining <= 0:
                raise S7ConnectionError("Invalid TPKT length")
                
            payload = self._recv_exact(remaining)
            
            # Parse COTP header and extract data
            return self._parse_cotp_data(payload)
            
        except socket.timeout:
            raise S7TimeoutError("Receive timeout")
        except socket.error as e:
            raise S7ConnectionError(f"Receive failed: {e}")
    
    def _tcp_connect(self) -> None:
        """Establish TCP connection."""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(self.timeout)
        
        try:
            self.socket.connect((self.host, self.port))
            logger.debug(f"TCP connected to {self.host}:{self.port}")
        except socket.error as e:
            raise S7ConnectionError(f"TCP connection failed: {e}")
    
    def _iso_connect(self) -> None:
        """Establish ISO connection using COTP handshake."""
        # Send Connection Request
        cr_pdu = self._build_cotp_cr()
        tpkt_frame = self._build_tpkt(cr_pdu)
        
        self.socket.sendall(tpkt_frame)
        logger.debug("Sent COTP Connection Request")
        
        # Receive Connection Confirm
        tpkt_header = self._recv_exact(4)
        version, reserved, length = struct.unpack('>BBH', tpkt_header)
        
        if version != 3:
            raise S7ConnectionError(f"Invalid TPKT version in response: {version}")
            
        payload = self._recv_exact(length - 4)
        self._parse_cotp_cc(payload)
        
        logger.debug("Received COTP Connection Confirm")
    
    def _build_tpkt(self, payload: bytes) -> bytes:
        """
        Build TPKT frame.
        
        TPKT Header (4 bytes):
        - Version (1 byte): Always 3
        - Reserved (1 byte): Always 0  
        - Length (2 bytes): Total frame length including header
        """
        length = len(payload) + 4
        return struct.pack('>BBH', 3, 0, length) + payload
    
    def _build_cotp_cr(self) -> bytes:
        """
        Build COTP Connection Request PDU.
        
        COTP CR format:
        - PDU Length: Length of COTP header (excluding this byte)
        - PDU Type: 0xE0 (Connection Request)
        - Destination Reference: 2 bytes
        - Source Reference: 2 bytes  
        - Class/Option: 1 byte
        - Parameters: Variable length
        """
        # Basic COTP CR without parameters
        base_pdu = struct.pack(
            '>BBHHB',
            6,                    # PDU length (header without parameters)
            self.COTP_CR,         # PDU type
            0x0000,               # Destination reference (0 for CR)
            self.src_ref,         # Source reference
            0x00                  # Class/option (Class 0, no extended formats)
        )
        
        # Add TSAP parameters
        # Calling TSAP (local)
        calling_tsap = struct.pack('>BBH', 0xC1, 2, self.local_tsap)
        # Called TSAP (remote)  
        called_tsap = struct.pack('>BBH', 0xC2, 2, self.remote_tsap)
        # PDU Size parameter
        pdu_size_param = struct.pack('>BBH', 0xC0, 2, self.pdu_size)
        
        parameters = calling_tsap + called_tsap + pdu_size_param
        
        # Update PDU length to include parameters
        total_length = 6 + len(parameters)
        pdu = struct.pack('>B', total_length) + base_pdu[1:] + parameters
        
        return pdu
    
    def _parse_cotp_cc(self, data: bytes) -> None:
        """
        Parse COTP Connection Confirm PDU.
        
        Extracts destination reference and negotiated PDU size.
        """
        if len(data) < 7:
            raise S7ConnectionError("Invalid COTP CC: too short")
            
        pdu_len, pdu_type, dst_ref, src_ref, class_opt = struct.unpack('>BBHHB', data[:7])
        
        if pdu_type != self.COTP_CC:
            raise S7ConnectionError(f"Expected COTP CC, got {pdu_type:#02x}")
            
        self.dst_ref = dst_ref
        
        # Parse parameters if present
        if len(data) > 7:
            self._parse_cotp_parameters(data[7:])
    
    def _parse_cotp_parameters(self, params: bytes) -> None:
        """Parse COTP parameters from Connection Confirm."""
        offset = 0
        
        while offset < len(params):
            if offset + 2 > len(params):
                break
                
            param_code = params[offset]
            param_len = params[offset + 1]
            
            if offset + 2 + param_len > len(params):
                break
                
            param_data = params[offset + 2:offset + 2 + param_len]
            
            if param_code == 0xC0 and param_len == 2:
                # PDU Size parameter
                self.pdu_size = struct.unpack('>H', param_data)[0]
                logger.debug(f"Negotiated PDU size: {self.pdu_size}")
                
            offset += 2 + param_len
    
    def _build_cotp_dt(self, data: bytes) -> bytes:
        """
        Build COTP Data Transfer PDU.
        
        COTP DT format:
        - PDU Length: 2 (fixed for DT)
        - PDU Type: 0xF0 (Data Transfer)
        - EOT + Number: 0x80 (End of TSDU, sequence number 0)
        - Data: Variable length
        """
        header = struct.pack('>BBB', 2, self.COTP_DT, 0x80)
        return header + data
    
    def _parse_cotp_data(self, cotp_pdu: bytes) -> bytes:
        """
        Parse COTP Data Transfer PDU and extract S7 data.
        """
        if len(cotp_pdu) < 3:
            raise S7ConnectionError("Invalid COTP DT: too short")
            
        pdu_len, pdu_type, eot_num = struct.unpack('>BBB', cotp_pdu[:3])
        
        if pdu_type != self.COTP_DT:
            raise S7ConnectionError(f"Expected COTP DT, got {pdu_type:#02x}")
            
        return cotp_pdu[3:]  # Return data portion
    
    def _send_cotp_disconnect(self) -> None:
        """Send COTP Disconnect Request."""
        dr_pdu = struct.pack(
            '>BBHHBB',
            6,                    # PDU length
            self.COTP_DR,         # PDU type
            self.dst_ref,         # Destination reference
            self.src_ref,         # Source reference  
            0x00,                 # Reason (normal disconnect)
            0x00                  # Additional info
        )
        
        tpkt_frame = self._build_tpkt(dr_pdu)
        try:
            self.socket.sendall(tpkt_frame)
        except socket.error:
            pass  # Ignore errors during disconnect
    
    def _recv_exact(self, size: int) -> bytes:
        """
        Receive exactly the specified number of bytes.
        
        Args:
            size: Number of bytes to receive
            
        Returns:
            Received data
            
        Raises:
            S7ConnectionError: If connection is lost
            S7TimeoutError: If timeout occurs
        """
        data = bytearray()
        
        while len(data) < size:
            try:
                chunk = self.socket.recv(size - len(data))
                if not chunk:
                    raise S7ConnectionError("Connection closed by peer")
                data.extend(chunk)
            except socket.timeout:
                raise S7TimeoutError("Receive timeout")
            except socket.error as e:
                raise S7ConnectionError(f"Receive error: {e}")
                
        return bytes(data)
    
    def __enter__(self):
        """Context manager entry."""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()