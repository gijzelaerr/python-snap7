"""
S7CommPlus connection management.

Establishes an ISO-on-TCP connection to S7-1200/1500 PLCs using the
S7CommPlus protocol, with support for all protocol versions:

- V1: Early S7-1200 (FW >= V4.0). Trivial anti-replay (challenge + 0x80).
- V2: Adds integrity checking and proprietary session authentication.
- V3: Adds ECC-based key exchange.
- V3 + TLS: TIA Portal V17+. Standard TLS 1.3 with per-device certificates.

The wire protocol (VLQ encoding, data types, function codes, object model) is
the same across all versions -- only the session authentication layer differs.

Connection sequence (all versions)::

    1. TCP connect to port 102
    2. COTP Connection Request / Confirm (same as legacy S7comm)
    3. S7CommPlus CreateObject request (NullServer session setup)
    4. PLC responds with CreateObject response containing:
       - Protocol version (V1/V2/V3)
       - Session ID
       - Server session challenge (V2/V3)

Version-specific authentication after step 4::

    V1: session_response = challenge_byte + 0x80
    V2: Proprietary HMAC-SHA256 / AES session key derivation
    V3 (no TLS): ECC-based key exchange (requires product-family keys)
    V3 (TLS): InitSsl request -> TLS 1.3 handshake over TPKT/COTP tunnel

Reference: thomas-v2/S7CommPlusDriver (C#, LGPL-3.0)
"""

import logging
import ssl
import struct
from typing import Optional, Type
from types import TracebackType

from ..connection import ISOTCPConnection
from .protocol import FunctionCode, Opcode, ProtocolVersion
from .codec import encode_header, decode_header

logger = logging.getLogger(__name__)


class S7CommPlusConnection:
    """S7CommPlus connection with multi-version support.

    Wraps an ISOTCPConnection and adds:
    - S7CommPlus session establishment (CreateObject)
    - Protocol version detection from PLC response
    - Version-appropriate authentication (V1/V2/V3/TLS)
    - Frame send/receive (TLS-encrypted when using V17+ firmware)

    Currently implements V1 authentication. V2/V3/TLS authentication
    layers are planned for future development.
    """

    def __init__(
        self,
        host: str,
        port: int = 102,
        local_tsap: int = 0x0100,
        remote_tsap: int = 0x0102,
    ):
        self.host = host
        self.port = port
        self.local_tsap = local_tsap
        self.remote_tsap = remote_tsap

        self._iso_conn = ISOTCPConnection(
            host=host,
            port=port,
            local_tsap=local_tsap,
            remote_tsap=remote_tsap,
        )

        self._ssl_context: Optional[ssl.SSLContext] = None
        self._session_id: int = 0
        self._sequence_number: int = 0
        self._protocol_version: int = 0  # Detected from PLC response
        self._tls_active: bool = False
        self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def protocol_version(self) -> int:
        """Protocol version negotiated with the PLC."""
        return self._protocol_version

    @property
    def session_id(self) -> int:
        """Session ID assigned by the PLC."""
        return self._session_id

    @property
    def tls_active(self) -> bool:
        """Whether TLS encryption is active on this connection."""
        return self._tls_active

    def connect(
        self,
        timeout: float = 5.0,
        use_tls: bool = False,
        tls_cert: Optional[str] = None,
        tls_key: Optional[str] = None,
        tls_ca: Optional[str] = None,
    ) -> None:
        """Establish S7CommPlus connection.

        The connection sequence:
        1. COTP connection (same as legacy S7comm)
        2. CreateObject to establish S7CommPlus session
        3. Protocol version is detected from PLC response
        4. If use_tls=True and PLC supports it, TLS is negotiated

        Args:
            timeout: Connection timeout in seconds
            use_tls: Whether to attempt TLS negotiation.
            tls_cert: Path to client TLS certificate (PEM)
            tls_key: Path to client private key (PEM)
            tls_ca: Path to CA certificate for PLC verification (PEM)
        """
        try:
            # Step 1: COTP connection
            self._iso_conn.connect(timeout)

            # Step 2: CreateObject (S7CommPlus session setup)
            self._create_session()

            # Step 3: Version-specific authentication
            if use_tls and self._protocol_version >= ProtocolVersion.V3:
                # TODO: Send InitSsl request and perform TLS handshake
                raise NotImplementedError(
                    "TLS authentication is not yet implemented. "
                    "Use use_tls=False for V1 connections."
                )
            elif self._protocol_version == ProtocolVersion.V2:
                # TODO: Proprietary HMAC-SHA256/AES session auth
                raise NotImplementedError(
                    "V2 authentication is not yet implemented."
                )

            # V1: No further authentication needed
            self._connected = True
            logger.info(
                f"S7CommPlus connected to {self.host}:{self.port}, "
                f"version=V{self._protocol_version}, session={self._session_id}"
            )

        except Exception:
            self.disconnect()
            raise

    def disconnect(self) -> None:
        """Disconnect from PLC."""
        if self._connected and self._session_id:
            try:
                self._delete_session()
            except Exception:
                pass

        self._connected = False
        self._tls_active = False
        self._session_id = 0
        self._sequence_number = 0
        self._protocol_version = 0
        self._iso_conn.disconnect()

    def send_request(
        self, function_code: int, payload: bytes = b""
    ) -> bytes:
        """Send an S7CommPlus request and receive the response.

        Args:
            function_code: S7CommPlus function code
            payload: Request payload (after the 14-byte request header)

        Returns:
            Response payload (after the 14-byte response header)
        """
        if not self._connected:
            from ..error import S7ConnectionError
            raise S7ConnectionError("Not connected")

        seq_num = self._next_sequence_number()

        # Build request header
        request = struct.pack(
            ">BHHHHIB",
            Opcode.REQUEST,
            0x0000,  # Reserved
            function_code,
            0x0000,  # Reserved
            seq_num,
            self._session_id,
            0x36,  # Transport flags
        ) + payload

        # Add S7CommPlus frame header and send
        frame = encode_header(self._protocol_version, len(request)) + request
        self._iso_conn.send_data(frame)

        # Receive response
        response_frame = self._iso_conn.receive_data()

        # Parse frame header
        version, data_length, consumed = decode_header(response_frame)
        response = response_frame[consumed:]

        if len(response) < 14:
            from ..error import S7ConnectionError
            raise S7ConnectionError("Response too short")

        return response[14:]

    def _create_session(self) -> None:
        """Send CreateObject request to establish an S7CommPlus session."""
        seq_num = self._next_sequence_number()

        # Build CreateObject request with NullServer session data
        request = struct.pack(
            ">BHHHHIB",
            Opcode.REQUEST,
            0x0000,
            FunctionCode.CREATE_OBJECT,
            0x0000,
            seq_num,
            0x00000000,  # No session yet
            0x36,
        )

        # Add empty request data (minimal CreateObject)
        request += struct.pack(">I", 0)

        # Wrap in S7CommPlus frame header
        frame = encode_header(ProtocolVersion.V1, len(request)) + request

        self._iso_conn.send_data(frame)

        # Receive response
        response_frame = self._iso_conn.receive_data()

        # Parse S7CommPlus frame header
        version, data_length, consumed = decode_header(response_frame)
        response = response_frame[consumed:]

        if len(response) < 14:
            from ..error import S7ConnectionError
            raise S7ConnectionError("CreateObject response too short")

        # Extract session ID from response header
        self._session_id = struct.unpack_from(">I", response, 9)[0]
        self._protocol_version = version

        logger.debug(f"Session created: id={self._session_id}, version=V{version}")

    def _delete_session(self) -> None:
        """Send DeleteObject to close the session."""
        seq_num = self._next_sequence_number()

        request = struct.pack(
            ">BHHHHIB",
            Opcode.REQUEST,
            0x0000,
            FunctionCode.DELETE_OBJECT,
            0x0000,
            seq_num,
            self._session_id,
            0x36,
        )
        request += struct.pack(">I", 0)

        frame = encode_header(self._protocol_version, len(request)) + request
        self._iso_conn.send_data(frame)

        # Best-effort receive
        try:
            self._iso_conn.receive_data()
        except Exception:
            pass

    def _next_sequence_number(self) -> int:
        """Get next sequence number and increment."""
        seq = self._sequence_number
        self._sequence_number = (self._sequence_number + 1) & 0xFFFF
        return seq

    def _setup_ssl_context(
        self,
        cert_path: Optional[str] = None,
        key_path: Optional[str] = None,
        ca_path: Optional[str] = None,
    ) -> ssl.SSLContext:
        """Create TLS context for S7CommPlus.

        Args:
            cert_path: Client certificate path (PEM)
            key_path: Client private key path (PEM)
            ca_path: PLC CA certificate path (PEM)

        Returns:
            Configured SSLContext
        """
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.minimum_version = ssl.TLSVersion.TLSv1_3

        if cert_path and key_path:
            ctx.load_cert_chain(cert_path, key_path)

        if ca_path:
            ctx.load_verify_locations(ca_path)
        else:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

        return ctx

    def __enter__(self) -> "S7CommPlusConnection":
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.disconnect()
