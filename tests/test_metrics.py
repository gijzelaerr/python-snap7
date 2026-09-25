"""Tests for Prometheus metrics."""

import unittest
import urllib.error
import urllib.request
from collections.abc import Iterator

import pytest

from snap7.client import Client
from snap7.error import S7ConnectionError
from snap7.metrics import MetricsRegistry, MetricsServer
from snap7.server import Server
from snap7.type import Area, SrvArea

ip = "127.0.0.1"
tcpport = 1104
rack = 1
slot = 1


class TestMetricsRegistry:
    def test_render_empty(self) -> None:
        registry = MetricsRegistry()
        text = registry.render()
        assert "snap7_operations_total" in text
        assert "snap7_client_connected" in text

    def test_record_counts_and_duration(self) -> None:
        registry = MetricsRegistry()
        registry.record("read_area", 0.5, error=False)
        registry.record("read_area", 1.5, error=True)
        text = registry.render()
        assert 'snap7_operations_total{operation="read_area"} 2' in text
        assert 'snap7_operation_errors_total{operation="read_area"} 1' in text
        assert 'snap7_operation_duration_seconds_sum{operation="read_area"} 2.0' in text

    def test_record_separates_operations(self) -> None:
        registry = MetricsRegistry()
        registry.record("read_area", 0.1, error=False)
        registry.record("write_area", 0.2, error=False)
        text = registry.render()
        assert 'snap7_operations_total{operation="read_area"} 1' in text
        assert 'snap7_operations_total{operation="write_area"} 1' in text

    def test_no_errors_line_when_none_recorded(self) -> None:
        registry = MetricsRegistry()
        registry.record("read_area", 0.1, error=False)
        text = registry.render()
        assert 'operation="read_area"}' in text
        assert "snap7_operation_errors_total{operation=" not in text

    def test_set_connected(self) -> None:
        registry = MetricsRegistry()
        registry.set_connected("10.0.0.1", True)
        text = registry.render()
        assert 'snap7_client_connected{plc="10.0.0.1"} 1' in text
        registry.set_connected("10.0.0.1", False)
        assert 'snap7_client_connected{plc="10.0.0.1"} 0' in registry.render()

    def test_label_escaping(self) -> None:
        registry = MetricsRegistry()
        registry.set_connected('plc"with"quotes', True)
        text = registry.render()
        assert 'plc="plc\\"with\\"quotes"' in text


class TestMetricsServer:
    @pytest.fixture
    def server(self) -> Iterator[MetricsServer]:
        registry = MetricsRegistry()
        srv = MetricsServer(registry, host="127.0.0.1", port=0)
        srv.start()
        yield srv
        srv.stop()

    def test_serves_metrics(self, server: MetricsServer) -> None:
        server._registry.record("db_read", 0.25, error=False)
        with urllib.request.urlopen(f"http://127.0.0.1:{server.port}/metrics", timeout=5) as resp:
            assert resp.status == 200
            assert resp.headers["Content-Type"] == "text/plain; version=0.0.4; charset=utf-8"
            body = resp.read().decode("utf-8")
        assert 'snap7_operations_total{operation="db_read"} 1' in body

    def test_unknown_path_is_404(self, server: MetricsServer) -> None:
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(f"http://127.0.0.1:{server.port}/", timeout=5)
        assert exc_info.value.code == 404

    def test_stop_is_idempotent(self, server: MetricsServer) -> None:
        server.stop()


@pytest.mark.client
class TestClientMetrics(unittest.TestCase):
    server: Server = None  # type: ignore

    @classmethod
    def setUpClass(cls) -> None:
        cls.server = Server()
        cls.server.register_area(SrvArea.DB, 1, bytearray(600))
        cls.server.start(tcp_port=tcpport)

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.server:
            cls.server.stop()
            cls.server.destroy()

    def setUp(self) -> None:
        self.registry = MetricsRegistry()
        self.client = Client(metrics=self.registry)
        self.client.connect(ip, rack, slot, tcpport)

    def tearDown(self) -> None:
        self.client.disconnect()
        self.client.destroy()

    def test_connect_sets_gauge(self) -> None:
        text = self.registry.render()
        assert f'snap7_client_connected{{plc="{ip}"}} 1' in text

    def test_disconnect_clears_gauge(self) -> None:
        self.client.disconnect()
        text = self.registry.render()
        assert f'snap7_client_connected{{plc="{ip}"}} 0' in text

    def test_db_read_records_read_area(self) -> None:
        self.client.db_read(db_number=1, start=0, size=4)
        text = self.registry.render()
        assert 'snap7_operations_total{operation="read_area"} 1' in text

    def test_db_write_records_write_area(self) -> None:
        self.client.db_write(db_number=1, start=0, data=bytearray(4))
        text = self.registry.render()
        assert 'snap7_operations_total{operation="write_area"} 1' in text

    def test_repeated_reads_accumulate(self) -> None:
        for _ in range(3):
            self.client.db_read(db_number=1, start=0, size=4)
        text = self.registry.render()
        assert 'snap7_operations_total{operation="read_area"} 3' in text

    def test_error_is_recorded(self) -> None:
        self.client.disconnect()
        with self.assertRaises(S7ConnectionError):
            self.client.read_area(Area.DB, 1, 0, 4)
        text = self.registry.render()
        assert 'snap7_operation_errors_total{operation="read_area"} 1' in text

    def test_client_without_metrics_is_unaffected(self) -> None:
        client = Client()
        client.connect(ip, rack, slot, tcpport)
        try:
            client.db_read(db_number=1, start=0, size=4)
        finally:
            client.disconnect()
            client.destroy()
