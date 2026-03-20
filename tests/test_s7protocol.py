"""Tests for snap7.s7protocol — response parsers with crafted PDUs, error paths."""

import struct
from typing import Any

import pytest
from datetime import datetime

from snap7.s7protocol import (
    S7Protocol,
    S7PDUType,
    S7Function,
    S7UserDataGroup,
    S7UserDataSubfunction,
    get_return_code_description,
)
from snap7.error import S7ProtocolError


class TestGetReturnCodeDescription:
    def test_known_code(self) -> None:
        assert get_return_code_description(0xFF) == "Success"

    def test_unknown_code(self) -> None:
        assert get_return_code_description(0xAB) == "Unknown error"


class TestParseResponse:
    """Test parse_response() with crafted PDUs."""

    def setup_method(self) -> None:
        self.proto = S7Protocol()

    def _build_ack_data_pdu(
        self,
        func_code: int,
        item_count: int = 1,
        data_section: bytes = b"",
        error_class: int = 0,
        error_code: int = 0,
        sequence: int = 1,
    ) -> bytes:
        """Build a minimal ACK_DATA PDU."""
        params = struct.pack(">BB", func_code, item_count)
        header = struct.pack(
            ">BBHHHHBB",
            0x32,
            S7PDUType.ACK_DATA,
            0x0000,
            sequence,
            len(params),
            len(data_section),
            error_class,
            error_code,
        )
        return header + params + data_section

    def test_pdu_too_short(self) -> None:
        with pytest.raises(S7ProtocolError, match="too short"):
            self.proto.parse_response(b"\x32\x03\x00")

    def test_invalid_protocol_id(self) -> None:
        # Build a valid-length PDU with wrong protocol ID
        pdu = struct.pack(">BBHHHHBB", 0x99, S7PDUType.ACK_DATA, 0, 1, 0, 0, 0, 0)
        with pytest.raises(S7ProtocolError, match="Invalid protocol ID"):
            self.proto.parse_response(pdu)

    def test_unexpected_pdu_type(self) -> None:
        # REQUEST type (0x01) is not a valid response
        pdu = struct.pack(">BBHHHHBB", 0x32, S7PDUType.REQUEST, 0, 1, 0, 0, 0, 0)
        with pytest.raises(S7ProtocolError, match="Expected response PDU"):
            self.proto.parse_response(pdu)

    def test_header_error(self) -> None:
        pdu = struct.pack(">BBHHHHBB", 0x32, S7PDUType.ACK_DATA, 0, 1, 0, 0, 0x05, 0x04)
        with pytest.raises(S7ProtocolError, match="S7 protocol error"):
            self.proto.parse_response(pdu)

    def test_ack_no_data(self) -> None:
        """ACK (type 0x02) PDU with no params or data — write response."""
        pdu = struct.pack(">BBHHHHBB", 0x32, S7PDUType.ACK, 0, 1, 0, 0, 0, 0)
        resp = self.proto.parse_response(pdu)
        assert resp["sequence"] == 1
        assert resp["parameters"] is None
        assert resp["data"] is None

    def test_read_response(self) -> None:
        """ACK_DATA with read parameters and data."""
        data_section = struct.pack(">BBH", 0xFF, 0x04, 16) + b"\xab\xcd"  # 16 bits = 2 bytes
        pdu = self._build_ack_data_pdu(S7Function.READ_AREA, 1, data_section)
        resp = self.proto.parse_response(pdu)
        assert resp["parameters"]["function_code"] == S7Function.READ_AREA
        assert resp["data"]["data"] == b"\xab\xcd"

    def test_write_response_single_byte_data(self) -> None:
        """Write response with single-byte data section (return code only)."""
        data_section = b"\xff"  # success
        pdu = self._build_ack_data_pdu(S7Function.WRITE_AREA, 1, data_section)
        resp = self.proto.parse_response(pdu)
        assert resp["data"]["return_code"] == 0xFF

    def test_setup_comm_response(self) -> None:
        params = struct.pack(">BBHHH", S7Function.SETUP_COMMUNICATION, 0x00, 1, 1, 480)
        header = struct.pack(">BBHHHHBB", 0x32, S7PDUType.ACK_DATA, 0, 1, len(params), 0, 0, 0)
        pdu = header + params
        resp = self.proto.parse_response(pdu)
        assert resp["parameters"]["pdu_length"] == 480

    def test_param_section_extends_beyond_pdu(self) -> None:
        # param_len = 100 but PDU is too short
        header = struct.pack(">BBHHHHBB", 0x32, S7PDUType.ACK_DATA, 0, 1, 100, 0, 0, 0)
        with pytest.raises(S7ProtocolError, match="Parameter section extends beyond PDU"):
            self.proto.parse_response(header)

    def test_data_section_extends_beyond_pdu(self) -> None:
        # data_len = 100 but no data follows
        params = struct.pack(">BB", S7Function.READ_AREA, 1)
        header = struct.pack(">BBHHHHBB", 0x32, S7PDUType.ACK_DATA, 0, 1, len(params), 100, 0, 0)
        pdu = header + params
        with pytest.raises(S7ProtocolError, match="Data section extends beyond PDU"):
            self.proto.parse_response(pdu)

    def test_unknown_function_code(self) -> None:
        pdu = self._build_ack_data_pdu(0xAA, 0)
        resp = self.proto.parse_response(pdu)
        assert resp["parameters"]["function_code"] == 0xAA


class TestUserDataParsing:
    """Test USERDATA PDU parsing."""

    def setup_method(self) -> None:
        self.proto = S7Protocol()

    def _build_userdata_response(
        self,
        group: int = S7UserDataGroup.SZL,
        subfunction: int = S7UserDataSubfunction.READ_SZL,
        sequence_number: int = 0,
        last_data_unit: int = 0x00,
        error_code: int = 0,
        data_payload: bytes = b"",
    ) -> bytes:
        """Build a USERDATA response PDU."""
        # Parameter section (12 bytes for response)
        type_group = 0x80 | (group & 0x0F)  # response type
        param_data = struct.pack(
            ">BBBBBBBBBBH",
            0x00,  # Reserved
            0x01,  # Parameter count
            0x12,  # Type header
            0x08,  # Length (response = 8)
            0x12,  # Method (response)
            type_group,
            subfunction,
            sequence_number,
            0x00,  # Data unit reference
            last_data_unit,
            error_code,
        )

        # Data section
        data_section = (
            struct.pack(
                ">BBH",
                0xFF,  # Return code (success)
                0x09,  # Transport size (octet string)
                len(data_payload),
            )
            + data_payload
        )

        header = struct.pack(
            ">BBHHHH",
            0x32,
            S7PDUType.USERDATA,
            0x0000,
            1,
            len(param_data),
            len(data_section),
        )

        return header + param_data + data_section

    def test_userdata_too_short(self) -> None:
        pdu = struct.pack(">BBHH", 0x32, S7PDUType.USERDATA, 0, 1)
        with pytest.raises(S7ProtocolError, match="too short"):
            self.proto.parse_response(pdu)

    def test_userdata_response(self) -> None:
        pdu = self._build_userdata_response(data_payload=b"\x01\x02\x03\x04")
        resp = self.proto.parse_response(pdu)
        assert resp["parameters"]["group"] == S7UserDataGroup.SZL
        assert resp["data"]["data"] == b"\x01\x02\x03\x04"

    def test_userdata_with_error(self) -> None:
        pdu = self._build_userdata_response(error_code=0x8104)
        resp = self.proto.parse_response(pdu)
        assert resp["parameters"]["error_code"] == 0x8104

    def test_userdata_more_data_available(self) -> None:
        pdu = self._build_userdata_response(last_data_unit=0x01, sequence_number=0x05)
        resp = self.proto.parse_response(pdu)
        assert resp["parameters"]["last_data_unit"] == 0x01
        assert resp["parameters"]["sequence_number"] == 0x05


class TestParseStartUploadResponse:
    def setup_method(self) -> None:
        self.proto = S7Protocol()

    def test_valid_response(self) -> None:
        # Layout: func(1) + status(1) + reserved(1) + reserved(1) + upload_id(4) = 8 bytes
        # Parser reads upload_id from raw_params[4:8]
        raw_params = struct.pack(">BBBBI", S7Function.START_UPLOAD, 0x00, 0x00, 0x00, 0x12345678)
        # Add block length: len_field(1) + length_str
        # Condition: len(raw_params) > 9 + len_field, so we need total > 9 + len(length_str)
        length_str = b"000100"
        raw_params += struct.pack(">B", len(length_str)) + length_str + b"\x00"  # extra byte to satisfy >
        response = {"raw_parameters": raw_params}
        result = self.proto.parse_start_upload_response(response)
        assert result["upload_id"] == 0x12345678
        assert result["block_length"] == 100

    def test_short_response(self) -> None:
        response = {"raw_parameters": b"\x00\x00\x00"}
        result = self.proto.parse_start_upload_response(response)
        assert result["upload_id"] == 0
        assert result["block_length"] == 0

    def test_no_raw_parameters(self) -> None:
        response: dict[str, Any] = {}
        result = self.proto.parse_start_upload_response(response)
        assert result["upload_id"] == 0

    def test_invalid_length_string(self) -> None:
        raw_params = struct.pack(">BBBI", 0x1D, 0, 0, 1)
        raw_params += struct.pack(">B", 3) + b"abc"
        response = {"raw_parameters": raw_params}
        result = self.proto.parse_start_upload_response(response)
        assert result["block_length"] == 0  # ValueError caught


class TestParseUploadResponse:
    def setup_method(self) -> None:
        self.proto = S7Protocol()

    def test_valid_response(self) -> None:
        response = {"data": {"data": b"\x01\x02\x03\x04\x05"}}
        result = self.proto.parse_upload_response(response)
        assert result == b"\x01\x02\x03\x04\x05"

    def test_short_data(self) -> None:
        response = {"data": {"data": b"\x01\x02"}}
        result = self.proto.parse_upload_response(response)
        assert result == b""

    def test_empty_response(self) -> None:
        response = {"data": {"data": b""}}
        result = self.proto.parse_upload_response(response)
        assert result == b""

    def test_no_data_key(self) -> None:
        response: dict[str, Any] = {}
        result = self.proto.parse_upload_response(response)
        assert result == b""


class TestParseListBlocksResponse:
    def setup_method(self) -> None:
        self.proto = S7Protocol()

    def test_valid_response(self) -> None:
        # Build entries: indicator(0x30) + type + count(2 bytes)
        data = b""
        data += struct.pack(">BBH", 0x30, 0x38, 5)  # OB: 5
        data += struct.pack(">BBH", 0x30, 0x41, 3)  # DB: 3
        data += struct.pack(">BBH", 0x30, 0x43, 7)  # FC: 7
        response = {"data": {"data": data}}
        result = self.proto.parse_list_blocks_response(response)
        assert result["OBCount"] == 5
        assert result["DBCount"] == 3
        assert result["FCCount"] == 7
        assert result["FBCount"] == 0

    def test_empty_data(self) -> None:
        response = {"data": {"data": b""}}
        result = self.proto.parse_list_blocks_response(response)
        assert result["DBCount"] == 0

    def test_no_data(self) -> None:
        response: dict[str, Any] = {}
        result = self.proto.parse_list_blocks_response(response)
        assert all(v == 0 for v in result.values())

    def test_unknown_block_type_ignored(self) -> None:
        data = struct.pack(">BBH", 0x30, 0xFF, 99)  # unknown type
        response = {"data": {"data": data}}
        result = self.proto.parse_list_blocks_response(response)
        assert all(v == 0 for v in result.values())


class TestParseListBlocksOfTypeResponse:
    def setup_method(self) -> None:
        self.proto = S7Protocol()

    def test_valid_response(self) -> None:
        # Each entry: block_num(2) + unknown(1) + lang(1)
        data = struct.pack(">HBB", 1, 0, 0) + struct.pack(">HBB", 5, 0, 0) + struct.pack(">HBB", 100, 0, 0)
        response = {"data": {"data": data}}
        result = self.proto.parse_list_blocks_of_type_response(response)
        assert result == [1, 5, 100]

    def test_empty_data(self) -> None:
        response = {"data": {"data": b""}}
        result = self.proto.parse_list_blocks_of_type_response(response)
        assert result == []

    def test_no_data(self) -> None:
        response: dict[str, Any] = {}
        result = self.proto.parse_list_blocks_of_type_response(response)
        assert result == []


class TestParseGetBlockInfoResponse:
    def setup_method(self) -> None:
        self.proto = S7Protocol()

    def test_short_data(self) -> None:
        response = {"data": {"data": b"\x00" * 10}}
        result = self.proto.parse_get_block_info_response(response)
        assert result["block_type"] == 0
        assert result["mc7_size"] == 0

    def test_valid_data(self) -> None:
        raw_data = bytearray(80)
        raw_data[1] = 0x41  # block_type = DB
        raw_data[9] = 0x01  # flags
        raw_data[10] = 0x05  # lang
        struct.pack_into(">H", raw_data, 12, 42)  # block_number
        struct.pack_into(">I", raw_data, 14, 1024)  # load_size
        struct.pack_into(">H", raw_data, 34, 100)  # sbb_length
        struct.pack_into(">H", raw_data, 38, 50)  # local_data
        struct.pack_into(">H", raw_data, 40, 200)  # mc7_size
        raw_data[66] = 0x03  # version
        struct.pack_into(">H", raw_data, 68, 0xABCD)  # checksum

        response = {"data": {"data": bytes(raw_data)}}
        result = self.proto.parse_get_block_info_response(response)
        assert result["block_type"] == 0x41
        assert result["block_number"] == 42
        assert result["mc7_size"] == 200
        assert result["load_size"] == 1024
        assert result["checksum"] == 0xABCD
        assert result["version"] == 0x03

    def test_no_data(self) -> None:
        response: dict[str, Any] = {}
        result = self.proto.parse_get_block_info_response(response)
        assert result["block_type"] == 0


class TestParseReadSZLResponse:
    def setup_method(self) -> None:
        self.proto = S7Protocol()

    def test_first_fragment(self) -> None:
        raw_data = struct.pack(">HH", 0x0011, 0x0000) + b"\x01\x02\x03"
        response = {"data": {"data": raw_data}}
        result = self.proto.parse_read_szl_response(response, first_fragment=True)
        assert result["szl_id"] == 0x0011
        assert result["szl_index"] == 0x0000
        assert result["data"] == b"\x01\x02\x03"

    def test_first_fragment_short_data(self) -> None:
        response = {"data": {"data": b"\x00\x01"}}
        result = self.proto.parse_read_szl_response(response, first_fragment=True)
        assert result["szl_id"] == 0
        assert result["data"] == b""

    def test_followup_fragment(self) -> None:
        response = {"data": {"data": b"\xaa\xbb\xcc"}}
        result = self.proto.parse_read_szl_response(response, first_fragment=False)
        assert result["data"] == b"\xaa\xbb\xcc"
        assert result["szl_id"] == 0

    def test_empty_data(self) -> None:
        response: dict[str, Any] = {}
        result = self.proto.parse_read_szl_response(response)
        assert result["data"] == b""


class TestParseGetClockResponse:
    def setup_method(self) -> None:
        self.proto = S7Protocol()

    def test_valid_bcd_time(self) -> None:
        # BCD: reserved, year=24, month=03, day=15, hour=10, minute=30, second=45, dow=6(Saturday)
        raw_data = struct.pack(">BBBBBBBB", 0x00, 0x24, 0x03, 0x15, 0x10, 0x30, 0x45, 0x06)
        response = {"data": {"data": raw_data}}
        result = self.proto.parse_get_clock_response(response)
        assert result.year == 2024
        assert result.month == 3
        assert result.day == 15
        assert result.hour == 10
        assert result.minute == 30
        assert result.second == 45

    def test_year_90_is_1990(self) -> None:
        raw_data = struct.pack(">BBBBBBBB", 0x00, 0x90, 0x01, 0x01, 0x00, 0x00, 0x00, 0x01)
        response = {"data": {"data": raw_data}}
        result = self.proto.parse_get_clock_response(response)
        assert result.year == 1990

    def test_short_data_returns_now(self) -> None:
        response = {"data": {"data": b"\x00\x01"}}
        result = self.proto.parse_get_clock_response(response)
        # Should return roughly "now"
        assert isinstance(result, datetime)

    def test_invalid_bcd_date_returns_now(self) -> None:
        # Month=99 is invalid
        raw_data = struct.pack(">BBBBBBBB", 0x00, 0x24, 0x99, 0x15, 0x10, 0x30, 0x45, 0x06)
        response = {"data": {"data": raw_data}}
        result = self.proto.parse_get_clock_response(response)
        # Should fallback to now
        assert isinstance(result, datetime)


class TestParseParameterEdgeCases:
    def setup_method(self) -> None:
        self.proto = S7Protocol()

    def test_empty_parameters(self) -> None:
        result = self.proto._parse_parameters(b"")
        assert result == {}

    def test_read_response_params_too_short(self) -> None:
        with pytest.raises(S7ProtocolError, match="too short"):
            self.proto._parse_read_response_params(b"\x04")

    def test_write_response_params_too_short(self) -> None:
        with pytest.raises(S7ProtocolError, match="too short"):
            self.proto._parse_write_response_params(b"\x05")

    def test_setup_comm_params_too_short(self) -> None:
        with pytest.raises(S7ProtocolError, match="too short"):
            self.proto._parse_setup_comm_response_params(b"\xf0\x00\x00")


class TestParseDataSection:
    def setup_method(self) -> None:
        self.proto = S7Protocol()

    def test_single_byte(self) -> None:
        result = self.proto._parse_data_section(b"\xff")
        assert result["return_code"] == 0xFF

    def test_two_three_bytes_raw(self) -> None:
        result = self.proto._parse_data_section(b"\xaa\xbb")
        assert result["raw_data"] == b"\xaa\xbb"

    def test_octet_string_transport(self) -> None:
        # Transport size 0x09 = octet string (byte length)
        data = struct.pack(">BBH", 0xFF, 0x09, 3) + b"\x01\x02\x03"
        result = self.proto._parse_data_section(data)
        assert result["data"] == b"\x01\x02\x03"

    def test_byte_transport_bit_length(self) -> None:
        # Transport size 0x04 = byte (bit length)
        data = struct.pack(">BBH", 0xFF, 0x04, 24) + b"\x01\x02\x03"  # 24 bits = 3 bytes
        result = self.proto._parse_data_section(data)
        assert result["data"] == b"\x01\x02\x03"


class TestExtractReadData:
    def setup_method(self) -> None:
        self.proto = S7Protocol()

    def test_no_data_in_response(self) -> None:
        with pytest.raises(S7ProtocolError, match="No data"):
            self.proto.extract_read_data({}, None, 0)  # type: ignore[arg-type]

    def test_non_success_return_code(self) -> None:
        response = {"data": {"return_code": 0x05, "data": b""}}
        with pytest.raises(S7ProtocolError, match="Read operation failed"):
            self.proto.extract_read_data(response, None, 0)  # type: ignore[arg-type]

    def test_success(self) -> None:
        from snap7.datatypes import S7WordLen

        response = {"data": {"return_code": 0xFF, "data": b"\x01\x02\x03"}}
        result = self.proto.extract_read_data(response, S7WordLen.BYTE, 3)
        assert result == [1, 2, 3]


class TestCheckWriteResponse:
    def setup_method(self) -> None:
        self.proto = S7Protocol()

    def test_header_error(self) -> None:
        with pytest.raises(S7ProtocolError, match="Write operation failed"):
            self.proto.check_write_response({"error_code": 0x8104})

    def test_data_section_error(self) -> None:
        with pytest.raises(S7ProtocolError, match="Write operation failed"):
            self.proto.check_write_response({"error_code": 0, "data": {"return_code": 0x05}})

    def test_success_with_data(self) -> None:
        # Should not raise
        self.proto.check_write_response({"error_code": 0, "data": {"return_code": 0xFF}})

    def test_success_without_data(self) -> None:
        # ACK without data section — should not raise
        self.proto.check_write_response({"error_code": 0})


class TestValidatePDUReference:
    def setup_method(self) -> None:
        self.proto = S7Protocol()
        self.proto.sequence = 5

    def test_matching(self) -> None:
        # Should not raise
        self.proto.validate_pdu_reference(5)

    def test_stale(self) -> None:
        from snap7.error import S7StalePacketError

        with pytest.raises(S7StalePacketError):
            self.proto.validate_pdu_reference(3)

    def test_lost(self) -> None:
        from snap7.error import S7PacketLostError

        with pytest.raises(S7PacketLostError):
            self.proto.validate_pdu_reference(7)
