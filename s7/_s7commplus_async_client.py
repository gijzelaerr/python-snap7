"""Pure async S7CommPlus client for S7-1200/1500 PLCs (no legacy fallback).

This is an internal module used by the unified ``s7.AsyncClient``.  It provides
raw S7CommPlus data operations without any fallback logic -- the unified
client is responsible for deciding when to fall back to legacy S7.

Reference: thomas-v2/S7CommPlusDriver (C#, LGPL-3.0)
"""

import asyncio
import logging
import ssl
import struct
from typing import Any, Optional

from .protocol import (
    DataType,
    ElementID,
    FunctionCode,
    ObjectId,
    Opcode,
    ProtocolVersion,
    READ_FUNCTION_CODES,
    S7COMMPLUS_LOCAL_TSAP,
    S7COMMPLUS_REMOTE_TSAP,
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
from ._s7commplus_client import (
    _build_read_payload,
    _parse_read_response,
    _build_write_payload,
    _parse_write_response,
    _build_area_read_payload,
    _build_area_write_payload,
    _build_symbolic_read_payload,
    _build_explore_payload,
    _build_invoke_payload,
    _build_explore_request,
    _parse_explore_datablocks,
)
from . import typeinfo
from .protocol import Ids

logger = logging.getLogger(__name__)

# COTP constants
_COTP_CR = 0xE0
_COTP_CC = 0xD0
_COTP_DT = 0xF0


class S7CommPlusAsyncClient:
    """Pure async S7CommPlus client without legacy fallback.

    Use ``s7.AsyncClient`` for automatic protocol selection.
    """

    def __init__(self) -> None:
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._session_id: int = 0
        self._sequence_number: int = 0
        self._protocol_version: int = 0
        self._connected = False
        self._lock = asyncio.Lock()

        # V2+ IntegrityId tracking
        self._integrity_id_read: int = 0
        self._integrity_id_write: int = 0
        self._with_integrity_id: bool = False

        # TLS state — TLS records are tunneled inside COTP DT frames via MemoryBIO
        # (TPKT/COTP headers stay unencrypted), mirroring the sync S7CommPlusConnection.
        self._tls_active: bool = False
        self._ssl_object: Optional[ssl.SSLObject] = None
        self._incoming_bio: Optional[ssl.MemoryBIO] = None
        self._outgoing_bio: Optional[ssl.MemoryBIO] = None
        self._oms_secret: Optional[bytes] = None
        # ServerSessionVersion is captured as its raw typed value (flags+datatype+data)
        # so it can be echoed back verbatim — real S7-1500 PLCs send it as a Struct.
        self._server_session_version: Optional[bytes] = None
        self._session_setup_ok: bool = False

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def protocol_version(self) -> int:
        return self._protocol_version

    @property
    def session_id(self) -> int:
        return self._session_id

    @property
    def session_setup_ok(self) -> bool:
        """Whether the S7CommPlus session setup succeeded for data operations."""
        return self._session_setup_ok

    @property
    def tls_active(self) -> bool:
        """Whether TLS is active on the connection."""
        return self._tls_active

    @property
    def oms_secret(self) -> Optional[bytes]:
        """OMS exporter secret from TLS session (None if TLS not active)."""
        return self._oms_secret

    async def connect(
        self,
        host: str,
        port: int = 102,
        rack: int = 0,
        slot: int = 1,
        *,
        use_tls: bool = False,
        tls_cert: Optional[str] = None,
        tls_key: Optional[str] = None,
        tls_ca: Optional[str] = None,
    ) -> None:
        """Connect to an S7-1200/1500 PLC using S7CommPlus.

        Args:
            host: PLC IP address or hostname
            port: TCP port (default 102)
            rack: PLC rack number (unused, kept for API symmetry)
            slot: PLC slot number (unused, kept for API symmetry)
            use_tls: Whether to activate TLS after InitSSL.
            tls_cert: Path to client TLS certificate (PEM)
            tls_key: Path to client private key (PEM)
            tls_ca: Path to CA certificate for PLC verification (PEM)
        """
        self._host = host

        # TCP connect
        self._reader, self._writer = await asyncio.open_connection(host, port)

        try:
            # Step 1: COTP handshake with S7CommPlus TSAP values
            await self._cotp_connect(S7COMMPLUS_LOCAL_TSAP, S7COMMPLUS_REMOTE_TSAP)

            # Step 2: InitSSL handshake
            await self._init_ssl()

            # Step 3: TLS activation (between InitSSL and CreateObject)
            if use_tls:
                await self._activate_tls(tls_cert=tls_cert, tls_key=tls_key, tls_ca=tls_ca)

            # Step 4: S7CommPlus session setup (CreateObject)
            await self._create_session()

            # After CreateObject (which always uses V1 framing), data PDUs over TLS
            # use ProtocolVersion V2 on a real S7-1500 (matches the C# reference driver).
            if self._tls_active:
                self._protocol_version = ProtocolVersion.V2

            # Step 5: Version-specific validation
            if self._protocol_version >= ProtocolVersion.V3:
                if not use_tls:
                    logger.warning(
                        "PLC reports V3 protocol but TLS is not enabled. Connection may not work without use_tls=True."
                    )
            elif self._protocol_version == ProtocolVersion.V2:
                if not self._tls_active:
                    from snap7.error import S7ConnectionError

                    raise S7ConnectionError("PLC reports V2 protocol but TLS is not active. V2 requires TLS. Use use_tls=True.")
                self._with_integrity_id = True
                self._integrity_id_read = 0
                self._integrity_id_write = 0
                logger.info("V2 IntegrityId tracking enabled")

            self._connected = True

            # Step 6: Session setup - echo ServerSessionVersion back to PLC
            if self._server_session_version is not None:
                self._session_setup_ok = await self._setup_session()
            else:
                logger.warning("PLC did not provide ServerSessionVersion - session setup incomplete")
                self._session_setup_ok = False
            logger.info(
                f"Async S7CommPlus connected to {host}:{port}, "
                f"version=V{self._protocol_version}, session={self._session_id}, "
                f"tls={self._tls_active}"
            )

        except Exception:
            await self.disconnect()
            raise

    async def authenticate(self, password: str, username: str = "") -> None:
        """Perform PLC password authentication (legitimation).

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

        challenge = await self._get_legitimation_challenge()
        logger.info(f"Received legitimation challenge ({len(challenge)} bytes)")

        from .legitimation import build_legacy_response, build_new_response

        if username:
            response_data = build_new_response(password, challenge, self._oms_secret, username)
            await self._send_legitimation_new(response_data)
        else:
            try:
                response_data = build_new_response(password, challenge, self._oms_secret, "")
                await self._send_legitimation_new(response_data)
            except NotImplementedError:
                response_data = build_legacy_response(password, challenge)
                await self._send_legitimation_legacy(response_data)

        logger.info("PLC legitimation completed successfully")

    async def _activate_tls(
        self,
        tls_cert: Optional[str] = None,
        tls_key: Optional[str] = None,
        tls_ca: Optional[str] = None,
    ) -> None:
        """Activate TLS 1.3 over the COTP connection."""
        if self._writer is None:
            from snap7.error import S7ConnectionError

            raise S7ConnectionError("Cannot activate TLS: not connected")

        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.minimum_version = ssl.TLSVersion.TLSv1_3

        if hasattr(ctx, "set_ciphersuites"):
            ctx.set_ciphersuites("TLS_AES_256_GCM_SHA384:TLS_AES_128_GCM_SHA256")

        if tls_cert and tls_key:
            ctx.load_cert_chain(tls_cert, tls_key)

        if tls_ca:
            ctx.load_verify_locations(tls_ca)
        else:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

        # BIO-based TLS: encrypt/decrypt in memory so the TLS records can be tunneled
        # through COTP DT frames (TPKT/COTP stay unencrypted) — `start_tls` would instead
        # wrap the whole TCP stream, encrypting TPKT/COTP too, which the PLC rejects.
        self._incoming_bio = ssl.MemoryBIO()
        self._outgoing_bio = ssl.MemoryBIO()
        self._ssl_object = ctx.wrap_bio(
            self._incoming_bio,
            self._outgoing_bio,
            server_side=False,
            server_hostname=self._host if ctx.check_hostname else None,
        )

        await self._do_tls_handshake()
        self._tls_active = True

        try:
            self._oms_secret = self._ssl_object.export_keying_material("EXPERIMENTAL_OMS", 32, None)
            logger.debug("OMS exporter secret extracted from TLS session")
        except (AttributeError, ssl.SSLError) as e:
            logger.warning(f"Could not extract OMS exporter secret: {e}")
            self._oms_secret = None

        logger.info("TLS 1.3 activated (tunneled inside COTP frames)")

    async def _do_tls_handshake(self) -> None:
        """Perform the TLS handshake, tunneling records through COTP DT frames."""
        assert self._ssl_object is not None
        while True:
            try:
                self._ssl_object.do_handshake()
                break
            except ssl.SSLWantReadError:
                await self._tls_flush_outgoing()
                await self._tls_read_incoming()
            except ssl.SSLWantWriteError:
                # Rare with MemoryBIO, but the SSLObject can ask to write before reading.
                await self._tls_flush_outgoing()
        await self._tls_flush_outgoing()

    async def _tls_flush_outgoing(self) -> None:
        """Send all pending outgoing TLS bytes as COTP DT frames."""
        assert self._outgoing_bio is not None
        data = self._outgoing_bio.read()
        if data:
            await self._send_cotp_raw(data)

    async def _tls_read_incoming(self) -> None:
        """Read one COTP DT frame and feed its payload to the TLS BIO."""
        assert self._incoming_bio is not None
        data = await self._recv_cotp_raw()
        self._incoming_bio.write(data)

    async def _get_legitimation_challenge(self) -> bytes:
        """Request legitimation challenge from PLC."""
        from .protocol import LegitimationId, DataType as DT

        payload = bytearray()
        payload += struct.pack(">I", self._session_id)
        payload += encode_uint32_vlq(1)
        payload += encode_uint32_vlq(1)
        payload += encode_uint32_vlq(LegitimationId.SERVER_SESSION_REQUEST)
        payload += struct.pack(">I", 0)

        resp_payload = await self._send_request(FunctionCode.GET_VAR_SUBSTREAMED, bytes(payload))

        offset = 0
        return_value, consumed = decode_uint64_vlq(resp_payload, offset)
        offset += consumed

        if return_value != 0:
            from snap7.error import S7ConnectionError

            raise S7ConnectionError(f"GetVarSubStreamed for challenge failed: return_value={return_value}")

        if offset + 2 > len(resp_payload):
            from snap7.error import S7ConnectionError

            raise S7ConnectionError("Challenge response too short")

        _flags = resp_payload[offset]
        datatype = resp_payload[offset + 1]
        offset += 2

        if datatype == DT.BLOB:
            length, consumed = decode_uint32_vlq(resp_payload, offset)
            offset += consumed
            return bytes(resp_payload[offset : offset + length])
        else:
            count, consumed = decode_uint32_vlq(resp_payload, offset)
            offset += consumed
            return bytes(resp_payload[offset : offset + count])

    async def _send_legitimation_new(self, encrypted_response: bytes) -> None:
        """Send new-style legitimation response (AES-256-CBC encrypted)."""
        from .protocol import LegitimationId, DataType as DT

        payload = bytearray()
        payload += struct.pack(">I", self._session_id)
        payload += encode_uint32_vlq(1)
        payload += encode_uint32_vlq(LegitimationId.LEGITIMATE)
        payload += bytes([0x00, DT.BLOB])
        payload += encode_uint32_vlq(len(encrypted_response))
        payload += encrypted_response
        payload += struct.pack(">I", 0)

        resp_payload = await self._send_request(FunctionCode.SET_VARIABLE, bytes(payload))

        if len(resp_payload) >= 1:
            return_value, _ = decode_uint64_vlq(resp_payload, 0)
            if return_value < 0:
                from snap7.error import S7ConnectionError

                raise S7ConnectionError(f"Legitimation rejected by PLC: return_value={return_value}")
            logger.debug(f"New legitimation return_value={return_value}")

    async def _send_legitimation_legacy(self, response: bytes) -> None:
        """Send legacy legitimation response (SHA-1 XOR)."""
        from .protocol import LegitimationId, DataType as DT

        payload = bytearray()
        payload += struct.pack(">I", self._session_id)
        payload += encode_uint32_vlq(1)
        payload += encode_uint32_vlq(LegitimationId.SERVER_SESSION_RESPONSE)
        payload += bytes([0x10, DT.USINT])  # flags=0x10 (array)
        payload += encode_uint32_vlq(len(response))
        payload += response
        payload += struct.pack(">I", 0)

        resp_payload = await self._send_request(FunctionCode.SET_VARIABLE, bytes(payload))

        if len(resp_payload) >= 1:
            return_value, _ = decode_uint64_vlq(resp_payload, 0)
            if return_value < 0:
                from snap7.error import S7ConnectionError

                raise S7ConnectionError(f"Legacy legitimation rejected by PLC: return_value={return_value}")
            logger.debug(f"Legacy legitimation return_value={return_value}")

    async def disconnect(self) -> None:
        """Disconnect from PLC."""
        if self._connected and self._session_id:
            try:
                await self._delete_session()
            except Exception:
                pass

        self._connected = False
        self._session_id = 0
        self._sequence_number = 0
        self._protocol_version = 0
        self._with_integrity_id = False
        self._integrity_id_read = 0
        self._integrity_id_write = 0
        self._tls_active = False
        self._ssl_object = None
        self._incoming_bio = None
        self._outgoing_bio = None
        self._oms_secret = None
        self._server_session_version = None
        self._session_setup_ok = False

        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:
                pass
            self._writer = None
            self._reader = None

    async def db_read(self, db_number: int, start: int, size: int) -> bytes:
        """Read raw bytes from a data block."""
        payload = _build_read_payload([(db_number, start, size)])
        response = await self._send_request(FunctionCode.GET_MULTI_VARIABLES, payload)

        results = _parse_read_response(response)
        if not results:
            raise RuntimeError("Read returned no data")
        if results[0] is None:
            raise RuntimeError("Read failed: PLC returned error for item")
        return results[0]

    async def db_write(self, db_number: int, start: int, data: bytes) -> None:
        """Write raw bytes to a data block."""
        payload = _build_write_payload([(db_number, start, data)])
        response = await self._send_request(FunctionCode.SET_MULTI_VARIABLES, payload)
        _parse_write_response(response)

    async def db_read_multi(self, items: list[tuple[int, int, int]]) -> list[bytes]:
        """Read multiple data block regions in a single request."""
        payload = _build_read_payload(items)
        response = await self._send_request(FunctionCode.GET_MULTI_VARIABLES, payload)
        parsed = _parse_read_response(response)
        return [r if r is not None else b"" for r in parsed]

    async def read_area(self, area_rid: int, start: int, size: int) -> bytes:
        """Read raw bytes from a controller memory area (M, I, Q, counters, timers)."""
        payload = _build_area_read_payload(area_rid, start, size)
        response = await self._send_request(FunctionCode.GET_MULTI_VARIABLES, payload)
        results = _parse_read_response(response)
        if not results or results[0] is None:
            raise RuntimeError("Area read failed")
        return results[0]

    async def write_area(self, area_rid: int, start: int, data: bytes) -> None:
        """Write raw bytes to a controller memory area (M, I, Q, counters, timers)."""
        payload = _build_area_write_payload(area_rid, start, data)
        response = await self._send_request(FunctionCode.SET_MULTI_VARIABLES, payload)
        _parse_write_response(response)

    async def explore(self, explore_id: int = 0) -> bytes:
        """Browse the PLC object tree."""
        payload = _build_explore_payload(explore_id)
        return await self._send_request(FunctionCode.EXPLORE, payload)

    async def set_plc_operating_state(self, state: int) -> None:
        """Set the PLC operating state (start/stop)."""
        payload = _build_invoke_payload(state)
        await self._send_request(FunctionCode.INVOKE, payload)

    async def read_symbolic(self, access_area: int, lids: list[int], symbol_crc: int = 0) -> bytes:
        """Read a variable using S7CommPlus symbolic (LID-based) access.

        .. warning:: This method is **experimental** and may change.
        """
        payload = _build_symbolic_read_payload(access_area, lids, symbol_crc)
        response = await self._send_request(FunctionCode.GET_MULTI_VARIABLES, payload)
        results = _parse_read_response(response)
        if not results or results[0] is None:
            raise RuntimeError("Symbolic read failed")
        return results[0]

    async def list_datablocks(self) -> list[dict[str, Any]]:
        """List all datablocks on the PLC via EXPLORE.

        .. warning:: This method is **experimental** and may change.
        """
        payload = _build_explore_request(Ids.NATIVE_THE_PLC_PROGRAM_RID, [Ids.OBJECT_VARIABLE_TYPE_NAME, Ids.BLOCK_BLOCK_NUMBER])
        response = await self._send_request(FunctionCode.EXPLORE, payload, integrity_tail=5, reassemble=True)
        return _parse_explore_datablocks(response)

    async def browse(self) -> list[dict[str, Any]]:
        """Browse the full per-tag symbol tree via EXPLORE + the type-info container.

        .. warning:: This method is **experimental** and may change.

        Returns a flat list of variable dicts with keys ``name``, ``access_sequence``
        (the dot-separated hex LID path usable with :meth:`read_tag`), ``data_type``,
        and the optimized/non-optimized byte+bit offsets. Steps: enumerate DBs, resolve
        each DB's type-info RID via a LID=1 read, explore the OMS type-info container,
        then recombine into the symbol tree.

        Returns:
            List of variable info dicts.
        """
        # Phase A: enumerate data blocks. Phase B/C: resolve each DB's type-info RID
        # (a LID=1 read — needed for instance DBs whose TI is not their own RID) and seed
        # a root node per DB.
        root_nodes: list[typeinfo.Node] = []
        for db_info in await self.list_datablocks():
            if db_info.get("number", 0) <= 0 or db_info.get("rid", 0) == 0:
                continue
            ti_rid = await self._read_typeinfo_rid(db_info["rid"])
            if ti_rid == 0:
                continue  # load-memory-only DB, skip
            root_nodes.append(
                typeinfo.Node(
                    node_type=typeinfo.NodeType.ROOT, name=db_info["name"], access_id=db_info["rid"], relation_id=ti_rid
                )
            )

        # Add the native process areas with their known synthetic type-info ids.
        for name, access_rid, ti_rid in (
            ("IArea", Ids.NATIVE_THE_I_AREA_RID, 0x90010000),
            ("QArea", Ids.NATIVE_THE_Q_AREA_RID, 0x90020000),
            ("MArea", Ids.NATIVE_THE_M_AREA_RID, 0x90030000),
            ("S7Timers", Ids.NATIVE_THE_S7_TIMERS_RID, 0x90050000),
            ("S7Counters", Ids.NATIVE_THE_S7_COUNTERS_RID, 0x90060000),
        ):
            root_nodes.append(
                typeinfo.Node(node_type=typeinfo.NodeType.ROOT, name=name, access_id=access_rid, relation_id=ti_rid)
            )

        # Phase D: explore the OMS type-info container (a large, multi-fragment PDU).
        type_objects = await self._explore_type_info_container()

        # Phase E: recombine type-info with the DB/area nodes and flatten.
        typeinfo.build_tree(root_nodes, type_objects)
        variables: list[dict[str, Any]] = []
        for v in typeinfo.build_flat_list(root_nodes):
            try:
                data_type = typeinfo.Softdatatype(v.softdatatype).name
            except ValueError:
                data_type = str(v.softdatatype)
            variables.append(
                {
                    "name": v.name,
                    "access_sequence": v.access_sequence,
                    "data_type": data_type,
                    "opt_address": v.opt_address,
                    "opt_bitoffset": v.opt_bitoffset,
                    "nonopt_address": v.nonopt_address,
                    "nonopt_bitoffset": v.nonopt_bitoffset,
                }
            )
        return variables

    async def _read_typeinfo_rid(self, db_rid: int) -> int:
        """Read LID=1 of a DB to get its type-info RID (0 if the DB has no readable value)."""
        try:
            raw = await self.read_symbolic(db_rid, [1], 0)
        except Exception:
            return 0
        return struct.unpack(">I", raw[:4])[0] if len(raw) >= 4 else 0

    async def _explore_type_info_container(self) -> list["typeinfo.PObject"]:
        """EXPLORE the OMS type-info container and return its per-type objects."""
        payload = _build_explore_request(Ids.OBJECT_OMS_TYPE_INFO_CONTAINER, [])
        response = await self._send_request(FunctionCode.EXPLORE, payload, integrity_tail=5, reassemble=True)
        return typeinfo.extract_type_info_objects(response)

    # -- Internal methods --

    # Sanity caps for fragment reassembly — generous vs. any real PLC EXPLORE response,
    # but bounded so a malformed/adversarial stream can't drive unbounded allocation.
    _MAX_REASSEMBLED_BYTES = 16 * 1024 * 1024
    _MAX_REASSEMBLED_FRAGMENTS = 4096

    async def _send_request(
        self,
        function_code: int,
        payload: bytes,
        integrity_tail: int = 4,
        reassemble: bool = False,
    ) -> bytes:
        """Send an S7CommPlus request and receive the response.

        Args:
            function_code: S7CommPlus function code.
            payload: Request payload (after the 14-byte request header).
            integrity_tail: number of trailing payload bytes the V2 IntegrityId is
                inserted *before* — 4 for GetMultiVariables/SetMultiVariables (a
                trailing UInt32), 5 for Explore (a trailing UInt32 + filler byte).
            reassemble: when True, concatenate a multi-fragment response (e.g. Explore)
                before returning its payload.

        Returns:
            Response payload (after the 10-byte response header).
        """
        async with self._lock:
            if not self._connected or self._writer is None or self._reader is None:
                raise RuntimeError("Not connected")

            seq_num = self._next_sequence_number()

            request_header = struct.pack(
                ">BHHHHIB",
                Opcode.REQUEST,
                0x0000,
                function_code,
                0x0000,
                seq_num,
                self._session_id,
                # Transport flags: 0x34 for GetMultiVariables and Explore, 0x36 otherwise.
                0x34 if function_code in (FunctionCode.GET_MULTI_VARIABLES, FunctionCode.EXPLORE) else 0x36,
            )

            integrity_id_bytes = b""
            if self._with_integrity_id and self._protocol_version >= ProtocolVersion.V2:
                is_read = function_code in READ_FUNCTION_CODES
                integrity_id = self._integrity_id_read if is_read else self._integrity_id_write
                integrity_id_bytes = encode_uint32_vlq(integrity_id)

            # The IntegrityId is spliced in just before the payload's trailing fill bytes
            # (integrity_tail of them), not right after the header.
            if integrity_id_bytes and len(payload) >= integrity_tail:
                request = request_header + payload[:-integrity_tail] + integrity_id_bytes + payload[-integrity_tail:]
            else:
                request = request_header + integrity_id_bytes + payload

            frame = encode_header(self._protocol_version, len(request)) + request
            frame += struct.pack(">BBH", 0x72, self._protocol_version, 0x0000)
            await self._send_cotp_dt(frame)

            if self._with_integrity_id and self._protocol_version >= ProtocolVersion.V2:
                if function_code in READ_FUNCTION_CODES:
                    self._integrity_id_read = (self._integrity_id_read + 1) & 0xFFFFFFFF
                else:
                    self._integrity_id_write = (self._integrity_id_write + 1) & 0xFFFFFFFF

            # Large responses (e.g. Explore) are split across several S7CommPlus PDUs.
            if reassemble:
                data = await self._recv_reassembled_payload()
                if len(data) < 10:
                    raise RuntimeError("Response too short")
                return bytes(data[10:])

            response_data = await self._recv_cotp_dt()

            version, data_length, consumed = decode_header(response_data)
            response = response_data[consumed : consumed + data_length]

            if len(response) < 10:
                raise RuntimeError("Response too short")

            # RESPONSE header is 10 bytes (opcode+res+func+res+seqnr+transport) — responses
            # carry no SessionId field (requests do, hence their 14-byte header). For V2+ the
            # IntegrityId travels at the END of the payload and is ignored by the parsers.
            return response[10:]

    async def _recv_reassembled_payload(self) -> bytes:
        """Receive a possibly-fragmented S7CommPlus response, returning its data section.

        A large response is split into several S7CommPlus PDUs. Each fragment is
        ``0x72 <ver> <len:2> <data:len>`` with no trailer; only the final fragment is
        followed by the ``0x72 <ver> 0x0000`` trailer. We concatenate the data parts
        of every fragment until the trailer is seen. Works for single-PDU responses
        too (one fragment immediately followed by the trailer).
        """
        buf = bytearray()

        async def ensure(n: int) -> None:
            while len(buf) < n:
                chunk = await self._recv_cotp_dt()
                if not chunk:
                    raise RuntimeError("Connection closed during response reassembly")
                buf.extend(chunk)

        data = bytearray()
        fragments = 0
        while True:
            await ensure(4)
            if buf[0] != 0x72:
                raise RuntimeError("Expected S7CommPlus fragment header (0x72)")
            frag_len = (buf[2] << 8) | buf[3]
            del buf[:4]
            if frag_len == 0:
                break  # standalone trailer (defensive)
            await ensure(frag_len)
            data.extend(buf[:frag_len])
            del buf[:frag_len]
            fragments += 1
            if fragments > self._MAX_REASSEMBLED_FRAGMENTS or len(data) > self._MAX_REASSEMBLED_BYTES:
                raise RuntimeError(f"Reassembled response exceeds limits ({len(data)} bytes, {fragments} fragments)")
            # The next 4 bytes are either the trailer (0x72 ver 0x0000) or the next
            # fragment's header (0x72 ver len>0).
            await ensure(4)
            if buf[0] == 0x72 and buf[2] == 0 and buf[3] == 0:
                del buf[:4]  # consume trailer — last fragment
                break
        return bytes(data)

    async def _cotp_connect(self, local_tsap: int, remote_tsap: bytes) -> None:
        """Perform COTP Connection Request / Confirm handshake."""
        if self._writer is None or self._reader is None:
            raise RuntimeError("Not connected")

        base_pdu = struct.pack(">BBHHB", 6, _COTP_CR, 0x0000, 0x0001, 0x00)
        calling_tsap = struct.pack(">BBH", 0xC1, 2, local_tsap)
        called_tsap = struct.pack(">BB", 0xC2, len(remote_tsap)) + remote_tsap
        pdu_size_param = struct.pack(">BBB", 0xC0, 1, 0x0A)

        params = calling_tsap + called_tsap + pdu_size_param
        cr_pdu = struct.pack(">B", 6 + len(params)) + base_pdu[1:] + params

        tpkt = struct.pack(">BBH", 3, 0, 4 + len(cr_pdu)) + cr_pdu
        self._writer.write(tpkt)
        await self._writer.drain()

        tpkt_header = await self._reader.readexactly(4)
        _, _, length = struct.unpack(">BBH", tpkt_header)
        payload = await self._reader.readexactly(length - 4)

        if len(payload) < 7 or payload[1] != _COTP_CC:
            raise RuntimeError(f"Expected COTP CC, got {payload[1]:#04x}")

    async def _init_ssl(self) -> None:
        """Send InitSSL request (required before CreateObject)."""
        seq_num = self._next_sequence_number()

        request = struct.pack(
            ">BHHHHIB",
            Opcode.REQUEST,
            0x0000,
            FunctionCode.INIT_SSL,
            0x0000,
            seq_num,
            0x00000000,
            0x30,
        )
        request += struct.pack(">I", 0)

        frame = encode_header(ProtocolVersion.V1, len(request)) + request
        frame += struct.pack(">BBH", 0x72, ProtocolVersion.V1, 0x0000)
        await self._send_cotp_dt(frame)

        response_data = await self._recv_cotp_dt()
        version, data_length, consumed = decode_header(response_data)
        response = response_data[consumed : consumed + data_length]

        if len(response) < 14:
            raise RuntimeError("InitSSL response too short")

        logger.debug(f"InitSSL response received, version=V{version}")

    async def _create_session(self) -> None:
        """Send CreateObject to establish S7CommPlus session."""
        seq_num = self._next_sequence_number()

        request = struct.pack(
            ">BHHHHIB",
            Opcode.REQUEST,
            0x0000,
            FunctionCode.CREATE_OBJECT,
            0x0000,
            seq_num,
            ObjectId.OBJECT_NULL_SERVER_SESSION,
            0x36,
        )

        request += struct.pack(">I", ObjectId.OBJECT_SERVER_SESSION_CONTAINER)
        request += bytes([0x00, DataType.UDINT]) + encode_uint32_vlq(0)
        request += struct.pack(">I", 0)

        request += bytes([ElementID.START_OF_OBJECT])
        request += struct.pack(">I", ObjectId.GET_NEW_RID_ON_SERVER)
        request += encode_uint32_vlq(ObjectId.CLASS_SERVER_SESSION)
        request += encode_uint32_vlq(0)
        request += encode_uint32_vlq(0)

        request += bytes([ElementID.ATTRIBUTE])
        request += encode_uint32_vlq(ObjectId.SERVER_SESSION_CLIENT_RID)
        request += bytes([0x00]) + encode_typed_value(DataType.RID, 0x80C3C901)

        request += bytes([ElementID.START_OF_OBJECT])
        request += struct.pack(">I", ObjectId.GET_NEW_RID_ON_SERVER)
        request += encode_uint32_vlq(ObjectId.CLASS_SUBSCRIPTIONS)
        request += encode_uint32_vlq(0)
        request += encode_uint32_vlq(0)
        request += bytes([ElementID.TERMINATING_OBJECT])

        request += bytes([ElementID.TERMINATING_OBJECT])
        request += struct.pack(">I", 0)

        frame = encode_header(ProtocolVersion.V1, len(request)) + request
        frame += struct.pack(">BBH", 0x72, ProtocolVersion.V1, 0x0000)
        await self._send_cotp_dt(frame)

        response_data = await self._recv_cotp_dt()
        version, data_length, consumed = decode_header(response_data)
        response = response_data[consumed : consumed + data_length]

        if len(response) < 14:
            raise RuntimeError("CreateObject response too short")

        # Parse response body: ReturnValue(VLQ) + ObjectIdCount + ObjectIds(VLQ).
        # The usable session id is ObjectIds[0] (NOT the header SessionId field).
        body = response[14:]
        object_ids, obj_end = parse_create_object_session_id(body)
        if object_ids:
            self._session_id = object_ids[0]
        else:
            self._session_id = struct.unpack_from(">I", response, 9)[0]
        self._protocol_version = version

        self._server_session_version = parse_server_session_version(response[14 + obj_end :])
        if self._server_session_version is not None:
            logger.info(f"ServerSessionVersion captured: {len(self._server_session_version)} bytes")
        else:
            logger.debug("ServerSessionVersion not found in CreateObject response")

    async def _setup_session(self) -> bool:
        """Echo ServerSessionVersion back to the PLC via SetMultiVariables."""
        if self._server_session_version is None:
            return False

        payload = bytearray()
        payload += struct.pack(">I", self._session_id)
        payload += encode_uint32_vlq(1)
        payload += encode_uint32_vlq(1)
        payload += encode_uint32_vlq(ObjectId.SERVER_SESSION_VERSION)
        payload += encode_uint32_vlq(1)
        # PValue: echo the ServerSessionVersion typed value verbatim (it may be a Struct)
        payload += self._server_session_version
        payload += bytes([0x00])
        payload += encode_object_qualifier()
        payload += struct.pack(">I", 0)

        try:
            resp_payload = await self._send_request(FunctionCode.SET_MULTI_VARIABLES, bytes(payload))
            if len(resp_payload) >= 1:
                return_value, _ = decode_uint64_vlq(resp_payload, 0)
                if return_value != 0:
                    logger.warning(f"SetupSession: PLC returned error {return_value}")
                    return False
                else:
                    logger.info("Session setup completed successfully")
                    return True
            return False
        except Exception as e:
            logger.warning(f"SetupSession failed: {e}")
            return False

    async def _delete_session(self) -> None:
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
        await self._send_cotp_dt(frame)

        try:
            await asyncio.wait_for(self._recv_cotp_dt(), timeout=1.0)
        except Exception:
            pass

    async def _send_cotp_dt(self, data: bytes) -> None:
        """Send an S7CommPlus frame, routing through TLS (tunneled in COTP) when active."""
        if self._tls_active:
            assert self._ssl_object is not None
            self._ssl_object.write(data)
            await self._tls_flush_outgoing()
        else:
            await self._send_cotp_raw(data)

    async def _recv_cotp_dt(self) -> bytes:
        """Receive an S7CommPlus frame, decrypting from the TLS tunnel when active."""
        if self._tls_active:
            assert self._ssl_object is not None
            while True:
                try:
                    return self._ssl_object.read(65536)
                except ssl.SSLWantReadError:
                    await self._tls_read_incoming()
        else:
            return await self._recv_cotp_raw()

    async def _send_cotp_raw(self, data: bytes) -> None:
        """Send raw bytes wrapped in COTP DT + TPKT (no TLS)."""
        if self._writer is None:
            raise RuntimeError("Not connected")

        cotp_dt = struct.pack(">BBB", 2, _COTP_DT, 0x80) + data
        tpkt = struct.pack(">BBH", 3, 0, 4 + len(cotp_dt)) + cotp_dt
        self._writer.write(tpkt)
        await self._writer.drain()

    async def _recv_cotp_raw(self) -> bytes:
        """Receive one TPKT + COTP DT frame and return the payload (no TLS)."""
        if self._reader is None:
            raise RuntimeError("Not connected")

        tpkt_header = await self._reader.readexactly(4)
        _, _, length = struct.unpack(">BBH", tpkt_header)
        payload = await self._reader.readexactly(length - 4)

        if len(payload) < 3 or payload[1] != _COTP_DT:
            raise RuntimeError(f"Expected COTP DT, got {payload[1]:#04x}")

        return payload[3:]

    def _next_sequence_number(self) -> int:
        seq = self._sequence_number
        self._sequence_number = (self._sequence_number + 1) & 0xFFFF
        return seq

    async def __aenter__(self) -> "S7CommPlusAsyncClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.disconnect()
