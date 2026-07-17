"""Smoke tests for the demo server.

Spin up the internals (MetricCollector, _encode_sensors, ControlWatcher)
directly — the server startup path is already covered by
``tests/test_s7_unified.py`` and a full end-to-end demo run would be
both slower and flakier. If ``psutil`` isn't installed the tests skip.
"""

from __future__ import annotations

import struct

import pytest

pytest.importorskip("psutil")

from snap7.demo import (  # noqa: E402
    _CONTROL_BOOLS,
    _CONTROL_LAYOUT,
    _SENSOR_BOOLS,
    _SENSOR_LAYOUT,
    _SENSORS_DB_SIZE,
    ControlWatcher,
    MetricCollector,
    Metrics,
    _encode_sensors,
)


def test_metric_collector_produces_plausible_values() -> None:
    collector = MetricCollector()
    m1 = collector.sample()  # seeds previous sample, rates are 0
    m2 = collector.sample()  # now real deltas

    # First sample has no delta so rates are 0; the second should be finite and >= 0.
    assert 0.0 <= m1.cpu_percent <= 100.0
    assert 0.0 <= m2.cpu_percent <= 100.0
    assert 0.0 <= m2.memory_percent <= 100.0
    assert m2.disk_read_mbps >= 0.0
    assert m2.net_rx_mbps >= 0.0
    assert m2.uptime_seconds >= 0


def test_encode_sensors_writes_all_fields_at_documented_offsets() -> None:
    buffer = bytearray(_SENSORS_DB_SIZE)
    m = Metrics(
        cpu_percent=42.5,
        memory_percent=67.25,
        disk_read_mbps=1.0,
        disk_write_mbps=2.0,
        net_rx_mbps=3.0,
        net_tx_mbps=4.0,
        cpu_temp_c=55.0,
        fan_rpm=1200.0,
        uptime_seconds=9999,
    )
    _encode_sensors(m, buffer)

    # Round-trip each REAL — verify the documented layout is what we actually emit.
    assert struct.unpack_from(">f", buffer, _SENSOR_LAYOUT["cpu_percent"][0])[0] == pytest.approx(42.5)
    assert struct.unpack_from(">f", buffer, _SENSOR_LAYOUT["memory_percent"][0])[0] == pytest.approx(67.25)
    assert struct.unpack_from(">f", buffer, _SENSOR_LAYOUT["cpu_temp_c"][0])[0] == pytest.approx(55.0)
    assert struct.unpack_from(">i", buffer, _SENSOR_LAYOUT["uptime_seconds"][0])[0] == 9999


def test_encode_sensors_sets_threshold_bools() -> None:
    buffer = bytearray(_SENSORS_DB_SIZE)

    # Below thresholds → all flags clear.
    _encode_sensors(Metrics(cpu_percent=50.0, cpu_temp_c=40.0, disk_read_mbps=1.0), buffer)
    flag_byte_cold = buffer[_SENSOR_BOOLS["overheating"][0]]
    assert (flag_byte_cold >> _SENSOR_BOOLS["overheating"][1]) & 1 == 0
    assert (flag_byte_cold >> _SENSOR_BOOLS["high_load"][1]) & 1 == 0
    assert (flag_byte_cold >> _SENSOR_BOOLS["disk_busy"][1]) & 1 == 0

    # Above thresholds → all flags set.
    _encode_sensors(
        Metrics(cpu_percent=95.0, cpu_temp_c=90.0, disk_read_mbps=40.0, disk_write_mbps=40.0),
        buffer,
    )
    flag_byte_hot = buffer[_SENSOR_BOOLS["overheating"][0]]
    assert (flag_byte_hot >> _SENSOR_BOOLS["overheating"][1]) & 1 == 1
    assert (flag_byte_hot >> _SENSOR_BOOLS["high_load"][1]) & 1 == 1
    assert (flag_byte_hot >> _SENSOR_BOOLS["disk_busy"][1]) & 1 == 1


def test_control_watcher_detects_bool_change() -> None:
    buffer = bytearray(64)
    changes: list[tuple[str, str]] = []
    watcher = ControlWatcher(buffer, lambda name, value: changes.append((name, value)))

    # No changes yet.
    watcher.tick()
    assert changes == []

    # Flip lamp_on.
    byte, bit = _CONTROL_BOOLS["lamp_on"]
    buffer[byte] |= 1 << bit
    watcher.tick()
    assert changes == [("lamp_on", "ON")]

    # Clear it.
    buffer[byte] &= ~(1 << bit)
    watcher.tick()
    assert changes == [("lamp_on", "ON"), ("lamp_on", "OFF")]


def test_control_watcher_detects_int_change() -> None:
    buffer = bytearray(64)
    changes: list[tuple[str, str]] = []
    watcher = ControlWatcher(buffer, lambda name, value: changes.append((name, value)))

    offset = _CONTROL_LAYOUT["brightness"][0]
    struct.pack_into(">h", buffer, offset, 200)
    watcher.tick()
    assert ("brightness", "200") in changes
