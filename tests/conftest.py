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
        help="PLC IP address for e2e tests",
    )


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers",
        "e2e: mark test as end-to-end test requiring real PLC connection",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip e2e tests unless --e2e flag is provided."""
    if config.getoption("--e2e"):
        # --e2e given: run e2e tests
        return

    skip_e2e = pytest.mark.skip(reason="Need --e2e option to run end-to-end tests")
    for item in items:
        if "e2e" in item.keywords:
            item.add_marker(skip_e2e)
