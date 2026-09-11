"""Tests for S7CommPlus symbolic data subscriptions."""

import asyncio
import hashlib
import hmac
import struct
from unittest.mock import AsyncMock, MagicMock

import pytest

from s7commplus.async_client import S7CommPlusAsyncClient
from s7commplus.catalog import SymbolicTag
from s7commplus.client import S7CommPlusClient
from s7commplus.codec import decode_header, encode_header, encode_pvalue_blob
from s7commplus.connection import S7CommPlusConnection
from s7commplus.protocol import DataType, FunctionCode, Ids, Opcode, ProtocolVersion
from s7commplus.subscription import (
    SubscriptionItem,
    SubscriptionRegistry,
    build_delete_subscription_request,
    build_subscription_request,
    parse_subscription_notification,
)
from s7commplus.typeinfo import Softdatatype
from s7commplus.vlq import encode_uint32_vlq, encode_uint64_vlq
from snap7.error import S7IntegrityError


def _response_frame(function_code: int, sequence: int, payload: bytes) -> bytes:
    response = struct.pack(">BHHHHB", Opcode.RESPONSE, 0, function_code, 0, sequence, 0x34) + payload
    return encode_header(ProtocolVersion.V2, len(response)) + response + b"\x72\x02\x00\x00"


def _notification_frame(
    *,
    version: int = ProtocolVersion.V2,
    with_hmac: bool = False,
    subscription_id: int = 0x70400025,
    credit_tick: int = 3,
    sequence_number: int = 9,
    change_counter: int = 1,
) -> bytes:
    data = bytearray([Opcode.NOTIFICATION])
    data += struct.pack(">IHHH", subscription_id, 4, 0, 0)
    data += bytes([credit_tick]) + encode_uint32_vlq(sequence_number) + bytes([change_counter])
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

    def test_from_catalog_tag_retains_type_metadata(self) -> None:
        tag = SymbolicTag("DB1.Count", 0x8A0E0001, (2,), Softdatatype.INT, DataType.INT, symbol_crc=7)

        item = SubscriptionItem.from_tag(tag, reference_id=4)

        assert item.tag is tag
        assert item.reference_id == 4
        assert item.symbol_crc == 7


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

    def test_catalog_tag_notification_is_decoded_and_raw_value_is_retained(self) -> None:
        connection = MagicMock(subscription_container_id=0x3C2, protocol_version=ProtocolVersion.V2)
        connection.send_request.return_value = encode_uint64_vlq(0) + b"\x01" + encode_uint32_vlq(0x70400025)
        connection.receive_notification.return_value = _notification_frame()
        tag = SymbolicTag("DB1.Count", 0x8A0E0001, (2,), Softdatatype.INT, DataType.INT)
        client = S7CommPlusClient()
        client._connection = connection
        subscription_id = client.create_subscription([SubscriptionItem.from_tag(tag, reference_id=7)])

        notification = client.receive_subscription_notification(subscription_id)

        assert notification.values[7] == b"\x12\x34"
        assert notification.decoded_values[7] == 0x1234
        assert notification.tags[7] is tag

    def test_finite_credit_is_replenished_before_expiry(self) -> None:
        connection = MagicMock(subscription_container_id=0x3C2, protocol_version=ProtocolVersion.V2)
        connection.send_request.return_value = encode_uint64_vlq(0) + b"\x01" + encode_uint32_vlq(0x70400025)
        connection.receive_notification.return_value = _notification_frame(credit_tick=9)
        client = S7CommPlusClient()
        client._connection = connection
        subscription_id = client.create_subscription(["8A0E0007.A"], credit_limit=10, credit_step=5)

        client.receive_subscription_notification(subscription_id)

        connection.send_subscription_credit.assert_called_once_with(subscription_id, 15)

    def test_callback_and_bounded_iterator(self) -> None:
        connection = MagicMock(subscription_container_id=0x3C2, protocol_version=ProtocolVersion.V2)
        connection.send_request.return_value = encode_uint64_vlq(0) + b"\x01" + encode_uint32_vlq(0x70400025)
        connection.receive_notification.side_effect = [
            _notification_frame(sequence_number=1),
            _notification_frame(sequence_number=2),
        ]
        client = S7CommPlusClient()
        client._connection = connection
        subscription_id = client.create_subscription(["8A0E0007.A"])
        delivered = []
        client.add_subscription_callback(subscription_id, delivered.append)

        notifications = list(client.iter_subscription_notifications(subscription_id, limit=2))

        assert [item.sequence_number for item in notifications] == [1, 2]
        assert [item.sequence_number for item in delivered] == [1, 2]

    def test_notification_for_another_subscription_is_queued(self) -> None:
        connection = MagicMock(subscription_container_id=0x3C2, protocol_version=ProtocolVersion.V2)
        connection.send_request.side_effect = [
            encode_uint64_vlq(0) + b"\x01" + encode_uint32_vlq(0x70400025),
            encode_uint64_vlq(0) + b"\x01" + encode_uint32_vlq(0x70400026),
        ]
        connection.receive_notification.side_effect = [
            _notification_frame(subscription_id=0x70400026, change_counter=2),
            _notification_frame(subscription_id=0x70400025, change_counter=1),
        ]
        client = S7CommPlusClient()
        client._connection = connection
        first = client.create_subscription(["8A0E0007.A"])
        second = client.create_subscription(["8A0E0007.B"])

        assert client.receive_subscription_notification(first).subscription_id == first
        assert client.receive_subscription_notification(second).subscription_id == second
        assert connection.receive_notification.call_count == 2


class TestSubscriptionRegistry:
    def test_buffers_pre_registration_notification(self) -> None:
        registry = SubscriptionRegistry()
        notification = parse_subscription_notification(_notification_frame())

        assert registry.route(notification) == (False, None)
        registry.register(
            notification.subscription_id,
            [SubscriptionItem.from_access_sequence("8A0E0007.A", reference_id=7)],
            change_counter=1,
            credit_limit=-1,
            credit_step=0,
            queue_size=2,
        )

        buffered = registry.pop(notification.subscription_id)
        assert buffered is not None
        assert buffered.sequence_number == notification.sequence_number
        assert buffered.values == notification.values

    def test_queue_overflow_sequence_gap_and_stale_generation_are_diagnostic(self) -> None:
        registry = SubscriptionRegistry()
        subscription_id = 0x70400025
        registry.register(
            subscription_id,
            [SubscriptionItem.from_access_sequence("8A0E0007.A")],
            change_counter=1,
            credit_limit=-1,
            credit_step=0,
            queue_size=1,
        )

        registry.route(parse_subscription_notification(_notification_frame(sequence_number=3)))
        registry.route(parse_subscription_notification(_notification_frame(sequence_number=5)))
        matched, _ = registry.route(parse_subscription_notification(_notification_frame(change_counter=2)))

        diagnostics = registry.diagnostics(subscription_id)
        assert not matched
        assert diagnostics.queued_notifications == 1
        assert diagnostics.dropped_notifications == 2
        assert diagnostics.missed_sequence_updates == 1

    def test_deleted_id_reuse_rejects_old_change_counter(self) -> None:
        registry = SubscriptionRegistry()
        subscription_id = 0x70400025
        item = SubscriptionItem.from_access_sequence("8A0E0007.A")
        registry.register(subscription_id, [item], change_counter=1, credit_limit=-1, credit_step=0, queue_size=2)
        registry.unregister(subscription_id)
        registry.register(subscription_id, [item], change_counter=2, credit_limit=-1, credit_step=0, queue_size=2)

        assert registry.route(parse_subscription_notification(_notification_frame(change_counter=1))) == (False, None)
        assert registry.pop(subscription_id) is None


@pytest.mark.asyncio
async def test_async_create_iterate_queue_and_delete_lifecycle() -> None:
    client = S7CommPlusAsyncClient()
    client._connected = True
    client._reader = MagicMock()
    client._writer = MagicMock()
    client._subscription_container_id = 0x3C2
    client._protocol_version = ProtocolVersion.V2
    create_response = encode_uint64_vlq(0) + b"\x01" + encode_uint32_vlq(0x70400025)
    client._send_request = AsyncMock(side_effect=[create_response, b""])
    client._recv_cotp_dt = AsyncMock(return_value=_notification_frame(credit_tick=9))
    client._send_subscription_credit = AsyncMock()
    tag = SymbolicTag("DB1.Count", 0x8A0E0001, (2,), Softdatatype.INT, DataType.INT)

    subscription_id = await client.create_subscription(
        [SubscriptionItem.from_tag(tag, reference_id=7)], credit_limit=10, credit_step=5, queue_size=2
    )
    queue = client.subscription_queue(subscription_id)
    assert queue.qsize() == 0
    assert (await queue.get()).decoded_values[7] == 0x1234
    client._send_subscription_credit.assert_awaited_once_with(subscription_id, 15)
    with pytest.raises(asyncio.QueueEmpty):
        queue.get_nowait()

    client._notification_frames.append(_notification_frame(sequence_number=10))
    received = [item async for item in client.iter_subscription_notifications(subscription_id, limit=1)]
    assert received[0].sequence_number == 10
    await client.delete_subscription(subscription_id)
    with pytest.raises(KeyError, match="Unknown subscription"):
        client.subscription_diagnostics(subscription_id)


def test_credit_update_uses_fire_and_forget_transport_flags() -> None:
    connection = S7CommPlusConnection("127.0.0.1")
    connection._connected = True
    connection._protocol_version = ProtocolVersion.V2
    connection._session_id = 0x70000CB8
    connection._with_integrity_id = True
    connection._integrity_id_write = 3
    connection._send_s7_data = MagicMock()

    connection.send_subscription_credit(0x70400025, 15)

    frame = connection._send_s7_data.call_args.args[0]
    _, length, consumed = decode_header(frame)
    request = frame[consumed : consumed + length]
    assert request[13] == 0x74
    assert request[14:18] == struct.pack(">I", 0x70400025)
    assert connection.integrity_id_write == 4


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

    def test_authenticated_notification_is_verified_before_queueing(self) -> None:
        connection = S7CommPlusConnection("127.0.0.1")
        connection._connected = True
        connection._protocol_version = ProtocolVersion.V3
        connection._session_id = 1
        connection._session_key = bytes(range(24))
        connection._iso_conn.disconnect = MagicMock()

        notification = _notification_frame(version=ProtocolVersion.V3)
        _, data_length, consumed = decode_header(notification)
        data = notification[consumed : consumed + data_length]
        digest = hmac.new(connection._session_key, data, hashlib.sha256).digest()
        protected = bytearray(bytes([len(digest)]) + digest + data)
        protected[1] ^= 1
        notification = encode_header(ProtocolVersion.V3, len(protected)) + protected
        connection._send_s7_data = MagicMock()
        connection._recv_s7_data = MagicMock(return_value=bytes(notification))

        with pytest.raises(S7IntegrityError, match="integrity check failed"):
            connection.send_request(FunctionCode.GET_VARIABLE, bytes(4))
        assert not connection.connected
        assert not connection._notification_frames
