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

import hashlib
import hmac
import logging
import os
import ssl
import struct
import tempfile
from typing import Any, Optional, Type
from types import TracebackType

from snap7.connection import ISOTCPConnection
from .protocol import (
    DataType,
    FunctionCode,
    Ids,
    LegitimationId,
    Opcode,
    ProtocolVersion,
    ElementID,
    ObjectId,
    S7COMMPLUS_LOCAL_TSAP,
    S7COMMPLUS_REMOTE_TSAP,
    READ_FUNCTION_CODES,
)
from .codec import encode_header, decode_header, encode_object_qualifier, parse_create_object_attributes
from .vlq import encode_uint32_vlq, encode_uint64_vlq, decode_uint32_vlq, decode_uint64_vlq

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


# OMS legitimation derives its session key from the TLS exporter secret
# (RFC 5705). The label/length are fixed by the S7CommPlus protocol.
_OMS_EXPORTER_LABEL = b"EXPERIMENTAL_OMS"
_OMS_EXPORTER_LENGTH = 32


def _hkdf_expand_label(secret: bytes, label: bytes, context: bytes, length: int, hashmod: Any) -> bytes:
    """TLS 1.3 HKDF-Expand-Label (RFC 8446 §7.1)."""
    full_label = b"tls13 " + label
    hkdf_label = length.to_bytes(2, "big") + bytes([len(full_label)]) + full_label + bytes([len(context)]) + context
    out, block, counter = b"", b"", 1
    while len(out) < length:
        block = hmac.new(secret, block + hkdf_label + bytes([counter]), hashmod).digest()
        out += block
        counter += 1
    return out[:length]


def _tls13_exporter(exporter_master_secret: bytes, label: bytes, length: int, hashmod: Any) -> bytes:
    """RFC 8446 §7.5 TLS-Exporter with an empty context.

    Computed from the exporter_master_secret because CPython's ssl module
    does not expose ``export_keying_material``; we capture the secret via the
    TLS key log instead. Equivalent to ``SSL.export_keying_material`` for a
    TLS 1.3 session with no context.
    """
    empty_hash = hashmod(b"").digest()
    derived = _hkdf_expand_label(exporter_master_secret, label, empty_hash, hashmod().digest_size, hashmod)
    return _hkdf_expand_label(derived, b"exporter", empty_hash, length, hashmod)


def _strip_paom_string_in_session_version(struct_bytes: bytes) -> bytes:
    """Replace element 319 in a captured ServerSessionVersion struct with an empty WString.

    The element is the device "PAOM string" (e.g. ``1;6ES7 215-1BG40-0XB0 ;V4.2``)
    that the PLC sends in its CreateObject response. Real PLCs reject the V2
    SetMultiVariables echo if we write that identity back verbatim — TIA
    Portal strips this element to empty before echoing, and the V1-initial
    S7-1200 drops the connection without it.

    The input is a captured raw typed value: ``[flags][0x17 STRUCT][4-byte ID]
    [...elements...][0x00 terminator]``. Element 319 is encoded as VLQ key
    ``0x82 0x3f`` followed by ``[flags][0x15 WSTRING][len VLQ][utf-8 bytes]``.
    """
    needle = bytes([0x82, 0x3F, 0x00, 0x15])
    idx = struct_bytes.find(needle)
    if idx < 0:
        return struct_bytes
    after_dtype = idx + len(needle)
    length, consumed = decode_uint32_vlq(struct_bytes, after_dtype)
    return struct_bytes[:after_dtype] + bytes([0x00]) + struct_bytes[after_dtype + consumed + length :]


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
        self._ssl_object: Optional[ssl.SSLObject] = None
        self._incoming_bio: Optional[ssl.MemoryBIO] = None
        self._outgoing_bio: Optional[ssl.MemoryBIO] = None
        self._session_id: int = 0
        self._sequence_number: int = 0
        self._protocol_version: int = 0  # Detected from PLC response
        self._tls_active: bool = False
        self._connected = False
        # ServerSessionVersion is captured as its raw typed value (flags+datatype+data)
        # so it can be echoed back verbatim — real S7-1500 PLCs send it as a Struct.
        self._server_session_version: Optional[bytes] = None
        self._session_setup_ok: bool = False
        # PLC-provided 8-byte public-key checksum (parsed from the
        # ObjectVariableTypeName "01:HEX" attribute in the CreateObject
        # response, e.g. "01:1A73081F096B42BD"). Used to look up the
        # matching Siemens public key for the SessionKey handshake.
        self._public_key_checksum: Optional[bytes] = None
        self._public_key_fingerprint: Optional[str] = None

        # 20-byte session challenge from CreateObject response, used
        # to generate the SecurityKeyEncryptedKey blob (pre-TLS auth).
        self._session_challenge: Optional[bytes] = None

        # Session key derived from the SessionKey handshake, used for
        # HMAC packet integrity after authentication.
        self._session_key: Optional[bytes] = None
        self._session_auth_public_key: bytes = b""
        self._session_auth_family: int = 0

        # V2+ IntegrityId tracking
        self._integrity_id_read: int = 0
        self._integrity_id_write: int = 0
        self._with_integrity_id: bool = False

        # TLS OMS exporter secret (for legitimation key derivation)
        self._oms_secret: Optional[bytes] = None

        # Password for post-auth legitimation (V1-initial PLCs)
        self._connect_password: str = ""

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
    def requires_substreamed(self) -> bool:
        """Whether data operations must use substreamed function codes.

        V1-initial PLCs with SessionKey auth reject GET_MULTI_VARIABLES
        (0x054C) and require GET_VAR_SUBSTREAMED (0x0586) /
        SET_VAR_SUBSTREAMED (0x057C) for all data operations.
        """
        return self._session_key is not None

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
        password: str = "",
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
        self._connect_password = password
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

            # Step 7: Session activation + legitimation (V1-initial PLCs)
            #
            # After the V2 key exchange, the PLC requires:
            # a) SET_VARIABLE addr 323 = USINT(5) to activate the V3 session
            # b) Legitimation handshake (even without a password)
            # Without (a), data reads fail with 0xE9.
            # Ref: TIA Portal pcap frame 17 (TIAPortalWatchDB7.pcapng, GH-710)
            self._connected = True

            if self._session_key is not None and self._session_setup_ok:
                self._session_activate()
                self._post_auth_legitimation(password=self._connect_password)
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
        self._ssl_object = None
        self._incoming_bio = None
        self._outgoing_bio = None
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
            # Transport flags: 0x34 after SessionKey auth (matches TIA Portal),
            # also for GetMultiVariables and Explore; 0x36 for other V1/TLS requests.
            0x34
            if self._session_key is not None or function_code in (FunctionCode.GET_MULTI_VARIABLES, FunctionCode.EXPLORE)
            else 0x36,
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

        # After SessionKey auth, all data ops use V3 framing with HMAC
        if self._session_key is not None:
            frame_version: int = ProtocolVersion.V3
        else:
            frame_version = self._protocol_version

        if frame_version == ProtocolVersion.V3 and self._session_key is not None:
            # V3: prepend 32-byte HMAC-SHA256 digest over the request
            import hmac as _hmac
            import hashlib

            digest = _hmac.new(self._session_key[:24], request, hashlib.sha256).digest()
            frame_data = bytes([0x20]) + digest + request
            frame = encode_header(ProtocolVersion.V3, len(frame_data)) + frame_data
            frame += struct.pack(">BBH", 0x72, ProtocolVersion.V3, 0x0000)
        else:
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

        # V3 responses have a hash-length byte + HMAC prefix before the payload
        if version == ProtocolVersion.V3 and len(response) > 33:
            hash_len = response[0]
            response_hmac = response[1 : 1 + hash_len]
            response = response[1 + hash_len :]
            logger.debug(f"  V3 HMAC ({hash_len} bytes): {response_hmac.hex()}")

        # V254 frames have no standard header — return raw data
        if version == ProtocolVersion.SYSTEM_EVENT:
            logger.debug(f"  V254 frame: returning raw data ({len(response)} bytes)")
            return bytes(response)

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

        # Response header is 10 bytes: opcode(1)+reserved(2)+func(2)+reserved(2)+seq(2)+transport(1).
        # Responses do NOT carry a SessionId field (unlike requests which are 14 bytes).
        resp_opcode = response[0]
        resp_func = struct.unpack_from(">H", response, 3)[0]
        resp_seq = struct.unpack_from(">H", response, 7)[0]
        resp_transport = response[9]

        offset = 10
        return_value, consumed = decode_uint64_vlq(response, offset)
        offset += consumed
        if offset >= len(response):
            from snap7.error import S7ConnectionError

            raise S7ConnectionError("CreateObject response truncated before ObjectIdCount")
        object_id_count = response[offset]
        offset += 1
        object_ids: list[int] = []
        for _ in range(object_id_count):
            obj_id, consumed = decode_uint32_vlq(response, offset)
            offset += consumed
            object_ids.append(obj_id)

        if not object_ids:
            from snap7.error import S7ConnectionError

            raise S7ConnectionError("CreateObject response has no session ObjectId")

        # First ObjectId is the new session id; second (if any) is for notifications.
        self._session_id = object_ids[0]
        self._protocol_version = version

        logger.debug(
            f"CreateObject response header: opcode=0x{resp_opcode:02X} function=0x{resp_func:04X} "
            f"seq={resp_seq} transport=0x{resp_transport:02X}"
        )
        logger.debug(f"CreateObject response: return_value={return_value} object_ids={[hex(i) for i in object_ids]}")
        logger.debug(f"Session created: id=0x{self._session_id:08X} ({self._session_id}), version=V{version}")

        if return_value != 0:
            logger.warning(f"CreateObject returned error 0x{return_value:X} — PLC may require TLS (use_tls=True)")

        # Parse remaining payload (the ResponseObject tree) for session attributes
        attrs = parse_create_object_attributes(response[offset:])
        self._server_session_version = attrs.server_session_version
        if self._server_session_version is not None:
            logger.info(f"ServerSessionVersion captured ({len(self._server_session_version)} bytes)")
        else:
            logger.debug("ServerSessionVersion not found in CreateObject response")
        if attrs.public_key_fingerprint is not None:
            self._public_key_fingerprint = attrs.public_key_fingerprint
            self._public_key_checksum = bytes.fromhex(attrs.public_key_fingerprint[3:])
            logger.info(f"Public key fingerprint captured: {attrs.public_key_fingerprint}")
        if attrs.session_challenge is not None:
            self._session_challenge = attrs.session_challenge
            logger.info(f"Session challenge captured ({len(attrs.session_challenge)} bytes): {attrs.session_challenge.hex()}")

    def _try_session_key_auth(self) -> Optional[tuple[bytes, bytes]]:
        """Attempt to generate the SecurityKey authentication blob.

        Returns (blob, session_key) if we have the challenge and a matching
        public key, or None if any prerequisite is missing.
        """
        if self._session_challenge is None:
            logger.debug("SessionKey auth: no challenge captured from CreateObject")
            return None

        if self._public_key_fingerprint is None:
            logger.debug("SessionKey auth: no public key fingerprint captured")
            return None

        try:
            from .session_auth.keys import get_public_key, parse_fingerprint

            family, _key_id = parse_fingerprint(self._public_key_fingerprint)

            public_key = get_public_key(self._public_key_fingerprint)
            if public_key is None:
                logger.info(f"SessionKey auth: no matching public key for {self._public_key_fingerprint}")
                return None

            from .session_auth.legacy_auth import authenticate_real_plc

            blob, session_key = authenticate_real_plc(self._session_challenge, public_key, family)
            self._session_auth_public_key = public_key
            self._session_auth_family = family
            logger.info(f"SessionKey auth blob generated ({len(blob)} bytes)")
            return blob, session_key

        except Exception as e:
            logger.warning(f"SessionKey auth failed: {e}")
            return None

    def _setup_session(self) -> bool:
        """Send V2 SetMultiVariables to echo ServerSessionVersion back to the PLC.

        Always uses V2 framing, transport flags 0x34, and no IntegrityId.

        On V1-initial PLCs (FW < 4.5), this also includes the SecurityKey
        blob at address 1830, carrying an encrypted random seed and
        AES-CBC-encrypted challenge derived from the PLC's public key.

        Returns:
            True if session setup succeeded (return_value == 0).
        """
        if self._server_session_version is None:
            return False

        auth_result = self._try_session_key_auth()
        include_security_key = auth_result is not None

        seq_num = self._next_sequence_number()

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

        if include_security_key and auth_result is not None:
            blob, session_key = auth_result
            payload += encode_uint32_vlq(2)  # ItemCount
            payload += encode_uint32_vlq(2)  # AddressCount
            payload += encode_uint32_vlq(LegitimationId.SESSION_SETUP_LEGITIMATION)  # 1830
            payload += encode_uint32_vlq(ObjectId.SERVER_SESSION_VERSION)  # 306
            payload += encode_uint32_vlq(1)  # ItemNumber for SecurityKey
            payload += self._encode_security_key_struct(blob)
        else:
            payload += encode_uint32_vlq(1)  # ItemCount
            payload += encode_uint32_vlq(1)  # AddressCount
            payload += encode_uint32_vlq(ObjectId.SERVER_SESSION_VERSION)  # 306
            payload += encode_uint32_vlq(1)  # ItemNumber

        if include_security_key:
            payload += encode_uint32_vlq(2)  # ItemNumber for ServerSessionVersion

        # PValue: echo the ServerSessionVersion typed value verbatim (it may be a Struct).
        # Strip the PAOM device string (element 319) which V1-initial PLCs reject.
        if self._server_session_version is not None:
            payload += _strip_paom_string_in_session_version(self._server_session_version)
        else:
            payload += bytes([0x00, DataType.UDINT])
            payload += encode_uint32_vlq(0)

        payload += bytes([0x00])  # Fill byte
        payload += encode_object_qualifier()
        payload += struct.pack(">I", 0)  # Trailing padding

        request += bytes(payload)

        if include_security_key:
            self._session_key = session_key
            self._with_integrity_id = True
            self._integrity_id_read = 0
            self._integrity_id_write = 0
            logger.info("SecurityKey blob included in session setup, IntegrityId tracking enabled")

        # Outer S7+ frame is always V2 for the setup write, even if the PLC
        # negotiated V1 on the initial CreateObject.
        frame = encode_header(ProtocolVersion.V2, len(request)) + request
        frame += struct.pack(">BBH", 0x72, ProtocolVersion.V2, 0x0000)

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

    def _build_get_var_substreamed(self, in_object_id: int, address: int, seq_field: int = 1) -> bytes:
        """Build a GET_VAR_SUBSTREAMED payload (reused by activation and legitimation)."""
        oq = encode_object_qualifier()
        payload = struct.pack(">I", in_object_id)
        payload += bytes([0x20, 0x04])
        payload += encode_uint32_vlq(1)  # field count
        payload += encode_uint32_vlq(address)
        payload += oq + bytes([0x00])
        payload += encode_uint32_vlq(1)
        payload += encode_uint32_vlq(seq_field)
        payload += struct.pack(">I", 0)
        return payload

    def _session_activate(self) -> None:
        """Activate the V3 session after the SecurityKey handshake.

        TIA Portal sends SET_VARIABLE writing USINT(5) to address 323 on the
        session object immediately after the V2 SetMultiVariables key exchange
        succeeds, BEFORE any data reads or legitimation.

        Without this step, the PLC rejects data operations with 0xE9.

        Previous attempt (432d9c6 → e73f915) bundled this with 3 extra
        GET_VAR_SUBSTREAMED reads that are NOT in TIA's flow and caused RST.
        This version sends only the SET_VARIABLE, matching the pcap exactly
        (frame 17 of TIAPortalWatchDB7.pcapng from GH-710).
        """
        oq = encode_object_qualifier()

        payload = struct.pack(">I", self._session_id)
        payload += encode_uint32_vlq(1)  # AddressCount
        payload += encode_uint32_vlq(323)  # address
        payload += bytes([0x00, DataType.USINT])
        payload += encode_uint32_vlq(5)
        payload += oq
        payload += struct.pack(">I", 0)

        logger.debug("Session activation: SET_VARIABLE addr 323 = USINT(5)")
        self.send_request(FunctionCode.SET_VARIABLE, payload)
        logger.info("Session activation completed")

    def _post_auth_legitimation(self, password: str = "") -> None:
        """Perform the post-SessionKey legitimation handshake.

        V1-initial PLCs require this exchange after the SessionKey blob
        is accepted before they'll allow elevated access (e.g. writes).

        Matches HarpoS7 PoC legitimation sequence:
        1. GET_VAR_SUBSTREAMED: read 20-byte challenge from address 303
        2. Solve the challenge cryptographically
        3. SET_VAR_SUBSTREAMED: write solved 248-byte blob to address 1846
        """
        oq = encode_object_qualifier()

        # Step 1: Read legitimation challenge from session, address 303
        logger.debug("Post-auth legitimation: reading challenge from address 303")
        challenge_resp = self.send_request(
            FunctionCode.GET_VAR_SUBSTREAMED,
            self._build_get_var_substreamed(self._session_id, LegitimationId.SERVER_SESSION_REQUEST),
        )

        # Extract the 20-byte challenge from the response.
        # Response format (per thomas-v2 GetVarSubstreamedResponse):
        #   UInt64Vlq ReturnValue | byte unknown | PValue(datatype + count_vlq + length_vlq + data) | UInt32Vlq IntegrityId
        legit_challenge: bytes = self._session_challenge or b""
        if len(challenge_resp) >= 26:
            offset = 0
            retval, c = decode_uint64_vlq(challenge_resp, offset)
            offset += c
            if retval != 0:
                logger.warning(f"Legitimation challenge read returned error: 0x{retval:X}")
            offset += 1  # unknown byte
            offset += 1  # datatype tag (0x10 = BLOB/USIntArray)
            _count, c = decode_uint32_vlq(challenge_resp, offset)
            offset += c
            length, c = decode_uint32_vlq(challenge_resp, offset)
            offset += c
            if offset + length <= len(challenge_resp) and length == 20:
                legit_challenge = bytes(challenge_resp[offset : offset + length])
                logger.info(f"Legitimation challenge: {legit_challenge.hex()}")

        if not legit_challenge:
            from snap7.error import S7ConnectionError

            raise S7ConnectionError("Post-auth legitimation failed: no challenge available")

        # Step 2: Solve the challenge
        from .session_auth.legitimate import solve_legitimate_challenge_real_plc

        session_key = self._session_key
        if session_key is None:
            from snap7.error import S7ConnectionError

            raise S7ConnectionError("Post-auth legitimation failed: no session key")

        legit_blob = solve_legitimate_challenge_real_plc(
            legit_challenge,
            self._session_auth_public_key,
            self._session_auth_family,
            session_key,
            password,
        )
        logger.info(f"Legitimation blob generated ({len(legit_blob)} bytes)")

        # Step 3: Write solved blob via SET_VAR_SUBSTREAMED to address 1846
        # Format matches HarpoS7 PoC SetVarSubStreamedRequest template
        svs = struct.pack(">I", self._session_id)
        svs += bytes([0x20, 0x04])
        svs += encode_uint32_vlq(1)
        svs += encode_uint32_vlq(LegitimationId.LEGITIMATE)  # 1846
        svs += oq + bytes([0x00])
        svs += encode_uint32_vlq(1)
        svs += bytes([0x00, DataType.BLOB, 0x00])  # extra 0x00 before VLQ length
        svs += encode_uint32_vlq(len(legit_blob))
        svs += legit_blob
        svs += encode_uint32_vlq(self._sequence_number)
        svs += struct.pack(">I", 0)

        logger.debug("Post-auth legitimation: writing solved blob to address 1846")
        legit_resp = self.send_request(FunctionCode.SET_VAR_SUBSTREAMED, svs)

        if len(legit_resp) >= 1:
            legit_retval, _ = decode_uint64_vlq(legit_resp, 0)
            signed_retval = legit_retval if legit_retval < (1 << 63) else legit_retval - (1 << 64)
            if signed_retval < 0:
                from snap7.error import S7ConnectionError

                raise S7ConnectionError(f"Post-auth legitimation rejected by PLC: return_value=0x{legit_retval:X}")
            logger.debug(f"Legitimation write return_value=0x{legit_retval:X}")

        logger.info("Post-auth legitimation completed")

    def _encode_security_key_struct(self, blob: bytes) -> bytes:
        """Encode the SecurityKey PObject struct (Struct 1800) wrapping the auth blob.

        Matches the wire format from TIA Portal / HarpoS7 PoC:
        Struct(1800) containing key descriptors for the public and symmetric
        keys, plus the encrypted blob.
        """
        from .session_auth.utils import derive_key_id

        public_key_id = derive_key_id(self._session_auth_public_key or b"\x00" * 24)
        # The symmetric key ID is derived from the session key
        symmetric_key_id = derive_key_id(self._session_key or b"\x00" * 24)

        # Determine key flags from family
        from .session_auth.keys import KeyFamily
        from .session_auth.blob_metadata import get_symmetric_key_flags, get_public_key_flags

        family = self._session_auth_family if self._session_auth_family else KeyFamily.S7_1500
        sym_flags = get_symmetric_key_flags(family)
        pub_flags = get_public_key_flags(family)

        # Inside a Struct, attributes are VLQ(absolute_id) + flags + type + value.
        # No 0xA3 tag prefix — that's only for PObject tree attributes.
        # Struct(1800): 1801=Version 1802=SecurityLevel 1803=PublicKey
        #               1804=SymmetricKey 1805=EncryptedKey
        # Struct(1825): 1826=KeyId 1827=KeyFlags 1828=InternalFlags

        def _udint_val(v: int) -> bytes:
            return bytes([0x00, DataType.UDINT]) + encode_uint32_vlq(v)

        def _usint_val(v: int) -> bytes:
            return bytes([0x00, DataType.USINT]) + bytes([v & 0xFF])

        def _ulint_val(v: int) -> bytes:
            return bytes([0x00, DataType.ULINT]) + encode_uint64_vlq(v)

        def _blob_val(data: bytes) -> bytes:
            return bytes([0x00, DataType.BLOB, 0x00]) + encode_uint32_vlq(len(data)) + data

        def _struct_begin(struct_id: int) -> bytes:
            return bytes([0x00, DataType.STRUCT]) + struct.pack(">I", struct_id)

        _STRUCT_END = bytes([0x00])

        def _key_descriptor(key_id: bytes, flags: int) -> bytes:
            key_id_int = int.from_bytes(key_id, byteorder="little", signed=False)
            out = _struct_begin(Ids.SECURITY_KEY_ID)
            out += encode_uint32_vlq(1826) + _ulint_val(key_id_int)  # KeyId
            out += encode_uint32_vlq(1827) + _udint_val(flags)  # KeyFlags
            out += encode_uint32_vlq(1828) + _udint_val(0)  # InternalFlags
            out += _STRUCT_END
            return out

        result = _struct_begin(Ids.STRUCT_SECURITY_KEY)
        result += encode_uint32_vlq(1801) + _udint_val(0)  # Version
        result += encode_uint32_vlq(1802) + _usint_val(0)  # SecurityLevel
        result += encode_uint32_vlq(1803) + _key_descriptor(public_key_id, pub_flags)  # PublicKey
        result += encode_uint32_vlq(1804) + _key_descriptor(symmetric_key_id, sym_flags | 0x10000)  # SymmetricKey
        result += encode_uint32_vlq(1805) + _blob_val(blob)  # EncryptedKey
        result += _STRUCT_END

        return result

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
        if self._tls_active:
            self._ssl_object.write(data)  # type: ignore[union-attr]
            self._tls_flush_outgoing()
        else:
            self._iso_conn.send_data(data)

    def _recv_s7_data(self) -> bytes:
        """Receive an S7CommPlus frame, routing through TLS when active."""
        if self._tls_active:
            while True:
                try:
                    return self._ssl_object.read(65536)  # type: ignore[union-attr]
                except ssl.SSLWantReadError:
                    self._tls_read_incoming()
        else:
            return self._iso_conn.receive_data()

    def _tls_flush_outgoing(self) -> None:
        """Send all pending TLS records through COTP framing."""
        data = self._outgoing_bio.read()  # type: ignore[union-attr]
        if data:
            self._iso_conn.send_data(data)

    def _tls_read_incoming(self) -> None:
        """Read a COTP frame and feed its payload to the TLS BIO."""
        data = self._iso_conn.receive_data()
        self._incoming_bio.write(data)  # type: ignore[union-attr]

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

        # CPython's ssl cannot export RFC 5705 keying material, which OMS
        # legitimation needs. Capture the TLS 1.3 exporter_master_secret via
        # the key log (written during the handshake) and derive it ourselves
        # in _derive_oms_secret. The key log is a private 0600 temp file,
        # removed immediately after the handshake.
        keylog_fd, keylog_path = tempfile.mkstemp(prefix="s7-tls-keylog-")
        os.close(keylog_fd)
        ctx.keylog_filename = keylog_path

        # BIO-based TLS: encrypt/decrypt bytes without touching the
        # TCP socket, so TPKT/COTP framing stays unencrypted.
        self._incoming_bio = ssl.MemoryBIO()
        self._outgoing_bio = ssl.MemoryBIO()
        self._ssl_object = ctx.wrap_bio(
            self._incoming_bio,
            self._outgoing_bio,
            server_side=False,
            server_hostname=self.host if ctx.check_hostname else None,
        )

        try:
            # TLS handshake — records tunnel through COTP frames
            self._do_tls_handshake()
            self._tls_active = True

            # Derive OMS exporter secret for legitimation key derivation
            self._oms_secret = self._derive_oms_secret(keylog_path)
            if self._oms_secret is not None:
                logger.debug("OMS exporter secret derived (%d bytes)", len(self._oms_secret))
        finally:
            try:
                os.unlink(keylog_path)
            except OSError:
                pass

        logger.info("TLS activated (tunneled inside COTP frames)")

    def _derive_oms_secret(self, keylog_path: str) -> Optional[bytes]:
        """Derive the OMS exporter secret (RFC 5705) for legitimation.

        CPython's ssl module has no ``export_keying_material``, so we read the
        TLS 1.3 ``exporter_master_secret`` from the session key log and run the
        RFC 8446 exporter derivation ourselves (stdlib hmac/hashlib only).
        Returns None (legitimation unavailable, anonymous reads still work) if
        the session isn't TLS 1.3 or the secret can't be recovered.
        """
        cipher = self._ssl_object.cipher() if self._ssl_object else None
        if not cipher or cipher[1] != "TLSv1.3":
            logger.warning(
                "OMS exporter derivation needs TLS 1.3 (session is %s)",
                cipher[1] if cipher else "unknown",
            )
            return None
        hashmod = hashlib.sha384 if cipher[0].endswith("SHA384") else hashlib.sha256

        exporter_master_secret = None
        try:
            with open(keylog_path, "r") as fh:
                for line in fh:
                    parts = line.split()
                    if len(parts) == 3 and parts[0] == "EXPORTER_SECRET":
                        exporter_master_secret = bytes.fromhex(parts[2])
        except OSError as e:
            logger.warning("Could not read TLS key log: %s", e)
            return None

        if exporter_master_secret is None:
            logger.warning("EXPORTER_SECRET not found in TLS key log")
            return None

        return _tls13_exporter(exporter_master_secret, _OMS_EXPORTER_LABEL, _OMS_EXPORTER_LENGTH, hashmod)

    def _do_tls_handshake(self) -> None:
        """Perform TLS handshake, tunneling records through COTP."""
        while True:
            try:
                self._ssl_object.do_handshake()  # type: ignore[union-attr]
                break
            except ssl.SSLWantReadError:
                self._tls_flush_outgoing()
                self._tls_read_incoming()
            except ssl.SSLWantWriteError:
                # Rare with MemoryBIO, but the SSLObject can ask to write before reading.
                self._tls_flush_outgoing()
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
