"""Tests for the s7 console entry point wrapper."""

import importlib.util
from typing import Any
from unittest.mock import patch

import pytest

from snap7 import _console


@pytest.mark.client
def test_missing_click_prints_install_hint(capsys: pytest.CaptureFixture[str]) -> None:
    real_find_spec = importlib.util.find_spec

    def find_spec(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "click":
            return None
        return real_find_spec(name, *args, **kwargs)

    with patch.object(importlib.util, "find_spec", find_spec):
        with pytest.raises(SystemExit) as exc_info:
            _console.main()

    assert exc_info.value.code == 1
    assert "pip install python-snap7[cli]" in capsys.readouterr().err


@pytest.mark.client
def test_runs_cli_when_click_installed() -> None:
    pytest.importorskip("click")
    with patch("sys.argv", ["s7", "--help"]):
        with pytest.raises(SystemExit) as exc_info:
            _console.main()
    assert exc_info.value.code == 0
