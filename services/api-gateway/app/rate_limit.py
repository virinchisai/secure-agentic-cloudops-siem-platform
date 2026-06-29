"""Simple in-memory token-bucket rate limiter (per-IP)."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field

RATE_LIMIT_RPM = int(os.getenv("RATE_LIMIT_RPM", "60"))


@dataclass
class _Bucket:
    tokens: float
    last_refill: float
    capacity: int
    refill_rate: float  # tokens per second

    def consume(self) -> bool:
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False


@dataclass
class RateLimiter:
    """Per-IP token-bucket rate limiter.

    *rpm* is the maximum requests per minute each IP is allowed.
    """

    rpm: int = RATE_LIMIT_RPM
    _buckets: dict[str, _Bucket] = field(default_factory=dict)

    def is_allowed(self, key: str) -> bool:
        if key not in self._buckets:
            self._buckets[key] = _Bucket(
                tokens=float(self.rpm),
                last_refill=time.monotonic(),
                capacity=self.rpm,
                refill_rate=self.rpm / 60.0,
            )
        return self._buckets[key].consume()
