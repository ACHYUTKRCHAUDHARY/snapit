"""Tests for operator command parsing and execution."""

import pytest

from snappe.application.commands import (
    CommandSyntaxError,
    OperatorCommand,
    parse_operator_command,
)


def test_parse_valid_commands() -> None:
    # pause with reason
    cmd = parse_operator_command("/pause conv-123 customer requested human")
    assert cmd == OperatorCommand(
        action="pause", conversation_id="conv-123", reason="customer requested human"
    )

    # pause without reason
    cmd = parse_operator_command("/pause conv-123")
    assert cmd == OperatorCommand(action="pause", conversation_id="conv-123", reason=None)

    # resume
    cmd = parse_operator_command("/resume conv-123")
    assert cmd == OperatorCommand(action="resume", conversation_id="conv-123", reason=None)

    # close with reason
    cmd = parse_operator_command("/close conv-123 resolved inquiry")
    assert cmd == OperatorCommand(
        action="close", conversation_id="conv-123", reason="resolved inquiry"
    )

    # close without reason
    cmd = parse_operator_command("/close conv-123")
    assert cmd == OperatorCommand(action="close", conversation_id="conv-123", reason=None)

    # status
    cmd = parse_operator_command("/status conv-123")
    assert cmd == OperatorCommand(action="status", conversation_id="conv-123", reason=None)


def test_parse_rejects_missing_slash() -> None:
    with pytest.raises(CommandSyntaxError, match="must start with '/'"):
        parse_operator_command("pause conv-1")


def test_parse_rejects_unknown_command() -> None:
    with pytest.raises(CommandSyntaxError, match="Unknown command"):
        parse_operator_command("/restart conv-1")


def test_parse_rejects_missing_conversation_id() -> None:
    with pytest.raises(CommandSyntaxError, match="requires a conversation_id"):
        parse_operator_command("/pause")


def test_parse_resume_rejects_extra_args() -> None:
    with pytest.raises(CommandSyntaxError, match="does not accept additional arguments"):
        parse_operator_command("/resume conv-1 extra arguments")
