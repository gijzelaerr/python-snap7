"""Tests for multi-packet USERDATA response support.

Tests USERDATA response parameter parsing, follow-up request building,
fragment-aware SZL parsing, and multi-packet accumulation in client methods.
"""

import struct
from typing import Any, Dict

import pytest

from snap7.s7protocol import S7Protocol, S7UserDataGroup, S7UserDataSubfunction


@pytest.mark.client
class TestUserdataResponseParamParsing:
    """Test _parse_userdata_response_params via _parse_parameters."""

    def setup_method(self) -> None:
        self.protocol = S7Protocol()

    def test_last_packet(self) -> None:
        """Parse USERDATA response params indicating last data unit."""
        # 12-byte param section: last_data_unit=0x00 (done)
        param_data = bytes(
            [
                0x00,  # Reserved
                0x01,  # Param count
                0x12,  # Type header
                0x08,  # Length
                0x12,  # Method (response)
                0x84,  # Type(8) | Group(4=SZL)
                0x01,  # Subfunction (READ_SZL)
                0x01,  # Sequence number
                0x00,  # Data unit reference
                0x00,  # Last data unit (done)
                0x00,
                0x00,  # Error code
            ]
        )
        result = self.protocol._parse_parameters(param_data)

        assert result["group"] == S7UserDataGroup.SZL
        assert result["subfunction"] == S7UserDataSubfunction.READ_SZL
        assert result["sequence_number"] == 0x01
        assert result["last_data_unit"] == 0x00
        assert result["error_code"] == 0x0000

    def test_more_data(self) -> None:
        """Parse USERDATA response params indicating more data coming."""
        # last_data_unit=0x01 means more data
        param_data = bytes(
            [
                0x00,
                0x01,
                0x12,
                0x08,
                0x12,
                0x84,  # Group 4 = SZL
                0x01,  # Subfunction
                0x02,  # Sequence number
                0xD5,  # Data unit reference
                0x01,  # Last data unit (MORE)
                0x00,
                0x00,
            ]
        )
        result = self.protocol._parse_parameters(param_data)

        assert result["group"] == S7UserDataGroup.SZL
        assert result["sequence_number"] == 0x02
        assert result["last_data_unit"] == 0x01

    def test_block_info_group(self) -> None:
        """Parse USERDATA response with block info group."""
        param_data = bytes(
            [
                0x00,
                0x01,
                0x12,
                0x08,
                0x12,
                0x83,  # Type(8) | Group(3=BlockInfo)
                0x02,  # Subfunction (LIST_BLOCKS_OF_TYPE)
                0x03,  # Sequence number
                0x00,  # Data unit ref
                0x01,  # More data
                0x00,
                0x00,
            ]
        )
        result = self.protocol._parse_parameters(param_data)

        assert result["group"] == S7UserDataGroup.BLOCK_INFO
        assert result["subfunction"] == S7UserDataSubfunction.LIST_BLOCKS_OF_TYPE
        assert result["sequence_number"] == 0x03
        assert result["last_data_unit"] == 0x01

    def test_non_userdata_still_works(self) -> None:
        """Non-USERDATA params still dispatch to existing parsers."""
        # READ_AREA response
        param_data = bytes([0x04, 0x01])
        result = self.protocol._parse_parameters(param_data)
        assert result["function_code"] == 0x04
        assert result["item_count"] == 1


@pytest.mark.client
class TestFollowupRequestBuilder:
    """Test build_userdata_followup_request byte format."""

    def setup_method(self) -> None:
        self.protocol = S7Protocol()

    def test_szl_followup(self) -> None:
        """Follow-up request for SZL has correct structure."""
        pdu = self.protocol.build_userdata_followup_request(
            group=S7UserDataGroup.SZL,
            subfunction=S7UserDataSubfunction.READ_SZL,
            sequence_number=0x02,
        )

        # S7 header: 10 bytes for USERDATA
        assert pdu[0] == 0x32  # Protocol ID
        assert pdu[1] == 0x07  # USERDATA

        # Extract param_len and data_len from header
        param_len = struct.unpack(">H", pdu[6:8])[0]
        data_len = struct.unpack(">H", pdu[8:10])[0]
        assert param_len == 8
        assert data_len == 4

        # Parameter section starts at offset 10
        params = pdu[10 : 10 + param_len]
        assert params[0] == 0x00  # Reserved
        assert params[1] == 0x01  # Param count
        assert params[2] == 0x12  # Type header
        assert params[3] == 0x04  # Length
        assert params[4] == 0x11  # Method (request)
        assert params[5] == 0x44  # Type(4) | Group(4=SZL)
        assert params[6] == 0x01  # Subfunction
        assert params[7] == 0x02  # DataRef = sequence_number

        # Data section
        data = pdu[10 + param_len :]
        assert data == bytes([0x0A, 0x00, 0x00, 0x00])

    def test_block_info_followup(self) -> None:
        """Follow-up request for block info group."""
        pdu = self.protocol.build_userdata_followup_request(
            group=S7UserDataGroup.BLOCK_INFO,
            subfunction=S7UserDataSubfunction.LIST_BLOCKS_OF_TYPE,
            sequence_number=0x05,
        )

        params = pdu[10:18]
        assert params[5] == 0x43  # Type(4) | Group(3=BlockInfo)
        assert params[6] == 0x02  # LIST_BLOCKS_OF_TYPE
        assert params[7] == 0x05  # DataRef


@pytest.mark.client
class TestSzlFragmentParsing:
    """Test parse_read_szl_response with first_fragment flag."""

    def setup_method(self) -> None:
        self.protocol = S7Protocol()

    def test_first_fragment_parses_header(self) -> None:
        """First fragment extracts SZL ID and Index from data."""
        response: Dict[str, Any] = {
            "data": {
                "data": b"\x00\x1c\x00\x00" + b"\xaa\xbb\xcc",
            }
        }
        result = self.protocol.parse_read_szl_response(response, first_fragment=True)
        assert result["szl_id"] == 0x001C
        assert result["szl_index"] == 0x0000
        assert result["data"] == b"\xaa\xbb\xcc"

    def test_followup_fragment_raw_data(self) -> None:
        """Follow-up fragment returns all data as raw payload."""
        payload = b"\xdd\xee\xff\x01\x02\x03"
        response: Dict[str, Any] = {
            "data": {
                "data": payload,
            }
        }
        result = self.protocol.parse_read_szl_response(response, first_fragment=False)
        assert result["szl_id"] == 0
        assert result["szl_index"] == 0
        assert result["data"] == payload

    def test_default_is_first_fragment(self) -> None:
        """Default behavior (no flag) treats as first fragment."""
        response: Dict[str, Any] = {
            "data": {
                "data": b"\x00\x11\x00\x22" + b"\x33",
            }
        }
        result = self.protocol.parse_read_szl_response(response)
        assert result["szl_id"] == 0x0011
        assert result["szl_index"] == 0x0022
        assert result["data"] == b"\x33"


@pytest.mark.client
class TestMultiPacketSzlIntegration:
    """Integration test: mock connection returning 2-packet SZL response.

    Uses real packet data from nikteliy's pcap captures.
    """

    def _build_full_pdu(self, param_bytes: bytes, data_bytes: bytes) -> bytes:
        """Helper to build a complete S7 USERDATA PDU."""
        header = struct.pack(
            ">BBHHHH",
            0x32,  # Protocol ID
            0x07,  # USERDATA
            0x0000,  # Reserved
            0x0001,  # Sequence
            len(param_bytes),
            len(data_bytes),
        )
        return header + param_bytes + data_bytes

    def test_two_packet_szl_response(self) -> None:
        """Simulate a 2-packet SZL response using nikteliy's test data."""
        # First response: last_data_unit=0x01 (more data), seq=0x02
        # Real packet data from pcap
        response1 = (
            b"\x32\x07\x00\x00\x02\x00\x00\x0c\x00\xda"
            b"\x00\x01\x12\x08\x12\x84\x01\x02\xd5\x01\x00\x00"
            b"\xff\x09\x00\xd6"
            b"\x00\x1c\x00\x00"
            b"\x00\x22\x00\x0a"
            b"\x00\x01"
            b"\x53\x37\x33\x30\x30\x2f\x45\x54\x32\x30\x30\x4d"
            b"\x20\x73\x74\x61\x74\x69\x6f\x6e\x5f\x31\x00\x00\x00\x00\x00\x00"
            b"\x00\x00\x00\x00"
            b"\x00\x02"
            b"\x50\x4c\x43\x5f\x31\x00\x00\x00\x00\x00"
            b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
            b"\x00\x00\x00\x00"
            b"\x00\x00\x00\x03"
            b"\x00\x00\x00\x00\x00\x00\x00\x00"
            b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
            b"\x00\x00\x00\x00\x00\x00\x00\x00"
            b"\x00\x04"
            b"\x4f\x72\x69\x67\x69\x6e\x61\x6c"
            b"\x20\x53\x69\x65\x6d\x65\x6e\x73\x20\x45\x71\x75\x69\x70"
            b"\x6d\x65\x6e\x74\x00\x00\x00\x00\x00\x00"
            b"\x00\x05"
            b"\x53\x20\x43\x2d\x42\x31\x55\x33\x39\x33\x31\x34\x32\x30\x31\x31"
            b"\x00\x00\x00\x00"
            b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
            b"\x00\x07"
            b"\x43\x50\x55\x20\x33\x31\x35\x2d\x32\x20\x50\x4e\x2f\x44\x50"
            b"\x00\x00\x00"
            b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08"
        )

        # Second response: last_data_unit=0x00 (done), seq=0x02
        response2 = (
            b"\x32\x07\x00\x00\x03\x00\x00\x0c\x00\x8a"
            b"\x00\x01\x12\x08\x12\x84\x01\x02\xd5\x00\x00\x00"
            b"\xff\x09\x00\x86"
            b"\x4d\x4d\x43\x20\x34\x41\x31\x41\x43\x30\x31\x39"
            b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
            b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
            b"\x00\x09"
            b"\x00\x2a\xf6\x00"
            b"\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
            b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
            b"\x00\x0a"
            b"\x00\x00"
            b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
            b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
            b"\x00\x0b"
            b"\x00\x00"
            b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
            b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        )

        protocol = S7Protocol()

        # Parse first response
        parsed1 = protocol.parse_response(response1)
        params1 = parsed1["parameters"]
        assert params1["last_data_unit"] == 0x01  # More data
        assert params1["sequence_number"] == 0x02

        # Parse SZL header from first fragment
        szl1 = protocol.parse_read_szl_response(parsed1, first_fragment=True)
        assert szl1["szl_id"] == 0x001C
        first_data = szl1["data"]

        # Parse second response
        parsed2 = protocol.parse_response(response2)
        params2 = parsed2["parameters"]
        assert params2["last_data_unit"] == 0x00  # Done

        # Parse follow-up fragment (no SZL header)
        szl2 = protocol.parse_read_szl_response(parsed2, first_fragment=False)
        second_data = szl2["data"]

        # Combined data should be larger than either fragment alone
        combined = first_data + second_data
        assert len(combined) > len(first_data)
        assert len(combined) > len(second_data)
        assert len(combined) == len(first_data) + len(second_data)

    def test_single_packet_no_loop(self) -> None:
        """Single-packet response (last_data_unit=0x00) skips follow-up."""
        protocol = S7Protocol()

        # Build a single-packet SZL response with last_data_unit=0x00
        param_bytes = bytes(
            [
                0x00,
                0x01,
                0x12,
                0x08,
                0x12,
                0x84,
                0x01,
                0x01,
                0x00,
                0x00,
                0x00,
                0x00,
            ]
        )
        data_bytes = (
            b"\xff\x09\x00\x08"  # return_code, transport_size, length
            b"\x00\x1c\x00\x00"  # SZL ID=0x001C, Index=0
            b"\xaa\xbb\xcc\xdd"  # payload
        )
        pdu = self._build_full_pdu(param_bytes, data_bytes)

        parsed = protocol.parse_response(pdu)
        params = parsed["parameters"]
        assert params["last_data_unit"] == 0x00

        szl = protocol.parse_read_szl_response(parsed, first_fragment=True)
        assert szl["szl_id"] == 0x001C
        assert szl["data"] == b"\xaa\xbb\xcc\xdd"
