"""S7CommPlus data subscription encoding and notification parsing.

The wire layout follows the subscription implementation in
``thomas-v2/S7CommPlusDriver`` and the TIA Portal captures attached to
GH-710.  Subscriptions use symbolic access sequences; raw byte offsets do
not identify variables in optimized data blocks.
"""

import struct
from collections import deque
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .catalog import SymbolicTag

from .codec import decode_header, decode_pvalue_to_bytes, encode_object_qualifier
from .protocol import DataType, ElementID, Ids, Opcode, ProtocolVersion
from .vlq import decode_uint32_vlq, encode_int64_vlq, encode_uint32_vlq


@dataclass(frozen=True)
class SubscriptionItem:
    """One symbolic variable included in a data subscription."""

    access_area: int
    lids: tuple[int, ...]
    access_sub_area: int | None = None
    symbol_crc: int = 0
    reference_id: int = 0
    tag: "SymbolicTag | None" = None

    def __post_init__(self) -> None:
        if not 0 <= self.access_area <= 0xFFFFFFFF:
            raise ValueError("access_area must fit in an unsigned 32-bit integer")
        if not self.lids:
            raise ValueError("a subscription item requires at least one LID")
        if any(not 0 <= lid <= 0xFFFFFFFF for lid in self.lids):
            raise ValueError("LIDs must fit in unsigned 32-bit integers")
        if self.access_sub_area is not None and not 0 <= self.access_sub_area <= 0xFFFFFFFF:
            raise ValueError("access_sub_area must fit in an unsigned 32-bit integer")
        if not 0 <= self.symbol_crc <= 0xFFFFFFFF:
            raise ValueError("symbol_crc must fit in an unsigned 32-bit integer")
        if not 0 <= self.reference_id <= 0xFFFFFFFF:
            raise ValueError("reference_id must fit in an unsigned 32-bit integer")

    @property
    def resolved_sub_area(self) -> int:
        """Return the explicit or inferred access sub-area."""
        if self.access_sub_area is not None:
            return self.access_sub_area
        if self.access_area & 0xFFFF0000 == Ids.DB_ACCESS_AREA_BASE:
            return Ids.DB_VALUE_ACTUAL
        return Ids.CONTROLLER_AREA_VALUE_ACTUAL

    @classmethod
    def from_access_sequence(
        cls,
        access_sequence: str,
        *,
        symbol_crc: int = 0,
        reference_id: int = 0,
        access_sub_area: int | None = None,
    ) -> "SubscriptionItem":
        """Build an item from a ``browse()`` access sequence.

        For example, ``"8A0E0007.A.2"`` addresses LIDs ``0xA, 0x2`` in
        DB7's actual-value area.
        """
        parts = access_sequence.split(".")
        if len(parts) < 2 or any(not part for part in parts):
            raise ValueError("access_sequence must contain an access area and at least one LID")
        try:
            access_area = int(parts[0], 16)
            lids = tuple(int(part, 16) for part in parts[1:])
        except ValueError as exc:
            raise ValueError("access_sequence components must be hexadecimal") from exc
        return cls(access_area, lids, access_sub_area, symbol_crc, reference_id)

    @classmethod
    def from_tag(cls, tag: "SymbolicTag", *, reference_id: int = 0) -> "SubscriptionItem":
        """Build an item that retains a catalog tag for typed notifications."""
        return cls(tag.access_area, tag.lids, symbol_crc=tag.symbol_crc, reference_id=reference_id, tag=tag)


@dataclass(frozen=True)
class SubscriptionNotification:
    """Values and errors carried by one unsolicited subscription update."""

    subscription_id: int
    credit_tick: int
    sequence_number: int
    change_counter: int
    values: dict[int, bytes]
    errors: dict[int, int]
    timestamp_microseconds: int | None = None
    trailing_data: bytes = b""
    decoded_values: dict[int, Any] = field(default_factory=dict)
    tags: dict[int, "SymbolicTag"] = field(default_factory=dict)


@dataclass(frozen=True)
class SubscriptionDiagnostics:
    """Queue and sequence-loss diagnostics for one active subscription."""

    subscription_id: int
    queued_notifications: int
    dropped_notifications: int
    missed_sequence_updates: int
    transport_frame_overflows: int = 0


@dataclass
class _SubscriptionState:
    items: dict[int, SubscriptionItem]
    change_counter: int
    credit_limit: int
    credit_step: int
    queue_size: int
    notifications: deque[SubscriptionNotification] = field(default_factory=deque)
    callbacks: list[Callable[[SubscriptionNotification], None]] = field(default_factory=list)
    dropped_notifications: int = 0
    missed_sequence_updates: int = 0
    last_sequence: int | None = None
    next_credit_limit: int = 0

    def __post_init__(self) -> None:
        self.next_credit_limit = self.credit_limit


class SubscriptionRegistry:
    """Bounded notification routing shared by the sync and async clients."""

    def __init__(self, orphan_queue_size: int = 100) -> None:
        self._states: dict[int, _SubscriptionState] = {}
        self._orphans: deque[SubscriptionNotification] = deque(maxlen=orphan_queue_size)
        self.unmatched_notifications = 0

    def register(
        self,
        subscription_id: int,
        items: Sequence[SubscriptionItem],
        *,
        change_counter: int,
        credit_limit: int,
        credit_step: int,
        queue_size: int,
    ) -> None:
        if queue_size <= 0:
            raise ValueError("queue_size must be positive")
        references = {item.reference_id or index: item for index, item in enumerate(items, 1)}
        state = _SubscriptionState(references, change_counter, credit_limit, credit_step, queue_size)
        self._states[subscription_id] = state
        retained: deque[SubscriptionNotification] = deque(maxlen=self._orphans.maxlen)
        while self._orphans:
            notification = self._orphans.popleft()
            if notification.subscription_id == subscription_id and notification.change_counter == change_counter:
                self._enqueue(state, self._decorate(notification, state))
            else:
                retained.append(notification)
        self._orphans = retained

    def unregister(self, subscription_id: int) -> None:
        self._states.pop(subscription_id, None)
        self._orphans = deque(
            (notification for notification in self._orphans if notification.subscription_id != subscription_id),
            maxlen=self._orphans.maxlen,
        )

    def clear(self) -> None:
        self._states.clear()
        self._orphans.clear()

    @property
    def subscription_ids(self) -> tuple[int, ...]:
        return tuple(self._states)

    def contains(self, subscription_id: int) -> bool:
        return subscription_id in self._states

    def add_callback(self, subscription_id: int, callback: Callable[[SubscriptionNotification], None]) -> None:
        self._state(subscription_id).callbacks.append(callback)

    def remove_callback(self, subscription_id: int, callback: Callable[[SubscriptionNotification], None]) -> None:
        state = self._state(subscription_id)
        if callback in state.callbacks:
            state.callbacks.remove(callback)

    def route(self, notification: SubscriptionNotification) -> tuple[bool, int | None]:
        state = self._states.get(notification.subscription_id)
        if state is None:
            if len(self._orphans) == self._orphans.maxlen:
                self.unmatched_notifications += 1
            self._orphans.append(notification)
            return False, None
        if notification.change_counter != state.change_counter:
            state.dropped_notifications += 1
            return False, None

        decorated = self._decorate(notification, state)
        if state.last_sequence is not None and decorated.sequence_number > state.last_sequence + 1:
            state.missed_sequence_updates += decorated.sequence_number - state.last_sequence - 1
        state.last_sequence = decorated.sequence_number
        self._enqueue(state, decorated)
        for callback in tuple(state.callbacks):
            callback(decorated)

        credit_update = None
        if state.credit_limit > 0 and state.credit_step > 0 and decorated.credit_tick >= state.next_credit_limit - 1:
            state.next_credit_limit = (state.next_credit_limit + state.credit_step) % 255 or state.credit_step
            credit_update = state.next_credit_limit
        return True, credit_update

    def pop(self, subscription_id: int) -> SubscriptionNotification | None:
        state = self._state(subscription_id)
        return state.notifications.popleft() if state.notifications else None

    def diagnostics(self, subscription_id: int) -> SubscriptionDiagnostics:
        state = self._state(subscription_id)
        return SubscriptionDiagnostics(
            subscription_id,
            len(state.notifications),
            state.dropped_notifications,
            state.missed_sequence_updates,
        )

    def _state(self, subscription_id: int) -> _SubscriptionState:
        try:
            return self._states[subscription_id]
        except KeyError as exc:
            raise KeyError(f"Unknown subscription: {subscription_id:#x}") from exc

    @staticmethod
    def _decorate(notification: SubscriptionNotification, state: _SubscriptionState) -> SubscriptionNotification:
        tags: dict[int, SymbolicTag] = {}
        decoded: dict[int, Any] = {}
        for reference_id, raw in notification.values.items():
            item = state.items.get(reference_id)
            if item is None or item.tag is None:
                decoded[reference_id] = raw
                continue
            tags[reference_id] = item.tag
            decoded[reference_id] = item.tag.decode_value(raw)
        for reference_id in notification.errors:
            item = state.items.get(reference_id)
            if item is not None and item.tag is not None:
                tags[reference_id] = item.tag
        return replace(notification, tags=tags, decoded_values=decoded)

    @staticmethod
    def _enqueue(state: _SubscriptionState, notification: SubscriptionNotification) -> None:
        if len(state.notifications) >= state.queue_size:
            state.notifications.popleft()
            state.dropped_notifications += 1
        state.notifications.append(notification)


def _attribute(attribute_id: int, value: bytes) -> bytes:
    return bytes([ElementID.ATTRIBUTE]) + encode_uint32_vlq(attribute_id) + value


def _scalar(data_type: DataType, data: bytes) -> bytes:
    return bytes([0x00, data_type]) + data


def _reference_list(items: Sequence[SubscriptionItem], change_counter: int) -> bytes:
    values = [0x80000000 | ((change_counter & 0xFF) << 16), 0, len(items)]
    used_references: set[int] = set()
    for index, item in enumerate(items, 1):
        reference_id = item.reference_id or index
        if reference_id in used_references:
            raise ValueError(f"duplicate subscription reference_id {reference_id}")
        used_references.add(reference_id)
        values.extend(
            (
                0x80040000 | (1 + len(item.lids)),
                reference_id,
                0,
                item.access_area,
                item.symbol_crc,
                item.resolved_sub_area,
                *item.lids,
            )
        )

    encoded = bytearray([0x20, DataType.UDINT])
    encoded += encode_uint32_vlq(len(values))
    for value in values:
        encoded += encode_uint32_vlq(value)
    return bytes(encoded)


def build_subscription_request(
    subscription_container_id: int,
    items: Sequence[SubscriptionItem],
    *,
    cycle_ms: int = 100,
    credit_limit: int = 10,
    change_counter: int = 1,
    relation_id: int = 0x7FFFC001,
    route_mode: int = 0x14,
) -> tuple[bytes, int]:
    """Build a CreateObject payload and its IntegrityId insertion tail.

    The returned tail must be passed as ``integrity_tail`` to
    :meth:`S7CommPlusConnection.send_request`; CreateObject carries its
    IntegrityId between the request set and object tree, rather than near the
    final padding used by most requests.
    """
    if not items:
        raise ValueError("a subscription requires at least one item")
    if not 0 <= cycle_ms <= 0xFFFFFFFF:
        raise ValueError("cycle_ms must fit in an unsigned 32-bit integer")
    if not -1 <= credit_limit <= 0x7FFF:
        raise ValueError("credit_limit must be -1 or a signed 16-bit positive value")
    if not 1 <= change_counter <= 0xFF:
        raise ValueError("change_counter must be between 1 and 255")

    payload = bytearray()
    payload += struct.pack(">I", subscription_container_id)
    payload += _scalar(DataType.UDINT, encode_uint32_vlq(0))
    payload += struct.pack(">I", 0)
    request_set_size = len(payload)

    payload += bytes([ElementID.START_OF_OBJECT])
    payload += struct.pack(">I", relation_id)
    payload += encode_uint32_vlq(Ids.CLASS_SUBSCRIPTION)
    payload += encode_uint32_vlq(0)
    payload += encode_uint32_vlq(0)

    name = f"Subscription_{relation_id}".encode()
    payload += _attribute(
        Ids.OBJECT_VARIABLE_TYPE_NAME,
        _scalar(DataType.WSTRING, encode_uint32_vlq(len(name)) + name),
    )
    payload += _attribute(Ids.SUBSCRIPTION_FUNCTION_CLASS_ID, _scalar(DataType.USINT, b"\x00"))
    payload += _attribute(Ids.SUBSCRIPTION_MISSED_SENDINGS, _scalar(DataType.UINT, struct.pack(">H", 0)))
    payload += _attribute(Ids.SUBSCRIPTION_SUBSYSTEM_ERROR, _scalar(DataType.LINT, encode_int64_vlq(0)))
    payload += _attribute(Ids.SUBSCRIPTION_ROUTE_MODE, _scalar(DataType.USINT, bytes([route_mode & 0xFF])))
    payload += _attribute(Ids.SUBSCRIPTION_ACTIVE, _scalar(DataType.BOOL, b"\x01"))
    payload += _attribute(Ids.SUBSCRIPTION_REFERENCE_LIST, _reference_list(items, change_counter))
    payload += _attribute(Ids.SUBSCRIPTION_CYCLE_TIME, _scalar(DataType.UDINT, encode_uint32_vlq(cycle_ms)))
    payload += _attribute(Ids.SUBSCRIPTION_DISABLED, _scalar(DataType.USINT, b"\x00"))
    payload += _attribute(Ids.SUBSCRIPTION_COUNT, _scalar(DataType.USINT, b"\x00"))
    payload += _attribute(Ids.SUBSCRIPTION_CREDIT_LIMIT, _scalar(DataType.INT, struct.pack(">h", credit_limit)))
    payload += _attribute(Ids.SUBSCRIPTION_TICKS, _scalar(DataType.UINT, struct.pack(">H", 0xFFFF)))
    payload += _attribute(1055, _scalar(DataType.USINT, b"\x00"))
    payload += bytes([ElementID.TERMINATING_OBJECT])
    payload += struct.pack(">I", 0)

    return bytes(payload), len(payload) - request_set_size


def build_delete_subscription_request(subscription_id: int, protocol_version: int) -> bytes:
    """Build the payload for deleting one subscription object."""
    return (
        struct.pack(">I", subscription_id)
        + b"\x00"
        + encode_object_qualifier(protocol_version=protocol_version)
        + struct.pack(">I", 0)
    )


def _decode_notification_value(data: bytes, offset: int) -> tuple[bytes, int]:
    """Decode a notification PValue, including Siemens' padded BLOB form."""
    if len(data) >= offset + 4 and data[offset] & 0x10 == 0 and data[offset + 1] == DataType.BLOB and data[offset + 2] == 0:
        length, width = decode_uint32_vlq(data, offset + 3)
        value_offset = offset + 3 + width
        value_end = value_offset + length
        if value_end > len(data):
            raise ValueError("subscription BLOB value is truncated")
        return data[value_offset:value_end], value_end - offset
    return decode_pvalue_to_bytes(data, offset)


def notification_subscription_id(frame: bytes) -> int:
    """Return the subscription object ID from any notification frame."""
    version, data_length, consumed = decode_header(frame)
    data = frame[consumed : consumed + data_length]
    if version == ProtocolVersion.V3 and data:
        hash_length = data[0]
        data = data[1 + hash_length :]
    if len(data) < 5 or data[0] != Opcode.NOTIFICATION:
        raise ValueError("expected an S7CommPlus notification with a subscription ID")
    return struct.unpack_from(">I", data, 1)[0]


def parse_subscription_notification(frame: bytes) -> SubscriptionNotification:
    """Parse one complete unsolicited S7CommPlus notification frame."""
    version, data_length, consumed = decode_header(frame)
    if len(frame) < consumed + data_length:
        raise ValueError("truncated S7CommPlus notification frame")
    data = frame[consumed : consumed + data_length]
    if version == ProtocolVersion.V3 and data:
        hash_length = data[0]
        if hash_length and len(data) > 1 + hash_length:
            data = data[1 + hash_length :]
    if not data or data[0] != Opcode.NOTIFICATION:
        raise ValueError("expected an S7CommPlus notification")

    offset = 1
    if len(data) < offset + 11:
        raise ValueError("subscription notification header is truncated")
    subscription_id = struct.unpack_from(">I", data, offset)[0]
    offset += 4
    offset += 6  # three protocol-reserved UInt16 fields
    credit_tick = data[offset]
    offset += 1
    sequence_number, width = decode_uint32_vlq(data, offset)
    offset += width
    if offset >= len(data):
        raise ValueError("subscription notification change counter is missing")

    timestamp: int | None = None
    change_counter = data[offset]
    offset += 1
    if change_counter == 0:
        offset -= 1
        if len(data) < offset + 9:
            raise ValueError("subscription notification timestamp is truncated")
        timestamp = struct.unpack_from(">Q", data, offset)[0]
        offset += 8
        change_counter = data[offset]
        offset += 1

    values: dict[int, bytes] = {}
    errors: dict[int, int] = {}
    while offset < len(data):
        status = data[offset]
        offset += 1
        if status == 0:
            break
        if status == 0x92:
            if len(data) < offset + 4:
                raise ValueError("subscription item reference is truncated")
            reference_id = struct.unpack_from(">I", data, offset)[0]
            offset += 4
            value, width = _decode_notification_value(data, offset)
            offset += width
            values[reference_id] = value
        elif status == 0x9B:
            reference_id, width = decode_uint32_vlq(data, offset)
            offset += width
            value, width = _decode_notification_value(data, offset)
            offset += width
            values[reference_id] = value
        elif status in (0x03, 0x13):
            if len(data) < offset + 4:
                raise ValueError("subscription error reference is truncated")
            reference_id = struct.unpack_from(">I", data, offset)[0]
            offset += 4
            errors[reference_id] = status
        else:
            raise ValueError(f"unsupported subscription item status 0x{status:02X}")

    return SubscriptionNotification(
        subscription_id=subscription_id,
        credit_tick=credit_tick,
        sequence_number=sequence_number,
        change_counter=change_counter,
        values=values,
        errors=errors,
        timestamp_microseconds=timestamp,
        trailing_data=data[offset:],
    )
