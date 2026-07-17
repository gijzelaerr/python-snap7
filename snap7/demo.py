"""Live demo server that exposes real host metrics as S7 PLC tags.

Starts an emulated S7 server and continuously writes real CPU / memory /
disk / network readings into well-known DB1 offsets, plus a writable
DB2 block that clients (e.g. the ha-s7 Home Assistant integration) can
write to. An optional :mod:`rich` live display shows the current values
and logs any writes with a timestamp.

This is a demo, not a production tool. Install with::

    pip install "python-snap7[demo]"
    s7 demo --port 10102

The ``demo`` extras pull in everything the demo needs: ``psutil`` for
metrics, ``rich`` for the live dashboard, and ``click`` for the CLI
entry point.

DB layout
---------

DB1 (read-only — updated by the host)::

    DB1.DBD0:REAL    cpu_percent          0..100
    DB1.DBD4:REAL    memory_percent       0..100
    DB1.DBD8:REAL    disk_read_mbps       megabytes/second
    DB1.DBD12:REAL   disk_write_mbps      megabytes/second
    DB1.DBD16:REAL   net_rx_mbps          megabytes/second
    DB1.DBD20:REAL   net_tx_mbps          megabytes/second
    DB1.DBD24:REAL   cpu_temp_c           0 if sensor not available
    DB1.DBD28:REAL   fan_rpm              0 if sensor not available
    DB1.DBD32:DINT   uptime_seconds
    DB1.DBX36.0:BOOL overheating          cpu_temp > 75
    DB1.DBX36.1:BOOL high_load            cpu_percent > 80
    DB1.DBX36.2:BOOL disk_busy            disk_read+write > 50 MB/s

DB2 (writable — observe writes from a client)::

    DB2.DBX0.0:BOOL  lamp_on
    DB2.DBX0.1:BOOL  alarm_enable
    DB2.DBW2:INT     brightness           0..255
    DB2.DBW4:INT     setpoint_c
    DB2:10:STRING[32] message
"""

from __future__ import annotations

import logging
import socket
import struct
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable

from .server import Server
from .type import SrvArea

if TYPE_CHECKING:
    import psutil as _psutil  # noqa: F401

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# DB layout constants — single source of truth, shared with docstring above.
# ---------------------------------------------------------------------------

DB_SENSORS = 1
DB_CONTROLS = 2

_SENSOR_LAYOUT: dict[str, tuple[int, str]] = {
    "cpu_percent": (0, "REAL"),
    "memory_percent": (4, "REAL"),
    "disk_read_mbps": (8, "REAL"),
    "disk_write_mbps": (12, "REAL"),
    "net_rx_mbps": (16, "REAL"),
    "net_tx_mbps": (20, "REAL"),
    "cpu_temp_c": (24, "REAL"),
    "fan_rpm": (28, "REAL"),
    "uptime_seconds": (32, "DINT"),
}
_SENSOR_BOOLS: dict[str, tuple[int, int]] = {
    "overheating": (36, 0),
    "high_load": (36, 1),
    "disk_busy": (36, 2),
}
_SENSORS_DB_SIZE = 40

_CONTROLS_DB_SIZE = 64
_CONTROL_LAYOUT: dict[str, tuple[int, str]] = {
    # Reserve byte 0 for the two BOOLs (lamp_on at .0, alarm_enable at .1)
    "brightness": (2, "INT"),
    "setpoint_c": (4, "INT"),
    "message": (10, "STRING[32]"),
}
_CONTROL_BOOLS: dict[str, tuple[int, int]] = {
    "lamp_on": (0, 0),
    "alarm_enable": (0, 1),
}


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


@dataclass
class Metrics:
    """Snapshot of host metrics."""

    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    disk_read_mbps: float = 0.0
    disk_write_mbps: float = 0.0
    net_rx_mbps: float = 0.0
    net_tx_mbps: float = 0.0
    cpu_temp_c: float = 0.0
    fan_rpm: float = 0.0
    uptime_seconds: int = 0


class MetricCollector:
    """Polls psutil for metrics, computing rate deltas against the previous reading."""

    def __init__(self) -> None:
        try:
            import psutil
        except ImportError as err:
            raise RuntimeError("psutil is required for the demo server. Install with: pip install 'python-snap7[demo]'") from err

        self._psutil = psutil
        self._start = time.time()
        self._prev_sample: tuple[float, Any, Any] | None = None  # (t, disk_io, net_io)

    def sample(self) -> Metrics:
        """Take a metrics snapshot. Rates are computed over the interval since the last sample."""
        now = time.time()
        disk_io = self._psutil.disk_io_counters()
        net_io = self._psutil.net_io_counters()

        if self._prev_sample is not None:
            prev_t, prev_disk, prev_net = self._prev_sample
            dt = max(now - prev_t, 1e-6)
            disk_read_mbps = (disk_io.read_bytes - prev_disk.read_bytes) / dt / 1_000_000
            disk_write_mbps = (disk_io.write_bytes - prev_disk.write_bytes) / dt / 1_000_000
            net_rx_mbps = (net_io.bytes_recv - prev_net.bytes_recv) / dt / 1_000_000
            net_tx_mbps = (net_io.bytes_sent - prev_net.bytes_sent) / dt / 1_000_000
        else:
            disk_read_mbps = disk_write_mbps = net_rx_mbps = net_tx_mbps = 0.0

        self._prev_sample = (now, disk_io, net_io)

        return Metrics(
            cpu_percent=self._psutil.cpu_percent(interval=None),
            memory_percent=self._psutil.virtual_memory().percent,
            disk_read_mbps=disk_read_mbps,
            disk_write_mbps=disk_write_mbps,
            net_rx_mbps=net_rx_mbps,
            net_tx_mbps=net_tx_mbps,
            cpu_temp_c=_read_cpu_temp(self._psutil),
            fan_rpm=_read_fan_rpm(self._psutil),
            uptime_seconds=int(now - self._start),
        )


def _read_cpu_temp(psutil: Any) -> float:
    """Return CPU temperature in °C, or 0.0 if unavailable (macOS, containers, ...)."""
    if not hasattr(psutil, "sensors_temperatures"):
        return 0.0
    try:
        readings = psutil.sensors_temperatures()
    except Exception:  # noqa: BLE001 — sensors are platform-specific and flaky
        return 0.0
    # Prefer well-known CPU sensors; fall back to the first reading we see.
    for key in ("coretemp", "cpu_thermal", "k10temp", "zenpower"):
        if key in readings and readings[key]:
            return float(readings[key][0].current)
    for entries in readings.values():
        if entries:
            return float(entries[0].current)
    return 0.0


def _read_fan_rpm(psutil: Any) -> float:
    """Return the first fan speed in RPM, or 0.0 if unavailable."""
    if not hasattr(psutil, "sensors_fans"):
        return 0.0
    try:
        readings = psutil.sensors_fans()
    except Exception:  # noqa: BLE001
        return 0.0
    for entries in readings.values():
        if entries:
            return float(entries[0].current)
    return 0.0


# ---------------------------------------------------------------------------
# DB encoding
# ---------------------------------------------------------------------------


def _encode_sensors(metrics: Metrics, buffer: bytearray) -> None:
    """Write ``metrics`` into ``buffer`` at the documented DB1 offsets."""
    struct.pack_into(">f", buffer, _SENSOR_LAYOUT["cpu_percent"][0], metrics.cpu_percent)
    struct.pack_into(">f", buffer, _SENSOR_LAYOUT["memory_percent"][0], metrics.memory_percent)
    struct.pack_into(">f", buffer, _SENSOR_LAYOUT["disk_read_mbps"][0], metrics.disk_read_mbps)
    struct.pack_into(">f", buffer, _SENSOR_LAYOUT["disk_write_mbps"][0], metrics.disk_write_mbps)
    struct.pack_into(">f", buffer, _SENSOR_LAYOUT["net_rx_mbps"][0], metrics.net_rx_mbps)
    struct.pack_into(">f", buffer, _SENSOR_LAYOUT["net_tx_mbps"][0], metrics.net_tx_mbps)
    struct.pack_into(">f", buffer, _SENSOR_LAYOUT["cpu_temp_c"][0], metrics.cpu_temp_c)
    struct.pack_into(">f", buffer, _SENSOR_LAYOUT["fan_rpm"][0], metrics.fan_rpm)
    struct.pack_into(">i", buffer, _SENSOR_LAYOUT["uptime_seconds"][0], metrics.uptime_seconds)

    # Derived BOOL flags in byte 36
    flags = 0
    if metrics.cpu_temp_c > 75.0:
        flags |= 1 << _SENSOR_BOOLS["overheating"][1]
    if metrics.cpu_percent > 80.0:
        flags |= 1 << _SENSOR_BOOLS["high_load"][1]
    if metrics.disk_read_mbps + metrics.disk_write_mbps > 50.0:
        flags |= 1 << _SENSOR_BOOLS["disk_busy"][1]
    buffer[_SENSOR_BOOLS["overheating"][0]] = flags


# ---------------------------------------------------------------------------
# Write detection (poll DB2 for changes)
# ---------------------------------------------------------------------------


WriteHandler = Callable[[str, str], None]


class ControlWatcher:
    """Diffs the controls DB buffer on each tick and reports human-readable changes.

    The server emulator doesn't expose a write callback, so we just
    snapshot the buffer and compare — simpler than monkey-patching
    internals and it's good enough for a demo (sub-second resolution).
    """

    def __init__(self, buffer: bytearray, on_change: WriteHandler) -> None:
        self._buffer = buffer
        self._on_change = on_change
        self._prev = bytes(buffer)

    def tick(self) -> None:
        current = bytes(self._buffer)
        if current == self._prev:
            return

        for name, (byte, bit) in _CONTROL_BOOLS.items():
            old = (self._prev[byte] >> bit) & 1
            new = (current[byte] >> bit) & 1
            if old != new:
                self._on_change(name, "ON" if new else "OFF")

        for name, (offset, datatype) in _CONTROL_LAYOUT.items():
            if datatype == "INT":
                old_val: Any = struct.unpack_from(">h", self._prev, offset)[0]
                new_val: Any = struct.unpack_from(">h", current, offset)[0]
            elif datatype.startswith("STRING"):
                max_len = self._prev[offset]
                old_len = self._prev[offset + 1]
                new_len = current[offset + 1]
                old_val = self._prev[offset + 2 : offset + 2 + old_len].decode("latin-1", "replace")
                new_val = current[offset + 2 : offset + 2 + new_len].decode("latin-1", "replace")
                if current[offset] == 0:
                    # STRING header not initialised by the client; suppress noise.
                    continue
                _ = max_len  # silence unused
            else:
                continue
            if old_val != new_val:
                self._on_change(name, str(new_val))

        self._prev = current


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def run_demo(
    port: int = 10102,
    refresh_seconds: float = 2.0,
    live: bool = True,
) -> None:
    """Run the demo server until interrupted.

    Args:
        port: TCP port the server listens on.
        refresh_seconds: Interval between metric samples and DB2 diffs.
        live: Use the rich live display. Falls back to plain logging if
            :mod:`rich` is not installed.
    """
    collector = MetricCollector()  # Raises with a helpful hint if psutil is missing.

    # Pass the bytearrays directly — Server.register_area keeps the same
    # reference for bytearray input, but copies when given a ctypes array.
    # The shared reference is what lets the metrics worker mutate the
    # buffer and have clients see fresh values.
    sensors_data = bytearray(_SENSORS_DB_SIZE)
    controls_data = bytearray(_CONTROLS_DB_SIZE)

    server = Server()
    server.register_area(SrvArea.DB, DB_SENSORS, sensors_data)
    server.register_area(SrvArea.DB, DB_CONTROLS, controls_data)
    server.start(tcp_port=port)
    logger.info("demo server listening on %s:%d", _primary_ip(), port)

    stop = threading.Event()

    latest = Metrics()
    events: list[tuple[datetime, str, str]] = []

    def log_write(name: str, value: str) -> None:
        events.append((datetime.now(), name, value))
        # Keep the scrollback bounded so a busy client doesn't grow this forever.
        if len(events) > 50:
            del events[:-50]

    watcher = ControlWatcher(controls_data, log_write)

    def _worker() -> None:
        nonlocal latest
        while not stop.is_set():
            latest = collector.sample()
            _encode_sensors(latest, sensors_data)
            watcher.tick()
            stop.wait(refresh_seconds)

    worker = threading.Thread(target=_worker, name="demo-metrics", daemon=True)
    worker.start()

    try:
        if live and _rich_available():
            _run_live_display(port, lambda: latest, events, stop)
        else:
            _run_plain_loop(lambda: latest, events, stop)
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        worker.join(timeout=refresh_seconds + 1)
        server.stop()
        server.destroy()


def _rich_available() -> bool:
    try:
        import rich  # noqa: F401

        return True
    except ImportError:
        return False


def _primary_ip() -> str:
    """Best-effort local IP for the on-screen banner (localhost fallback on failure)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return str(s.getsockname()[0])
    except OSError:
        return "127.0.0.1"


def _run_plain_loop(
    latest: Callable[[], Metrics],
    events: list[tuple[datetime, str, str]],
    stop: threading.Event,
) -> None:
    """Fallback loop: periodically print a one-liner of the latest metrics."""
    last_event_count = 0
    while not stop.is_set():
        m = latest()
        logger.info(
            "CPU %.1f%% MEM %.1f%% DISK r/w %.1f/%.1f MB/s NET rx/tx %.1f/%.1f MB/s TEMP %.1f°C",
            m.cpu_percent,
            m.memory_percent,
            m.disk_read_mbps,
            m.disk_write_mbps,
            m.net_rx_mbps,
            m.net_tx_mbps,
            m.cpu_temp_c,
        )
        for ts, name, value in events[last_event_count:]:
            logger.info("[WRITE %s] %s = %s", ts.strftime("%H:%M:%S"), name, value)
        last_event_count = len(events)
        stop.wait(2.0)


def _run_live_display(
    port: int,
    latest: Callable[[], Metrics],
    events: list[tuple[datetime, str, str]],
    stop: threading.Event,
) -> None:
    """Rich-based full-screen dashboard. Imports rich lazily so the module loads without it."""
    from rich.console import Group
    from rich.live import Live
    from rich.panel import Panel
    from rich.table import Table

    def render() -> Group:
        m = latest()
        metrics_table = Table(title="Sensors (DB1)", expand=True)
        metrics_table.add_column("Tag", style="cyan")
        metrics_table.add_column("Value", justify="right")
        metrics_table.add_column("Unit")
        metrics_table.add_row("DB1.DBD0:REAL  cpu_percent", f"{m.cpu_percent:6.1f}", "%")
        metrics_table.add_row("DB1.DBD4:REAL  memory_percent", f"{m.memory_percent:6.1f}", "%")
        metrics_table.add_row("DB1.DBD8:REAL  disk_read_mbps", f"{m.disk_read_mbps:6.2f}", "MB/s")
        metrics_table.add_row("DB1.DBD12:REAL disk_write_mbps", f"{m.disk_write_mbps:6.2f}", "MB/s")
        metrics_table.add_row("DB1.DBD16:REAL net_rx_mbps", f"{m.net_rx_mbps:6.2f}", "MB/s")
        metrics_table.add_row("DB1.DBD20:REAL net_tx_mbps", f"{m.net_tx_mbps:6.2f}", "MB/s")
        metrics_table.add_row("DB1.DBD24:REAL cpu_temp_c", f"{m.cpu_temp_c:6.1f}", "°C")
        metrics_table.add_row("DB1.DBD28:REAL fan_rpm", f"{m.fan_rpm:6.0f}", "RPM")
        metrics_table.add_row("DB1.DBD32:DINT uptime_seconds", f"{m.uptime_seconds}", "s")

        writes_table = Table(title="Client writes (DB2)", expand=True)
        writes_table.add_column("Time")
        writes_table.add_column("Tag", style="magenta")
        writes_table.add_column("Value")
        for ts, name, value in events[-10:]:
            writes_table.add_row(ts.strftime("%H:%M:%S"), name, value)
        if not events:
            writes_table.add_row("—", "waiting for a client write…", "")

        banner = Panel(
            f"[bold]python-snap7 demo server[/bold]   listening on [green]{_primary_ip()}:{port}[/green]\n"
            f"Press [bold]Ctrl-C[/bold] to quit.",
            border_style="blue",
        )
        return Group(banner, metrics_table, writes_table)

    with Live(render(), refresh_per_second=4, screen=False) as live_display:
        while not stop.is_set():
            live_display.update(render())
            stop.wait(0.25)
