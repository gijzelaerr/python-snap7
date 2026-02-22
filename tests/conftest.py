"""Pytest configuration for python-snap7 tests."""

import pytest


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


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers",
        "e2e: mark test as end-to-end test requiring real PLC connection",
    )


def pytest_sessionstart(session: pytest.Session) -> None:
    """Propagate CLI options to test_client_e2e module globals."""
    config = session.config
    try:
        import tests.test_client_e2e as e2e

        e2e.PLC_IP = str(config.getoption("--plc-ip"))
        e2e.PLC_RACK = int(config.getoption("--plc-rack"))
        e2e.PLC_SLOT = int(config.getoption("--plc-slot"))
        e2e.PLC_PORT = int(config.getoption("--plc-port"))
        e2e.DB_READ_ONLY = int(config.getoption("--plc-db-read"))
        e2e.DB_READ_WRITE = int(config.getoption("--plc-db-write"))
    except Exception:
        pass  # Module may not be importable or options not available


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip e2e tests unless --e2e flag is provided."""
    if config.getoption("--e2e"):
        # --e2e given: run e2e tests
        return

    skip_e2e = pytest.mark.skip(reason="Need --e2e option to run end-to-end tests")
    for item in items:
        if "e2e" in item.keywords:
            item.add_marker(skip_e2e)


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
