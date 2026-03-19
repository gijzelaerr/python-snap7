"""Tests for the CLI tools."""

import unittest

import pytest

click = pytest.importorskip("click")
from click.testing import CliRunner  # noqa: E402

from snap7.cli import main  # noqa: E402
from snap7.server import Server  # noqa: E402
from snap7.type import SrvArea  # noqa: E402

ip = "127.0.0.1"
tcpport = 1102
rack = 1
slot = 1


@pytest.mark.client
class TestCLI(unittest.TestCase):
    server: Server = None  # type: ignore

    @classmethod
    def setUpClass(cls) -> None:
        cls.server = Server()
        cls.server.register_area(SrvArea.DB, 0, bytearray(600))
        cls.server.register_area(SrvArea.DB, 1, bytearray(600))
        cls.server.register_area(SrvArea.PA, 0, bytearray(100))
        cls.server.register_area(SrvArea.PE, 0, bytearray(100))
        cls.server.register_area(SrvArea.MK, 0, bytearray(100))
        cls.server.register_area(SrvArea.TM, 0, bytearray(100))
        cls.server.register_area(SrvArea.CT, 0, bytearray(100))
        cls.server.start(tcp_port=tcpport)

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.server:
            cls.server.stop()
            cls.server.destroy()

    def setUp(self) -> None:
        self.runner = CliRunner()

    def test_help(self) -> None:
        result = self.runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "python-snap7" in result.output

    def test_version(self) -> None:
        result = self.runner.invoke(main, ["--version"])
        assert result.exit_code == 0

    def test_read_bytes(self) -> None:
        result = self.runner.invoke(main, ["read", ip, "--db", "1", "--offset", "0", "--size", "4", "--port", str(tcpport)])
        assert result.exit_code == 0
        assert "0000" in result.output

    def test_read_bytes_missing_size(self) -> None:
        result = self.runner.invoke(main, ["read", ip, "--db", "1", "--offset", "0", "--port", str(tcpport)])
        assert result.exit_code != 0

    def test_read_int(self) -> None:
        result = self.runner.invoke(main, ["read", ip, "--db", "1", "--offset", "0", "--type", "int", "--port", str(tcpport)])
        assert result.exit_code == 0

    def test_read_real(self) -> None:
        result = self.runner.invoke(main, ["read", ip, "--db", "1", "--offset", "0", "--type", "real", "--port", str(tcpport)])
        assert result.exit_code == 0

    def test_read_bool(self) -> None:
        result = self.runner.invoke(
            main, ["read", ip, "--db", "1", "--offset", "0", "--type", "bool", "--bit", "0", "--port", str(tcpport)]
        )
        assert result.exit_code == 0
        assert result.output.strip() in ("True", "False")

    def test_write_int(self) -> None:
        result = self.runner.invoke(
            main, ["write", ip, "--db", "1", "--offset", "0", "--type", "int", "--value", "42", "--port", str(tcpport)]
        )
        assert result.exit_code == 0
        assert "OK" in result.output

        # Verify
        result = self.runner.invoke(main, ["read", ip, "--db", "1", "--offset", "0", "--type", "int", "--port", str(tcpport)])
        assert result.exit_code == 0
        assert "42" in result.output

    def test_write_real(self) -> None:
        result = self.runner.invoke(
            main, ["write", ip, "--db", "1", "--offset", "4", "--type", "real", "--value", "3.14", "--port", str(tcpport)]
        )
        assert result.exit_code == 0
        assert "OK" in result.output

    def test_write_bool(self) -> None:
        result = self.runner.invoke(
            main,
            [
                "write",
                ip,
                "--db",
                "1",
                "--offset",
                "10",
                "--type",
                "bool",
                "--value",
                "true",
                "--bit",
                "3",
                "--port",
                str(tcpport),
            ],
        )
        assert result.exit_code == 0
        assert "OK" in result.output

    def test_write_bytes_hex(self) -> None:
        result = self.runner.invoke(
            main, ["write", ip, "--db", "1", "--offset", "20", "--type", "bytes", "--value", "DEADBEEF", "--port", str(tcpport)]
        )
        assert result.exit_code == 0
        assert "OK" in result.output

    def test_dump(self) -> None:
        result = self.runner.invoke(main, ["dump", ip, "--db", "1", "--size", "32", "--port", str(tcpport)])
        assert result.exit_code == 0
        assert "DB1" in result.output
        assert "0000" in result.output

    def test_dump_bytes_format(self) -> None:
        result = self.runner.invoke(main, ["dump", ip, "--db", "1", "--size", "16", "--format", "bytes", "--port", str(tcpport)])
        assert result.exit_code == 0

    def test_info(self) -> None:
        result = self.runner.invoke(main, ["info", ip, "--port", str(tcpport)])
        assert result.exit_code == 0

    def test_read_connection_failure(self) -> None:
        result = self.runner.invoke(main, ["read", "192.0.2.1", "--db", "1", "--offset", "0", "--size", "4", "--port", "9999"])
        assert result.exit_code != 0
        assert "Connection failed" in result.output

    def test_server_help(self) -> None:
        result = self.runner.invoke(main, ["server", "--help"])
        assert result.exit_code == 0

    def test_write_dint(self) -> None:
        result = self.runner.invoke(
            main, ["write", ip, "--db", "1", "--offset", "30", "--type", "dint", "--value", "-100000", "--port", str(tcpport)]
        )
        assert result.exit_code == 0
        assert "OK" in result.output

    def test_write_word(self) -> None:
        result = self.runner.invoke(
            main, ["write", ip, "--db", "1", "--offset", "34", "--type", "word", "--value", "1234", "--port", str(tcpport)]
        )
        assert result.exit_code == 0
        assert "OK" in result.output

    def test_read_all_types(self) -> None:
        """Test that all type names are accepted without error."""
        for type_name in ["byte", "uint", "word", "dword", "udint", "lreal"]:
            result = self.runner.invoke(
                main, ["read", ip, "--db", "1", "--offset", "0", "--type", type_name, "--port", str(tcpport)]
            )
            assert result.exit_code == 0, f"Failed for type {type_name}: {result.output}"
