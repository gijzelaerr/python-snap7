"""
Tests for MicroPython / CircuitPython compatibility.

These tests verify that the core protocol modules can be imported and
perform basic operations using only features available in MicroPython.
They do NOT test actual socket connections (those are platform-dependent).
"""

import struct


class TestCompatModule:
    """Tests for snap7.compat itself."""

    def test_micropython_flag_is_bool(self) -> None:
        from snap7.compat import MICROPYTHON

        assert isinstance(MICROPYTHON, bool)

    def test_cache_decorator_works(self) -> None:
        """The cache shim (or real functools.cache) must be callable."""
        from snap7.compat import cache

        call_count = 0

        @cache
        def add(a: int, b: int) -> int:
            nonlocal call_count
            call_count += 1
            return a + b

        assert add(1, 2) == 3
        assert add(1, 2) == 3  # second call -- cached on CPython
        # On CPython call_count == 1 (cached), on MicroPython == 2 (no cache).
        # Both are acceptable.
        assert call_count in (1, 2)

    def test_has_ctypes_flag(self) -> None:
        from snap7.compat import HAS_CTYPES

        assert isinstance(HAS_CTYPES, bool)
        # On CPython this should always be True
        assert HAS_CTYPES is True


class TestProtocolEncodingDecoding:
    """Verify that core protocol operations work with basic byte ops."""

    def test_tpkt_framing(self) -> None:
        """TPKT header build/parse round-trips correctly."""
        payload = b"\x01\x02\x03"
        length = len(payload) + 4
        frame = struct.pack(">BBH", 3, 0, length) + payload

        version, reserved, parsed_length = struct.unpack(">BBH", frame[:4])
        assert version == 3
        assert reserved == 0
        assert parsed_length == 7
        assert frame[4:] == payload

    def test_cotp_dt_header(self) -> None:
        """COTP Data Transfer header encoding."""
        header = struct.pack(">BBB", 2, 0xF0, 0x80)
        assert len(header) == 3
        assert header[1] == 0xF0  # DT PDU type

    def test_s7_header_encoding(self) -> None:
        """S7 PDU header can be built with struct.pack."""
        header = struct.pack(
            ">BBHHHH",
            0x32,   # Protocol ID
            0x01,   # PDU type (request)
            0x0000, # Reserved
            0x0001, # Sequence
            0x000E, # Param length
            0x0000, # Data length
        )
        # BBHHHH = 1+1+2+2+2+2 = 10 bytes (request header without error fields)
        assert len(header) == 10
        assert header[0] == 0x32

    def test_s7_address_encoding(self) -> None:
        """S7 address specification encoding uses struct only."""
        from snap7.datatypes import S7Area, S7WordLen, S7DataTypes

        addr = S7DataTypes.encode_address(
            area=S7Area.DB,
            db_number=1,
            start=0,
            word_len=S7WordLen.BYTE,
            count=4,
        )
        assert isinstance(addr, bytes)
        assert len(addr) == 12
        # First byte is specification type 0x12
        assert addr[0] == 0x12


class TestDataTypeConversions:
    """Verify data type encode/decode without ctypes."""

    def test_decode_int16(self) -> None:
        from snap7.datatypes import S7DataTypes, S7WordLen

        data = struct.pack(">h", -1234)
        values = S7DataTypes.decode_s7_data(data, S7WordLen.INT, 1)
        assert values == [-1234]

    def test_encode_int16(self) -> None:
        from snap7.datatypes import S7DataTypes, S7WordLen

        encoded = S7DataTypes.encode_s7_data([-1234], S7WordLen.INT)
        assert encoded == struct.pack(">h", -1234)

    def test_decode_real(self) -> None:
        from snap7.datatypes import S7DataTypes, S7WordLen

        data = struct.pack(">f", 3.14)
        values = S7DataTypes.decode_s7_data(data, S7WordLen.REAL, 1)
        assert abs(values[0] - 3.14) < 0.001

    def test_encode_real(self) -> None:
        from snap7.datatypes import S7DataTypes, S7WordLen

        encoded = S7DataTypes.encode_s7_data([3.14], S7WordLen.REAL)
        (val,) = struct.unpack(">f", encoded)
        assert abs(val - 3.14) < 0.001

    def test_decode_dword(self) -> None:
        from snap7.datatypes import S7DataTypes, S7WordLen

        data = struct.pack(">I", 0xDEADBEEF)
        values = S7DataTypes.decode_s7_data(data, S7WordLen.DWORD, 1)
        assert values == [0xDEADBEEF]

    def test_decode_bit(self) -> None:
        from snap7.datatypes import S7DataTypes, S7WordLen

        values = S7DataTypes.decode_s7_data(b"\x01\x00", S7WordLen.BIT, 2)
        assert values == [True, False]

    def test_encode_multiple_bytes(self) -> None:
        from snap7.datatypes import S7DataTypes, S7WordLen

        encoded = S7DataTypes.encode_s7_data([10, 20, 30], S7WordLen.BYTE)
        assert encoded == bytes([10, 20, 30])


class TestAddressParsing:
    """Verify address string parsing (pure Python, no ctypes)."""

    def test_parse_db_address(self) -> None:
        from snap7.datatypes import S7Area, S7DataTypes

        area, db, offset = S7DataTypes.parse_address("DB1.DBW10")
        assert area == S7Area.DB
        assert db == 1
        assert offset == 10

    def test_parse_marker_address(self) -> None:
        from snap7.datatypes import S7Area, S7DataTypes

        area, db, offset = S7DataTypes.parse_address("MW20")
        assert area == S7Area.MK
        assert db == 0
        assert offset == 20

    def test_parse_input_bit_address(self) -> None:
        from snap7.datatypes import S7Area, S7DataTypes

        area, db, offset = S7DataTypes.parse_address("I0.3")
        assert area == S7Area.PE
        assert db == 0
        assert offset == 3  # bit 3 of byte 0


class TestUtilGettersSetters:
    """Verify util getters/setters work with pure bytearray ops."""

    def test_get_set_bool(self) -> None:
        from snap7.util import get_bool, set_bool

        buf = bytearray(2)
        set_bool(buf, 0, 3, True)
        assert get_bool(buf, 0, 3) is True
        assert get_bool(buf, 0, 0) is False

    def test_get_set_int(self) -> None:
        from snap7.util import get_int, set_int

        buf = bytearray(10)
        set_int(buf, 2, -500)
        assert get_int(buf, 2) == -500

    def test_get_set_real(self) -> None:
        from snap7.util import get_real, set_real

        buf = bytearray(10)
        set_real(buf, 0, 3.14)
        assert abs(get_real(buf, 0) - 3.14) < 0.001

    def test_get_set_dword(self) -> None:
        from snap7.util import get_dword, set_dword

        buf = bytearray(10)
        set_dword(buf, 0, 0xCAFEBABE)
        assert get_dword(buf, 0) == 0xCAFEBABE

    def test_get_set_byte(self) -> None:
        from snap7.util import get_byte, set_byte

        buf = bytearray(4)
        set_byte(buf, 1, 0xAB)
        assert get_byte(buf, 1) == 0xAB  # type: ignore[comparison-overlap]


class TestS7ProtocolBuild:
    """Verify S7Protocol PDU building works (struct-only, no ctypes)."""

    def test_build_setup_communication(self) -> None:
        from snap7.s7protocol import S7Protocol

        proto = S7Protocol()
        pdu = proto.build_setup_communication_request()
        assert isinstance(pdu, bytes)
        assert pdu[0] == 0x32  # S7 protocol ID

    def test_build_read_request(self) -> None:
        from snap7.s7protocol import S7Protocol
        from snap7.datatypes import S7Area, S7WordLen

        proto = S7Protocol()
        pdu = proto.build_read_request(S7Area.DB, 1, 0, S7WordLen.BYTE, 4)
        assert isinstance(pdu, bytes)
        assert pdu[0] == 0x32

    def test_build_write_request(self) -> None:
        from snap7.s7protocol import S7Protocol
        from snap7.datatypes import S7Area, S7WordLen

        proto = S7Protocol()
        pdu = proto.build_write_request(S7Area.DB, 1, 0, S7WordLen.BYTE, b"\x01\x02\x03\x04")
        assert isinstance(pdu, bytes)
        assert pdu[0] == 0x32

    def test_parse_response_setup_comm(self) -> None:
        """Round-trip: build a mock setup-comm response and parse it."""
        from snap7.s7protocol import S7Protocol, S7PDUType, S7Function

        # Build a minimal ACK_DATA response for setup communication
        params = struct.pack(
            ">BBHHH",
            S7Function.SETUP_COMMUNICATION,
            0x00,   # reserved
            1,      # max_amq_caller
            1,      # max_amq_callee
            480,    # pdu_length
        )
        header = struct.pack(
            ">BBHHHHBB",
            0x32,
            S7PDUType.ACK_DATA,
            0x0000,
            0x0001,         # sequence
            len(params),    # param_len
            0,              # data_len
            0,              # error_class
            0,              # error_code
        )
        pdu = header + params

        proto = S7Protocol()
        proto.sequence = 1  # match the sequence
        response = proto.parse_response(pdu)

        assert response["parameters"]["pdu_length"] == 480
        assert response["error_code"] == 0


class TestErrorModule:
    """Verify error module works with the compat cache shim."""

    def test_error_text(self) -> None:
        from snap7.error import error_text

        msg = error_text(0x00100000, "client")
        assert msg == "errNegotiatingPDU"

    def test_get_error_message(self) -> None:
        from snap7.error import get_error_message

        assert get_error_message(0) == "Success"

    def test_get_protocol_error_message(self) -> None:
        from snap7.error import get_protocol_error_message

        assert "No error" in get_protocol_error_message(0x0000)
