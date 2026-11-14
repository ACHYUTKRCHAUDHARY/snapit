"""Tests for RateLimiter and CircuitBreaker resilience components."""

import pytest

from snappe.application.resilience import (
    CircuitBreaker,
    CircuitOpenError,
    RateLimiter,
    RateLimitExceeded,
    TokenBucket,
)


def test_token_bucket_consume_and_refill() -> None:
    bucket = TokenBucket.create(rate_per_second=10.0, capacity=2.0)
    assert bucket.consume(1.0) is True
    assert bucket.consume(1.0) is True
    # Now exhausted
    assert bucket.consume(1.0) is False


def test_rate_limiter_blocks_burst() -> None:
    limiter = RateLimiter(default_rate=1.0, default_capacity=2.0)
    limiter.acquire("biz-1", 1.0)
    limiter.acquire("biz-1", 1.0)

    with pytest.raises(RateLimitExceeded, match="Rate limit exceeded"):
        limiter.acquire("biz-1", 1.0)

    # Different key is unaffected
    limiter.acquire("biz-2", 1.0)


def test_circuit_breaker_trips_after_max_failures() -> None:
    breaker = CircuitBreaker(max_consecutive_failures=3, reset_timeout_seconds=60.0)
    assert breaker.state == "CLOSED"

    breaker.check_permission()
    breaker.record_failure()
    assert breaker.state == "CLOSED"

    breaker.record_failure()
    assert breaker.state == "CLOSED"

    breaker.record_failure()
    assert breaker.state == "OPEN"

    with pytest.raises(CircuitOpenError, match="Circuit is OPEN"):
        breaker.check_permission()


def test_circuit_breaker_resets_on_success() -> None:
    breaker = CircuitBreaker(max_consecutive_failures=2, reset_timeout_seconds=60.0)
    breaker.record_failure()
    breaker.record_success()
    assert breaker.state == "CLOSED"

    # Should take 2 more failures to trip
    breaker.record_failure()
    assert breaker.state == "CLOSED"
    breaker.record_failure()
    assert breaker.state == "OPEN"


def test_circuit_breaker_half_open_recovery() -> None:
    breaker = CircuitBreaker(max_consecutive_failures=1, reset_timeout_seconds=0.01)
    breaker.record_failure()
    assert breaker.state == "OPEN"

    # Advance time / simulate timeout passed
    breaker._opened_at -= 1.0
    assert breaker.state == "HALF_OPEN"

    # Check permission should pass in HALF_OPEN
    breaker.check_permission()

    # Success closes circuit
    breaker.record_success()
    assert breaker.state == "CLOSED"
