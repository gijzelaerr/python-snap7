"""Unit tests for real-PLC safety and reporting helpers (no hardware needed)."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from tests.real_plc.reporting import RealPLCReport, sanitize_diagnostic
from tests.real_plc.support import ScratchRestoreGuard, assert_canonical_fixture, canonical_fixture_bytes


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
