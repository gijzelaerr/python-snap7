"""Request rate limiting for synchronous and asynchronous S7 clients."""

import asyncio
import math
import threading
import time
from collections.abc import Callable
from typing import Literal

from .error import S7RateLimitError

RateLimitAlgorithm = Literal["fixed", "token_bucket"]
RateLimitBehavior = Literal["block", "raise", "drop"]


class RequestRateLimiter:
    """Thread-safe per-client request rate limiter.

    ``fixed`` spaces requests evenly. ``token_bucket`` permits bursts up to
    ``burst_capacity`` and then refills continuously at the configured rate.
    A rate of zero disables limiting.
    """

    def __init__(
        self,
        max_requests_per_second: float = 0,
        *,
        algorithm: RateLimitAlgorithm = "fixed",
        behavior: RateLimitBehavior = "block",
        burst_capacity: int | None = None,
        _clock: Callable[[], float] = time.monotonic,
        _sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if not math.isfinite(max_requests_per_second) or max_requests_per_second < 0:
            raise ValueError("max_requests_per_second must be a finite non-negative number")
        if algorithm not in ("fixed", "token_bucket"):
            raise ValueError("rate_limit_algorithm must be 'fixed' or 'token_bucket'")
        if behavior not in ("block", "raise", "drop"):
            raise ValueError("rate_limit_behavior must be 'block', 'raise', or 'drop'")
        if burst_capacity is not None and burst_capacity < 1:
            raise ValueError("rate_limit_burst must be at least 1")

        self.rate = float(max_requests_per_second)
        self.algorithm = algorithm
        self.behavior = behavior
        self.burst_capacity = burst_capacity or max(1, math.ceil(self.rate))
        self._clock = _clock
        self._sleep = _sleep
        self._lock = threading.Lock()

        now = self._clock()
        self._next_request = now
        self._tokens = float(self.burst_capacity)
        self._last_refill = now

    @property
    def enabled(self) -> bool:
        """Whether rate limiting is active."""
        return self.rate > 0

    def _reserve(self) -> float:
        """Reserve one request and return the required delay in seconds."""
        if not self.enabled:
            return 0.0

        with self._lock:
            now = self._clock()
            if self.algorithm == "fixed":
                delay = max(0.0, self._next_request - now)
                if delay > 0 and self.behavior != "block":
                    self._reject()
                slot = now + delay
                self._next_request = slot + (1.0 / self.rate)
                return delay

            # Refill only through the current time. A future _last_refill
            # represents tokens already reserved by blocking callers.
            if now > self._last_refill:
                elapsed = now - self._last_refill
                self._tokens = min(float(self.burst_capacity), self._tokens + elapsed * self.rate)
                self._last_refill = now

            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return 0.0

            queued_delay = max(0.0, self._last_refill - now)
            delay = queued_delay + ((1.0 - self._tokens) / self.rate)
            if self.behavior != "block":
                self._reject()
            self._tokens = 0.0
            self._last_refill = now + delay
            return delay

    def _reject(self) -> None:
        dropped = self.behavior == "drop"
        action = "dropped" if dropped else "rejected"
        raise S7RateLimitError(f"Request {action}: rate limit of {self.rate:g} requests/second exceeded", dropped=dropped)

    def acquire(self) -> None:
        """Wait for or reserve permission to send one synchronous request."""
        delay = self._reserve()
        if delay > 0:
            self._sleep(delay)

    async def acquire_async(self) -> None:
        """Wait for or reserve permission to send one asynchronous request."""
        delay = self._reserve()
        if delay > 0:
            await asyncio.sleep(delay)
