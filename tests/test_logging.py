"""Tests for structured logging."""

import json
import logging

import pytest

from snap7.log import PLCLoggerAdapter, OperationLogger, JSONFormatter


class TestPLCLoggerAdapter:
    def test_prefix_added(self, caplog: pytest.LogCaptureFixture) -> None:
        base = logging.getLogger("test.adapter")
        adapter = PLCLoggerAdapter(base, plc_host="10.0.0.1", rack=0, slot=1)
        with caplog.at_level(logging.INFO, logger="test.adapter"):
            adapter.info("Connected")
        assert "[10.0.0.1 R0/S1] Connected" in caplog.text

    def test_no_prefix_without_host(self, caplog: pytest.LogCaptureFixture) -> None:
        base = logging.getLogger("test.nohost")
        adapter = PLCLoggerAdapter(base)
        with caplog.at_level(logging.INFO, logger="test.nohost"):
            adapter.info("Init")
        assert "Init" in caplog.text
        assert "[" not in caplog.text

    def test_update_context(self) -> None:
        base = logging.getLogger("test.update")
        adapter = PLCLoggerAdapter(base)
        assert adapter._prefix == ""
        adapter.update_context(plc_host="192.168.1.10", rack=2, slot=3)
        assert adapter._prefix == "[192.168.1.10 R2/S3]"

    def test_update_context_partial(self) -> None:
        base = logging.getLogger("test.partial")
        adapter = PLCLoggerAdapter(base, plc_host="1.2.3.4", rack=0, slot=1)
        adapter.update_context(protocol="s7commplus")
        assert adapter.extra is not None
        assert adapter.extra.get("plc_protocol") == "s7commplus"
        # Host/rack/slot unchanged
        assert adapter._prefix == "[1.2.3.4 R0/S1]"


class TestOperationLogger:
    def test_logs_timing(self, caplog: pytest.LogCaptureFixture) -> None:
        base = logging.getLogger("test.oplog")
        with caplog.at_level(logging.DEBUG, logger="test.oplog"):
            with OperationLogger(base, "db_read", db=1, start=0, size=4):
                pass
        assert "db_read" in caplog.text
        assert "db=1" in caplog.text
        assert "ms)" in caplog.text

    def test_works_with_adapter(self, caplog: pytest.LogCaptureFixture) -> None:
        base = logging.getLogger("test.oplog_adapter")
        adapter = PLCLoggerAdapter(base, plc_host="10.0.0.1", rack=0, slot=1)
        with caplog.at_level(logging.DEBUG, logger="test.oplog_adapter"):
            with OperationLogger(adapter, "db_write", db=2, start=10, size=8):
                pass
        assert "db_write" in caplog.text


class TestJSONFormatter:
    def test_basic_format(self) -> None:
        handler = logging.StreamHandler()
        formatter = JSONFormatter()
        handler.setFormatter(formatter)

        record = logging.LogRecord(
            name="snap7.client",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Connected",
            args=None,
            exc_info=None,
        )
        output = formatter.format(record)
        data = json.loads(output)
        assert data["level"] == "INFO"
        assert data["msg"] == "Connected"
        assert data["logger"] == "snap7.client"

    def test_plc_context_included(self) -> None:
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="snap7.client",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Read OK",
            args=None,
            exc_info=None,
        )
        record.plc_host = "192.168.1.10"
        record.plc_rack = 0
        record.plc_slot = 1
        output = formatter.format(record)
        data = json.loads(output)
        assert data["plc_host"] == "192.168.1.10"
        assert data["plc_slot"] == 1
