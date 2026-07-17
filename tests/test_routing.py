"""Tests for S7 routing support (multi-subnet PLC access)."""

import struct

import pytest

from snap7.connection import ISOTCPConnection
from snap7.client import Client

# Use a unique port to avoid conflicts with other test suites
ROUTING_TEST_PORT = 11102


@pytest.mark.routing
class TestRoutingTSAP:
    """Test TSAP construction for routed connections."""

    def test_remote_tsap_encodes_rack_slot(self) -> None:
        """Remote TSAP should encode rack and slot per S7 spec."""
        rack, slot = 0, 2
        expected = 0x0100 | (rack << 5) | slot  # 0x0102
        conn = ISOTCPConnection("127.0.0.1", remote_tsap=expected)
        assert conn.remote_tsap == 0x0102

    def test_routing_tsap_encodes_dest_rack_slot(self) -> None:
        """Routing TSAP should encode destination rack/slot."""
        conn = ISOTCPConnection("127.0.0.1")
        conn.set_routing(subnet_id=0x0001, dest_rack=0, dest_slot=3)
        assert conn._routing_tsap == 0x0100 | (0 << 5) | 3  # 0x0103

    def test_routing_tsap_higher_rack(self) -> None:
        """Routing TSAP with rack=2, slot=1."""
        conn = ISOTCPConnection("127.0.0.1")
        conn.set_routing(subnet_id=0x0002, dest_rack=2, dest_slot=1)
        assert conn._routing_tsap == 0x0100 | (2 << 5) | 1  # 0x0141


@pytest.mark.routing
class TestCOTPCRRouting:
    """Test COTP Connection Request PDU generation with routing."""

    def _parse_cotp_cr(self, pdu: bytes) -> dict[str, object]:
        """Parse a COTP CR PDU into its components for inspection."""
        result: dict[str, object] = {}
        pdu_len = pdu[0]
        result["pdu_len"] = pdu_len
        result["pdu_type"] = pdu[1]
        result["dst_ref"] = struct.unpack(">H", pdu[2:4])[0]
        result["src_ref"] = struct.unpack(">H", pdu[4:6])[0]
        result["class_opt"] = pdu[6]

        # Parse variable-part parameters
        params: dict[int, bytes] = {}
        offset = 7
        while offset < len(pdu):
            if offset + 2 > len(pdu):
                break
            code = pdu[offset]
            length = pdu[offset + 1]
            data = pdu[offset + 2 : offset + 2 + length]
            params[code] = data
            offset += 2 + length

        result["params"] = params
        return result

    def test_standard_cr_has_no_routing_params(self) -> None:
        """A non-routed CR should not contain routing parameters."""
        conn = ISOTCPConnection("127.0.0.1")
        pdu = conn._build_cotp_cr()
        parsed = self._parse_cotp_cr(pdu)
        params = parsed["params"]
        assert isinstance(params, dict)
        assert ISOTCPConnection.COTP_PARAM_SUBNET_ID not in params
        assert ISOTCPConnection.COTP_PARAM_ROUTING_TSAP not in params

    def test_routed_cr_contains_subnet_param(self) -> None:
        """A routed CR must include the subnet ID parameter (0xC6)."""
        conn = ISOTCPConnection("127.0.0.1")
        conn.set_routing(subnet_id=0x0001, dest_rack=0, dest_slot=2)
        pdu = conn._build_cotp_cr()
        parsed = self._parse_cotp_cr(pdu)
        params = parsed["params"]
        assert isinstance(params, dict)
        assert ISOTCPConnection.COTP_PARAM_SUBNET_ID in params
        subnet_data = params[ISOTCPConnection.COTP_PARAM_SUBNET_ID]
        assert struct.unpack(">H", subnet_data)[0] == 0x0001

    def test_routed_cr_contains_routing_tsap(self) -> None:
        """A routed CR must include the routing TSAP parameter (0xC7)."""
        conn = ISOTCPConnection("127.0.0.1")
        conn.set_routing(subnet_id=0x0001, dest_rack=0, dest_slot=2)
        pdu = conn._build_cotp_cr()
        parsed = self._parse_cotp_cr(pdu)
        params = parsed["params"]
        assert isinstance(params, dict)
        assert ISOTCPConnection.COTP_PARAM_ROUTING_TSAP in params
        tsap_data = params[ISOTCPConnection.COTP_PARAM_ROUTING_TSAP]
        expected_tsap = 0x0100 | (0 << 5) | 2
        assert struct.unpack(">H", tsap_data)[0] == expected_tsap

    def test_routed_cr_pdu_length_is_consistent(self) -> None:
        """The PDU length byte must equal len(pdu) - 1."""
        conn = ISOTCPConnection("127.0.0.1")
        conn.set_routing(subnet_id=0x00FF, dest_rack=1, dest_slot=1)
        pdu = conn._build_cotp_cr()
        # The first byte is the length of the rest of the PDU
        assert pdu[0] == len(pdu) - 1

    def test_standard_cr_pdu_length_is_consistent(self) -> None:
        """Non-routed PDU length byte must also be consistent."""
        conn = ISOTCPConnection("127.0.0.1")
        pdu = conn._build_cotp_cr()
        assert pdu[0] == len(pdu) - 1

    def test_routed_cr_still_has_standard_params(self) -> None:
        """Routing should not remove the standard TSAP / PDU size params."""
        conn = ISOTCPConnection("127.0.0.1")
        conn.set_routing(subnet_id=0x0001, dest_rack=0, dest_slot=3)
        pdu = conn._build_cotp_cr()
        parsed = self._parse_cotp_cr(pdu)
        params = parsed["params"]
        assert isinstance(params, dict)
        assert ISOTCPConnection.COTP_PARAM_CALLING_TSAP in params
        assert ISOTCPConnection.COTP_PARAM_CALLED_TSAP in params
        assert ISOTCPConnection.COTP_PARAM_PDU_SIZE in params


@pytest.mark.routing
class TestRoutedFrameValidity:
    """Test that routed connections produce valid protocol frames."""

    def test_routed_cr_wrapped_in_tpkt(self) -> None:
        """A routed CR wrapped in TPKT should have correct TPKT header."""
        conn = ISOTCPConnection("127.0.0.1")
        conn.set_routing(subnet_id=0x0005, dest_rack=0, dest_slot=1)
        cr_pdu = conn._build_cotp_cr()
        tpkt = conn._build_tpkt(cr_pdu)

        # TPKT header: version=3, reserved=0, length=total
        assert tpkt[0] == 3
        assert tpkt[1] == 0
        total_len = struct.unpack(">H", tpkt[2:4])[0]
        assert total_len == len(tpkt)
        assert tpkt[4:] == cr_pdu

    def test_subnet_id_truncated_to_16_bits(self) -> None:
        """Subnet IDs larger than 16 bits should be masked."""
        conn = ISOTCPConnection("127.0.0.1")
        conn.set_routing(subnet_id=0x1FFFF, dest_rack=0, dest_slot=1)
        # 0x1FFFF & 0xFFFF == 0xFFFF
        assert conn._subnet_id == 0xFFFF


@pytest.mark.routing
@pytest.mark.server
class TestClientConnectRouted:
    """Test Client.connect_routed against the built-in server."""

    def test_connect_routed_to_server(self) -> None:
        """Client.connect_routed should negotiate PDU with a local server.

        The server does not validate routing parameters in the COTP CR,
        so the connection handshake should succeed.
        """
        from snap7.server import Server
        from snap7.type import SrvArea
        from ctypes import c_char

        server = Server()
        size = 100
        db_data = bytearray(size)
        db_array = (c_char * size).from_buffer(db_data)
        server.register_area(SrvArea.DB, 1, db_array)
        server.start(tcp_port=ROUTING_TEST_PORT)

        try:
            client = Client()
            client.connect_routed(
                host="127.0.0.1",
                router_rack=0,
                router_slot=2,
                subnet=0x0001,
                dest_rack=0,
                dest_slot=3,
                port=ROUTING_TEST_PORT,
            )
            assert client.get_connected()

            # Verify we can do a basic read through the routed connection
            data = client.db_read(1, 0, 10)
            assert len(data) == 10

            client.disconnect()
        finally:
            server.stop()

    def test_connect_routed_returns_self(self) -> None:
        """connect_routed should return self for method chaining."""
        from snap7.server import Server
        from snap7.type import SrvArea
        from ctypes import c_char

        server = Server()
        size = 10
        db_data = bytearray(size)
        db_array = (c_char * size).from_buffer(db_data)
        server.register_area(SrvArea.DB, 1, db_array)
        server.start(tcp_port=ROUTING_TEST_PORT + 1)

        try:
            client = Client()
            result = client.connect_routed(
                host="127.0.0.1",
                router_rack=0,
                router_slot=2,
                subnet=0x0002,
                dest_rack=0,
                dest_slot=1,
                port=ROUTING_TEST_PORT + 1,
            )
            assert result is client
            client.disconnect()
        finally:
            server.stop()
