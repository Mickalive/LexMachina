"""Deterministic request pacing + request budget.

The OpenCaseLaw public API documents a soft pace of <=5 req/s. The adapter
enforces that with a monotonic-clock minimum-interval limiter. The clock and
sleep functions are injectable so tests can assert pacing without sleeping.
"""
from __future__ import annotations

import time
from typing import Callable, Optional

from .errors import OCLBudgetExceeded


class RateLimiter:
    """Minimum-interval limiter (``1 / rps`` seconds between call starts)."""

    def __init__(
        self,
        rps: float = 4.0,
        time_fn: Callable[[], float] = time.monotonic,
        sleep_fn: Callable[[float], None] = time.sleep,
    ):
        if rps <= 0:
            raise ValueError("rps must be > 0")
        self.rps = float(rps)
        self.min_interval = 1.0 / self.rps
        self._time = time_fn
        self._sleep = sleep_fn
        self._last: Optional[float] = None
        self.calls = 0
        self.total_slept = 0.0

    def wait(self) -> float:
        """Block until the next request is allowed. Returns seconds slept."""
        now = self._time()
        slept = 0.0
        if self._last is not None:
            due = self._last + self.min_interval
            if now < due:
                slept = due - now
                self._sleep(slept)
                now = self._time()
        self._last = now
        self.calls += 1
        self.total_slept += slept
        return slept

    def reset(self) -> None:
        self._last = None


class RequestBudget:
    """Hard cap on remote requests so a loop can never run away."""

    def __init__(self, max_requests: int):
        if max_requests < 1:
            raise ValueError("max_requests must be >= 1")
        self.max_requests = int(max_requests)
        self.used = 0

    def consume(self, n: int = 1, *, stage: str = "") -> None:
        if self.used + n > self.max_requests:
            raise OCLBudgetExceeded(
                f"request budget exhausted ({self.used}/{self.max_requests})"
                + (f" at stage {stage}" if stage else "")
            )
        self.used += n

    @property
    def remaining(self) -> int:
        return max(0, self.max_requests - self.used)

    @property
    def exhausted(self) -> bool:
        return self.used >= self.max_requests
