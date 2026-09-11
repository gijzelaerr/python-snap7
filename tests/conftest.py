"""Pytest configuration for python-snap7 tests."""

import socket
import sys
from pathlib import Path
from typing import Any

import pytest

from tests.real_plc.reporting import RealPLCReport, report_metadata

_REAL_PLC_REPORT = RealPLCReport()


def get_free_tcp_port() -> int:
    """Return a TCP port that is free *right now* on 127.0.0.1.

    Bind a throwaway socket to port 0, let the OS pick an ephemeral port,
    read it back, then close the socket. Preferred over ``random.randint``
    for test servers: the OS guarantees the port is currently unused, and
    the collision window is vanishingly small (the ephemeral range is tens
    of thousands of ports wide) instead of 1-in-5000 from a random pick
    that drifts toward collision under pytest-xdist or repeated reruns.

    There is a tiny TOCTOU race between closing this socket and the test
    server binding, but the pool is large enough that it is not observed
    in practice. Servers that set ``SO_REUSEADDR`` tolerate lingering
    TIME_WAIT sockets too.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        port: int = s.getsockname()[1]
        return port


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add command line options for e2e tests."""
    parser.addoption(
        "--e2e",
        action="store_true",
        default=False,
        help="Run end-to-end tests against a real PLC",
    )
    parser.addoption(
        "--plc-ip",
        action="store",
        default="10.10.10.100",
        help="PLC IP address for e2e tests (default: 10.10.10.100)",
    )
    parser.addoption(
        "--plc-rack",
        action="store",
        type=int,
        default=0,
        help="PLC rack number for e2e tests (default: 0)",
    )
    parser.addoption(
        "--plc-slot",
        action="store",
        type=int,
        default=1,
        help="PLC slot number for e2e tests (default: 1)",
    )
    parser.addoption(
        "--plc-port",
        action="store",
        type=int,
        default=102,
        help="PLC TCP port for e2e tests (default: 102)",
    )
    parser.addoption(
        "--plc-db-read",
        action="store",
        type=int,
        default=1,
        help="Read-only DB number for e2e tests (default: 1)",
    )
    parser.addoption(
        "--plc-db-write",
        action="store",
        type=int,
        default=2,
        help="Read-write DB number for e2e tests (default: 2)",
    )
    parser.addoption(
        "--allow-plc-write",
        action="store_true",
        default=False,
        help="Allow tests that modify and restore the dedicated scratch DB",
    )
    parser.addoption(
        "--allow-plc-admin",
        action="store_true",
        default=False,
        help="Allow disruptive administrative tests on a dedicated non-production PLC",
    )
    parser.addoption("--plc-protocol", choices=("legacy_s7", "s7commplus"), default="legacy_s7")
    parser.addoption("--plc-report-json", default="", help="Write a sanitized real-PLC JSON report")
    parser.addoption("--tester", default="", help="GitHub handle of the volunteer running the test")
    parser.addoption("--plc-family", default="", help="Reportable PLC family, such as S7-1500")
    parser.addoption("--plc-model", default="", help="Reportable PLC model")
    parser.addoption("--plc-order-code", default="", help="Reportable PLC order code")
    parser.addoption("--plc-firmware", default="", help="Reportable PLC firmware version")
    parser.addoption("--plc-security-mode", default="", help="Reportable access/TLS mode; never enter credentials")
    parser.addoption("--plc-tia-configuration", default="", help="Reportable TIA settings, without site details")


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers",
        "e2e: mark test as end-to-end test requiring real PLC connection",
    )
    global _REAL_PLC_REPORT
    _REAL_PLC_REPORT = RealPLCReport()
    config._real_plc_report = _REAL_PLC_REPORT


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Propagate CLI options and skip e2e tests unless --e2e flag is provided."""
    # Propagate CLI options to e2e test module globals
    for mod_name in [
        "tests.test_client_e2e",
        "test_client_e2e",
        "tests.test_s7_e2e",
        "test_s7_e2e",
    ]:
        e2e = sys.modules.get(mod_name)
        if e2e is not None:
            e2e.PLC_IP = str(config.getoption("--plc-ip"))
            e2e.PLC_RACK = int(config.getoption("--plc-rack"))
            e2e.PLC_SLOT = int(config.getoption("--plc-slot"))
            e2e.PLC_PORT = int(config.getoption("--plc-port"))
            e2e.DB_READ_ONLY = int(config.getoption("--plc-db-read"))
            e2e.DB_READ_WRITE = int(config.getoption("--plc-db-write"))

    for item in items:
        if "e2e" in item.keywords and not config.getoption("--e2e"):
            item.add_marker(pytest.mark.skip(reason="Need --e2e option to run end-to-end tests"))
        if ("write" in item.keywords or "plc_write" in item.keywords) and not config.getoption("--allow-plc-write"):
            item.add_marker(pytest.mark.skip(reason="WRITE_OPT_IN_REQUIRED: pass --allow-plc-write"))
        if "administrative" in item.keywords and not config.getoption("--allow-plc-admin"):
            item.add_marker(pytest.mark.skip(reason="ADMIN_OPT_IN_REQUIRED: pass --allow-plc-admin"))


def pytest_runtest_logreport(report: Any) -> None:
    """Capture final BDD outcomes without recording connection secrets."""
    _REAL_PLC_REPORT.record(report)


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Write the optional structured report after all scenario outcomes are known."""
    del exitstatus
    report_path = session.config.getoption("--plc-report-json")
    if report_path:
        session.config._real_plc_report.write(Path(report_path), report_metadata(session.config))


@pytest.fixture(scope="session")
def plc_ip(request: pytest.FixtureRequest) -> str:
    """Get PLC IP address from command line."""
    return str(request.config.getoption("--plc-ip"))


@pytest.fixture(scope="session")
def plc_rack(request: pytest.FixtureRequest) -> int:
    """Get PLC rack number from command line."""
    return int(request.config.getoption("--plc-rack"))


@pytest.fixture(scope="session")
def plc_slot(request: pytest.FixtureRequest) -> int:
    """Get PLC slot number from command line."""
    return int(request.config.getoption("--plc-slot"))


@pytest.fixture(scope="session")
def plc_port(request: pytest.FixtureRequest) -> int:
    """Get PLC TCP port from command line."""
    return int(request.config.getoption("--plc-port"))


@pytest.fixture(scope="session")
def plc_db_read(request: pytest.FixtureRequest) -> int:
    """Get read-only DB number from command line."""
    return int(request.config.getoption("--plc-db-read"))


@pytest.fixture(scope="session")
def plc_db_write(request: pytest.FixtureRequest) -> int:
    """Get read-write DB number from command line."""
    return int(request.config.getoption("--plc-db-write"))
