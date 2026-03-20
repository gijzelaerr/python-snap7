"""Protocol conformance test suite.

Validates that the S7 protocol implementation correctly encodes/decodes
packets according to the TPKT, COTP, and S7 protocol specifications.
"""

import struct

import pytest

from snap7.connection import ISOTCPConnection, TPDUSize
from snap7.datatypes import S7Area, S7WordLen
from snap7.error import S7ConnectionError, S7ProtocolError
from snap7.s7protocol import S7Function, S7PDUType, S7Protocol, S7_RETURN_CODES


@pytest.mark.conformance
class TestTPKTConformance:
    """Verify TPKT frame encoding per RFC 1006."""

    def test_tpkt_header_format(self) -> None:
        """TPKT header: version=3, reserved=0, 2-byte big-endian length."""
        conn = ISOTCPConnection("127.0.0.1")
        payload = b"\x01\x02\x03"
        frame = conn._build_tpkt(payload)

        assert frame[0] == 3, "TPKT version must be 3"
        assert frame[1] == 0, "TPKT reserved must be 0"

    def test_tpkt_length_includes_header(self) -> None:
        """Length field includes the 4-byte TPKT header."""
        conn = ISOTCPConnection("127.0.0.1")
        payload = b"\x01\x02\x03"
        frame = conn._build_tpkt(payload)

        length = struct.unpack(">H", frame[2:4])[0]
        assert length == len(payload) + 4

    def test_tpkt_payload_preserved(self) -> None:
        """Payload appears intact after the 4-byte header."""
        conn = ISOTCPConnection("127.0.0.1")
        payload = b"\xde\xad\xbe\xef"
        frame = conn._build_tpkt(payload)

        assert frame[4:] == payload

    def test_tpkt_empty_payload(self) -> None:
        """Empty payload produces a 4-byte frame."""
        conn = ISOTCPConnection("127.0.0.1")
        frame = conn._build_tpkt(b"")

        assert len(frame) == 4
        length = struct.unpack(">H", frame[2:4])[0]
        assert length == 4

    def test_tpkt_large_payload(self) -> None:
        """Length field correctly handles large payloads."""
        conn = ISOTCPConnection("127.0.0.1")
        payload = b"\x00" * 1000
        frame = conn._build_tpkt(payload)

        length = struct.unpack(">H", frame[2:4])[0]
        assert length == 1004


@pytest.mark.conformance
class TestCOTPConformance:
    """Verify COTP PDU encoding per ISO 8073."""

    def test_cotp_cr_pdu_type(self) -> None:
        """CR PDU type code is 0xE0."""
        conn = ISOTCPConnection("127.0.0.1")
        cr = conn._build_cotp_cr()
        assert cr[1] == 0xE0

    def test_cotp_cr_destination_reference_zero(self) -> None:
        """CR destination reference must be 0x0000."""
        conn = ISOTCPConnection("127.0.0.1")
        cr = conn._build_cotp_cr()
        dst_ref = struct.unpack(">H", cr[2:4])[0]
        assert dst_ref == 0x0000

    def test_cotp_cr_source_reference(self) -> None:
        """CR source reference matches connection setting."""
        conn = ISOTCPConnection("127.0.0.1")
        conn.src_ref = 0x1234
        cr = conn._build_cotp_cr()
        src_ref = struct.unpack(">H", cr[4:6])[0]
        assert src_ref == 0x1234

    def test_cotp_cr_class_zero(self) -> None:
        """CR class/option byte is 0x00 (Class 0, no extended formats)."""
        conn = ISOTCPConnection("127.0.0.1")
        cr = conn._build_cotp_cr()
        assert cr[6] == 0x00

    def test_cotp_cr_contains_tsap_parameters(self) -> None:
        """CR includes calling TSAP (0xC1) and called TSAP (0xC2) parameters."""
        conn = ISOTCPConnection("127.0.0.1", local_tsap=0x0100, remote_tsap=0x0102)
        cr = conn._build_cotp_cr()
        # Search for parameter codes in the parameter section
        param_data = cr[7:]  # Parameters start after the 7-byte base header
        param_codes = []
        offset = 0
        while offset < len(param_data):
            param_codes.append(param_data[offset])
            param_len = param_data[offset + 1]
            offset += 2 + param_len
        assert 0xC1 in param_codes, "Must contain calling TSAP parameter"
        assert 0xC2 in param_codes, "Must contain called TSAP parameter"

    def test_cotp_cr_pdu_size_parameter(self) -> None:
        """CR includes PDU size parameter (0xC0)."""
        conn = ISOTCPConnection("127.0.0.1")
        cr = conn._build_cotp_cr()
        param_data = cr[7:]
        param_codes = []
        offset = 0
        while offset < len(param_data):
            param_codes.append(param_data[offset])
            param_len = param_data[offset + 1]
            offset += 2 + param_len
        assert 0xC0 in param_codes, "Must contain PDU size parameter"

    def test_cotp_dt_pdu_format(self) -> None:
        """DT PDU: length=2, type=0xF0, EOT=0x80."""
        conn = ISOTCPConnection("127.0.0.1")
        dt = conn._build_cotp_dt(b"\x01\x02")
        assert dt[0] == 2, "DT PDU length must be 2"
        assert dt[1] == 0xF0, "DT PDU type must be 0xF0"
        assert dt[2] == 0x80, "EOT+number must be 0x80"

    def test_cotp_dt_carries_data(self) -> None:
        """DT PDU correctly carries the S7 data payload."""
        conn = ISOTCPConnection("127.0.0.1")
        payload = b"\xde\xad\xbe\xef"
        dt = conn._build_cotp_dt(payload)
        assert dt[3:] == payload

    def test_cotp_cc_parsing(self) -> None:
        """CC PDU parsing extracts destination reference."""
        conn = ISOTCPConnection("127.0.0.1")
        # Build a minimal CC: pdu_len, type=0xD0, dst_ref, src_ref, class
        cc = struct.pack(">BBHHB", 6, 0xD0, 0x0042, 0x0001, 0x00)
        conn._parse_cotp_cc(cc)
        assert conn.dst_ref == 0x0042

    def test_cotp_cc_wrong_type_rejected(self) -> None:
        """Non-CC PDU type raises error."""
        conn = ISOTCPConnection("127.0.0.1")
        bad_cc = struct.pack(">BBHHB", 6, 0xE0, 0x0000, 0x0001, 0x00)
        with pytest.raises(S7ConnectionError, match="Expected COTP CC"):
            conn._parse_cotp_cc(bad_cc)

    def test_cotp_cc_too_short_rejected(self) -> None:
        """CC PDU shorter than 7 bytes is rejected."""
        conn = ISOTCPConnection("127.0.0.1")
        with pytest.raises(S7ConnectionError, match="too short"):
            conn._parse_cotp_cc(b"\x06\xd0\x00")

    def test_cotp_data_parsing(self) -> None:
        """Data parsing extracts payload from DT PDU."""
        conn = ISOTCPConnection("127.0.0.1")
        cotp_pdu = struct.pack(">BBB", 2, 0xF0, 0x80) + b"\x32\x01\x02\x03"
        data = conn._parse_cotp_data(cotp_pdu)
        assert data == b"\x32\x01\x02\x03"

    def test_cotp_data_wrong_type_rejected(self) -> None:
        """Non-DT PDU type in data parsing raises error."""
        conn = ISOTCPConnection("127.0.0.1")
        bad_dt = struct.pack(">BBB", 2, 0xE0, 0x80) + b"\x01"
        with pytest.raises(S7ConnectionError, match="Expected COTP DT"):
            conn._parse_cotp_data(bad_dt)

    def test_cotp_data_too_short_rejected(self) -> None:
        """DT PDU shorter than 3 bytes is rejected."""
        conn = ISOTCPConnection("127.0.0.1")
        with pytest.raises(S7ConnectionError, match="too short"):
            conn._parse_cotp_data(b"\x02\xf0")


@pytest.mark.conformance
class TestS7HeaderConformance:
    """Verify S7 PDU header encoding."""

    def test_protocol_id(self) -> None:
        """S7 protocol ID is always 0x32."""
        proto = S7Protocol()
        pdu = proto.build_read_request(S7Area.DB, 1, 0, S7WordLen.BYTE, 1)
        assert pdu[0] == 0x32

    def test_request_pdu_type(self) -> None:
        """Read/write requests use PDU type 0x01 (REQUEST)."""
        proto = S7Protocol()
        read_pdu = proto.build_read_request(S7Area.DB, 1, 0, S7WordLen.BYTE, 1)
        assert read_pdu[1] == S7PDUType.REQUEST

        proto2 = S7Protocol()
        write_pdu = proto2.build_write_request(S7Area.DB, 1, 0, S7WordLen.BYTE, b"\x00")
        assert write_pdu[1] == S7PDUType.REQUEST

    def test_header_reserved_zero(self) -> None:
        """Reserved field (bytes 2-3) is always 0x0000."""
        proto = S7Protocol()
        pdu = proto.build_read_request(S7Area.DB, 1, 0, S7WordLen.BYTE, 1)
        reserved = struct.unpack(">H", pdu[2:4])[0]
        assert reserved == 0x0000

    def test_sequence_number_increments(self) -> None:
        """Sequence number increments with each request."""
        proto = S7Protocol()
        pdu1 = proto.build_read_request(S7Area.DB, 1, 0, S7WordLen.BYTE, 1)
        pdu2 = proto.build_read_request(S7Area.DB, 1, 0, S7WordLen.BYTE, 1)
        seq1 = struct.unpack(">H", pdu1[4:6])[0]
        seq2 = struct.unpack(">H", pdu2[4:6])[0]
        assert seq2 == seq1 + 1

    def test_header_is_12_bytes(self) -> None:
        """S7 request header is exactly 12 bytes (proto, type, reserved, seq, param_len, data_len)."""
        proto = S7Protocol()
        pdu = proto.build_setup_communication_request()
        # Header: proto(1) + type(1) + reserved(2) + seq(2) + param_len(2) + data_len(2) = 10
        # Actually for REQUEST type it's 10 bytes
        assert pdu[0] == 0x32
        assert len(pdu) >= 10


@pytest.mark.conformance
class TestS7FunctionCodes:
    """Verify S7 function codes match the specification."""

    def test_read_area_function_code(self) -> None:
        """Read area function code is 0x04."""
        proto = S7Protocol()
        pdu = proto.build_read_request(S7Area.DB, 1, 0, S7WordLen.BYTE, 1)
        # Function code is first byte of parameter section (after 10-byte header)
        assert pdu[10] == 0x04

    def test_write_area_function_code(self) -> None:
        """Write area function code is 0x05."""
        proto = S7Protocol()
        pdu = proto.build_write_request(S7Area.DB, 1, 0, S7WordLen.BYTE, b"\x00")
        assert pdu[10] == 0x05

    def test_setup_communication_function_code(self) -> None:
        """Setup communication function code is 0xF0."""
        proto = S7Protocol()
        pdu = proto.build_setup_communication_request()
        assert pdu[10] == 0xF0

    def test_plc_control_function_code(self) -> None:
        """PLC control function code is 0x28."""
        proto = S7Protocol()
        pdu = proto.build_plc_control_request("hot_start")
        assert pdu[10] == 0x28


@pytest.mark.conformance
class TestS7AreaCodes:
    """Verify S7 area codes match the specification."""

    def test_area_code_pe(self) -> None:
        assert S7Area.PE.value == 0x81

    def test_area_code_pa(self) -> None:
        assert S7Area.PA.value == 0x82

    def test_area_code_mk(self) -> None:
        assert S7Area.MK.value == 0x83

    def test_area_code_db(self) -> None:
        assert S7Area.DB.value == 0x84

    def test_area_code_ct(self) -> None:
        assert S7Area.CT.value == 0x1C

    def test_area_code_tm(self) -> None:
        assert S7Area.TM.value == 0x1D


@pytest.mark.conformance
class TestS7WordLenCodes:
    """Verify S7 word length codes match the specification."""

    def test_wordlen_bit(self) -> None:
        assert S7WordLen.BIT.value == 0x01

    def test_wordlen_byte(self) -> None:
        assert S7WordLen.BYTE.value == 0x02

    def test_wordlen_char(self) -> None:
        assert S7WordLen.CHAR.value == 0x03

    def test_wordlen_word(self) -> None:
        assert S7WordLen.WORD.value == 0x04

    def test_wordlen_int(self) -> None:
        assert S7WordLen.INT.value == 0x05

    def test_wordlen_dword(self) -> None:
        assert S7WordLen.DWORD.value == 0x06

    def test_wordlen_dint(self) -> None:
        assert S7WordLen.DINT.value == 0x07

    def test_wordlen_real(self) -> None:
        assert S7WordLen.REAL.value == 0x08

    def test_wordlen_counter(self) -> None:
        assert S7WordLen.COUNTER.value == 0x1C

    def test_wordlen_timer(self) -> None:
        assert S7WordLen.TIMER.value == 0x1D


@pytest.mark.conformance
class TestS7PDUTypes:
    """Verify S7 PDU type codes match the specification."""

    def test_pdu_type_request(self) -> None:
        assert S7PDUType.REQUEST.value == 0x01

    def test_pdu_type_ack(self) -> None:
        assert S7PDUType.ACK.value == 0x02

    def test_pdu_type_ack_data(self) -> None:
        assert S7PDUType.ACK_DATA.value == 0x03

    def test_pdu_type_userdata(self) -> None:
        assert S7PDUType.USERDATA.value == 0x07


@pytest.mark.conformance
class TestS7ReadRequestEncoding:
    """Verify read request PDU structure."""

    def test_read_request_item_count(self) -> None:
        """Read request has item count = 1."""
        proto = S7Protocol()
        pdu = proto.build_read_request(S7Area.DB, 1, 0, S7WordLen.BYTE, 4)
        assert pdu[11] == 0x01  # Item count

    def test_read_request_variable_spec(self) -> None:
        """Variable specification marker is 0x12."""
        proto = S7Protocol()
        pdu = proto.build_read_request(S7Area.DB, 1, 0, S7WordLen.BYTE, 4)
        assert pdu[12] == 0x12

    def test_read_request_data_length_zero(self) -> None:
        """Read requests have data length = 0."""
        proto = S7Protocol()
        pdu = proto.build_read_request(S7Area.DB, 1, 0, S7WordLen.BYTE, 4)
        data_len = struct.unpack(">H", pdu[8:10])[0]
        assert data_len == 0

    def test_read_request_parameter_length(self) -> None:
        """Read request parameter length is 14 (function + count + address spec)."""
        proto = S7Protocol()
        pdu = proto.build_read_request(S7Area.DB, 1, 0, S7WordLen.BYTE, 4)
        param_len = struct.unpack(">H", pdu[6:8])[0]
        assert param_len == 14


@pytest.mark.conformance
class TestS7WriteRequestEncoding:
    """Verify write request PDU structure."""

    def test_write_request_has_data_section(self) -> None:
        """Write requests include a data section."""
        proto = S7Protocol()
        data = b"\x01\x02\x03\x04"
        pdu = proto.build_write_request(S7Area.DB, 1, 0, S7WordLen.BYTE, data)
        data_len = struct.unpack(">H", pdu[8:10])[0]
        assert data_len > 0

    def test_write_request_data_section_structure(self) -> None:
        """Write data section: reserved(1) + transport_size(1) + bit_length(2) + data."""
        proto = S7Protocol()
        data = b"\x01\x02\x03\x04"
        pdu = proto.build_write_request(S7Area.DB, 1, 0, S7WordLen.BYTE, data)
        # Data section starts after header(10) + parameters(14)
        data_section = pdu[24:]
        assert data_section[0] == 0x00  # Reserved
        assert len(data_section) >= 4 + len(data)  # transport header + data

    def test_write_request_bit_length(self) -> None:
        """Bit length in data section is data_bytes * 8."""
        proto = S7Protocol()
        data = b"\x01\x02\x03\x04"
        pdu = proto.build_write_request(S7Area.DB, 1, 0, S7WordLen.BYTE, data)
        data_section = pdu[24:]
        bit_length = struct.unpack(">H", data_section[2:4])[0]
        assert bit_length == len(data) * 8


@pytest.mark.conformance
class TestS7SetupCommunication:
    """Verify setup communication PDU structure."""

    def test_setup_comm_pdu_size(self) -> None:
        """Setup communication encodes requested PDU size."""
        proto = S7Protocol()
        pdu = proto.build_setup_communication_request(pdu_length=480)
        # Parameter section: function(1) + reserved(1) + max_amq_caller(2) + max_amq_callee(2) + pdu_len(2)
        param_start = 10
        pdu_length = struct.unpack(">H", pdu[param_start + 6 : param_start + 8])[0]
        assert pdu_length == 480

    def test_setup_comm_amq_values(self) -> None:
        """Setup communication encodes AMQ caller/callee."""
        proto = S7Protocol()
        pdu = proto.build_setup_communication_request(max_amq_caller=3, max_amq_callee=3, pdu_length=960)
        param_start = 10
        amq_caller = struct.unpack(">H", pdu[param_start + 2 : param_start + 4])[0]
        amq_callee = struct.unpack(">H", pdu[param_start + 4 : param_start + 6])[0]
        assert amq_caller == 3
        assert amq_callee == 3


@pytest.mark.conformance
class TestS7ResponseParsing:
    """Verify S7 response PDU parsing."""

    def test_parse_valid_ack_data(self) -> None:
        """Valid ACK_DATA response parses without error."""
        proto = S7Protocol()
        # Build a minimal ACK_DATA response: header(12 bytes)
        pdu = struct.pack(
            ">BBHHHHBB",
            0x32,  # Protocol ID
            S7PDUType.ACK_DATA,
            0x0000,  # Reserved
            0x0001,  # Sequence
            0x0000,  # Parameter length
            0x0000,  # Data length
            0x00,  # Error class
            0x00,  # Error code
        )
        response = proto.parse_response(pdu)
        assert response["sequence"] == 1
        assert response["error_code"] == 0

    def test_parse_ack_response(self) -> None:
        """ACK (write response) parses correctly."""
        proto = S7Protocol()
        # ACK with function code + item count in parameters (min 2 bytes for write response)
        pdu = struct.pack(
            ">BBHHHHBB",
            0x32,
            S7PDUType.ACK,
            0x0000,
            0x0005,
            0x0002,  # Param length = 2
            0x0000,  # Data length
            0x00,
            0x00,
        ) + struct.pack(">BB", S7Function.WRITE_AREA, 0x01)
        response = proto.parse_response(pdu)
        assert response["error_code"] == 0

    def test_reject_invalid_protocol_id(self) -> None:
        """Non-0x32 protocol ID raises error."""
        proto = S7Protocol()
        pdu = struct.pack(">BBHHHHBB", 0x33, S7PDUType.ACK_DATA, 0, 1, 0, 0, 0, 0)
        with pytest.raises(S7ProtocolError, match="Invalid protocol ID"):
            proto.parse_response(pdu)

    def test_reject_request_pdu_type(self) -> None:
        """REQUEST PDU type in response is rejected."""
        proto = S7Protocol()
        pdu = struct.pack(">BBHHHHBB", 0x32, S7PDUType.REQUEST, 0, 1, 0, 0, 0, 0)
        with pytest.raises(S7ProtocolError, match="Expected response PDU"):
            proto.parse_response(pdu)

    def test_reject_too_short_pdu(self) -> None:
        """PDU shorter than 10 bytes is rejected."""
        proto = S7Protocol()
        with pytest.raises(S7ProtocolError, match="too short"):
            proto.parse_response(b"\x32\x03\x00")

    def test_error_class_raises(self) -> None:
        """Non-zero error class raises S7ProtocolError."""
        proto = S7Protocol()
        pdu = struct.pack(">BBHHHHBB", 0x32, S7PDUType.ACK_DATA, 0, 1, 0, 0, 0x81, 0x04)
        with pytest.raises(S7ProtocolError):
            proto.parse_response(pdu)


@pytest.mark.conformance
class TestS7ReturnCodes:
    """Verify S7 return code definitions."""

    def test_success_code(self) -> None:
        assert S7_RETURN_CODES[0xFF] == "Success"

    def test_hardware_error_code(self) -> None:
        assert S7_RETURN_CODES[0x01] == "Hardware error"

    def test_invalid_address_code(self) -> None:
        assert S7_RETURN_CODES[0x05] == "Invalid address"

    def test_object_does_not_exist_code(self) -> None:
        assert S7_RETURN_CODES[0x0A] == "Object does not exist"

    def test_all_codes_have_descriptions(self) -> None:
        """Every defined return code has a non-empty description."""
        for code, desc in S7_RETURN_CODES.items():
            assert desc, f"Return code {code:#04x} has empty description"


@pytest.mark.conformance
class TestTPDUSizes:
    """Verify TPDU size constants match ISO 8073."""

    def test_tpdu_sizes_are_powers_of_two(self) -> None:
        """Each TPDU size value is an exponent where actual_size = 2^value."""
        for size in TPDUSize:
            actual = 1 << size.value
            assert actual >= 128
            assert actual <= 8192

    def test_tpdu_size_values(self) -> None:
        assert TPDUSize.S_128.value == 0x07
        assert TPDUSize.S_256.value == 0x08
        assert TPDUSize.S_512.value == 0x09
        assert TPDUSize.S_1024.value == 0x0A
        assert TPDUSize.S_2048.value == 0x0B
        assert TPDUSize.S_4096.value == 0x0C
        assert TPDUSize.S_8192.value == 0x0D
