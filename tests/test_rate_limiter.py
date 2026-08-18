"""Tests for per-client request rate limiting."""

from unittest.mock import AsyncMock, Mock

import pytest

from snap7.async_client import AsyncClient
from snap7.client import Client
from snap7.error import S7RateLimitError
from snap7.rate_limiter import RequestRateLimiter


class FakeTime:
    def __init__(self) -> None:
        self.now = 0.0
        self.delays: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, delay: float) -> None:
        self.delays.append(delay)
        self.now += delay


def test_fixed_rate_blocks_between_requests() -> None:
    fake = FakeTime()
    limiter = RequestRateLimiter(2, _clock=fake.monotonic, _sleep=fake.sleep)

    limiter.acquire()
    limiter.acquire()
    limiter.acquire()

    assert fake.delays == [0.5, 0.5]


def test_fixed_rate_can_reject_without_waiting() -> None:
    fake = FakeTime()
    limiter = RequestRateLimiter(10, behavior="raise", _clock=fake.monotonic)

    limiter.acquire()
    with pytest.raises(S7RateLimitError) as exc_info:
        limiter.acquire()

    assert not exc_info.value.dropped


def test_drop_marks_request_as_dropped() -> None:
    fake = FakeTime()
    limiter = RequestRateLimiter(10, behavior="drop", _clock=fake.monotonic)

    limiter.acquire()
    with pytest.raises(S7RateLimitError) as exc_info:
        limiter.acquire()

    assert exc_info.value.dropped


def test_token_bucket_allows_configured_burst() -> None:
    fake = FakeTime()
    limiter = RequestRateLimiter(
        2,
        algorithm="token_bucket",
        burst_capacity=2,
        _clock=fake.monotonic,
        _sleep=fake.sleep,
    )

    limiter.acquire()
    limiter.acquire()
    limiter.acquire()

    assert fake.delays == [0.5]


def test_disabled_limiter_never_waits() -> None:
    fake = FakeTime()
    limiter = RequestRateLimiter(0, _clock=fake.monotonic, _sleep=fake.sleep)

    for _ in range(100):
        limiter.acquire()

    assert not fake.delays


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"max_requests_per_second": -1}, "finite non-negative"),
        ({"algorithm": "sliding"}, "rate_limit_algorithm"),
        ({"behavior": "wait"}, "rate_limit_behavior"),
        ({"burst_capacity": 0}, "rate_limit_burst"),
    ],
)
def test_invalid_configuration_rejected(kwargs: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        RequestRateLimiter(**kwargs)  # type: ignore[arg-type]


def test_sync_client_limits_each_outbound_pdu() -> None:
    client = Client(max_requests_per_second=1)
    client._rate_limiter.acquire = Mock()
    connection = Mock()

    client._send_data(connection, b"request")

    client._rate_limiter.acquire.assert_called_once_with()
    connection.send_data.assert_called_once_with(b"request")


@pytest.mark.asyncio
async def test_async_limiter_waits_without_blocking(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeTime()
    limiter = RequestRateLimiter(4, _clock=fake.monotonic)

    async def advance(delay: float) -> None:
        fake.sleep(delay)

    monkeypatch.setattr("snap7.rate_limiter.asyncio.sleep", advance)
    await limiter.acquire_async()
    await limiter.acquire_async()

    assert fake.delays == [0.25]


@pytest.mark.asyncio
async def test_async_client_limits_each_outbound_pdu() -> None:
    client = AsyncClient(max_requests_per_second=1)
    client._rate_limiter.acquire_async = AsyncMock()
    connection = AsyncMock()

    await client._send_data(connection, b"request")

    client._rate_limiter.acquire_async.assert_awaited_once_with()
    connection.send_data.assert_awaited_once_with(b"request")
