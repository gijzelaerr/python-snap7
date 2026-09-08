"""Tests for S7CommPlus symbolic data subscriptions."""

import struct
from unittest.mock import MagicMock

import pytest

from s7commplus.client import S7CommPlusClient
from s7commplus.codec import encode_header, encode_pvalue_blob
from s7commplus.connection import S7CommPlusConnection
from s7commplus.protocol import DataType, FunctionCode, Ids, Opcode, ProtocolVersion
from s7commplus.subscription import (
    SubscriptionItem,
    build_delete_subscription_request,
    build_subscription_request,
    parse_subscription_notification,
)
from s7commplus.vlq import encode_uint32_vlq, encode_uint64_vlq


def _response_frame(function_code: int, sequence: int, payload: bytes) -> bytes:
    response = struct.pack(">BHHHHB", Opcode.RESPONSE, 0, function_code, 0, sequence, 0x34) + payload
    return encode_header(ProtocolVersion.V2, len(response)) + response + b"\x72\x02\x00\x00"


def _notification_frame(*, version: int = ProtocolVersion.V2, with_hmac: bool = False) -> bytes:
    data = bytearray([Opcode.NOTIFICATION])
    data += struct.pack(">IHHH", 0x70400025, 4, 0, 0)
    data += b"\x03" + encode_uint32_vlq(9) + b"\x01"
    data += b"\x92" + struct.pack(">I", 7) + encode_pvalue_blob(b"\x12\x34")
    data += b"\x9b" + encode_uint32_vlq(8) + bytes([0, DataType.USINT, 0x2A])
    data += b"\x13" + struct.pack(">I", 9)
    data += b"\x00\xaa"
    framed_data = (b"\x20" + bytes(32) if with_hmac else b"") + data
    return encode_header(version, len(framed_data)) + framed_data + bytes([0x72, version, 0, 0])


class TestSubscriptionItem:
    def test_from_db_access_sequence(self) -> None:
        item = SubscriptionItem.from_access_sequence("8A0E0007.A.2")

        assert item.access_area == Ids.DB_ACCESS_AREA_BASE + 7
        assert item.lids == (0xA, 0x2)
        assert item.resolved_sub_area == Ids.DB_VALUE_ACTUAL

    def test_from_native_area_access_sequence(self) -> None:
        item = SubscriptionItem.from_access_sequence("52.9")
        assert item.resolved_sub_area == Ids.CONTROLLER_AREA_VALUE_ACTUAL

    @pytest.mark.parametrize("value", ["", "8A0E0007", "8A0E0007.not-hex", ".A"])
    def test_rejects_invalid_access_sequence(self, value: str) -> None:
        with pytest.raises(ValueError):
            SubscriptionItem.from_access_sequence(value)


class TestSubscriptionRequest:
    def test_matches_real_plc_reference_trace(self) -> None:
        item = SubscriptionItem.from_access_sequence("8A0E0027.25.1A")
        payload, integrity_tail = build_subscription_request(
            0x70000CB8,
            [item],
            cycle_ms=100,
            relation_id=0x7FFFC001,
        )

        # Before TLS encryption, captured from the working C# reference driver.
        # The request's IntegrityId 2 appears at offset 11 and is inserted later
        # by send_request(), so remove it when comparing the builder output.
        captured = bytes.fromhex(
            "70000cb80004000000000002a17fffc00187690000a38169001517"
            "537562736372697074696f6e5f32313437343637323635a3883a000200"
            "a3876a00030000a3876b000900a38810000214a38811000101a388182004"
            "0b888084800000018880908003010088d0b88027009376251aa38819000464"
            "a3881b000200a3881c000200a3881d0007000aa3881e0003ffffa3881f000200"
            "a200000000"
        )
        assert payload == captured[:11] + captured[12:]
        assert integrity_tail == len(payload) - 11

    def test_uses_subscription_container_and_symbolic_reference_list(self) -> None:
        item = SubscriptionItem.from_access_sequence("8A0E0007.A.2", symbol_crc=0x1234, reference_id=7)
        payload, integrity_tail = build_subscription_request(0x3C2, [item], cycle_ms=250)

        assert payload.startswith(struct.pack(">I", 0x3C2) + bytes([0, DataType.UDINT, 0]) + struct.pack(">I", 0))
        assert integrity_tail == len(payload) - 11
        expected_reference = b"".join(
            encode_uint32_vlq(value)
            for value in (
                0x80010000,
                0,
                1,
                0x80040003,
                7,
                0,
                Ids.DB_ACCESS_AREA_BASE + 7,
                0x1234,
                Ids.DB_VALUE_ACTUAL,
                0xA,
                2,
            )
        )
        assert bytes([0x20, DataType.UDINT]) + encode_uint32_vlq(11) + expected_reference in payload

    def test_requires_items(self) -> None:
        with pytest.raises(ValueError, match="at least one"):
            build_subscription_request(0x3C2, [])

    def test_delete_request_contains_object_qualifier(self) -> None:
        payload = build_delete_subscription_request(0x70400025, ProtocolVersion.V2)
        assert payload.startswith(struct.pack(">I", 0x70400025) + b"\x00")
        assert payload.endswith(struct.pack(">I", 0))
        assert len(payload) > 9

    def test_delete_request_matches_real_plc_reference_trace(self) -> None:
        payload = build_delete_subscription_request(0x70000CB8, ProtocolVersion.V2)
        wire_payload = payload[:-4] + b"\x03" + payload[-4:]
        assert wire_payload == bytes.fromhex("70000cb800000004e88969001200000000896a001300896b000400000300000000")


class TestSubscriptionNotification:
    @pytest.mark.parametrize(
        ("version", "with_hmac"),
        [(ProtocolVersion.V2, False), (ProtocolVersion.V3, True)],
    )
    def test_parses_values_errors_and_metadata(self, version: int, with_hmac: bool) -> None:
        notification = parse_subscription_notification(_notification_frame(version=version, with_hmac=with_hmac))

        assert notification.subscription_id == 0x70400025
        assert notification.credit_tick == 3
        assert notification.sequence_number == 9
        assert notification.change_counter == 1
        assert notification.values == {7: b"\x12\x34", 8: b"\x2a"}
        assert notification.errors == {9: 0x13}
        assert notification.trailing_data == b"\xaa"

    def test_rejects_response_frame(self) -> None:
        with pytest.raises(ValueError, match="notification"):
            parse_subscription_notification(_response_frame(FunctionCode.GET_VARIABLE, 1, b"\x00"))

    def test_parses_tia_portal_watch_notification_from_issue_710(self) -> None:
        frame = bytes.fromhex(
            "7203006520db9b8947109b14bc56e8bd25032cda2dd3a9488cbd1807017a69f90af8982371"
            "337040002504000000000000050192000000070014001801000006278ab08c18c456364dfc0d"
            "d0800000000f000000920000000800020092000000090001000000000000"
        )

        notification = parse_subscription_notification(frame)

        assert notification.subscription_id == 0x70400025
        assert notification.sequence_number == 5
        assert notification.values[7] == bytes.fromhex("01000006278ab08c18c456364dfc0dd0800000000f000000")
        assert notification.values[8] == b"\x00"
        assert notification.values[9] == b"\x00"


class TestSubscriptionClient:
    def test_create_receive_and_delete(self) -> None:
        connection = MagicMock()
        connection.subscription_container_id = 0x3C2
        connection.protocol_version = ProtocolVersion.V2
        create_response = encode_uint64_vlq(0) + b"\x01" + encode_uint32_vlq(0x70400025)
        connection.send_request.return_value = create_response
        connection.receive_notification.return_value = _notification_frame()

        client = S7CommPlusClient()
        client._connection = connection
        subscription_id = client.create_subscription(["8A0E0007.A"], cycle_ms=100)

        assert subscription_id == 0x70400025
        create_call = connection.send_request.call_args_list[0]
        assert create_call.args[0] == FunctionCode.CREATE_OBJECT
        assert create_call.kwargs["integrity_tail"] > 4
        assert client.receive_subscription_notification().values[7] == b"\x12\x34"

        client.delete_subscription(subscription_id)
        delete_call = connection.send_request.call_args_list[1]
        assert delete_call.args[0] == FunctionCode.DELETE_OBJECT
        assert delete_call.args[1].startswith(struct.pack(">I", connection.subscription_container_id))


class TestNotificationQueue:
    def test_send_request_queues_interleaved_notification(self) -> None:
        connection = S7CommPlusConnection("127.0.0.1")
        connection._connected = True
        connection._protocol_version = ProtocolVersion.V2
        connection._session_id = 1
        notification = _notification_frame()
        response = _response_frame(FunctionCode.GET_VARIABLE, 0, b"\x00")
        connection._send_s7_data = MagicMock()
        connection._recv_s7_data = MagicMock(side_effect=[notification, response])

        assert connection.send_request(FunctionCode.GET_VARIABLE, b"\x00\x00\x00\x00") == b"\x00"
        assert connection.receive_notification() == notification
        assert connection._recv_s7_data.call_count == 2
