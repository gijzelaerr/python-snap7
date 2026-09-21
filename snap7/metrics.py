"""Prometheus exposition for S7 client operations.

Accumulates per-operation counters and durations in a :class:`MetricsRegistry`,
and optionally serves them as ``GET /metrics`` via :class:`MetricsServer`::

    from snap7.client import Client
    from snap7.metrics import MetricsRegistry, MetricsServer

    registry = MetricsRegistry()
    server = MetricsServer(registry, port=9110)
    server.start()

    client = Client(metrics=registry)
    client.connect("192.168.1.10", 0, 1)
    client.db_read(1, 0, 4)

    server.stop()
"""

from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

CONTENT_TYPE = "text/plain; version=0.0.4; charset=utf-8"

_ESCAPES = str.maketrans({"\\": r"\\", '"': r"\"", "\n": r"\n"})


def _label(value: str) -> str:
    return value.translate(_ESCAPES)


class MetricsRegistry:
    """Thread-safe counters and durations for client operations."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counts: dict[str, int] = {}
        self._errors: dict[str, int] = {}
        self._duration_sum: dict[str, float] = {}
        self._connected: dict[str, bool] = {}

    def record(self, operation: str, duration_seconds: float, error: bool) -> None:
        with self._lock:
            self._counts[operation] = self._counts.get(operation, 0) + 1
            self._duration_sum[operation] = self._duration_sum.get(operation, 0.0) + duration_seconds
            if error:
                self._errors[operation] = self._errors.get(operation, 0) + 1

    def set_connected(self, plc: str, connected: bool) -> None:
        with self._lock:
            self._connected[plc] = connected

    def render(self) -> str:
        with self._lock:
            counts = dict(self._counts)
            errors = dict(self._errors)
            duration_sum = dict(self._duration_sum)
            connected = dict(self._connected)

        lines = [
            "# HELP snap7_client_connected Whether the client is currently connected to a PLC.",
            "# TYPE snap7_client_connected gauge",
        ]
        for plc in sorted(connected):
            lines.append(f'snap7_client_connected{{plc="{_label(plc)}"}} {int(connected[plc])}')

        lines += [
            "# HELP snap7_operations_total Total number of client operations.",
            "# TYPE snap7_operations_total counter",
        ]
        for operation in sorted(counts):
            lines.append(f'snap7_operations_total{{operation="{_label(operation)}"}} {counts[operation]}')

        lines += [
            "# HELP snap7_operation_errors_total Total number of client operations that raised.",
            "# TYPE snap7_operation_errors_total counter",
        ]
        for operation in sorted(errors):
            lines.append(f'snap7_operation_errors_total{{operation="{_label(operation)}"}} {errors[operation]}')

        lines += [
            "# HELP snap7_operation_duration_seconds_sum Cumulative time spent in client operations.",
            "# TYPE snap7_operation_duration_seconds_sum counter",
        ]
        for operation in sorted(duration_sum):
            lines.append(f'snap7_operation_duration_seconds_sum{{operation="{_label(operation)}"}} {duration_sum[operation]}')
        return "\n".join(lines) + "\n"


class _MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path != "/metrics":
            self.send_response(404)
            self.end_headers()
            return
        registry: MetricsRegistry = self.server.registry
        body = registry.render().encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", CONTENT_TYPE)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        pass


class _MetricsHTTPServer(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], registry: MetricsRegistry) -> None:
        super().__init__(address, _MetricsHandler)
        self.registry = registry


class MetricsServer:
    """Serves a MetricsRegistry as ``GET /metrics`` on a background thread."""

    def __init__(self, registry: MetricsRegistry, host: str = "0.0.0.0", port: int = 9110) -> None:
        self._registry = registry
        self._host = host
        self._port = port
        self._httpd: _MetricsHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def port(self) -> int:
        assert self._httpd is not None
        return self._httpd.server_address[1]

    def start(self) -> None:
        self._httpd = _MetricsHTTPServer((self._host, self._port), self._registry)
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
