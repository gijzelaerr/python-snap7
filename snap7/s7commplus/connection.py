"""
S7CommPlus connection management.

Establishes an ISO-on-TCP connection to S7-1200/1500 PLCs using the
S7CommPlus protocol, with support for all protocol versions:

- V1: Early S7-1200 (FW >= V4.0). Simple session handshake.
- V2: Adds integrity checking and session authentication.
- V3: Adds public-key-based key exchange.
- V3 + TLS: TIA Portal V17+. Standard TLS 1.3 with per-device certificates.

The wire protocol (VLQ encoding, data types, function codes, object model) is
the same across all versions -- only the session authentication layer differs.

Connection sequence (all versions)::

    1. TCP connect to port 102
    2. COTP Connection Request / Confirm
       - Local TSAP: 0x0600
       - Remote TSAP: "SIMATIC-ROOT-HMI" (16-byte ASCII string)
    3. InitSSL request / response (unencrypted)
    4. TLS activation (for V3/TLS PLCs)
    5. S7CommPlus CreateObject request (NullServer session setup)
       - SessionId = ObjectNullServerSession (288)
       - Proper PObject tree with ServerSession class
    6. PLC responds with CreateObject response containing:
       - Protocol version (V1/V2/V3)
       - Session ID
       - Server session challenge (V2/V3)

Version-specific authentication after step 6::

    V1: No further authentication needed
    V2: Session key derivation and integrity checking
    V3 (no TLS): Public-key key exchange
    V3 (TLS): TLS 1.3 handshake is already done in step 4

Reference: thomas-v2/S7CommPlusDriver (C#, LGPL-3.0)
"""

import logging
import ssl
import struct
from typing import Optional, Type
from types import TracebackType

from ..connection import ISOTCPConnection
from .protocol import (
    FunctionCode,
    Opcode,
    ProtocolVersion,
    ElementID,
    ObjectId,
    S7COMMPLUS_LOCAL_TSAP,
    S7COMMPLUS_REMOTE_TSAP,
)
from .codec import encode_header, decode_header, encode_typed_value
from .vlq import encode_uint32_vlq
from .protocol import DataType

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
    ):
        self.host = host
        self.port = port

        self._iso_conn = ISOTCPConnection(
            host=host,
            port=port,
            local_tsap=S7COMMPLUS_LOCAL_TSAP,
            remote_tsap=S7COMMPLUS_REMOTE_TSAP,
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
            # Step 1: COTP connection (same TSAP for all S7CommPlus versions)
            self._iso_conn.connect(timeout)

            # Step 2: InitSSL handshake (required before CreateObject)
            self._init_ssl()

            # Step 3: TLS activation (required for modern firmware)
            if use_tls:
                # TODO: Perform TLS 1.3 handshake over the existing COTP connection
                raise NotImplementedError("TLS activation is not yet implemented. Use use_tls=False for V1 connections.")

            # Step 4: CreateObject (S7CommPlus session setup)
            self._create_session()

            # Step 5: Version-specific authentication
            if self._protocol_version >= ProtocolVersion.V3:
                if not use_tls:
                    logger.warning(
                        "PLC reports V3 protocol but TLS is not enabled. Connection may not work without use_tls=True."
                    )
            elif self._protocol_version == ProtocolVersion.V2:
                # TODO: Proprietary HMAC-SHA256/AES session auth
                raise NotImplementedError("V2 authentication is not yet implemented.")

            # V1: No further authentication needed after CreateObject
            self._connected = True
            logger.info(
                f"S7CommPlus connected to {self.host}:{self.port}, version=V{self._protocol_version}, session={self._session_id}"
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

    def send_request(self, function_code: int, payload: bytes = b"") -> bytes:
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
        request_header = struct.pack(
            ">BHHHHIB",
            Opcode.REQUEST,
            0x0000,  # Reserved
            function_code,
            0x0000,  # Reserved
            seq_num,
            self._session_id,
            0x36,  # Transport flags
        )
        request = request_header + payload

        logger.debug(f"=== SEND REQUEST === function_code=0x{function_code:04X} seq={seq_num} session=0x{self._session_id:08X}")
        logger.debug(f"  Request header (14 bytes): {request_header.hex(' ')}")
        logger.debug(f"  Request payload ({len(payload)} bytes): {payload.hex(' ')}")

        # Add S7CommPlus frame header and trailer, then send
        frame = encode_header(self._protocol_version, len(request)) + request
        frame += struct.pack(">BBH", 0x72, self._protocol_version, 0x0000)

        logger.debug(f"  Full frame ({len(frame)} bytes): {frame.hex(' ')}")
        self._iso_conn.send_data(frame)

        # Receive response
        response_frame = self._iso_conn.receive_data()
        logger.debug(f"=== RECV RESPONSE === raw frame ({len(response_frame)} bytes): {response_frame.hex(' ')}")

        # Parse frame header, use data_length to exclude trailer
        version, data_length, consumed = decode_header(response_frame)
        logger.debug(f"  Frame header: version=V{version}, data_length={data_length}, header_size={consumed}")

        response = response_frame[consumed : consumed + data_length]
        logger.debug(f"  Response data ({len(response)} bytes): {response.hex(' ')}")

        if len(response) < 14:
            from ..error import S7ConnectionError

            raise S7ConnectionError("Response too short")

        # Parse response header for debug
        resp_opcode = response[0]
        resp_func = struct.unpack_from(">H", response, 3)[0]
        resp_seq = struct.unpack_from(">H", response, 7)[0]
        resp_session = struct.unpack_from(">I", response, 9)[0]
        resp_transport = response[13]
        logger.debug(
            f"  Response header: opcode=0x{resp_opcode:02X} function=0x{resp_func:04X} "
            f"seq={resp_seq} session=0x{resp_session:08X} transport=0x{resp_transport:02X}"
        )

        resp_payload = response[14:]
        logger.debug(f"  Response payload ({len(resp_payload)} bytes): {resp_payload.hex(' ')}")

        # Check for trailer bytes after data_length
        trailer = response_frame[consumed + data_length :]
        if trailer:
            logger.debug(f"  Trailer ({len(trailer)} bytes): {trailer.hex(' ')}")

        return resp_payload

    def _init_ssl(self) -> None:
        """Send InitSSL request to prepare the connection.

        This is the first S7CommPlus message sent after COTP connect.
        The PLC responds with an InitSSL response. For PLCs that support
        TLS, the caller should then activate TLS before sending CreateObject.
        For V1 PLCs without TLS, the response may indicate that TLS is
        not supported, but the connection can continue without it.

        Reference: thomas-v2/S7CommPlusDriver InitSslRequest
        """
        seq_num = self._next_sequence_number()

        # InitSSL request: header + padding
        request = struct.pack(
            ">BHHHHIB",
            Opcode.REQUEST,
            0x0000,  # Reserved
            FunctionCode.INIT_SSL,
            0x0000,  # Reserved
            seq_num,
            0x00000000,  # No session yet
            0x30,  # Transport flags (0x30 for InitSSL)
        )
        # Trailing padding
        request += struct.pack(">I", 0)

        # Wrap in S7CommPlus frame header + trailer
        frame = encode_header(ProtocolVersion.V1, len(request)) + request
        frame += struct.pack(">BBH", 0x72, ProtocolVersion.V1, 0x0000)

        logger.debug(f"=== InitSSL === sending ({len(frame)} bytes): {frame.hex(' ')}")
        self._iso_conn.send_data(frame)

        # Receive InitSSL response
        response_frame = self._iso_conn.receive_data()
        logger.debug(f"=== InitSSL === received ({len(response_frame)} bytes): {response_frame.hex(' ')}")

        # Parse S7CommPlus frame header
        version, data_length, consumed = decode_header(response_frame)
        response = response_frame[consumed:]

        if len(response) < 14:
            from ..error import S7ConnectionError

            raise S7ConnectionError("InitSSL response too short")

        logger.debug(f"InitSSL response: version=V{version}, data_length={data_length}")
        logger.debug(f"InitSSL response body ({len(response)} bytes): {response.hex(' ')}")

    def _create_session(self) -> None:
        """Send CreateObject request to establish an S7CommPlus session.

        Builds a NullServerSession CreateObject request matching the
        structure expected by S7-1200/1500 PLCs:

        Reference: thomas-v2/S7CommPlusDriver CreateObjectRequest.SetNullServerSessionData()
        """
        seq_num = self._next_sequence_number()

        # Build CreateObject request header
        request = struct.pack(
            ">BHHHHIB",
            Opcode.REQUEST,
            0x0000,
            FunctionCode.CREATE_OBJECT,
            0x0000,
            seq_num,
            ObjectId.OBJECT_NULL_SERVER_SESSION,  # SessionId = 288 for initial setup
            0x36,  # Transport flags
        )

        # RequestId: ObjectServerSessionContainer (285)
        request += struct.pack(">I", ObjectId.OBJECT_SERVER_SESSION_CONTAINER)

        # RequestValue: ValueUDInt(0) = DatatypeFlags(0x00) + Datatype.UDInt(0x04) + VLQ(0)
        request += bytes([0x00, DataType.UDINT]) + encode_uint32_vlq(0)

        # Unknown padding (always 0)
        request += struct.pack(">I", 0)

        # RequestObject: PObject for NullServerSession
        # StartOfObject
        request += bytes([ElementID.START_OF_OBJECT])
        # RelationId: GetNewRIDOnServer (211)
        request += struct.pack(">I", ObjectId.GET_NEW_RID_ON_SERVER)
        # ClassId: ClassServerSession (287), VLQ encoded
        request += encode_uint32_vlq(ObjectId.CLASS_SERVER_SESSION)
        # ClassFlags: 0
        request += encode_uint32_vlq(0)
        # AttributeId: None (0)
        request += encode_uint32_vlq(0)

        # Attribute: ServerSessionClientRID (300) = RID 0x80c3c901
        request += bytes([ElementID.ATTRIBUTE])
        request += encode_uint32_vlq(ObjectId.SERVER_SESSION_CLIENT_RID)
        request += encode_typed_value(DataType.RID, 0x80C3C901)

        # Nested object: ClassSubscriptions
        request += bytes([ElementID.START_OF_OBJECT])
        request += struct.pack(">I", ObjectId.GET_NEW_RID_ON_SERVER)
        request += encode_uint32_vlq(ObjectId.CLASS_SUBSCRIPTIONS)
        request += encode_uint32_vlq(0)  # ClassFlags
        request += encode_uint32_vlq(0)  # AttributeId
        request += bytes([ElementID.TERMINATING_OBJECT])

        # End outer object
        request += bytes([ElementID.TERMINATING_OBJECT])

        # Trailing padding
        request += struct.pack(">I", 0)

        # Wrap in S7CommPlus frame header + trailer
        frame = encode_header(ProtocolVersion.V1, len(request)) + request
        # S7CommPlus trailer (end-of-frame marker)
        frame += struct.pack(">BBH", 0x72, ProtocolVersion.V1, 0x0000)

        logger.debug(f"=== CreateObject === sending ({len(frame)} bytes): {frame.hex(' ')}")
        self._iso_conn.send_data(frame)

        # Receive response
        response_frame = self._iso_conn.receive_data()
        logger.debug(f"=== CreateObject === received ({len(response_frame)} bytes): {response_frame.hex(' ')}")

        # Parse S7CommPlus frame header
        version, data_length, consumed = decode_header(response_frame)
        response = response_frame[consumed:]

        logger.debug(f"CreateObject response: version=V{version}, data_length={data_length}")
        logger.debug(f"CreateObject response body ({len(response)} bytes): {response.hex(' ')}")

        if len(response) < 14:
            from ..error import S7ConnectionError

            raise S7ConnectionError("CreateObject response too short")

        # Extract session ID from response header
        self._session_id = struct.unpack_from(">I", response, 9)[0]
        self._protocol_version = version

        # Parse and log the full response header
        resp_opcode = response[0]
        resp_func = struct.unpack_from(">H", response, 3)[0]
        resp_seq = struct.unpack_from(">H", response, 7)[0]
        resp_transport = response[13]
        logger.debug(
            f"CreateObject response header: opcode=0x{resp_opcode:02X} function=0x{resp_func:04X} "
            f"seq={resp_seq} session=0x{self._session_id:08X} transport=0x{resp_transport:02X}"
        )
        logger.debug(f"CreateObject response payload: {response[14:].hex(' ')}")
        logger.debug(f"Session created: id=0x{self._session_id:08X} ({self._session_id}), version=V{version}")

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
        frame += struct.pack(">BBH", 0x72, self._protocol_version, 0x0000)
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
