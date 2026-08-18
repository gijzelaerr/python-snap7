"""Siemens S7-200 PPI serial transport and client.

PPI carries ordinary S7 PDUs inside PROFIBUS-style SD1/SD2 frames. The
implementation follows the request/acknowledgement exchange used by libnodave:
an SD2 request, an E5 acknowledgement, an SD1 request-data poll, and an SD2
response.
"""

import importlib
import logging
import threading
from dataclasses import dataclass
from enum import IntEnum
from types import TracebackType
from typing import Any, Protocol, cast

from .datatypes import S7Area, S7WordLen
from .error import S7ConnectionError, S7ProtocolError
from .s7protocol import S7Protocol

logger = logging.getLogger(__name__)


class PPIFrameType(IntEnum):
    """PPI/PROFIBUS frame delimiters."""

    SD1 = 0x10
    SD2 = 0x68
    SD3 = 0xA2
    SC = 0xE5


class PPIArea(IntEnum):
    """S7-200 memory area identifiers."""

    S = 0x03
    SM = 0x05
    AI = 0x06
    AQ = 0x07
    I = 0x81
    Q = 0x82
    M = 0x83
    V = 0x84  # V memory is addressed as DB1 on the wire.
    C = 0x1E
    T = 0x1F


@dataclass(frozen=True)
class PPIFrame:
    """Decoded PPI frame."""

    frame_type: PPIFrameType
    destination: int | None = None
    source: int | None = None
    control: int | None = None
    payload: bytes = b""


class SerialPort(Protocol):
    """Minimal serial-port interface used by :class:`PPITransport`."""

    def read(self, size: int = 1) -> bytes: ...

    def write(self, data: bytes) -> int | None: ...

    def close(self) -> None: ...


class PPIExchangeTransport(Protocol):
    """Transport interface consumed by :class:`PPIClient`."""

    def open(self) -> None: ...

    def close(self) -> None: ...

    def exchange(self, pdu: bytes) -> bytes: ...


def _validate_station(address: int) -> None:
    if not 0 <= address <= 126:
        raise ValueError(f"PPI station address must be between 0 and 126, got {address}")


def _checksum(data: bytes) -> int:
    return sum(data) & 0xFF


def encode_sd1(destination: int, source: int, control: int) -> bytes:
    """Encode a fixed-length SD1 frame."""
    _validate_station(destination)
    _validate_station(source)
    body = bytes((destination, source, control))
    return bytes((PPIFrameType.SD1,)) + body + bytes((_checksum(body), 0x16))


def encode_sd2(destination: int, source: int, control: int, payload: bytes) -> bytes:
    """Encode a variable-length SD2 frame."""
    _validate_station(destination)
    _validate_station(source)
    body = bytes((destination, source, control)) + payload
    if len(body) > 249:
        raise ValueError(f"SD2 body exceeds the 249-byte limit: {len(body)}")
    length = len(body)
    return bytes((PPIFrameType.SD2, length, length, PPIFrameType.SD2)) + body + bytes((_checksum(body), 0x16))


def encode_sd3(destination: int, source: int, control: int, payload: bytes) -> bytes:
    """Encode an SD3 frame with its fixed eight-byte data field."""
    _validate_station(destination)
    _validate_station(source)
    if len(payload) != 8:
        raise ValueError("SD3 payload must contain exactly 8 bytes")
    body = bytes((destination, source, control)) + payload
    return bytes((PPIFrameType.SD3,)) + body + bytes((_checksum(body), 0x16))


def decode_frame(data: bytes) -> PPIFrame:
    """Decode and validate one complete PPI frame."""
    if not data:
        raise S7ProtocolError("Empty PPI frame")

    try:
        frame_type = PPIFrameType(data[0])
    except ValueError as exc:
        raise S7ProtocolError(f"Unknown PPI start delimiter: 0x{data[0]:02x}") from exc

    if frame_type == PPIFrameType.SC:
        if data != bytes((PPIFrameType.SC,)):
            raise S7ProtocolError("SC acknowledgement must be exactly one byte")
        return PPIFrame(frame_type)

    if frame_type == PPIFrameType.SD1:
        if len(data) != 6:
            raise S7ProtocolError(f"SD1 frame must be 6 bytes, got {len(data)}")
        body = data[1:4]
    elif frame_type == PPIFrameType.SD2:
        if len(data) < 9:
            raise S7ProtocolError("SD2 frame is too short")
        if data[1] != data[2] or data[3] != PPIFrameType.SD2:
            raise S7ProtocolError("Invalid SD2 repeated length or delimiter")
        if len(data) != data[1] + 6:
            raise S7ProtocolError(f"SD2 length mismatch: header says {data[1]}, frame has {len(data)} bytes")
        body = data[4:-2]
    else:
        if len(data) != 14:
            raise S7ProtocolError(f"SD3 frame must be 14 bytes, got {len(data)}")
        body = data[1:-2]

    if data[-1] != 0x16:
        raise S7ProtocolError("Invalid PPI end delimiter")
    if data[-2] != _checksum(body):
        raise S7ProtocolError("Invalid PPI frame checksum")

    return PPIFrame(frame_type, body[0], body[1], body[2], bytes(body[3:]))


class PPITransport:
    """Serial PPI master transport for a single S7-200 slave."""

    def __init__(
        self,
        port: str,
        *,
        station: int = 2,
        local_station: int = 0,
        baudrate: int = 9600,
        timeout: float = 0.15,
        retries: int = 3,
        serial_port: SerialPort | None = None,
    ) -> None:
        _validate_station(station)
        _validate_station(local_station)
        if baudrate <= 0:
            raise ValueError("baudrate must be positive")
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        if retries < 1:
            raise ValueError("retries must be at least 1")

        self.port = port
        self.station = station
        self.local_station = local_station
        self.baudrate = baudrate
        self.timeout = timeout
        self.retries = retries
        self._serial = serial_port
        self._owns_serial = serial_port is None
        self._lock = threading.Lock()

    @property
    def is_open(self) -> bool:
        return self._serial is not None

    def open(self) -> None:
        """Open the configured serial port using PPI's 8E1 settings."""
        if self._serial is not None:
            return
        try:
            serial = importlib.import_module("serial")
        except ImportError as exc:
            raise ImportError("PPI support requires pyserial; install python-snap7[ppi]") from exc

        try:
            self._serial = cast(
                SerialPort,
                serial.Serial(
                    port=self.port,
                    baudrate=self.baudrate,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_EVEN,
                    stopbits=serial.STOPBITS_ONE,
                    timeout=self.timeout,
                    write_timeout=self.timeout,
                ),
            )
        except Exception as exc:
            raise S7ConnectionError(f"Could not open PPI serial port {self.port}: {exc}") from exc

    def close(self) -> None:
        """Close a serial port opened by this transport."""
        if self._serial is not None and self._owns_serial:
            self._serial.close()
            self._serial = None

    def _read_exact(self, size: int) -> bytes:
        assert self._serial is not None
        data = bytearray()
        while len(data) < size:
            chunk = self._serial.read(size - len(data))
            if not chunk:
                raise S7ConnectionError(f"Timeout while reading PPI frame ({len(data)}/{size} bytes)")
            data.extend(chunk)
        return bytes(data)

    def _read_frame(self) -> PPIFrame:
        start = self._read_exact(1)
        delimiter = start[0]
        if delimiter == PPIFrameType.SC:
            return decode_frame(start)
        if delimiter == PPIFrameType.SD1:
            return decode_frame(start + self._read_exact(5))
        if delimiter == PPIFrameType.SD2:
            prefix = self._read_exact(3)
            if prefix[0] != prefix[1] or prefix[2] != PPIFrameType.SD2:
                raise S7ProtocolError("Invalid SD2 repeated length or delimiter")
            return decode_frame(start + prefix + self._read_exact(prefix[0] + 2))
        if delimiter == PPIFrameType.SD3:
            return decode_frame(start + self._read_exact(13))
        raise S7ProtocolError(f"Unknown PPI start delimiter: 0x{delimiter:02x}")

    def _write_frame(self, frame: bytes) -> None:
        assert self._serial is not None
        written = self._serial.write(frame)
        if written is not None and written != len(frame):
            raise S7ConnectionError(f"Short PPI serial write ({written}/{len(frame)} bytes)")

    def exchange(self, pdu: bytes) -> bytes:
        """Exchange one S7 PDU with the configured S7-200 station."""
        if self._serial is None:
            raise S7ConnectionError("PPI serial port is not open")

        request = encode_sd2(self.station, self.local_station, 0x6C, pdu)
        with self._lock:
            for attempt in range(self.retries):
                self._write_frame(request)
                try:
                    acknowledgement = self._read_frame()
                except S7ConnectionError:
                    if attempt + 1 == self.retries:
                        raise
                    continue
                if acknowledgement.frame_type != PPIFrameType.SC:
                    raise S7ProtocolError("Expected E5 acknowledgement after PPI request")
                break

            poll_control = 0x5C
            self._write_frame(encode_sd1(self.station, self.local_station, poll_control))
            for _ in range(self.retries * 2):
                response = self._read_frame()
                if response.frame_type == PPIFrameType.SC:
                    poll_control = 0x7C if poll_control == 0x5C else 0x5C
                    self._write_frame(encode_sd1(self.station, self.local_station, poll_control))
                    continue
                if response.frame_type != PPIFrameType.SD2:
                    raise S7ProtocolError(f"Expected SD2 PPI response, got {response.frame_type.name}")
                if response.destination != self.local_station or response.source != self.station:
                    raise S7ProtocolError(
                        f"Unexpected PPI response addresses: {response.source} -> {response.destination}"
                    )
                return response.payload

        raise S7ConnectionError("PPI response was not available after polling")


class PPIClient:
    """Minimal S7-200 client using PPI over a serial port."""

    def __init__(
        self,
        port: str,
        *,
        station: int = 2,
        local_station: int = 0,
        baudrate: int = 9600,
        timeout: float = 0.15,
        transport: PPIExchangeTransport | None = None,
    ) -> None:
        self.transport = transport or PPITransport(
            port,
            station=station,
            local_station=local_station,
            baudrate=baudrate,
            timeout=timeout,
        )
        self.protocol = S7Protocol()
        self.connected = False
        self.pdu_length = 240

    def connect(self) -> "PPIClient":
        """Open the serial port and negotiate the S7 PDU length."""
        self.transport.open()
        try:
            request = self.protocol.build_setup_communication_request(pdu_length=self.pdu_length)
            response = self._exchange(request)
            parameters = response.get("parameters") or {}
            negotiated = int(parameters.get("pdu_length", self.pdu_length))
            # SD2's one-byte length field permits at most 249 body bytes;
            # three of those are the PPI destination/source/control fields.
            self.pdu_length = min(negotiated, 246)
            self.connected = True
        except Exception:
            self.transport.close()
            raise
        return self

    def disconnect(self) -> None:
        """Close the PPI transport."""
        self.transport.close()
        self.connected = False

    def _exchange(self, request: bytes) -> dict[str, Any]:
        response = self.protocol.parse_response(self.transport.exchange(request))
        self.protocol.validate_pdu_reference(int(response["sequence"]))
        return response

    @staticmethod
    def _area_spec(area: PPIArea) -> tuple[S7Area, int, S7WordLen]:
        if area == PPIArea.V:
            return S7Area.DB, 1, S7WordLen.BYTE
        if area in (PPIArea.AI, PPIArea.AQ):
            return cast(S7Area, area), 0, S7WordLen.WORD
        if area == PPIArea.C:
            return cast(S7Area, area), 0, S7WordLen.COUNTER_200
        if area == PPIArea.T:
            return cast(S7Area, area), 0, S7WordLen.TIMER_200
        return cast(S7Area, area), 0, S7WordLen.BYTE

    def read_area(self, area: PPIArea, start: int, count: int) -> bytearray:
        """Read items from an S7-200 memory area.

        ``count`` is bytes for S/SM/I/Q/M/V and 16-bit items for AI/AQ/C/T.
        """
        if not self.connected:
            raise S7ConnectionError("PPI client is not connected")
        if count < 1:
            raise ValueError("count must be at least 1")
        wire_area, db_number, word_len = self._area_spec(area)
        item_size = 2 if word_len in (S7WordLen.WORD, S7WordLen.COUNTER_200, S7WordLen.TIMER_200) else 1
        if count * item_size > self.pdu_length - 18:
            raise ValueError("PPI read exceeds the negotiated PDU size")
        request = self.protocol.build_read_request(wire_area, db_number, start, word_len, count)
        response = self._exchange(request)
        return bytearray(self.protocol.extract_read_data(response, word_len, count))

    def write_area(self, area: PPIArea, start: int, data: bytes | bytearray) -> None:
        """Write data to an S7-200 memory area."""
        if not self.connected:
            raise S7ConnectionError("PPI client is not connected")
        wire_area, db_number, word_len = self._area_spec(area)
        item_size = 2 if word_len in (S7WordLen.WORD, S7WordLen.COUNTER_200, S7WordLen.TIMER_200) else 1
        if not data or len(data) % item_size:
            raise ValueError(f"data length must be a non-zero multiple of {item_size}")
        if len(data) > self.pdu_length - 35:
            raise ValueError("PPI write exceeds the negotiated PDU size")
        request = self.protocol.build_write_request(wire_area, db_number, start, word_len, bytes(data))
        self.protocol.check_write_response(self._exchange(request))

    def v_read(self, start: int, size: int) -> bytearray:
        """Read bytes from S7-200 V memory (wire-level DB1)."""
        return self.read_area(PPIArea.V, start, size)

    def v_write(self, start: int, data: bytes | bytearray) -> None:
        """Write bytes to S7-200 V memory (wire-level DB1)."""
        self.write_area(PPIArea.V, start, data)

    def __enter__(self) -> "PPIClient":
        return self.connect()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.disconnect()
