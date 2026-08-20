"""Tests for S7CommPlus alarm subscriptions, browsing, and notifications."""

import struct
from unittest.mock import AsyncMock, MagicMock

import pytest

from s7commplus import Alarm, AlarmNotification, AlarmText, LanguageId
from s7commplus.alarm import (
    build_alarm_explore_request,
    build_alarm_subscription_request,
    build_delete_alarm_subscription_request,
    parse_alarm_explore_response,
    parse_alarm_notification,
)
from s7commplus.async_client import S7CommPlusAsyncClient
from s7commplus.client import S7CommPlusClient
from s7commplus.protocol import DataType, ElementID, FunctionCode, Ids, Opcode, ProtocolVersion
from s7commplus.vlq import encode_uint32_vlq, encode_uint64_vlq


def _attribute(attribute_id: int, datatype: int, value: bytes, flags: int = 0) -> bytes:
    return bytes([ElementID.ATTRIBUTE]) + encode_uint32_vlq(attribute_id) + bytes([flags, datatype]) + value


def _alarm_object() -> bytes:
    result = bytearray([ElementID.START_OF_OBJECT])
    result += struct.pack(">I", 0x8A7E0001)
    result += encode_uint32_vlq(Ids.ALARM_DAI_CLASS_RID)
    result += encode_uint32_vlq(0) + encode_uint32_vlq(0)
    result += _attribute(Ids.ALARM_DAI_CPU_ALARM_ID, DataType.LWORD, struct.pack(">Q", 0x8A7E0001002A0000))
    result += _attribute(Ids.ALARM_DAI_ALL_STATES_INFO, DataType.USINT, b"\x03")
    result += _attribute(Ids.ALARM_DAI_DOMAIN, DataType.UINT, struct.pack(">H", 256))
    result += _attribute(Ids.ALARM_DAI_MESSAGE_TYPE, DataType.DINT, encode_uint32_vlq(1))
    result += _attribute(Ids.ALARM_DAI_SEQUENCE_COUNTER, DataType.UDINT, encode_uint32_vlq(17))
    result += _attribute(Ids.OBJECT_VARIABLE_TYPE_NAME, DataType.WSTRING, encode_uint32_vlq(6) + b"Motor1")
    result += _attribute(Ids.ALARM_DAI_HMI_INFO, DataType.BLOB, b"\x00\x03hmi")

    coming = bytearray(struct.pack(">I", Ids.ALARM_DAI_COMING))
    coming += encode_uint32_vlq(3475) + bytes([0, DataType.TIMESTAMP]) + struct.pack(">Q", 123456789)
    coming += b"\x00"
    result += _attribute(Ids.ALARM_DAI_COMING, DataType.STRUCT, bytes(coming))

    texts = bytearray()
    for language_id, text_id, text in ((1031, 1, "Info"), (1031, 2, "Alarm"), (1033, 2, "Alert")):
        raw = text.encode()
        texts += encode_uint32_vlq((language_id << 16) | text_id)
        texts += encode_uint32_vlq(0) + encode_uint32_vlq(len(raw)) + raw
    texts += b"\x00"
    result += _attribute(Ids.ALARM_DAI_TEXTS, DataType.BLOB, bytes(texts), flags=0x40)
    result += bytes([ElementID.TERMINATING_OBJECT])
    return bytes(result)


def _explore_response() -> bytes:
    return encode_uint64_vlq(0) + struct.pack(">I", Ids.NATIVE_THE_ALARM_SUBSYSTEM_RID) + encode_uint32_vlq(4) + _alarm_object()


def _notification_frame() -> bytes:
    body = bytearray([Opcode.NOTIFICATION])
    body += struct.pack(">IHHH", 0x11223344, 0, 0, 0)
    body += b"\x05" + encode_uint32_vlq(12) + b"\x01"
    body += b"\x00"  # end of data-change values
    body += struct.pack(">IH", 0x11223344, 0) + b"\x81" + _alarm_object()
    return struct.pack(">BBH", 0x72, ProtocolVersion.V2, len(body)) + body + struct.pack(">BBH", 0x72, ProtocolVersion.V2, 0)


def test_alarm_models_are_public() -> None:
    assert Alarm.__module__ == "s7commplus.alarm"
    assert AlarmNotification.__module__ == "s7commplus.alarm"
    assert AlarmText.__module__ == "s7commplus.alarm"
    assert LanguageId.ENGLISH_UNITED_STATES == 1033


def test_alarm_subscription_matches_real_plc_reference_trace() -> None:
    payload = build_alarm_subscription_request(0x70000CB8)
    captured = bytes.fromhex(
        "70000cb80004000000000002a17fffc00187690000a38169001517"
        "537562736372697074696f6e5f32313437343637323635a3883a000202"
        "a3876a00030000a3876b000900a38810000202a38811000101a388182004"
        "0388808480000000a38819000400a3881a000400a3881b000200a3881c000200"
        "a3881d0007000aa3881e0003ffffa15101000194660000a38169001512"
        "5337704472697665725f416c61726d696e67a3876d000203a3946310030a"
        "0000000000000000000000000000000000000000a3bc33200301ffff"
        "a3bf75200400a3bf6d000101a4946400000008a2a200000000"
    )
    # The write IntegrityId 2 is inserted by _send_request at offset 11.
    assert payload == captured[:11] + captured[12:]


def test_alarm_delete_matches_real_plc_reference_trace() -> None:
    payload = build_delete_alarm_subscription_request(0x70000CB8, ProtocolVersion.V2)
    wire_payload = payload[:-4] + b"\x03" + payload[-4:]
    assert wire_payload == bytes.fromhex("70000cb800000004e88969001200000000896a001300896b000400000300000000")


def test_build_alarm_subscription_request_contains_filters() -> None:
    payload = build_alarm_subscription_request(0x12345678, [1031, 1033], [256, 257])
    assert payload.startswith(struct.pack(">I", 0x12345678))
    assert encode_uint32_vlq(Ids.ALARM_SUBSCRIPTION_REF_CLASS_RID) in payload
    assert encode_uint32_vlq(1031) in payload
    assert struct.pack(">H", 257) in payload
    assert payload.endswith(bytes([ElementID.TERMINATING_OBJECT, ElementID.TERMINATING_OBJECT]) + b"\x00\x00\x00\x00")


@pytest.mark.parametrize("credit_limit", [-2, 256])
def test_build_alarm_subscription_rejects_invalid_credit(credit_limit: int) -> None:
    with pytest.raises(ValueError, match="credit_limit"):
        build_alarm_subscription_request(1, credit_limit=credit_limit)


def test_build_alarm_explore_request_targets_alarm_subsystem() -> None:
    payload = build_alarm_explore_request()
    assert payload.startswith(struct.pack(">I", Ids.NATIVE_THE_ALARM_SUBSYSTEM_RID))
    assert encode_uint32_vlq(Ids.ALARM_SUBSYSTEM_UPDATE_RELEVANT_DAI) in payload
    assert encode_uint32_vlq(Ids.ALARM_DAI_TEXTS) in payload


def test_parse_alarm_explore_response_with_language_filter() -> None:
    alarms = parse_alarm_explore_response(_explore_response(), [1031])
    assert len(alarms) == 1
    alarm = alarms[0]
    assert alarm.cpu_alarm_id == 0x8A7E0001002A0000
    assert alarm.name == "Motor1"
    assert alarm.state == "coming"
    assert alarm.timestamp == 123456789
    assert alarm.hmi_info == b"hmi"
    assert alarm.texts == {1031: AlarmText(1031, "Info", "Alarm", ("",) * 9)}


def test_parse_alarm_notification() -> None:
    notification = parse_alarm_notification(_notification_frame())
    assert notification.subscription_id == 0x11223344
    assert notification.credit_tick == 5
    assert notification.sequence_number == 12
    assert len(notification.alarms) == 1
    assert notification.alarms[0].texts[1033].alarm_text == "Alert"


def test_sync_alarm_client_apis() -> None:
    client = S7CommPlusClient()
    connection = MagicMock()
    connection.session_id = 0x1234
    connection.subscription_container_id = 0x1235
    connection.protocol_version = ProtocolVersion.V2
    connection.send_request.side_effect = [
        encode_uint64_vlq(0) + b"\x01" + encode_uint32_vlq(0x55667788),
        _explore_response(),
        b"\x00",
    ]
    connection.receive_notification.return_value = _notification_frame()
    client._connection = connection

    assert client.create_alarm_subscription([1031]) == 0x55667788
    create_call = connection.send_request.call_args_list[0]
    assert create_call.kwargs["integrity_tail"] == len(create_call.args[1]) - 11
    assert create_call.args[1].startswith(struct.pack(">I", 0x1235))
    assert client.browse_alarms([1031])[0].texts[1031].alarm_text == "Alarm"
    assert client.receive_alarm_notification().alarms[0].cpu_alarm_id == 0x8A7E0001002A0000
    client.delete_alarm_subscription(0x55667788)
    delete_call = connection.send_request.call_args_list[-1]
    assert delete_call.args[0] == FunctionCode.DELETE_OBJECT
    assert delete_call.args[1].startswith(struct.pack(">I", 0x1235))


@pytest.mark.asyncio
async def test_async_alarm_client_apis() -> None:
    client = S7CommPlusAsyncClient()
    client._connected = True
    client._session_id = 0x1234
    client._subscription_container_id = 0x1235
    client._protocol_version = ProtocolVersion.V2
    client._send_request = AsyncMock(
        side_effect=[
            encode_uint64_vlq(0) + b"\x01" + encode_uint32_vlq(0x55667788),
            _explore_response(),
            b"\x00",
        ]
    )
    client._recv_cotp_dt = AsyncMock(return_value=_notification_frame())

    assert await client.create_alarm_subscription([1031]) == 0x55667788
    assert (await client.browse_alarms([1031]))[0].name == "Motor1"
    assert (await client.receive_alarm_notification(timeout=1)).credit_tick == 5
    await client.delete_alarm_subscription(0x55667788)


@pytest.mark.parametrize(
    "method,args",
    [
        ("create_alarm_subscription", ()),
        ("browse_alarms", ()),
        ("receive_alarm_notification", ()),
        ("delete_alarm_subscription", (1,)),
    ],
)
def test_sync_alarm_methods_require_connection(method: str, args: tuple[object, ...]) -> None:
    client = S7CommPlusClient()
    with pytest.raises(RuntimeError, match="Not connected"):
        getattr(client, method)(*args)
