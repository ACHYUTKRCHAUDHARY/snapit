"""Resilience utilities: Token Bucket Rate Limiter and Circuit Breaker."""

from dataclasses import dataclass
from threading import Lock
from time import monotonic
from typing import Final

_DEFAULT_MAX_FAILURES: Final[int] = 5
_DEFAULT_RESET_TIMEOUT: Final[float] = 30.0


class RateLimitExceeded(RuntimeError):
    """Raised when an operation exceeds allowed request quota."""


class CircuitOpenError(RuntimeError):
    """Raised when an action is blocked by an open circuit breaker."""


@dataclass
class TokenBucket:
    """Thread-safe token bucket for rate limiting."""

    capacity: float
    refill_rate: float  # tokens per second
    tokens: float
    last_update: float
    _lock: Lock

    @classmethod
    def create(cls, rate_per_second: float, capacity: float | None = None) -> "TokenBucket":
        cap = capacity if capacity is not None else rate_per_second
        return cls(
            capacity=cap,
            refill_rate=rate_per_second,
            tokens=cap,
            last_update=monotonic(),
            _lock=Lock(),
        )

    def consume(self, amount: float = 1.0) -> bool:
        """Attempt to consume tokens. Returns True if successful, False if rate limited."""
        with self._lock:
            now = monotonic()
            elapsed = now - self.last_update
            self.last_update = now
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)

            if self.tokens >= amount:
                self.tokens -= amount
                return True
            return False


class RateLimiter:
    """Per-key (e.g. business_id or endpoint) token bucket rate limiter."""

    def __init__(self, default_rate: float = 10.0, default_capacity: float = 20.0) -> None:
        self._default_rate = default_rate
        self._default_capacity = default_capacity
        self._buckets: dict[str, TokenBucket] = {}
        self._lock = Lock()

    def acquire(self, key: str, amount: float = 1.0) -> None:
        """Acquire quota for *key*, raising :exc:`RateLimitExceeded` if quota is exhausted."""
        with self._lock:
            if key not in self._buckets:
                self._buckets[key] = TokenBucket.create(
                    rate_per_second=self._default_rate,
                    capacity=self._default_capacity,
                )
            bucket = self._buckets[key]

        if not bucket.consume(amount):
            raise RateLimitExceeded(f"Rate limit exceeded for key '{key}'")


class CircuitBreaker:
    """Three-state Circuit Breaker (CLOSED, OPEN, HALF-OPEN)."""

    def __init__(
        self,
        max_consecutive_failures: int = _DEFAULT_MAX_FAILURES,
        reset_timeout_seconds: float = _DEFAULT_RESET_TIMEOUT,
    ) -> None:
        self._max_failures = max_consecutive_failures
        self._timeout = reset_timeout_seconds
        self._failure_count = 0
        self._state: str = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self._opened_at: float = 0.0
        self._lock = Lock()

    @property
    def state(self) -> str:
        with self._lock:
            self._evaluate_state()
            return self._state

    def _evaluate_state(self) -> None:
        now = monotonic()
        if self._state == "OPEN" and (now - self._opened_at) >= self._timeout:
            self._state = "HALF_OPEN"

    def check_permission(self) -> None:
        """Raise :exc:`CircuitOpenError` if the circuit is currently blocking requests."""
        with self._lock:
            self._evaluate_state()
            if self._state == "OPEN":
                raise CircuitOpenError("Circuit is OPEN; requests are blocked")

    def record_success(self) -> None:
        """Record a successful operation to reset or close the circuit."""
        with self._lock:
            self._failure_count = 0
            self._state = "CLOSED"

    def record_failure(self) -> None:
        """Record an operation failure to potentially trip the circuit."""
        with self._lock:
            self._failure_count += 1
            if self._state == "HALF_OPEN" or self._failure_count >= self._max_failures:
                self._state = "OPEN"
                self._opened_at = monotonic()
