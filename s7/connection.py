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

from snap7.connection import ISOTCPConnection
from .protocol import (
    FunctionCode,
    Opcode,
    ProtocolVersion,
    ElementID,
    ObjectId,
    S7COMMPLUS_LOCAL_TSAP,
    S7COMMPLUS_REMOTE_TSAP,
    READ_FUNCTION_CODES,
)
from .codec import encode_header, decode_header, encode_object_qualifier
from .vlq import encode_uint32_vlq, decode_uint32_vlq, decode_uint64_vlq
from .protocol import DataType

logger = logging.getLogger(__name__)


def _element_size(datatype: int) -> int:
    """Return the fixed byte size for an array element, or 0 for variable-length."""
    if datatype in (DataType.BOOL, DataType.USINT, DataType.BYTE, DataType.SINT):
        return 1
    elif datatype in (DataType.UINT, DataType.WORD, DataType.INT):
        return 2
    elif datatype in (DataType.REAL, DataType.RID):
        return 4
    elif datatype in (DataType.LREAL, DataType.TIMESTAMP):
        return 8
    else:
        return 0


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
        self._ssl_socket: Optional[ssl.SSLSocket] = None
        self._session_id: int = 0
        self._sequence_number: int = 0
        self._protocol_version: int = 0  # Detected from PLC response
        self._tls_active: bool = False
        self._connected = False
        self._server_session_version: Optional[int] = None
        self._server_session_version_raw: Optional[bytes] = None
        self._session_setup_ok: bool = False

        # V2+ IntegrityId tracking
        self._integrity_id_read: int = 0
        self._integrity_id_write: int = 0
        self._with_integrity_id: bool = False

        # TLS OMS exporter secret (for legitimation key derivation)
        self._oms_secret: Optional[bytes] = None

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

    @property
    def integrity_id_read(self) -> int:
        """Current read IntegrityId counter (V2+)."""
        return self._integrity_id_read

    @property
    def integrity_id_write(self) -> int:
        """Current write IntegrityId counter (V2+)."""
        return self._integrity_id_write

    @property
    def session_setup_ok(self) -> bool:
        """Whether the session setup (ServerSessionVersion echo) succeeded."""
        return self._session_setup_ok

    @property
    def oms_secret(self) -> Optional[bytes]:
        """OMS exporter secret from TLS session (for legitimation)."""
        return self._oms_secret

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
        2. InitSSL handshake
        3. TLS activation (if use_tls=True, required for V2)
        4. CreateObject to establish S7CommPlus session
        5. Session setup (echo ServerSessionVersion)
        6. Enable IntegrityId tracking (V2+)

        Args:
            timeout: Connection timeout in seconds
            use_tls: Whether to activate TLS after InitSSL.
            tls_cert: Path to client TLS certificate (PEM)
            tls_key: Path to client private key (PEM)
            tls_ca: Path to CA certificate for PLC verification (PEM)
        """
        try:
            # Step 1: COTP connection (same TSAP for all S7CommPlus versions)
            self._iso_conn.connect(timeout)

            # Step 2: InitSSL handshake (required before CreateObject)
            self._init_ssl()

            # Step 3: TLS activation (between InitSSL and CreateObject)
            if use_tls:
                self._activate_tls(tls_cert=tls_cert, tls_key=tls_key, tls_ca=tls_ca)

            # Step 4: CreateObject (S7CommPlus session setup)
            # CreateObject always uses V1 framing
            self._create_session()

            # Step 5: Session setup - echo ServerSessionVersion back to PLC
            if self._server_session_version_raw is not None or self._server_session_version is not None:
                self._session_setup_ok = self._setup_session()
            else:
                logger.warning("PLC did not provide ServerSessionVersion - session setup incomplete")
                self._session_setup_ok = False

            # Step 6: Version-specific post-setup
            if self._protocol_version >= ProtocolVersion.V3:
                if not use_tls:
                    logger.warning(
                        "PLC reports V3 protocol but TLS is not enabled. Connection may not work without use_tls=True."
                    )
            elif self._protocol_version == ProtocolVersion.V2:
                if not self._tls_active:
                    from snap7.error import S7ConnectionError

                    raise S7ConnectionError("PLC reports V2 protocol but TLS is not active. V2 requires TLS. Use use_tls=True.")
                # Enable IntegrityId tracking for V2+
                self._with_integrity_id = True
                self._integrity_id_read = 0
                self._integrity_id_write = 0
                logger.info("V2 IntegrityId tracking enabled")

            # V1: No further authentication needed after CreateObject
            self._connected = True
            logger.info(
                f"S7CommPlus connected to {self.host}:{self.port}, "
                f"version=V{self._protocol_version}, session={self._session_id}, "
                f"tls={self._tls_active}"
            )

        except Exception:
            self.disconnect()
            raise

    def authenticate(self, password: str, username: str = "") -> None:
        """Perform PLC password authentication (legitimation).

        Must be called after connect() and before data operations on
        password-protected PLCs. Requires TLS to be active (V2+).

        The method auto-detects legacy vs new legitimation based on
        the PLC's firmware version (stored in ServerSessionVersion).

        Args:
            password: PLC password
            username: Username for new-style auth (optional)

        Raises:
            S7ConnectionError: If not connected, TLS not active, or auth fails
        """
        if not self._connected:
            from snap7.error import S7ConnectionError

            raise S7ConnectionError("Not connected")

        if not self._tls_active or self._oms_secret is None:
            from snap7.error import S7ConnectionError

            raise S7ConnectionError("Legitimation requires TLS. Connect with use_tls=True.")

        # Step 1: Get challenge from PLC via GetVarSubStreamed
        challenge = self._get_legitimation_challenge()
        logger.info(f"Received legitimation challenge ({len(challenge)} bytes)")

        # Step 2: Build response (auto-detect legacy vs new)
        from .legitimation import build_legacy_response, build_new_response

        if username:
            # New-style auth with username always uses AES-256-CBC
            response_data = build_new_response(password, challenge, self._oms_secret, username)
            self._send_legitimation_new(response_data)
        else:
            # Try new-style first, fall back to legacy SHA-1 XOR
            try:
                response_data = build_new_response(password, challenge, self._oms_secret, "")
                self._send_legitimation_new(response_data)
            except NotImplementedError:
                # cryptography package not available, use legacy
                response_data = build_legacy_response(password, challenge)
                self._send_legitimation_legacy(response_data)

        logger.info("PLC legitimation completed successfully")

    def _get_legitimation_challenge(self) -> bytes:
        """Request legitimation challenge from PLC.

        Sends GetVarSubStreamed with address ServerSessionRequest (303).

        Returns:
            Challenge bytes from PLC (typically 20 bytes)
        """
        from .protocol import LegitimationId

        # Build GetVarSubStreamed request
        payload = bytearray()
        # InObjectId = session ID
        payload += struct.pack(">I", self._session_id)
        # Item count = 1
        payload += encode_uint32_vlq(1)
        # Address field count = 1
        payload += encode_uint32_vlq(1)
        # Address = ServerSessionRequest (303)
        payload += encode_uint32_vlq(LegitimationId.SERVER_SESSION_REQUEST)
        # Trailing padding
        payload += struct.pack(">I", 0)

        resp_payload = self.send_request(FunctionCode.GET_VAR_SUBSTREAMED, bytes(payload))

        # Parse response: return value + value list
        offset = 0
        return_value, consumed = decode_uint64_vlq(resp_payload, offset)
        offset += consumed

        if return_value != 0:
            from snap7.error import S7ConnectionError

            raise S7ConnectionError(f"GetVarSubStreamed for challenge failed: return_value={return_value}")

        # Value is a USIntArray (BLOB) - read flags + type + length + data
        if offset + 2 > len(resp_payload):
            from snap7.error import S7ConnectionError

            raise S7ConnectionError("Challenge response too short")

        _flags = resp_payload[offset]
        datatype = resp_payload[offset + 1]
        offset += 2

        from .protocol import DataType

        if datatype == DataType.BLOB:
            length, consumed = decode_uint32_vlq(resp_payload, offset)
            offset += consumed
            return bytes(resp_payload[offset : offset + length])
        else:
            # Try reading as array of USINT
            count, consumed = decode_uint32_vlq(resp_payload, offset)
            offset += consumed
            return bytes(resp_payload[offset : offset + count])

    def _send_legitimation_new(self, encrypted_response: bytes) -> None:
        """Send new-style legitimation response (AES-256-CBC encrypted).

        Uses SetVariable with address Legitimate (1846).
        """
        from .protocol import LegitimationId, DataType

        payload = bytearray()
        # InObjectId = session ID
        payload += struct.pack(">I", self._session_id)
        # Address field count = 1
        payload += encode_uint32_vlq(1)
        # Address = Legitimate (1846)
        payload += encode_uint32_vlq(LegitimationId.LEGITIMATE)
        # Value: BLOB(0, encrypted_response)
        payload += bytes([0x00, DataType.BLOB])
        payload += encode_uint32_vlq(len(encrypted_response))
        payload += encrypted_response
        # Trailing padding
        payload += struct.pack(">I", 0)

        resp_payload = self.send_request(FunctionCode.SET_VARIABLE, bytes(payload))

        # Check return value
        if len(resp_payload) >= 1:
            return_value, _ = decode_uint64_vlq(resp_payload, 0)
            if return_value < 0:
                from snap7.error import S7ConnectionError

                raise S7ConnectionError(f"Legitimation rejected by PLC: return_value={return_value}")
            logger.debug(f"New legitimation return_value={return_value}")

    def _send_legitimation_legacy(self, response: bytes) -> None:
        """Send legacy legitimation response (SHA-1 XOR).

        Uses SetVariable with address ServerSessionResponse (304).
        """
        from .protocol import LegitimationId, DataType

        payload = bytearray()
        # InObjectId = session ID
        payload += struct.pack(">I", self._session_id)
        # Address field count = 1
        payload += encode_uint32_vlq(1)
        # Address = ServerSessionResponse (304)
        payload += encode_uint32_vlq(LegitimationId.SERVER_SESSION_RESPONSE)
        # Value: array of USINT (the XOR'd response bytes)
        payload += bytes([0x10, DataType.USINT])  # flags=0x10 (array)
        payload += encode_uint32_vlq(len(response))
        payload += response
        # Trailing padding
        payload += struct.pack(">I", 0)

        resp_payload = self.send_request(FunctionCode.SET_VARIABLE, bytes(payload))

        # Check return value
        if len(resp_payload) >= 1:
            return_value, _ = decode_uint64_vlq(resp_payload, 0)
            if return_value < 0:
                from snap7.error import S7ConnectionError

                raise S7ConnectionError(f"Legacy legitimation rejected by PLC: return_value={return_value}")
            logger.debug(f"Legacy legitimation return_value={return_value}")

    def disconnect(self) -> None:
        """Disconnect from PLC."""
        if self._connected and self._session_id:
            try:
                self._delete_session()
            except Exception:
                pass

        self._connected = False
        self._session_setup_ok = False
        self._tls_active = False
        self._ssl_socket = None
        self._oms_secret = None
        self._session_id = 0
        self._sequence_number = 0
        self._protocol_version = 0
        self._server_session_version = None
        self._server_session_version_raw = None
        self._with_integrity_id = False
        self._integrity_id_read = 0
        self._integrity_id_write = 0
        self._iso_conn.disconnect()

    def send_request(self, function_code: int, payload: bytes = b"") -> bytes:
        """Send an S7CommPlus request and receive the response.

        For V2+ with IntegrityId tracking enabled, the IntegrityId is
        appended after the 14-byte request header (as a VLQ uint32).
        Read vs write counters are selected based on the function code.

        Args:
            function_code: S7CommPlus function code
            payload: Request payload (after the 14-byte request header)

        Returns:
            Response payload (after the 14-byte response header)
        """
        if not self._connected:
            from snap7.error import S7ConnectionError

            raise S7ConnectionError("Not connected")

        seq_num = self._next_sequence_number()

        # Build request header (14 bytes)
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

        # For V2+ with IntegrityId enabled, insert IntegrityId after header
        integrity_id_bytes = b""
        if self._with_integrity_id and self._protocol_version >= ProtocolVersion.V2:
            is_read = function_code in READ_FUNCTION_CODES
            if is_read:
                integrity_id = self._integrity_id_read
            else:
                integrity_id = self._integrity_id_write
            integrity_id_bytes = encode_uint32_vlq(integrity_id)
            logger.debug(f"  IntegrityId: {'read' if is_read else 'write'}={integrity_id}")

        request = request_header + integrity_id_bytes + payload

        logger.debug(f"=== SEND REQUEST === function_code=0x{function_code:04X} seq={seq_num} session=0x{self._session_id:08X}")
        logger.debug(f"  Request header (14 bytes): {request_header.hex(' ')}")
        if integrity_id_bytes:
            logger.debug(f"  IntegrityId ({len(integrity_id_bytes)} bytes): {integrity_id_bytes.hex(' ')}")
        logger.debug(f"  Request payload ({len(payload)} bytes): {payload.hex(' ')}")

        # Determine frame version: V2 data PDUs use V2, but CreateObject uses V1
        frame_version = self._protocol_version

        # Add S7CommPlus frame header and trailer, then send
        frame = encode_header(frame_version, len(request)) + request
        frame += struct.pack(">BBH", 0x72, frame_version, 0x0000)

        logger.debug(f"  Full frame ({len(frame)} bytes): {frame.hex(' ')}")
        self._iso_conn.send_data(frame)

        # Increment the appropriate IntegrityId counter after sending
        if self._with_integrity_id and self._protocol_version >= ProtocolVersion.V2:
            if function_code in READ_FUNCTION_CODES:
                self._integrity_id_read = (self._integrity_id_read + 1) & 0xFFFFFFFF
            else:
                self._integrity_id_write = (self._integrity_id_write + 1) & 0xFFFFFFFF

        # Receive response
        response_frame = self._iso_conn.receive_data()
        logger.debug(f"=== RECV RESPONSE === raw frame ({len(response_frame)} bytes): {response_frame.hex(' ')}")

        # Parse frame header, use data_length to exclude trailer
        version, data_length, consumed = decode_header(response_frame)
        logger.debug(f"  Frame header: version=V{version}, data_length={data_length}, header_size={consumed}")

        response = response_frame[consumed : consumed + data_length]
        logger.debug(f"  Response data ({len(response)} bytes): {response.hex(' ')}")

        if len(response) < 14:
            from snap7.error import S7ConnectionError

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

        # For V2+ responses, skip IntegrityId in response before returning payload
        resp_offset = 14
        if self._with_integrity_id and self._protocol_version >= ProtocolVersion.V2:
            if resp_offset < len(response):
                resp_integrity_id, iid_consumed = decode_uint32_vlq(response, resp_offset)
                resp_offset += iid_consumed
                logger.debug(f"  Response IntegrityId: {resp_integrity_id}")

        resp_payload = response[resp_offset:]
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
            from snap7.error import S7ConnectionError

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

        # ServerSession attributes — full TIA-Portal-style identification.
        # V1-initial S7-1200 firmware (e.g. FW v4.2.x) only returns
        # ServerSessionVersion in its CreateObject response when the client
        # introduces itself with this fuller attribute set; minimal requests
        # (ClientRID only) get an incomplete session. See GH-712.
        def _wstring_attr(attr_id: int, s: str) -> bytes:
            data = s.encode("utf-8")
            return (
                bytes([ElementID.ATTRIBUTE])
                + encode_uint32_vlq(attr_id)
                + bytes([0x00, DataType.WSTRING])
                + encode_uint32_vlq(len(data))
                + data
            )

        client_id = "python-snap7"
        request += _wstring_attr(233, client_id)  # ObjectVariableTypeName / class name
        request += _wstring_attr(289, f"1:::6.0::{client_id}")  # network interface info
        request += _wstring_attr(296, client_id)  # project name
        request += _wstring_attr(297, "")
        request += _wstring_attr(298, client_id)  # hostname
        # 299: UDInt(1)
        request += bytes([ElementID.ATTRIBUTE]) + encode_uint32_vlq(299)
        request += bytes([0x00, DataType.UDINT]) + encode_uint32_vlq(1)
        # 300: ServerSessionClientRID
        request += bytes([ElementID.ATTRIBUTE])
        request += encode_uint32_vlq(ObjectId.SERVER_SESSION_CLIENT_RID)
        request += bytes([0x00, DataType.RID]) + struct.pack(">I", 0x80C3C901)
        request += _wstring_attr(301, "")

        # Nested object: ClassSubscriptions, with required class-name attribute
        request += bytes([ElementID.START_OF_OBJECT])
        request += struct.pack(">I", ObjectId.GET_NEW_RID_ON_SERVER)
        request += encode_uint32_vlq(ObjectId.CLASS_SUBSCRIPTIONS)
        request += encode_uint32_vlq(0)  # ClassFlags
        request += encode_uint32_vlq(0)  # AttributeId
        request += _wstring_attr(233, "SubscriptionContainer")
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
            from snap7.error import S7ConnectionError

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

        # Parse response payload to extract ServerSessionVersion
        self._parse_create_object_response(response[14:])

    def _parse_create_object_response(self, payload: bytes) -> None:
        """Parse CreateObject response payload to extract ServerSessionVersion.

        The response contains a PObject tree with attributes. We scan for
        attribute 306 (ServerSessionVersion) which must be echoed back to
        complete the session handshake.

        Args:
            payload: Response payload after the 14-byte response header
        """
        offset = 0
        while offset < len(payload):
            tag = payload[offset]

            if tag == ElementID.ATTRIBUTE:
                offset += 1
                if offset >= len(payload):
                    break
                attr_id, consumed = decode_uint32_vlq(payload, offset)
                offset += consumed

                if attr_id == ObjectId.SERVER_SESSION_VERSION:
                    # Typed value: flags + datatype + value
                    if offset + 2 > len(payload):
                        break
                    _flags = payload[offset]
                    datatype = payload[offset + 1]
                    if datatype == DataType.STRUCT:
                        # Real S7-1200/1500 PLCs send ServerSessionVersion as
                        # Struct(314); capture it verbatim for the V2 setup echo.
                        value_start = offset
                        offset += 2
                        offset = self._skip_typed_value(payload, offset, DataType.STRUCT, _flags)
                        self._server_session_version_raw = bytes(payload[value_start:offset])
                        logger.info(f"ServerSessionVersion struct captured ({len(self._server_session_version_raw)} bytes)")
                        return
                    offset += 2
                    if datatype == DataType.UDINT:
                        value, consumed = decode_uint32_vlq(payload, offset)
                        offset += consumed
                        self._server_session_version = value
                        logger.info(f"ServerSessionVersion = {value}")
                        return
                    elif datatype == DataType.DWORD:
                        value, consumed = decode_uint32_vlq(payload, offset)
                        offset += consumed
                        self._server_session_version = value
                        logger.info(f"ServerSessionVersion = {value}")
                        return
                    else:
                        # Skip unknown type - try to continue scanning
                        logger.debug(f"ServerSessionVersion has unexpected type {datatype:#04x}")
                else:
                    # Skip this attribute's value - we don't parse it, just advance
                    # Try to skip the typed value (flags + datatype + value)
                    if offset + 2 > len(payload):
                        break
                    _flags = payload[offset]
                    datatype = payload[offset + 1]
                    offset += 2
                    offset = self._skip_typed_value(payload, offset, datatype, _flags)

            elif tag == ElementID.START_OF_OBJECT:
                offset += 1
                # Skip RelationId (4 bytes fixed) + ClassId (VLQ) + ClassFlags (VLQ) + AttributeId (VLQ)
                if offset + 4 > len(payload):
                    break
                offset += 4  # RelationId
                _, consumed = decode_uint32_vlq(payload, offset)
                offset += consumed  # ClassId
                _, consumed = decode_uint32_vlq(payload, offset)
                offset += consumed  # ClassFlags
                _, consumed = decode_uint32_vlq(payload, offset)
                offset += consumed  # AttributeId

            elif tag == ElementID.TERMINATING_OBJECT:
                offset += 1

            elif tag == 0x00:
                # Null terminator / padding
                offset += 1

            else:
                # Unknown tag - try to skip
                offset += 1

        logger.debug("ServerSessionVersion not found in CreateObject response")

    def _skip_typed_value(self, data: bytes, offset: int, datatype: int, flags: int) -> int:
        """Skip over a typed value in the PObject tree.

        Best-effort: advances offset past common value types.
        Returns new offset.
        """
        is_array = bool(flags & 0x10)

        if is_array:
            if offset >= len(data):
                return offset
            count, consumed = decode_uint32_vlq(data, offset)
            offset += consumed
            # For fixed-size types, skip count * size
            elem_size = _element_size(datatype)
            if elem_size > 0:
                offset += count * elem_size
            else:
                # Variable-length: skip each VLQ element
                for _ in range(count):
                    if offset >= len(data):
                        break
                    _, consumed = decode_uint32_vlq(data, offset)
                    offset += consumed
            return offset

        if datatype == DataType.NULL:
            return offset
        elif datatype in (DataType.BOOL, DataType.USINT, DataType.BYTE, DataType.SINT):
            return offset + 1
        elif datatype in (DataType.UINT, DataType.WORD, DataType.INT):
            return offset + 2
        elif datatype in (DataType.UDINT, DataType.DWORD, DataType.AID, DataType.DINT):
            _, consumed = decode_uint32_vlq(data, offset)
            return offset + consumed
        elif datatype in (DataType.ULINT, DataType.LWORD, DataType.LINT):
            _, consumed = decode_uint64_vlq(data, offset)
            return offset + consumed
        elif datatype == DataType.REAL:
            return offset + 4
        elif datatype == DataType.LREAL:
            return offset + 8
        elif datatype == DataType.TIMESTAMP:
            return offset + 8
        elif datatype == DataType.TIMESPAN:
            _, consumed = decode_uint64_vlq(data, offset)  # int64 VLQ
            return offset + consumed
        elif datatype == DataType.RID:
            return offset + 4
        elif datatype in (DataType.BLOB, DataType.WSTRING):
            length, consumed = decode_uint32_vlq(data, offset)
            return offset + consumed + length
        elif datatype == DataType.STRUCT:
            # Struct format: 4-byte UInt32 ID, then a sequence of
            # (VLQ key, nested PValue=flags+dtype+value) pairs, terminated
            # by a single 0x00 byte.
            if offset + 4 > len(data):
                return offset
            offset += 4
            while offset < len(data):
                if data[offset] == 0x00:
                    offset += 1
                    break
                _, consumed = decode_uint32_vlq(data, offset)
                offset += consumed
                if offset + 2 > len(data):
                    return offset
                sub_flags = data[offset]
                sub_type = data[offset + 1]
                offset += 2
                offset = self._skip_typed_value(data, offset, sub_type, sub_flags)
            return offset
        else:
            # Unknown type - can't skip reliably
            return offset

    def _setup_session(self) -> bool:
        """Send V2 SetMultiVariables to echo ServerSessionVersion back to the PLC.

        Always uses V2 framing (`72 02 ...`), transport flags 0x34, and no
        IntegrityId — these are the established session-setup conventions
        regardless of which version the PLC negotiated on initial connect.
        See ``thomas-v2/S7CommPlusDriver`` ``SetMultiVariablesRequest.SetSessionSetupData``.

        Without this step, the PLC rejects all subsequent data operations
        with ERROR2 (0x05A9).

        Returns:
            True if session setup succeeded (return_value == 0).
        """
        if self._server_session_version_raw is None and self._server_session_version is None:
            return False

        seq_num = self._next_sequence_number()

        # SET_MULTI_VARIABLES request header. Transport flags = 0x34 for the
        # session-setup write (vs 0x36 for normal data ops).
        request = struct.pack(
            ">BHHHHIB",
            Opcode.REQUEST,
            0x0000,
            FunctionCode.SET_MULTI_VARIABLES,
            0x0000,
            seq_num,
            self._session_id,
            0x34,
        )

        payload = bytearray()
        payload += struct.pack(">I", self._session_id)  # InObjectId
        payload += encode_uint32_vlq(1)  # ItemCount
        payload += encode_uint32_vlq(1)  # AddressCount
        payload += encode_uint32_vlq(ObjectId.SERVER_SESSION_VERSION)  # Address: 306
        payload += encode_uint32_vlq(1)  # ItemNumber

        if self._server_session_version_raw is not None:
            # Echo the Struct(314) value verbatim (real S7-1200/1500 path).
            payload += self._server_session_version_raw
        else:
            # Test/emulator path: scalar UDInt fallback.
            payload += bytes([0x00, DataType.UDINT])
            payload += encode_uint32_vlq(self._server_session_version or 0)

        payload += bytes([0x00])  # Fill byte
        payload += encode_object_qualifier()
        # No IntegrityId — WithIntegrityId=false for session setup.
        payload += struct.pack(">I", 0)  # Trailing padding

        request += bytes(payload)

        # Outer S7+ frame is always V2 for the setup write, even if the PLC
        # negotiated V1 on the initial CreateObject.
        frame = encode_header(ProtocolVersion.V2, len(request)) + request
        frame += struct.pack(">BBH", 0x72, ProtocolVersion.V2, 0x0000)

        logger.debug(f"=== SetupSession === sending ({len(frame)} bytes): {frame.hex(' ')}")
        self._iso_conn.send_data(frame)

        # Receive response
        response_frame = self._iso_conn.receive_data()
        logger.debug(f"=== SetupSession === received ({len(response_frame)} bytes): {response_frame.hex(' ')}")

        version, data_length, consumed = decode_header(response_frame)
        response = response_frame[consumed : consumed + data_length]

        if len(response) < 14:
            from snap7.error import S7ConnectionError

            raise S7ConnectionError("SetupSession response too short")

        resp_func = struct.unpack_from(">H", response, 3)[0]
        logger.debug(f"SetupSession response: function=0x{resp_func:04X}")

        # Parse return value from payload
        resp_payload = response[14:]
        if len(resp_payload) >= 1:
            return_value, _ = decode_uint64_vlq(resp_payload, 0)
            if return_value != 0:
                logger.warning(f"SetupSession: PLC returned error {return_value}")
                return False
            else:
                logger.info("Session setup completed successfully")
                return True
        return False

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

    def _activate_tls(
        self,
        tls_cert: Optional[str] = None,
        tls_key: Optional[str] = None,
        tls_ca: Optional[str] = None,
    ) -> None:
        """Activate TLS 1.3 over the COTP connection.

        Called after InitSSL and before CreateObject. Wraps the underlying
        TCP socket with TLS and extracts the OMS exporter secret for
        legitimation key derivation.

        Args:
            tls_cert: Path to client TLS certificate (PEM)
            tls_key: Path to client private key (PEM)
            tls_ca: Path to CA certificate for PLC verification (PEM)
        """
        ctx = self._setup_ssl_context(
            cert_path=tls_cert,
            key_path=tls_key,
            ca_path=tls_ca,
        )

        # Wrap the raw TCP socket used by ISOTCPConnection
        raw_socket = self._iso_conn.socket
        if raw_socket is None:
            from snap7.error import S7ConnectionError

            raise S7ConnectionError("Cannot activate TLS: no TCP socket")

        self._ssl_socket = ctx.wrap_socket(raw_socket, server_hostname=self.host)

        # Replace the socket in ISOTCPConnection so all subsequent
        # send_data/receive_data calls go through TLS
        self._iso_conn.socket = self._ssl_socket
        self._tls_active = True

        # Extract OMS exporter secret for legitimation key derivation
        try:
            self._oms_secret = self._ssl_socket.export_keying_material("EXPERIMENTAL_OMS", 32, None)
            logger.debug("OMS exporter secret extracted from TLS session")
        except (AttributeError, ssl.SSLError) as e:
            logger.warning(f"Could not extract OMS exporter secret: {e}")
            self._oms_secret = None

        logger.info("TLS 1.3 activated on COTP connection")

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

        # TLS 1.3 ciphersuites are configured differently from TLS 1.2
        if hasattr(ctx, "set_ciphersuites"):
            ctx.set_ciphersuites("TLS_AES_256_GCM_SHA384:TLS_AES_128_GCM_SHA256")
        # If set_ciphersuites not available, TLS 1.3 uses its mandatory defaults

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
