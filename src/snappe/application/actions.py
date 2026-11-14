"""Action ports and bounded failure handling."""

from collections.abc import Callable
from dataclasses import dataclass
from time import sleep
from typing import Protocol, TypeVar

T_co = TypeVar("T_co", covariant=True)


class ActionUnavailable(RuntimeError):
    """Raised when an external action cannot complete safely."""


class Action(Protocol[T_co]):
    def __call__(self) -> T_co:
        """Execute an external action."""


@dataclass(frozen=True)
class RetryPolicy:
    attempts: int = 3
    delay_seconds: float = 0.05
    backoff_factor: float = 1.0

    def __post_init__(self) -> None:
        if self.attempts < 1 or self.delay_seconds < 0 or self.backoff_factor < 1.0:
            raise ValueError("retry policy values are invalid")


def execute_action[T](action: Callable[[], T], policy: RetryPolicy | None = None) -> T:
    """Retry transient action failures with optional exponential backoff."""
    retry_policy = policy or RetryPolicy()
    delay = retry_policy.delay_seconds
    for attempt in range(retry_policy.attempts):
        try:
            return action()
        except (ActionUnavailable, TimeoutError) as error:
            if attempt == retry_policy.attempts - 1:
                raise ActionUnavailable("action unavailable after retries") from error
            if delay:
                sleep(delay)
                delay *= retry_policy.backoff_factor
    raise AssertionError("retry loop must return or raise")
