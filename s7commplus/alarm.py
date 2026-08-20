"""Alarm models and wire decoders for S7CommPlus notifications."""

from __future__ import annotations

import struct
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any

from .codec import encode_object_qualifier
from .protocol import DataType, ElementID, Ids, Opcode
from .vlq import decode_int32_vlq, decode_int64_vlq, decode_uint32_vlq, decode_uint64_vlq, encode_uint32_vlq

_ALARM_SUBSCRIPTION_RELATION_ID = 0x7FFFC001
_ALARM_REFERENCE_RELATION_ID = 0x51010001


class LanguageId(IntEnum):
    """Windows locale identifiers (LCIDs) commonly supported by Siemens HMIs."""

    CHINESE_TRADITIONAL = 1028
    CZECH = 1029
    DANISH = 1030
    GERMAN_GERMANY = 1031
    GREEK = 1032
    ENGLISH_UNITED_STATES = 1033
    SPANISH_TRADITIONAL = 1034
    FINNISH = 1035
    FRENCH_FRANCE = 1036
    HUNGARIAN = 1038
    ITALIAN_ITALY = 1040
    JAPANESE = 1041
    KOREAN = 1042
    DUTCH_NETHERLANDS = 1043
    POLISH = 1045
    PORTUGUESE_BRAZIL = 1046
    RUSSIAN = 1049
    SWEDISH = 1053
    TURKISH = 1055
    CHINESE_SIMPLIFIED = 2052
    DUTCH_BELGIUM = 2067
    PORTUGUESE_PORTUGAL = 2070


@dataclass(frozen=True)
class AlarmText:
    """The texts for one alarm in one PLC language."""

    language_id: LanguageId | int
    info_text: str = ""
    alarm_text: str = ""
    additional_texts: tuple[str, ...] = ()


@dataclass(frozen=True)
class Alarm:
    """Current state of a PLC alarm."""

    cpu_alarm_id: int
    all_states_info: int
    domain: int
    message_type: int
    sequence_counter: int
    name: str = ""
    state: str = "unknown"
    timestamp: int | None = None
    acknowledge_timestamp: int | None = None
    hmi_info: bytes = b""
    associated_values: tuple[bytes, ...] = ()
    texts: dict[int, AlarmText] = field(default_factory=dict)


@dataclass(frozen=True)
class AlarmNotification:
    """An unsolicited S7CommPlus alarm notification."""

    subscription_id: int
    credit_tick: int
    sequence_number: int
    subscription_change_counter: int
    timestamp: int | None
    alarms: tuple[Alarm, ...]


@dataclass
class _Object:
    relation_id: int
    class_id: int
    attributes: dict[int, Any] = field(default_factory=dict)
    children: list[_Object] = field(default_factory=list)


@dataclass(frozen=True)
class _Blob:
    root_id: int
    value: bytes


def _attribute(attribute_id: int, datatype: int, value: bytes, flags: int = 0) -> bytes:
    return bytes([ElementID.ATTRIBUTE]) + encode_uint32_vlq(attribute_id) + bytes([flags, datatype]) + value


def _wstring(value: str) -> bytes:
    encoded = value.encode("utf-8")
    return encode_uint32_vlq(len(encoded)) + encoded


def _udint_array(values: list[int], flags: int = 0x20) -> bytes:
    return (
        bytes([flags, DataType.UDINT]) + encode_uint32_vlq(len(values)) + b"".join(encode_uint32_vlq(value) for value in values)
    )


def _uint_array(values: list[int], flags: int = 0x10) -> bytes:
    return bytes([flags, DataType.UINT]) + encode_uint32_vlq(len(values)) + b"".join(struct.pack(">H", value) for value in values)


def build_alarm_subscription_request(
    subscription_container_id: int,
    language_ids: Sequence[LanguageId | int] | None = None,
    domains: list[int] | None = None,
    credit_limit: int = 10,
) -> bytes:
    """Build an alarm-subscription CREATE_OBJECT payload."""
    if not -1 <= credit_limit <= 255:
        raise ValueError("credit_limit must be -1 (unlimited) or between 0 and 255")
    languages = [] if language_ids is None else language_ids
    domain_filter = [0xFFFF] if domains is None else domains
    if any(not 0 <= value <= 0xFFFF for value in domain_filter):
        raise ValueError("alarm domains must be UInt16 values")
    if any(not 0 <= value <= 0xFFFFFFFF for value in languages):
        raise ValueError("language IDs must be UInt32 values")

    payload = bytearray()
    payload += struct.pack(">I", subscription_container_id)
    payload += bytes([0, DataType.UDINT]) + encode_uint32_vlq(0)
    payload += struct.pack(">I", 0)
    payload += bytes([ElementID.START_OF_OBJECT])
    payload += struct.pack(">I", _ALARM_SUBSCRIPTION_RELATION_ID)
    payload += encode_uint32_vlq(Ids.CLASS_SUBSCRIPTION)
    payload += encode_uint32_vlq(0) + encode_uint32_vlq(0)
    payload += _attribute(
        Ids.OBJECT_VARIABLE_TYPE_NAME,
        DataType.WSTRING,
        _wstring(f"Subscription_{_ALARM_SUBSCRIPTION_RELATION_ID}"),
    )
    payload += _attribute(Ids.SUBSCRIPTION_FUNCTION_CLASS_ID, DataType.USINT, b"\x02")
    payload += _attribute(Ids.SUBSCRIPTION_MISSED_SENDINGS, DataType.UINT, struct.pack(">H", 0))
    payload += _attribute(Ids.SUBSCRIPTION_SUBSYSTEM_ERROR, DataType.LINT, encode_uint32_vlq(0))
    payload += _attribute(Ids.SUBSCRIPTION_ROUTE_MODE, DataType.USINT, b"\x02")
    payload += _attribute(Ids.SUBSCRIPTION_ACTIVE, DataType.BOOL, b"\x01")
    payload += bytes([ElementID.ATTRIBUTE]) + encode_uint32_vlq(Ids.SUBSCRIPTION_REFERENCE_LIST)
    payload += _udint_array([0x80010000, 0, 0])
    payload += _attribute(Ids.SUBSCRIPTION_CYCLE_TIME, DataType.UDINT, encode_uint32_vlq(0))
    payload += _attribute(Ids.SUBSCRIPTION_DELAY_TIME, DataType.UDINT, encode_uint32_vlq(0))
    payload += _attribute(Ids.SUBSCRIPTION_DISABLED, DataType.USINT, b"\x00")
    payload += _attribute(Ids.SUBSCRIPTION_COUNT, DataType.USINT, b"\x00")
    payload += _attribute(Ids.SUBSCRIPTION_CREDIT_LIMIT, DataType.INT, struct.pack(">h", credit_limit))
    payload += _attribute(Ids.SUBSCRIPTION_TICKS, DataType.UINT, struct.pack(">H", 0xFFFF))

    payload += bytes([ElementID.START_OF_OBJECT])
    payload += struct.pack(">I", _ALARM_REFERENCE_RELATION_ID)
    payload += encode_uint32_vlq(Ids.ALARM_SUBSCRIPTION_REF_CLASS_RID)
    payload += encode_uint32_vlq(0) + encode_uint32_vlq(0)
    payload += _attribute(Ids.OBJECT_VARIABLE_TYPE_NAME, DataType.WSTRING, _wstring("S7pDriver_Alarming"))
    payload += _attribute(Ids.SUBSCRIPTION_REFERENCE_TRIGGER_MODE, DataType.USINT, b"\x03")
    payload += bytes([ElementID.ATTRIBUTE]) + encode_uint32_vlq(Ids.ALARM_SUBSCRIPTION_REF_ALARM_DOMAIN)
    payload += _uint_array([0] * 10)
    payload += bytes([ElementID.ATTRIBUTE]) + encode_uint32_vlq(Ids.ALARM_SUBSCRIPTION_REF_ALARM_DOMAIN_FILTER)
    payload += _uint_array(domain_filter, flags=0x20)
    payload += bytes([ElementID.ATTRIBUTE]) + encode_uint32_vlq(Ids.ALARM_SUBSCRIPTION_REF_TEXT_LANGUAGES)
    payload += _udint_array(languages)
    payload += _attribute(Ids.ALARM_SUBSCRIPTION_REF_SEND_TEXTS, DataType.BOOL, b"\x01")
    payload += bytes([ElementID.RELATION])
    payload += encode_uint32_vlq(Ids.ALARM_SUBSCRIPTION_REF_ITS_ALARM_SUBSYSTEM)
    payload += struct.pack(">I", Ids.NATIVE_THE_ALARM_SUBSYSTEM_RID)
    payload += bytes([ElementID.TERMINATING_OBJECT, ElementID.TERMINATING_OBJECT])
    payload += struct.pack(">I", 0)
    return bytes(payload)


def build_delete_alarm_subscription_request(subscription_container_id: int, protocol_version: int) -> bytes:
    """Build the DeleteObject payload used for an alarm subscription container."""
    return (
        struct.pack(">I", subscription_container_id)
        + b"\x00"
        + encode_object_qualifier(protocol_version=protocol_version)
        + struct.pack(">I", 0)
    )


def build_alarm_explore_request() -> bytes:
    """Build an EXPLORE request for the current alarm state."""
    attributes = [
        Ids.ALARM_DAI_CPU_ALARM_ID,
        Ids.ALARM_DAI_ALL_STATES_INFO,
        Ids.ALARM_DAI_DOMAIN,
        Ids.ALARM_DAI_COMING,
        Ids.ALARM_DAI_GOING,
        Ids.ALARM_DAI_MESSAGE_TYPE,
        Ids.ALARM_DAI_HMI_INFO,
        Ids.OBJECT_VARIABLE_TYPE_NAME,
        Ids.ALARM_DAI_SEQUENCE_COUNTER,
        Ids.ALARM_DAI_TEXTS,
    ]
    payload = bytearray(struct.pack(">I", Ids.NATIVE_THE_ALARM_SUBSYSTEM_RID))
    payload += encode_uint32_vlq(Ids.ALARM_SUBSYSTEM_UPDATE_RELEVANT_DAI)
    payload += b"\x01\x01\x00\x00"
    payload += encode_uint32_vlq(len(attributes))
    for attribute_id in attributes:
        payload += encode_uint32_vlq(attribute_id)
    payload += struct.pack(">I", 0) + b"\x00"
    return bytes(payload)


def _read_vlq32(data: bytes, offset: int) -> tuple[int, int]:
    value, consumed = decode_uint32_vlq(data, offset)
    return value, offset + consumed


def _read_vlq64(data: bytes, offset: int) -> tuple[int, int]:
    value, consumed = decode_uint64_vlq(data, offset)
    return value, offset + consumed


def _decode_blob(data: bytes, offset: int) -> tuple[_Blob, int]:
    root_id, offset = _read_vlq32(data, offset)
    if root_id > 1:
        if offset + 9 > len(data):
            raise ValueError("Truncated typed alarm blob")
        offset += 8
        blob_type = data[offset]
        offset += 1
        if blob_type not in (2, 3):
            raise ValueError(f"Unsupported alarm blob type: {blob_type}")
    size, offset = _read_vlq32(data, offset)
    end = offset + size
    if end > len(data):
        raise ValueError("Truncated alarm blob")
    return _Blob(root_id, bytes(data[offset:end])), end


def _decode_scalar(data: bytes, offset: int, datatype: int) -> tuple[Any, int]:
    if datatype == DataType.NULL:
        return None, offset
    if datatype == DataType.BOOL:
        return bool(data[offset]), offset + 1
    if datatype in (DataType.USINT, DataType.BYTE):
        return data[offset], offset + 1
    if datatype == DataType.SINT:
        return struct.unpack_from(">b", data, offset)[0], offset + 1
    if datatype in (DataType.UINT, DataType.WORD):
        return struct.unpack_from(">H", data, offset)[0], offset + 2
    if datatype == DataType.INT:
        return struct.unpack_from(">h", data, offset)[0], offset + 2
    if datatype in (DataType.UDINT, DataType.AID):
        return _read_vlq32(data, offset)
    if datatype == DataType.DINT:
        value, consumed = decode_int32_vlq(data, offset)
        return value, offset + consumed
    if datatype == DataType.ULINT:
        return _read_vlq64(data, offset)
    if datatype in (DataType.LINT, DataType.TIMESPAN):
        value, consumed = decode_int64_vlq(data, offset)
        return value, offset + consumed
    if datatype in (DataType.DWORD, DataType.RID):
        return struct.unpack_from(">I", data, offset)[0], offset + 4
    if datatype == DataType.LWORD:
        return struct.unpack_from(">Q", data, offset)[0], offset + 8
    if datatype == DataType.REAL:
        return struct.unpack_from(">f", data, offset)[0], offset + 4
    if datatype == DataType.LREAL:
        return struct.unpack_from(">d", data, offset)[0], offset + 8
    if datatype == DataType.TIMESTAMP:
        return struct.unpack_from(">Q", data, offset)[0], offset + 8
    if datatype == DataType.WSTRING:
        size, offset = _read_vlq32(data, offset)
        end = offset + size
        return data[offset:end].decode("utf-8", errors="replace"), end
    if datatype == DataType.BLOB:
        return _decode_blob(data, offset)
    if datatype == DataType.STRUCT:
        struct_id = struct.unpack_from(">I", data, offset)[0]
        offset += 4
        members: dict[int, Any] = {0: struct_id}
        while offset < len(data) and data[offset] != 0:
            member_id, offset = _read_vlq32(data, offset)
            value, offset = _decode_value(data, offset)
            members[member_id] = value
        return members, offset + 1
    raise ValueError(f"Unsupported alarm value datatype: {datatype:#x}")


def _decode_value(data: bytes, offset: int) -> tuple[Any, int]:
    if offset + 2 > len(data):
        raise ValueError("Truncated alarm value")
    flags, datatype = data[offset], data[offset + 1]
    offset += 2
    if flags == 0x40:
        values: dict[int, Any] = {}
        key, offset = _read_vlq32(data, offset)
        while key:
            if datatype == DataType.BLOB:
                value, offset = _decode_blob(data, offset)
            else:
                value, offset = _decode_scalar(data, offset, datatype)
            values[key] = value
            key, offset = _read_vlq32(data, offset)
        return values, offset
    if flags in (0x10, 0x20):
        count, offset = _read_vlq32(data, offset)
        array_values: list[Any] = []
        for _ in range(count):
            value, offset = _decode_scalar(data, offset, datatype)
            array_values.append(value)
        return array_values, offset
    return _decode_scalar(data, offset, datatype)


def _decode_object(data: bytes, offset: int) -> tuple[_Object, int]:
    if data[offset] != ElementID.START_OF_OBJECT:
        raise ValueError("Expected S7CommPlus object")
    offset += 1
    relation_id = struct.unpack_from(">I", data, offset)[0]
    offset += 4
    class_id, offset = _read_vlq32(data, offset)
    _, offset = _read_vlq32(data, offset)  # class flags
    _, offset = _read_vlq32(data, offset)  # attribute id
    result = _Object(relation_id, class_id)
    while offset < len(data):
        tag = data[offset]
        if tag == ElementID.TERMINATING_OBJECT:
            return result, offset + 1
        if tag == ElementID.START_OF_OBJECT:
            child, offset = _decode_object(data, offset)
            result.children.append(child)
            continue
        if tag == ElementID.ATTRIBUTE:
            attribute_id, value_offset = _read_vlq32(data, offset + 1)
            value, offset = _decode_value(data, value_offset)
            result.attributes[attribute_id] = value
            continue
        if tag == ElementID.RELATION:
            _, offset = _read_vlq32(data, offset + 1)
            offset += 4
            continue
        raise ValueError(f"Unsupported object element: {tag:#x}")
    raise ValueError("Unterminated S7CommPlus object")


def _decode_objects(data: bytes, offset: int) -> tuple[list[_Object], int]:
    objects = []
    while offset < len(data) and data[offset] == ElementID.START_OF_OBJECT:
        obj, offset = _decode_object(data, offset)
        objects.append(obj)
    return objects, offset


def _alarm_texts(value: Any, language_ids: set[LanguageId | int] | None) -> dict[int, AlarmText]:
    grouped: dict[int, dict[int, str]] = {}
    if not isinstance(value, dict):
        return {}
    for key, blob in value.items():
        if not isinstance(key, int) or not isinstance(blob, _Blob):
            continue
        language_id, text_id = key >> 16, key & 0xFFFF
        if language_ids is not None and language_id not in language_ids:
            continue
        grouped.setdefault(language_id, {})[text_id] = blob.value.decode("utf-8", errors="replace")
    result = {}
    for language_id, texts in grouped.items():
        additional = tuple(texts.get(i, "") for i in range(3, 12))
        result[language_id] = AlarmText(language_id, texts.get(1, ""), texts.get(2, ""), additional)
    return result


def _alarm_from_object(obj: _Object, language_ids: set[LanguageId | int] | None) -> Alarm:
    attrs = obj.attributes
    state_id = Ids.ALARM_DAI_COMING if Ids.ALARM_DAI_COMING in attrs else Ids.ALARM_DAI_GOING
    state_value = attrs.get(state_id)
    state = "coming" if state_id == Ids.ALARM_DAI_COMING else "going"
    timestamp: int | None = None
    acknowledge_timestamp: int | None = None
    associated_values: tuple[bytes, ...] = ()
    if isinstance(state_value, dict):
        timestamp_value = state_value.get(3475)
        acknowledge_value = state_value.get(3646)
        timestamp = timestamp_value if isinstance(timestamp_value, int) else None
        acknowledge_timestamp = acknowledge_value if isinstance(acknowledge_value, int) else None
        raw_values = state_value.get(3476)
        if isinstance(raw_values, list):
            associated_values = tuple(value.value for value in raw_values if isinstance(value, _Blob))
    hmi = attrs.get(Ids.ALARM_DAI_HMI_INFO)
    return Alarm(
        cpu_alarm_id=int(attrs.get(Ids.ALARM_DAI_CPU_ALARM_ID, 0)),
        all_states_info=int(attrs.get(Ids.ALARM_DAI_ALL_STATES_INFO, 0)),
        domain=int(attrs.get(Ids.ALARM_DAI_DOMAIN, 0)),
        message_type=int(attrs.get(Ids.ALARM_DAI_MESSAGE_TYPE, 0)),
        sequence_counter=int(attrs.get(Ids.ALARM_DAI_SEQUENCE_COUNTER, 0)),
        name=str(attrs.get(Ids.OBJECT_VARIABLE_TYPE_NAME, "")),
        state=state if state_value is not None else "unknown",
        timestamp=timestamp,
        acknowledge_timestamp=acknowledge_timestamp,
        hmi_info=hmi.value if isinstance(hmi, _Blob) else b"",
        associated_values=associated_values,
        texts=_alarm_texts(attrs.get(Ids.ALARM_DAI_TEXTS), language_ids),
    )


def parse_alarm_explore_response(response: bytes, language_ids: Sequence[LanguageId | int] | None = None) -> list[Alarm]:
    """Parse the payload returned by an alarm-subsystem EXPLORE request."""
    return_value, offset = _read_vlq64(response, 0)
    if return_value != 0:
        raise RuntimeError(f"Alarm browse failed: PLC returned {return_value:#x}")
    if offset + 4 > len(response):
        raise ValueError("Alarm browse response is truncated")
    offset += 4  # ExploreId
    # IntegrityId is between ExploreId and the object list on V2+ responses.
    while offset < len(response) and response[offset] != ElementID.START_OF_OBJECT:
        _, offset = _read_vlq32(response, offset)
    objects, _ = _decode_objects(response, offset)
    wanted = set(language_ids) if language_ids is not None else None
    return [_alarm_from_object(obj, wanted) for obj in objects if obj.class_id == Ids.ALARM_DAI_CLASS_RID]


def parse_alarm_notification(frame: bytes, language_ids: Sequence[LanguageId | int] | None = None) -> AlarmNotification:
    """Parse one complete S7CommPlus notification frame."""
    if len(frame) < 5 or frame[0] != 0x72:
        raise ValueError("Invalid S7CommPlus notification frame")
    data_length = struct.unpack_from(">H", frame, 2)[0]
    data = frame[4 : 4 + data_length]
    if not data or data[0] != Opcode.NOTIFICATION:
        raise ValueError("Expected S7CommPlus notification opcode")
    offset = 1
    subscription_id = struct.unpack_from(">I", data, offset)[0]
    offset += 10  # subscription id plus three unknown UInt16 fields
    credit_tick = data[offset]
    offset += 1
    sequence_number, offset = _read_vlq32(data, offset)
    change_counter = data[offset]
    timestamp: int | None = None
    if change_counter:
        offset += 1
    else:
        timestamp = struct.unpack_from(">Q", data, offset)[0]
        offset += 9  # timestamp plus additional change counter
    # Skip the data-change value list. Alarm-only subscriptions terminate it with zero.
    while offset < len(data) and data[offset] != 0:
        raise ValueError("Mixed data/alarm notifications are not supported")
    offset += 1
    alarms: list[Alarm] = []
    if offset < len(data) and data[offset] != 0:
        alarm_subscription_id = struct.unpack_from(">I", data, offset)[0]
        offset += 6
        if data[offset] != 0x81:
            raise ValueError(f"Unsupported alarm notification return value: {data[offset]:#x}")
        offset += 1
        objects, _ = _decode_objects(data, offset)
        wanted = set(language_ids) if language_ids is not None else None
        alarms = [_alarm_from_object(obj, wanted) for obj in objects if obj.class_id == Ids.ALARM_DAI_CLASS_RID]
        if subscription_id == 0:
            subscription_id = alarm_subscription_id
    return AlarmNotification(subscription_id, credit_tick, sequence_number, change_counter, timestamp, tuple(alarms))
