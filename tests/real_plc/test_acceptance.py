"""Executable pytest-bdd bindings for the versioned real-PLC specification."""

from __future__ import annotations

from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.real_plc.support import (
    DB_SIZE,
    WRITE_VALUES,
    PLCAdapter,
    PLCConfig,
    ScratchRestoreGuard,
    assert_canonical_fixture,
    canonical_fixture_bytes,
    make_adapter,
)

pytestmark = [pytest.mark.e2e, pytest.mark.real_plc]
scenarios("../features/real_plc")


@pytest.fixture
def plc_config(request: pytest.FixtureRequest) -> PLCConfig:
    return PLCConfig(
        host=request.config.getoption("--plc-ip"),
        port=request.config.getoption("--plc-port"),
        rack=request.config.getoption("--plc-rack"),
        slot=request.config.getoption("--plc-slot"),
        read_db=request.config.getoption("--plc-db-read"),
        write_db=request.config.getoption("--plc-db-write"),
    )


@pytest.fixture
def scenario_state() -> dict[str, Any]:
    return {}


@given("I am using a dedicated test PLC")
def dedicated_plc() -> None:
    """The runbook makes this an explicit operator precondition."""


@given("the test configuration contains no secrets in reportable fields")
def reportable_fields_are_safe(request: pytest.FixtureRequest) -> None:
    sensitive_fragments = ("password", "secret", "private key", "plc ip", "hostname")
    values = (
        request.config.getoption("--plc-family"),
        request.config.getoption("--plc-model"),
        request.config.getoption("--plc-order-code"),
        request.config.getoption("--plc-firmware"),
        request.config.getoption("--plc-security-mode"),
        request.config.getoption("--plc-tia-configuration"),
    )
    assert not any(fragment in value.lower() for value in values for fragment in sensitive_fragments)


@given(parsers.parse('the client uses the "{protocol}" protocol path'), target_fixture="plc_adapter")
def selected_adapter(protocol: str, plc_config: PLCConfig, request: pytest.FixtureRequest) -> PLCAdapter:
    selected = request.config.getoption("--plc-protocol")
    if protocol != selected:
        pytest.skip(f"CAPABILITY_PROTOCOL_NOT_SELECTED: selected {selected}")
    adapter = make_adapter(protocol, plc_config)

    def disconnect() -> None:
        if adapter.is_connected():
            adapter.disconnect()

    request.addfinalizer(disconnect)
    return adapter


def _ensure_connected(adapter: PLCAdapter) -> None:
    if not adapter.is_connected():
        adapter.connect()


@when("I connect to the configured PLC")
@given("I am connected to the PLC")
def connect(plc_adapter: PLCAdapter) -> None:
    _ensure_connected(plc_adapter)


@then("the client reports that it is connected")
def reports_connected(plc_adapter: PLCAdapter) -> None:
    assert plc_adapter.is_connected()


@then("the negotiated protocol and security mode are recorded")
@then("the PLC identity and CPU state are recorded when available")
def record_runtime_metadata(plc_adapter: PLCAdapter, request: pytest.FixtureRequest) -> None:
    request.config._real_plc_report.runtime_metadata.update(plc_adapter.runtime_metadata())


@when("I disconnect")
def disconnect(plc_adapter: PLCAdapter) -> None:
    plc_adapter.disconnect()


@then("the client reports that it is disconnected")
def reports_disconnected(plc_adapter: PLCAdapter) -> None:
    assert not plc_adapter.is_connected()


@given("the read-only test DB has the documented canonical layout")
def canonical_layout(plc_adapter: PLCAdapter, plc_config: PLCConfig) -> None:
    _ensure_connected(plc_adapter)
    assert_canonical_fixture(plc_adapter.read(plc_config.read_db, 0, DB_SIZE))


@when("I read the complete fixture DB")
def read_complete_fixture(plc_adapter: PLCAdapter, plc_config: PLCConfig, scenario_state: dict[str, Any]) -> None:
    scenario_state["complete"] = plc_adapter.read(plc_config.read_db, 0, DB_SIZE)


@then("INT, REAL, BYTE, WORD, DWORD, DINT, CHAR and BOOL values match the fixture")
def complete_values_match(scenario_state: dict[str, Any]) -> None:
    assert_canonical_fixture(scenario_state["complete"])


@then("individual reads return the same values as the complete-block read")
def individual_values_match(plc_adapter: PLCAdapter, plc_config: PLCConfig, scenario_state: dict[str, Any]) -> None:
    complete = scenario_state["complete"]
    for offset, size in ((0, 2), (4, 4), (12, 1), (14, 2), (18, 4), (26, 4), (34, 1), (36, 1)):
        assert plc_adapter.read(plc_config.read_db, offset, size) == complete[offset : offset + size]


@when("I read values of different sizes in one multi-variable request")
def read_multiple(plc_adapter: PLCAdapter, plc_config: PLCConfig, scenario_state: dict[str, Any]) -> None:
    regions = ((0, 2), (4, 4), (12, 1), (18, 4), (34, 1), (36, 1))
    scenario_state["multi_regions"] = regions
    scenario_state["multi_values"] = plc_adapter.read_multi(plc_config.read_db, regions)


@then("every value and result code matches the fixture")
def multiple_values_match(scenario_state: dict[str, Any]) -> None:
    expected = canonical_fixture_bytes()
    assert scenario_state["multi_values"] == [
        expected[offset : offset + size] for offset, size in scenario_state["multi_regions"]
    ]


@given("writing has been explicitly enabled")
def write_is_enabled(request: pytest.FixtureRequest) -> None:
    assert request.config.getoption("--allow-plc-write")


@given("I have a dedicated scratch DB")
def scratch_db(plc_adapter: PLCAdapter, plc_config: PLCConfig) -> None:
    _ensure_connected(plc_adapter)
    if plc_config.read_db == plc_config.write_db:
        pytest.fail("scratch DB must differ from the read-only fixture DB")


@given(parsers.parse("the original bytes for {value_type} have been saved"))
def save_original(
    value_type: str,
    plc_adapter: PLCAdapter,
    plc_config: PLCConfig,
    scenario_state: dict[str, Any],
    request: pytest.FixtureRequest,
) -> None:
    offset, encoded, _, _ = WRITE_VALUES[value_type]
    guard = ScratchRestoreGuard(plc_adapter, plc_config.write_db, offset, len(encoded))
    scenario_state["guard"] = guard
    scenario_state["value_type"] = value_type
    request.addfinalizer(guard.restore)


@when(parsers.parse("I write a valid {value_type} value"))
def write_value(value_type: str, plc_adapter: PLCAdapter, plc_config: PLCConfig) -> None:
    offset, encoded, _, _ = WRITE_VALUES[value_type]
    plc_adapter.write(plc_config.write_db, offset, encoded)


@then("reading the address returns the written value")
def value_round_trips(plc_adapter: PLCAdapter, plc_config: PLCConfig, scenario_state: dict[str, Any]) -> None:
    offset, encoded, decoder, expected = WRITE_VALUES[scenario_state["value_type"]]
    actual = plc_adapter.read(plc_config.write_db, offset, len(encoded))
    assert decoder(actual) == expected


@then("the original bytes are restored and verified")
def original_is_restored(scenario_state: dict[str, Any]) -> None:
    scenario_state["guard"].restore()


@given("I connected to and disconnected from the PLC")
def connected_then_disconnected(plc_adapter: PLCAdapter) -> None:
    plc_adapter.connect()
    plc_adapter.disconnect()


@when("I reconnect with the same configuration")
def reconnect(plc_adapter: PLCAdapter) -> None:
    plc_adapter.connect()


@then("a known read succeeds")
def known_read_succeeds(plc_adapter: PLCAdapter, plc_config: PLCConfig) -> None:
    assert plc_adapter.read(plc_config.read_db, 0, 2) == canonical_fixture_bytes()[:2]


@when("I read the canonical fixture repeatedly")
def read_repeatedly(plc_adapter: PLCAdapter, plc_config: PLCConfig, scenario_state: dict[str, Any]) -> None:
    scenario_state["repeated"] = [plc_adapter.read(plc_config.read_db, 0, DB_SIZE) for _ in range(10)]


@then("every read succeeds with the expected value")
def repeated_reads_match(scenario_state: dict[str, Any]) -> None:
    for data in scenario_state["repeated"]:
        assert_canonical_fixture(data)


@then("disconnect completes cleanly")
def final_disconnect(plc_adapter: PLCAdapter) -> None:
    plc_adapter.disconnect()
    assert not plc_adapter.is_connected()
