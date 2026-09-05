"""Tests for S7-200 PPI frames, serial exchange, and client operations."""

import struct

import pytest

from snap7.error import S7ConnectionError, S7ProtocolError
from snap7.ppi import (
    PPIArea,
    PPIClient,
    PPIFrame,
    PPIFrameType,
    PPITransport,
    decode_frame,
    encode_sd1,
    encode_sd2,
    encode_sd3,
)
from snap7.s7protocol import S7Function, S7PDUType


class FakeSerial:
    def __init__(self, incoming: bytes, *, chunk_size: int = 2) -> None:
        self.incoming = bytearray(incoming)
        self.chunk_size = chunk_size
        self.writes: list[bytes] = []
        self.closed = False

    def read(self, size: int = 1) -> bytes:
        count = min(size, self.chunk_size, len(self.incoming))
        data = bytes(self.incoming[:count])
        del self.incoming[:count]
        return data

    def write(self, data: bytes) -> int:
        self.writes.append(data)
        return len(data)

    def close(self) -> None:
        self.closed = True


def _response_pdu(sequence: int, function: int, *, data: bytes = b"", setup_pdu_length: int | None = None) -> bytes:
    if setup_pdu_length is None:
        parameters = bytes((function, 1))
    else:
        parameters = struct.pack(">BBHHH", function, 0, 1, 1, setup_pdu_length)
    header = struct.pack(
        ">BBHHHHBB",
        0x32,
        S7PDUType.ACK_DATA,
        0,
        sequence,
        len(parameters),
        len(data),
        0,
        0,
    )
    return header + parameters + data


class StubTransport:
    def __init__(self) -> None:
        self.requests: list[bytes] = []
        self.opened = False

    def open(self) -> None:
        self.opened = True

    def close(self) -> None:
        self.opened = False

    def exchange(self, pdu: bytes) -> bytes:
        self.requests.append(pdu)
        sequence = struct.unpack_from(">H", pdu, 4)[0]
        function = pdu[10]
        if function == S7Function.SETUP_COMMUNICATION:
            return _response_pdu(sequence, function, setup_pdu_length=240)
        if function == S7Function.READ_AREA:
            count = struct.unpack_from(">H", pdu, 16)[0]
            word_len = pdu[15]
            byte_count = count * (2 if word_len in (0x04, 0x1E, 0x1F) else 1)
            values = bytes(range(byte_count))
            data = struct.pack(">BBH", 0xFF, 0x04, byte_count * 8) + values
            return _response_pdu(sequence, function, data=data)
        return _response_pdu(sequence, function)


@pytest.mark.parametrize(
    "frame",
    [
        encode_sd1(2, 0, 0x5C),
        encode_sd2(2, 0, 0x6C, b"\x32\x01"),
        encode_sd3(2, 0, 0x03, bytes(range(8))),
        bytes((PPIFrameType.SC,)),
    ],
)
def test_frame_roundtrip(frame: bytes) -> None:
    decoded = decode_frame(frame)
    assert decoded.frame_type == frame[0]


def test_decode_sd2_fields() -> None:
    assert decode_frame(encode_sd2(2, 0, 0x6C, b"payload")) == PPIFrame(
        PPIFrameType.SD2,
        destination=2,
        source=0,
        control=0x6C,
        payload=b"payload",
    )


@pytest.mark.parametrize(
    "frame",
    [
        b"",
        b"\x99",
        b"\xe5\x00",
        b"\x10\x02",
        b"\x68\x03\x04\x68\x02\x00\x6c\x6e\x16",
        b"\x68\x03\x03\x68\x02\x00\x6c\x00\x16",
    ],
)
def test_malformed_frames_rejected(frame: bytes) -> None:
    with pytest.raises(S7ProtocolError):
        decode_frame(frame)


def test_frame_encoder_validation() -> None:
    with pytest.raises(ValueError, match="station address"):
        encode_sd1(127, 0, 0x5C)
    with pytest.raises(ValueError, match="249-byte"):
        encode_sd2(2, 0, 0x6C, bytes(247))
    with pytest.raises(ValueError, match="exactly 8"):
        encode_sd3(2, 0, 0x03, b"short")


def test_serial_exchange_uses_sd2_ack_sd1_sd2_flow() -> None:
    response_pdu = b"\x32\x03 response"
    incoming = bytes((PPIFrameType.SC,)) + encode_sd2(0, 2, 0x08, response_pdu)
    serial = FakeSerial(incoming)
    transport = PPITransport("test", serial_port=serial)

    assert transport.exchange(b"request") == response_pdu
    assert serial.writes == [encode_sd2(2, 0, 0x6C, b"request"), encode_sd1(2, 0, 0x5C)]


def test_serial_exchange_alternates_poll_control_after_e5() -> None:
    incoming = bytes((PPIFrameType.SC, PPIFrameType.SC)) + encode_sd2(0, 2, 0x08, b"response")
    serial = FakeSerial(incoming)
    transport = PPITransport("test", serial_port=serial)

    assert transport.exchange(b"request") == b"response"
    assert serial.writes[-2:] == [encode_sd1(2, 0, 0x5C), encode_sd1(2, 0, 0x7C)]


def test_serial_timeout_is_reported() -> None:
    transport = PPITransport("test", retries=1, serial_port=FakeSerial(b""))
    with pytest.raises(S7ConnectionError, match="Timeout"):
        transport.exchange(b"request")


def test_client_negotiates_and_reads_writes_v_memory_as_db1() -> None:
    transport = StubTransport()
    client = PPIClient("test", transport=transport).connect()

    assert client.pdu_length == 240
    assert client.v_read(3, 4) == bytearray(range(4))
    client.v_write(5, b"\x01\x02")

    read_request = transport.requests[1]
    assert read_request[15] == 0x02  # BYTE
    assert read_request[18:20] == b"\x00\x01"  # DB1
    assert read_request[20] == 0x84  # DB/V area
    assert read_request[21:24] == b"\x00\x00\x18"  # byte 3 as a bit address

    write_request = transport.requests[2]
    assert write_request[18:20] == b"\x00\x01"
    assert write_request[21:24] == b"\x00\x00\x28"


def test_client_encodes_analog_and_counter_item_addresses() -> None:
    transport = StubTransport()
    client = PPIClient("test", transport=transport).connect()

    assert client.read_area(PPIArea.AI, 1, 2) == bytearray(range(4))
    assert client.read_area(PPIArea.C, 3, 2) == bytearray(range(4))

    analog_request = transport.requests[1]
    assert analog_request[15] == 0x04  # WORD
    assert analog_request[20] == PPIArea.AI
    assert analog_request[21:24] == b"\x00\x00\x08"

    counter_request = transport.requests[2]
    assert counter_request[15] == PPIArea.C
    assert counter_request[20] == PPIArea.C
    assert counter_request[21:24] == b"\x00\x00\x03"  # item index, not bit address


@pytest.mark.parametrize(
    ("area", "wire_area", "db_number", "word_len"),
    [
        (PPIArea.S, 0x03, 0, 0x02),
        (PPIArea.SM, 0x05, 0, 0x02),
        (PPIArea.AI, 0x06, 0, 0x04),
        (PPIArea.AQ, 0x07, 0, 0x04),
        (PPIArea.I, 0x81, 0, 0x02),
        (PPIArea.Q, 0x82, 0, 0x02),
        (PPIArea.M, 0x83, 0, 0x02),
        (PPIArea.V, 0x84, 1, 0x02),
        (PPIArea.C, 0x1E, 0, 0x1E),
        (PPIArea.T, 0x1F, 0, 0x1F),
    ],
)
def test_s7_200_area_mapping(area: PPIArea, wire_area: int, db_number: int, word_len: int) -> None:
    mapped_area, mapped_db, mapped_word_len = PPIClient._area_spec(area)
    assert int(mapped_area) == wire_area
    assert mapped_db == db_number
    assert int(mapped_word_len) == word_len


def test_client_requires_connection_and_aligned_word_data() -> None:
    client = PPIClient("test", transport=StubTransport())
    with pytest.raises(S7ConnectionError, match="not connected"):
        client.v_read(0, 1)

    client.connect()
    with pytest.raises(ValueError, match="multiple of 2"):
        client.write_area(PPIArea.AQ, 0, b"\x01")
    with pytest.raises(ValueError, match="negotiated PDU"):
        client.v_read(0, client.pdu_length)
    with pytest.raises(ValueError, match="negotiated PDU"):
        client.v_write(0, bytes(client.pdu_length))
