"""
S7CommPlus connection management.

Establishes an ISO-on-TCP connection to S7-1200/1500 PLCs using the
S7CommPlus protocol, with support for all protocol versions:

- V1: Early S7-1200 (FW >= V4.0). Simple session handshake.
- V2: Adds integrity checking and session authentication.
- V3: Adds public-key-based key exchange.
- V3 + TLS: TIA Portal V17+. TLS 1.2 with per-device certificates.

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
from .codec import (
    encode_header,
    decode_header,
    encode_typed_value,
    encode_object_qualifier,
    parse_create_object_session_id,
    parse_server_session_version,
)
from .vlq import encode_uint32_vlq, decode_uint32_vlq, decode_uint64_vlq
from .protocol import DataType

logger = logging.getLogger(__name__)

# TLS cipher suites for S7 PLC compatibility.
# ECDHE suites are preferred (forward secrecy); RSA-kx kept as fallback for
# older firmware.  The key to Siemens PLC compatibility is restricting the
# offered groups to x25519 via set_ecdh_curve — PLCs RST when they see
# unsupported groups like x448 or ffdhe*.
_S7_CIPHERS = (
    "ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:AES128-GCM-SHA256:AES256-GCM-SHA384:AES128-SHA256:AES256-SHA256"
)

# Siemens PLCs only accept a small set of TLS groups.  X25519 is preferred
# but unavailable on older OpenSSL/CPython; fall back to prime256v1.
_S7_PREFERRED_GROUPS = ("X25519", "prime256v1")


def _set_s7_groups(ctx: ssl.SSLContext) -> None:
    for group in _S7_PREFERRED_GROUPS:
        try:
            ctx.set_ecdh_curve(group)
            return
        except (ssl.SSLError, ValueError):
            continue
    logger.warning("Could not restrict TLS groups — PLC may reject unsupported groups in ClientHello")


class _BioTLS:
    """Thin wrapper over BIO-based TLS — either stdlib or pyOpenSSL.

    Provides a uniform interface for write/read/handshake/export_keying_material
    so the connection code doesn't branch on the backend.
    """

    def __init__(self, ctx: ssl.SSLContext, hostname: Optional[str]) -> None:
        self._backend: str = "stdlib"
        try:
            self._init_pyopenssl(ctx, hostname)
        except Exception:
            self._init_stdlib(ctx, hostname)

    def _init_stdlib(self, ctx: ssl.SSLContext, hostname: Optional[str]) -> None:
        self._backend = "stdlib"
        self._in_bio = ssl.MemoryBIO()
        self._out_bio = ssl.MemoryBIO()
        self._obj = ctx.wrap_bio(
            self._in_bio,
            self._out_bio,
            server_side=False,
            server_hostname=hostname,
        )

    def _init_pyopenssl(self, ctx: ssl.SSLContext, hostname: Optional[str]) -> None:
        from OpenSSL.SSL import Context, Connection, SSLv23_METHOD, WantReadError  # type: ignore[import-untyped]

        pyctx = Context(SSLv23_METHOD)
        pyctx.set_min_proto_version(ctx.minimum_version)
        pyctx.set_cipher_list(_S7_CIPHERS.encode())
        for group in _S7_PREFERRED_GROUPS:
            try:
                pyctx.set_tmp_ecdh_curve(group)
                break
            except Exception:
                continue
        pyctx.set_options(ctx.options)
        pyctx.set_verify(0x00, lambda *a: True)
        conn = Connection(pyctx, None)
        conn.set_connect_state()
        if hostname:
            conn.set_tlsext_host_name(hostname.encode())
        self._pyopenssl_conn = conn
        self._pyopenssl_want_read = WantReadError
        self._backend = "pyopenssl"

    def do_handshake(self) -> None:
        if self._backend == "pyopenssl":
            self._pyopenssl_conn.do_handshake()
        else:
            self._obj.do_handshake()

    def write(self, data: bytes) -> None:
        if self._backend == "pyopenssl":
            self._pyopenssl_conn.write(data)
        else:
            self._obj.write(data)

    def read(self, bufsize: int = 65536) -> bytes:
        if self._backend == "pyopenssl":
            return self._pyopenssl_conn.read(bufsize)
        else:
            return self._obj.read(bufsize)

    def bio_write(self, data: bytes) -> None:
        if self._backend == "pyopenssl":
            self._pyopenssl_conn.bio_write(data)
        else:
            self._in_bio.write(data)

    def bio_read(self) -> bytes:
        if self._backend == "pyopenssl":
            try:
                return self._pyopenssl_conn.bio_read(65536)
            except Exception:
                return b""
        else:
            return self._out_bio.read()

    @property
    def want_read_error(self) -> type:
        if self._backend == "pyopenssl":
            return self._pyopenssl_want_read
        return ssl.SSLWantReadError

    def export_keying_material(self, label: str, length: int) -> Optional[bytes]:
        if self._backend == "pyopenssl":
            return self._pyopenssl_conn.export_keying_material(label.encode(), length, False)
        try:
            return self._obj.export_keying_material(label, length, None)
        except (AttributeError, ssl.SSLError):
            return None


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
        self._tls: Optional[_BioTLS] = None
        self._session_id: int = 0
        self._sequence_number: int = 0
        self._protocol_version: int = 0  # Detected from PLC response
        self._tls_active: bool = False
        self._connected = False
        # ServerSessionVersion is captured as its raw typed value (flags+datatype+data)
        # so it can be echoed back verbatim — real S7-1500 PLCs send it as a Struct.
        self._server_session_version: Optional[bytes] = None
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

    @property
    def requires_substreamed(self) -> bool:
        """Whether data operations must use substreamed function codes.

        V1-initial PLCs with SessionKey auth reject GET_MULTI_VARIABLES
        (0x054C) and require GET_VAR_SUBSTREAMED (0x0586) /
        SET_VAR_SUBSTREAMED (0x057C) for all data operations.
        """
        return self._session_key is not None

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

            # After CreateObject (V1), data PDUs over TLS use ProtocolVersion V2 (matches C# driver)
            if self._tls_active:
                self._protocol_version = ProtocolVersion.V2

            # Step 5: Session setup - echo ServerSessionVersion back to PLC
            if self._server_session_version is not None:
                self._session_setup_ok = self._setup_session()
            else:
                logger.warning(
                    "PLC did not provide a scalar ServerSessionVersion attribute. "
                    "This is the V1-initial S7-1200 firmware band (FW < 4.5 "
                    "predating TLS) which sends a Struct(314) value and requires "
                    "the proprietary SessionKey handshake — not yet implemented "
                    "in python-snap7 (tracked in issue #710). Falling back to "
                    "legacy PUT/GET: db_read/db_write will work, browse() will not."
                )
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

    def collect_explore_frames(self, first_payload: bytes) -> bytes:
        """Collect multi-fragment EXPLORE continuation frames for V3 PLCs.

        On V3 PLCs (FW >= V4.5) a large EXPLORE response (e.g. RID 0x8A11FFFF)
        spans multiple TPKT frames.  The first frame is the normal response
        (already stripped of its 10-byte header by send_request).  Continuation
        frames carry **no** response header — they are raw BLOB data protected
        only by a V3 HMAC prefix.  The caller must concatenate them before
        parsing.

        Termination: a ``frag_len == 0`` frame is the standard S7CommPlus
        end-of-stream trailer.  As a fallback, a frame whose body (after HMAC
        strip) is measurably shorter than the first frame body is treated as the
        last fragment (5-byte tolerance).

        Collection is capped by ``_MAX_REASSEMBLED_FRAGMENTS`` and
        ``_MAX_REASSEMBLED_BYTES`` to prevent unbounded allocation on malformed
        or adversarial responses.

        Args:
            first_payload: First EXPLORE response payload, already returned by
                send_request() (10-byte response header already stripped).

        Returns:
            All fragment payloads concatenated (first_payload + continuations).
        """
        # The first frame body (already header-stripped) was originally
        # len(first_payload) + 10 bytes on the wire (10-byte response header).
        # Continuation frames of the same "full" size will be that long after
        # HMAC strip; a shorter body signals the last fragment.
        reference_size = len(first_payload) + 10
        all_data = first_payload
        fragment_count = 0
        while True:
            if len(all_data) > self._MAX_REASSEMBLED_BYTES or fragment_count >= self._MAX_REASSEMBLED_FRAGMENTS:
                from snap7.error import S7ConnectionError

                raise S7ConnectionError(
                    f"collect_explore_frames: response too large ({len(all_data)} bytes, {fragment_count} fragments)"
                )
            try:
                raw = self._recv_s7_data()
                if not raw:
                    break
                # Strip the 4-byte S7CommPlus fragment header (0x72 ver len:2)
                if len(raw) < 4 or raw[0] != 0x72:
                    break
                frag_len = (raw[2] << 8) | raw[3]
                if frag_len == 0:
                    break  # standard S7CommPlus end-of-stream trailer
                body = raw[4 : 4 + frag_len]
                # V3 non-TLS: strip the HMAC prefix ([hash_len][hash_bytes])
                if self._protocol_version >= ProtocolVersion.V3 and len(body) > 33:
                    hash_len = body[0]
                    body = body[1 + hash_len :]
                if not body:
                    break
                all_data += body
                fragment_count += 1
                if len(body) < reference_size - 5:
                    break  # fallback: shorter-than-full frame signals last fragment
            except Exception:
                break
        return all_data

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
        self._tls = None
        self._oms_secret = None
        self._session_id = 0
        self._sequence_number = 0
        self._protocol_version = 0
        self._server_session_version = None
        self._with_integrity_id = False
        self._integrity_id_read = 0
        self._integrity_id_write = 0
        self._iso_conn.disconnect()

    def send_request(self, function_code: int, payload: bytes = b"", integrity_tail: int = 4, reassemble: bool = False) -> bytes:
        """Send an S7CommPlus request and receive the response.

        For V2+ with IntegrityId tracking enabled, the IntegrityId is spliced into
        the request payload just before its trailing fill bytes. Read vs write
        counters are selected based on the function code.

        Args:
            function_code: S7CommPlus function code
            payload: Request payload (after the 14-byte request header)
            integrity_tail: number of trailing payload bytes the V2 IntegrityId is
                inserted *before* — 4 for GetMultiVariables/SetMultiVariables (a
                trailing UInt32), 5 for Explore (a trailing UInt32 + filler byte).
            reassemble: when True, concatenate a multi-fragment response (e.g. Explore)
                before returning its payload.

        Returns:
            Response payload (after the 10-byte response header)
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
            # Transport flags: 0x34 for GetMultiVariables and Explore, 0x36 otherwise.
            0x34 if function_code in (FunctionCode.GET_MULTI_VARIABLES, FunctionCode.EXPLORE) else 0x36,
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

        # The IntegrityId is spliced in just before the payload's trailing fill bytes
        # (integrity_tail of them), not right after the header.
        if integrity_id_bytes and len(payload) >= integrity_tail:
            request = request_header + payload[:-integrity_tail] + integrity_id_bytes + payload[-integrity_tail:]
        else:
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
        self._send_s7_data(frame)

        # Increment the appropriate IntegrityId counter after sending
        if self._with_integrity_id and self._protocol_version >= ProtocolVersion.V2:
            if function_code in READ_FUNCTION_CODES:
                self._integrity_id_read = (self._integrity_id_read + 1) & 0xFFFFFFFF
            else:
                self._integrity_id_write = (self._integrity_id_write + 1) & 0xFFFFFFFF

        # Large responses (e.g. Explore) are split across several S7CommPlus PDUs.
        if reassemble:
            data = self._recv_reassembled_payload()
            if len(data) < 10:
                from snap7.error import S7ConnectionError

                raise S7ConnectionError("Response too short")
            logger.debug(f"  Reassembled response ({len(data)} bytes), payload {len(data) - 10} bytes")
            return bytes(data[10:])

        # Receive response
        response_frame = self._recv_s7_data()
        logger.debug(f"=== RECV RESPONSE === raw frame ({len(response_frame)} bytes): {response_frame.hex(' ')}")

        # Parse frame header, use data_length to exclude trailer
        version, data_length, consumed = decode_header(response_frame)
        logger.debug(f"  Frame header: version=V{version}, data_length={data_length}, header_size={consumed}")

        response = response_frame[consumed : consumed + data_length]
        logger.debug(f"  Response data ({len(response)} bytes): {response.hex(' ')}")

        if len(response) < 10:
            from snap7.error import S7ConnectionError

            raise S7ConnectionError("Response too short")

        # Parse the 10-byte response header for debug (responses carry no SessionId)
        resp_opcode = response[0]
        resp_func = struct.unpack_from(">H", response, 3)[0]
        resp_seq = struct.unpack_from(">H", response, 7)[0]
        resp_transport = response[9]
        logger.debug(
            f"  Response header: opcode=0x{resp_opcode:02X} function=0x{resp_func:04X} "
            f"seq={resp_seq} transport=0x{resp_transport:02X}"
        )

        # RESPONSE header is 10 bytes (opcode+res+func+res+seqnr+transport) — responses have
        # NO SessionId field (requests do, making their header 14 bytes). Integrity is at the END.
        resp_offset = 10

        resp_payload = response[resp_offset:]
        logger.debug(f"  Response payload ({len(resp_payload)} bytes): {resp_payload.hex(' ')}")

        # Check for trailer bytes after data_length
        trailer = response_frame[consumed + data_length :]
        if trailer:
            logger.debug(f"  Trailer ({len(trailer)} bytes): {trailer.hex(' ')}")

        return resp_payload

    # Sanity caps for fragment reassembly — generous vs. any real PLC EXPLORE response,
    # but bounded so a malformed/adversarial stream can't drive unbounded allocation.
    _MAX_REASSEMBLED_BYTES = 16 * 1024 * 1024
    _MAX_REASSEMBLED_FRAGMENTS = 4096

    def _recv_reassembled_payload(self) -> bytes:
        """Receive a possibly-fragmented S7CommPlus response, returning its data section.

        A large response is split into several S7CommPlus PDUs. Each fragment is
        ``0x72 <ver> <len:2> <data:len>`` with no trailer; only the final fragment is
        followed by the ``0x72 <ver> 0x0000`` trailer. We concatenate the data parts
        of every fragment until the trailer is seen. Works for single-PDU responses
        too (one fragment immediately followed by the trailer).
        """
        from snap7.error import S7ConnectionError

        buf = bytearray()

        def ensure(n: int) -> None:
            while len(buf) < n:
                chunk = self._recv_s7_data()
                if not chunk:
                    raise S7ConnectionError("Connection closed during response reassembly")
                buf.extend(chunk)

        data = bytearray()
        fragments = 0
        while True:
            ensure(4)
            if buf[0] != 0x72:
                raise S7ConnectionError("Expected S7CommPlus fragment header (0x72)")
            frag_len = (buf[2] << 8) | buf[3]
            del buf[:4]
            if frag_len == 0:
                break  # standalone trailer (defensive)
            ensure(frag_len)
            data.extend(buf[:frag_len])
            del buf[:frag_len]
            fragments += 1
            if fragments > self._MAX_REASSEMBLED_FRAGMENTS or len(data) > self._MAX_REASSEMBLED_BYTES:
                raise S7ConnectionError(f"Reassembled response exceeds limits ({len(data)} bytes, {fragments} fragments)")
            # The next 4 bytes are either the trailer (0x72 ver 0x0000) or the next
            # fragment's header (0x72 ver len>0).
            ensure(4)
            if buf[0] == 0x72 and buf[2] == 0 and buf[3] == 0:
                del buf[:4]  # consume trailer — last fragment
                break
        return bytes(data)

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
        self._send_s7_data(frame)

        # Receive InitSSL response
        response_frame = self._recv_s7_data()
        logger.debug(f"=== InitSSL === received ({len(response_frame)} bytes): {response_frame.hex(' ')}")

        # Parse S7CommPlus frame header
        version, data_length, consumed = decode_header(response_frame)
        response = response_frame[consumed:]

        if len(response) < 10:
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

        # Attribute: ServerSessionClientRID (300) = RID 0x80c3c901.
        # PValue on the wire is DatatypeFlags(1) + Datatype(1) + value; encode_typed_value emits
        # only Datatype+value (by codec contract), so prepend the flags byte here at the call site.
        request += bytes([ElementID.ATTRIBUTE])
        request += encode_uint32_vlq(ObjectId.SERVER_SESSION_CLIENT_RID)
        request += bytes([0x00]) + encode_typed_value(DataType.RID, 0x80C3C901)

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
        self._send_s7_data(frame)

        # Receive response
        response_frame = self._recv_s7_data()
        logger.debug(f"=== CreateObject === received ({len(response_frame)} bytes): {response_frame.hex(' ')}")

        # Parse S7CommPlus frame header
        version, data_length, consumed = decode_header(response_frame)
        response = response_frame[consumed:]

        logger.debug(f"CreateObject response: version=V{version}, data_length={data_length}")
        logger.debug(f"CreateObject response body ({len(response)} bytes): {response.hex(' ')}")

        if len(response) < 10:
            from snap7.error import S7ConnectionError

            raise S7ConnectionError("CreateObject response too short")

        # Response header is 10 bytes (opcode+reserved+func+reserved+seq+transport).
        # Responses do NOT carry a SessionId field (unlike requests which are 14 bytes).
        # The session ID comes from the payload body, not the header.
        body = response[10:]
        object_ids, obj_end, return_value = parse_create_object_session_id(body)
        if object_ids:
            self._session_id = object_ids[0]
        else:
            self._session_id = struct.unpack_from(">I", response, 9)[0]
        self._protocol_version = version

        # Parse and log the full response header
        resp_opcode = response[0]
        resp_func = struct.unpack_from(">H", response, 3)[0]
        resp_seq = struct.unpack_from(">H", response, 7)[0]
        resp_transport = response[9]
        logger.debug(
            f"CreateObject response header: opcode=0x{resp_opcode:02X} function=0x{resp_func:04X} "
            f"seq={resp_seq} session=0x{self._session_id:08X} transport=0x{resp_transport:02X}"
        )
        logger.debug(f"CreateObject response payload: {response[10:].hex(' ')}")
        logger.debug(f"Session created: id=0x{self._session_id:08X} ({self._session_id}), version=V{version}")

        if return_value != 0:
            logger.warning(f"CreateObject returned error 0x{return_value:X} — PLC may require TLS (use_tls=True)")

        # Parse response payload to extract ServerSessionVersion
        self._server_session_version = parse_server_session_version(response[10 + obj_end :])
        if self._server_session_version is not None:
            logger.info(f"ServerSessionVersion captured: {len(self._server_session_version)} bytes")
        else:
            logger.debug("ServerSessionVersion not found in CreateObject response")

    def _setup_session(self) -> bool:
        """Send SetMultiVariables to echo ServerSessionVersion back to the PLC.

        This completes the session handshake by writing the ServerSessionVersion
        attribute back to the session object. Without this step, the PLC rejects
        all subsequent data operations with ERROR2 (0x05A9).

        Returns:
            True if session setup succeeded (return_value == 0).

        Reference: thomas-v2/S7CommPlusDriver SetSessionSetupData
        """
        if self._server_session_version is None:
            return False

        seq_num = self._next_sequence_number()

        # Build SetMultiVariables request
        request = struct.pack(
            ">BHHHHIB",
            Opcode.REQUEST,
            0x0000,
            FunctionCode.SET_MULTI_VARIABLES,
            0x0000,
            seq_num,
            self._session_id,
            0x36,  # Transport flags
        )

        payload = bytearray()
        # InObjectId = session ID (tells PLC which object we're writing to)
        payload += struct.pack(">I", self._session_id)
        # Item count = 1
        payload += encode_uint32_vlq(1)
        # Total address field count = 1 (just the attribute ID)
        payload += encode_uint32_vlq(1)
        # Address: attribute ID = ServerSessionVersion (306) as VLQ
        payload += encode_uint32_vlq(ObjectId.SERVER_SESSION_VERSION)
        # Value: ItemNumber = 1 (VLQ)
        payload += encode_uint32_vlq(1)
        # PValue: echo the ServerSessionVersion typed value verbatim (it is a Struct)
        payload += self._server_session_version
        # Fill byte
        payload += bytes([0x00])
        # ObjectQualifier
        payload += encode_object_qualifier()
        # Trailing padding
        payload += struct.pack(">I", 0)

        request += bytes(payload)

        # Wrap in S7CommPlus frame
        frame = encode_header(self._protocol_version, len(request)) + request
        frame += struct.pack(">BBH", 0x72, self._protocol_version, 0x0000)

        logger.debug(f"=== SetupSession === sending ({len(frame)} bytes): {frame.hex(' ')}")
        self._send_s7_data(frame)

        # Receive response
        response_frame = self._recv_s7_data()
        logger.debug(f"=== SetupSession === received ({len(response_frame)} bytes): {response_frame.hex(' ')}")

        version, data_length, consumed = decode_header(response_frame)
        response = response_frame[consumed : consumed + data_length]

        if len(response) < 10:
            from snap7.error import S7ConnectionError

            raise S7ConnectionError("SetupSession response too short")

        resp_func = struct.unpack_from(">H", response, 3)[0]
        logger.debug(f"SetupSession response: function=0x{resp_func:04X}")

        # Parse return value from payload (data responses use a 10-byte header)
        resp_payload = response[10:]
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
        self._send_s7_data(frame)

        # Best-effort receive
        try:
            self._recv_s7_data()
        except Exception:
            pass

    def _next_sequence_number(self) -> int:
        """Get next sequence number and increment."""
        seq = self._sequence_number
        self._sequence_number = (self._sequence_number + 1) & 0xFFFF
        return seq

    def _send_s7_data(self, data: bytes) -> None:
        """Send an S7CommPlus frame, routing through TLS when active."""
        if self._tls_active and self._tls is not None:
            self._tls.write(data)
            self._tls_flush_outgoing()
        else:
            self._iso_conn.send_data(data)

    def _recv_s7_data(self) -> bytes:
        """Receive an S7CommPlus frame, routing through TLS when active."""
        if self._tls_active and self._tls is not None:
            while True:
                try:
                    return self._tls.read(65536)
                except Exception as e:
                    if isinstance(e, self._tls.want_read_error):
                        self._tls_read_incoming()
                    else:
                        raise
        else:
            return self._iso_conn.receive_data()

    def _tls_flush_outgoing(self) -> None:
        """Send all pending TLS records through COTP framing."""
        assert self._tls is not None
        data = self._tls.bio_read()
        if data:
            self._iso_conn.send_data(data)

    def _tls_read_incoming(self) -> None:
        """Read a COTP frame and feed its payload to the TLS BIO."""
        assert self._tls is not None
        data = self._iso_conn.receive_data()
        self._tls.bio_write(data)

    def _activate_tls(
        self,
        tls_cert: Optional[str] = None,
        tls_key: Optional[str] = None,
        tls_ca: Optional[str] = None,
    ) -> None:
        """Activate TLS tunneled inside COTP data frames.

        The S7CommPlus protocol transports TLS records as the payload
        of COTP DT frames — TPKT and COTP headers stay unencrypted on
        the wire. This differs from a standard ``ssl.wrap_socket`` call
        which would encrypt everything (including TPKT/COTP), which
        Siemens PLCs reject.

        Uses ``ssl.MemoryBIO`` + ``ssl.SSLObject`` to encrypt/decrypt
        without wrapping the TCP socket, keeping TPKT/COTP framing
        intact via ``ISOTCPConnection.send_data/receive_data``.

        Called after InitSSL and before CreateObject.

        Args:
            tls_cert: Path to client TLS certificate (PEM)
            tls_key: Path to client private key (PEM)
            tls_ca: Path to PLC CA certificate (PEM)
        """
        ctx = self._setup_ssl_context(
            cert_path=tls_cert,
            key_path=tls_key,
            ca_path=tls_ca,
        )

        hostname = self.host if ctx.check_hostname else None
        self._tls = _BioTLS(ctx, hostname)
        logger.debug(f"TLS backend: {self._tls._backend}")

        # TLS handshake — records tunnel through COTP frames
        self._do_tls_handshake()

        self._tls_active = True

        self._oms_secret = self._tls.export_keying_material("EXPERIMENTAL_OMS", 32)
        if self._oms_secret is not None:
            logger.debug("OMS exporter secret extracted from TLS session")
        else:
            logger.warning("Could not extract OMS exporter secret (legitimation will be unavailable)")

        logger.info("TLS activated (tunneled inside COTP frames)")

    def _do_tls_handshake(self) -> None:
        """Perform TLS handshake, tunneling records through COTP."""
        assert self._tls is not None
        while True:
            try:
                self._tls.do_handshake()
                break
            except Exception as e:
                if isinstance(e, self._tls.want_read_error):
                    self._tls_flush_outgoing()
                    self._tls_read_incoming()
                elif isinstance(e, ssl.SSLWantWriteError):
                    self._tls_flush_outgoing()
                else:
                    raise
        self._tls_flush_outgoing()

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
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2

        ctx.set_ciphers(_S7_CIPHERS)
        _set_s7_groups(ctx)
        ctx.options |= ssl.OP_NO_TICKET
        ctx.options |= 0x00080000  # SSL_OP_NO_ENCRYPT_THEN_MAC
        ctx.options |= 0x00000001  # SSL_OP_NO_EXTENDED_MASTER_SECRET (OpenSSL 3.0+)

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
