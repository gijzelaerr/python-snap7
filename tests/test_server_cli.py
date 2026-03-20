"""Tests for snap7.server.__main__ — CLI entrypoint."""

import pytest

click = pytest.importorskip("click")
from click.testing import CliRunner  # noqa: E402
from snap7.server.__main__ import main  # noqa: E402


class TestServerCLI:
    """Test the Click CLI entrypoint."""

    def test_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Start a S7 dummy server" in result.output

    def test_help_short(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["-h"])
        assert result.exit_code == 0
        assert "--port" in result.output

    def test_version(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        # Should print version string
        assert "version" in result.output.lower() or "." in result.output
