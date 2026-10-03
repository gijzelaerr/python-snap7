"""Unit tests for real-PLC safety and reporting helpers (no hardware needed)."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from snap7.type import S7OrderCode
from tests.real_plc.reporting import RealPLCReport, sanitize_diagnostic, sanitize_junit
from tests.real_plc.support import (
    ClassicS7Adapter,
    PLCConfig,
    ScratchRestoreGuard,
    assert_canonical_fixture,
    canonical_fixture_bytes,
)


def test_canonical_fixture_validates_all_documented_types() -> None:
    data = canonical_fixture_bytes()
    assert len(data) == 37
    assert_canonical_fixture(data)


@pytest.mark.parametrize("failure", [None, AssertionError("scenario failed"), KeyboardInterrupt()])
def test_scratch_guard_restores_after_success_failure_or_interrupt(failure: BaseException | None) -> None:
    original = b"\x12\x34"
    adapter = MagicMock()
    adapter.read.side_effect = [original, original]
    guard = ScratchRestoreGuard(adapter, 2, 0, 2)

    if failure is None:
        guard.restore()
    else:
        with pytest.raises(type(failure)):
            try:
                raise failure
            finally:
                guard.restore()

    adapter.write.assert_called_once_with(2, 0, original)


def test_scratch_guard_detects_failed_restoration() -> None:
    adapter = MagicMock()
    adapter.read.side_effect = [b"old", b"bad"]
    guard = ScratchRestoreGuard(adapter, 2, 0, 3)
    with pytest.raises(AssertionError, match="restoration verification failed"):
        guard.restore()


def test_report_sanitizes_network_and_credentials(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("tests.real_plc.reporting._git_source", lambda: {"kind": "git", "commit": "a" * 40, "dirty": False})
    report = RealPLCReport()
    fake = SimpleNamespace(
        location=("tests/real_plc/test_acceptance.py", 1, "test"),
        when="call",
        passed=False,
        skipped=False,
        keywords={"smoke": 1, "real_plc": 1},
        longrepr="connect 192.168.10.2 password=hunter2 private_key=/tmp/key",
        nodeid="tests/real_plc/test_acceptance.py::test_failure",
        duration=0.1,
    )
    report.record(fake)
    target = tmp_path / "report.json"
    report.write(target, {"tester": "@tester", "model": "CPU 1511"})

    serialized = target.read_text()
    payload = json.loads(serialized)
    assert payload["schema_version"] == "1.0"
    assert payload["overall_result"] == "fail"
    assert "192.168.10.2" not in serialized
    assert "hunter2" not in serialized
    assert "/tmp/key" not in serialized
    assert serialized.count("<redacted") >= 3


def test_sanitize_diagnostic_caps_size() -> None:
    assert len(sanitize_diagnostic("x" * 20, limit=5)) == 5


def test_plc_config_repr_omits_host() -> None:
    config = PLCConfig(host="plc.example.internal", port=102, rack=0, slot=1, read_db=1, write_db=2)
    assert "plc.example.internal" not in repr(config)


def test_runtime_metadata_reports_order_code() -> None:
    adapter = ClassicS7Adapter(PLCConfig(host="unused", port=102, rack=0, slot=1, read_db=1, write_db=2))
    adapter.client = MagicMock()
    adapter.client.get_order_code.return_value = S7OrderCode(b"6ES7 212-1AE40-0XB0 ", 4, 7, 3)
    adapter.client.get_cpu_state.return_value = "S7CpuStatusRun"
    metadata = adapter.runtime_metadata()
    assert metadata["order_code"] == "6ES7 212-1AE40-0XB0 "
    assert metadata["firmware"] == "4.7.3"
    assert "order_code_status" not in metadata


def test_sanitize_junit_removes_host_details(tmp_path: Path) -> None:
    junit = tmp_path / "report.junit.xml"
    junit.write_text(
        '<testsuites><testsuite name="pytest" hostname="lab-bench-7" tests="1">'
        "<testcase><failure>PLCConfig(host='plc.example.internal') connect 192.168.10.2</failure></testcase>"
        "</testsuite></testsuites>",
        encoding="utf-8",
    )
    sanitize_junit(junit, ("plc.example.internal",))
    text = junit.read_text(encoding="utf-8")
    assert "lab-bench-7" not in text
    assert "hostname" not in text
    assert "plc.example.internal" not in text
    assert "192.168.10.2" not in text
    assert 'tests="1"' in text
