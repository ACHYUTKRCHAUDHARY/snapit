import pytest

from snappe.application.actions import ActionUnavailable, RetryPolicy, execute_action


def test_action_retries_transient_failures() -> None:
    calls = 0

    def action() -> str:
        nonlocal calls
        calls += 1
        if calls < 3:
            raise ActionUnavailable("temporary")
        return "done"

    assert execute_action(action, RetryPolicy(attempts=3)) == "done"
    assert calls == 3


def test_action_outage_is_explicit_after_bounded_retries() -> None:
    with pytest.raises(ActionUnavailable, match="after retries"):
        execute_action(lambda: (_ for _ in ()).throw(TimeoutError()), RetryPolicy(attempts=2))


def test_retry_policy_rejects_invalid_values() -> None:
    with pytest.raises(ValueError, match="invalid"):
        RetryPolicy(attempts=0)
