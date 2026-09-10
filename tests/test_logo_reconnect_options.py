"""LOGO connection options and explicit TSAP regression."""

from unittest.mock import MagicMock

import pytest

from snap7.logo import Logo


def test_logo_reconnect_preserves_options_and_tsaps(monkeypatch: pytest.MonkeyPatch) -> None:
    disconnected, reconnected = MagicMock(), MagicMock()
    client = Logo(
        auto_reconnect=True,
        max_retries=2,
        retry_delay=0,
        backoff_factor=3,
        max_delay=4,
        heartbeat_interval=9,
        max_requests_per_second=5,
        rate_limit_algorithm="token_bucket",
        rate_limit_behavior="raise",
        rate_limit_burst=2,
        on_disconnect=disconnected,
        on_reconnect=reconnected,
        legacy_option="ignored",
    )
    transport = MagicMock()
    monkeypatch.setattr("snap7.client.ISOTCPConnection", transport)
    monkeypatch.setattr(client, "_setup_communication", MagicMock())
    monkeypatch.setattr(client, "_start_heartbeat", MagicMock())
    client.connect("127.0.0.1", 0x1000, 0x2000, 1102)
    client.connected = False
    client._do_reconnect()
    transport.assert_called_with(host="127.0.0.1", port=1102, local_tsap=0x1000, remote_tsap=0x2000)
    disconnected.assert_called_once_with()
    reconnected.assert_called_once_with()
    assert client._auto_reconnect
    assert (client._max_retries, client._retry_delay, client._backoff_factor, client._max_delay) == (2, 0, 3, 4)
    assert client._heartbeat_interval == 9
    assert client._rate_limiter.rate == 5
    assert client._rate_limiter.algorithm == "token_bucket"
    assert client._rate_limiter.behavior == "raise"
    assert client._rate_limiter.burst_capacity == 2
    client.disconnect()
