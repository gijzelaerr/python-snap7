"""Fresh-session orchestration for legacy family-only key identifiers."""

from unittest.mock import MagicMock, patch

import pytest

from snap7.error import S7ConnectionError
from s7commplus.client import S7CommPlusClient, _LEGACY_KEY_CACHE
from s7commplus.connection import FamilyOnlyFingerprintError, S7CommPlusConnection, SessionKeyCandidateRejectedError
from s7commplus.protocol import DataType, ProtocolVersion
from s7commplus.session_auth import KeyFamily, get_public_key


@pytest.fixture(autouse=True)
def clear_key_cache() -> None:
    _LEGACY_KEY_CACHE.clear()


def _connection_factory(connect_effects):  # type: ignore[no-untyped-def]
    instances: list[MagicMock] = []

    def factory(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        connection = MagicMock(tls_active=False, requires_substreamed=False)
        connection.connect.side_effect = connect_effects
        instances.append(connection)
        return connection

    return factory, instances


def test_complete_fingerprint_path_does_not_probe() -> None:
    factory, instances = _connection_factory(None)
    with patch("s7commplus.client.S7CommPlusConnection", side_effect=factory):
        S7CommPlusClient().connect("plc")

    assert len(instances) == 1
    assert instances[0].connect.call_args.kwargs["_session_key_fingerprint"] is None


def test_family_only_identifier_tries_same_family_candidates_on_fresh_sessions() -> None:
    attempts: list[str | None] = []

    def connect_effect(**kwargs):  # type: ignore[no-untyped-def]
        fingerprint = kwargs["_session_key_fingerprint"]
        attempts.append(fingerprint)
        if fingerprint is None:
            raise FamilyOnlyFingerprintError(KeyFamily.S7_1200)
        if fingerprint != "01:GOOD":
            raise SessionKeyCandidateRejectedError("rejected")

    factory, instances = _connection_factory(connect_effect)
    with (
        patch("s7commplus.client.S7CommPlusConnection", side_effect=factory),
        patch("s7commplus.session_auth.keys.fingerprints_for_family", return_value=("01:BAD", "01:GOOD")),
    ):
        S7CommPlusClient().connect("plc")

    assert attempts == [None, "01:BAD", "01:GOOD"]
    assert len(instances) == 3
    assert _LEGACY_KEY_CACHE[("plc", 102)] == "01:GOOD"


def test_cached_success_is_used_on_the_first_session() -> None:
    _LEGACY_KEY_CACHE[("plc", 102)] = "01:CACHED"
    attempts: list[str | None] = []

    def connect_effect(**kwargs):  # type: ignore[no-untyped-def]
        attempts.append(kwargs["_session_key_fingerprint"])

    factory, instances = _connection_factory(connect_effect)
    with patch("s7commplus.client.S7CommPlusConnection", side_effect=factory):
        S7CommPlusClient().connect("plc")

    assert attempts == ["01:CACHED"]
    assert len(instances) == 1


def test_disabled_fallback_fails_without_probing() -> None:
    def connect_effect(**_kwargs):  # type: ignore[no-untyped-def]
        raise FamilyOnlyFingerprintError(KeyFamily.S7_1500)

    factory, instances = _connection_factory(connect_effect)
    with (
        patch("s7commplus.client.S7CommPlusConnection", side_effect=factory),
        patch("s7commplus.session_auth.keys.fingerprints_for_family") as candidates,
        pytest.raises(S7ConnectionError, match="fallback is disabled"),
    ):
        S7CommPlusClient().connect("plc", allow_legacy_key_fallback=False)

    assert len(instances) == 1
    candidates.assert_not_called()


def test_exhausted_candidates_fail_clearly_and_each_uses_a_fresh_session() -> None:
    def connect_effect(**kwargs):  # type: ignore[no-untyped-def]
        if kwargs["_session_key_fingerprint"] is None:
            raise FamilyOnlyFingerprintError(KeyFamily.S7_1200)
        raise SessionKeyCandidateRejectedError("rejected")

    factory, instances = _connection_factory(connect_effect)
    with (
        patch("s7commplus.client.S7CommPlusConnection", side_effect=factory),
        patch("s7commplus.session_auth.keys.fingerprints_for_family", return_value=("01:A", "01:B")),
        pytest.raises(S7ConnectionError, match="rejected all 2"),
    ):
        S7CommPlusClient().connect("plc")

    assert len(instances) == 3
    assert all(connection.connect.call_count == 1 for connection in instances)


def test_low_level_connection_reports_family_before_setup() -> None:
    connection = S7CommPlusConnection("plc")
    connection._iso_conn.connect = MagicMock()
    connection._iso_conn.disconnect = MagicMock()
    connection._init_ssl = MagicMock()

    def create_session() -> None:
        connection._protocol_version = ProtocolVersion.V1
        connection._session_id = 7
        connection._server_session_version = bytes([0, DataType.UDINT, 1])
        connection._public_key_fingerprint = "01"

    connection._create_session = MagicMock(side_effect=create_session)
    connection._setup_session = MagicMock(return_value=True)

    with pytest.raises(FamilyOnlyFingerprintError) as error:
        connection.connect()

    assert error.value.family is KeyFamily.S7_1200
    connection._setup_session.assert_not_called()


def test_low_level_connection_rejects_unknown_family_clearly() -> None:
    connection = S7CommPlusConnection("plc")
    connection._iso_conn.connect = MagicMock()
    connection._iso_conn.disconnect = MagicMock()
    connection._init_ssl = MagicMock()

    def create_session() -> None:
        connection._protocol_version = ProtocolVersion.V1
        connection._session_id = 7
        connection._server_session_version = bytes([0, DataType.UDINT, 1])
        connection._public_key_fingerprint = "02"

    connection._create_session = MagicMock(side_effect=create_session)
    connection._setup_session = MagicMock(return_value=True)

    with pytest.raises(S7ConnectionError, match="Unsupported public-key family 0x02"):
        connection.connect()

    connection._setup_session.assert_not_called()


def test_explicit_candidate_selects_its_public_key() -> None:
    connection = S7CommPlusConnection("plc")
    connection._protocol_version = ProtocolVersion.V1
    connection._public_key_fingerprint = "01"
    connection._session_key_fingerprint_override = "01:BD426B091F08731A"
    connection._session_challenge = bytes(range(20))
    generated = (bytes(180), bytes(24))

    with patch("s7commplus.session_auth.legacy_auth.authenticate_real_plc", return_value=generated) as authenticate:
        assert connection._try_session_key_auth() == generated

    assert authenticate.call_args.args[1] == get_public_key("01:BD426B091F08731A")
    assert authenticate.call_args.args[2] is KeyFamily.S7_1200


def test_setup_disconnect_rejects_candidate_and_cleans_session() -> None:
    connection = S7CommPlusConnection("plc")
    connection._iso_conn.connect = MagicMock()
    connection._iso_conn.disconnect = MagicMock()
    connection._init_ssl = MagicMock()

    def create_session() -> None:
        connection._protocol_version = ProtocolVersion.V1
        connection._session_id = 7
        connection._server_session_version = bytes([0, DataType.UDINT, 1])
        connection._public_key_fingerprint = "01"

    connection._create_session = MagicMock(side_effect=create_session)
    connection._setup_session = MagicMock(side_effect=OSError("reset by PLC"))

    with pytest.raises(SessionKeyCandidateRejectedError, match="BD426B091F08731A") as error:
        connection.connect(_session_key_fingerprint="01:BD426B091F08731A")

    assert isinstance(error.value.__cause__, OSError)
    assert not connection.connected
    assert connection.session_id == 0


def test_complete_fingerprint_ignores_fallback_override() -> None:
    connection = S7CommPlusConnection("plc")
    connection._iso_conn.connect = MagicMock()
    connection._iso_conn.disconnect = MagicMock()
    connection._init_ssl = MagicMock()

    def create_session() -> None:
        connection._protocol_version = ProtocolVersion.V1
        connection._session_id = 7
        connection._server_session_version = bytes([0, DataType.UDINT, 1])
        connection._public_key_fingerprint = "01:BD426B091F08731A"

    connection._create_session = MagicMock(side_effect=create_session)
    connection._setup_session = MagicMock(return_value=True)
    connection._get_effective_protection_level = MagicMock(return_value=None)

    connection.connect(_session_key_fingerprint="01:A95850575DF7B3DE")

    assert connection.connected
    assert connection._session_key_fingerprint_override is None
