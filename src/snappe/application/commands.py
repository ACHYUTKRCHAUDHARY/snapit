"""Operator command models and execution engine."""

from dataclasses import dataclass
from typing import Literal

OperatorAction = Literal["pause", "resume", "close", "status"]


class CommandSyntaxError(ValueError):
    """Raised when an operator command cannot be parsed."""


@dataclass(frozen=True)
class OperatorCommand:
    """Parsed operator command."""

    action: OperatorAction
    conversation_id: str
    reason: str | None = None


_MIN_PARTS_FOR_CONV_ID = 2


def parse_operator_command(raw_text: str) -> OperatorCommand:
    """Parse a slash command string such as '/pause <conv_id> <reason>'.

    Supported formats:
      - /pause <conversation_id> [optional reason...]
      - /resume <conversation_id>
      - /close <conversation_id> [optional reason...]
      - /status <conversation_id>
    """
    cleaned = raw_text.strip()
    if not cleaned.startswith("/"):
        raise CommandSyntaxError("Operator commands must start with '/'")

    parts = cleaned.split(maxsplit=2)
    command_name = parts[0][1:].lower()

    if command_name not in ("pause", "resume", "close", "status"):
        raise CommandSyntaxError(f"Unknown command: /{command_name}")

    if len(parts) < _MIN_PARTS_FOR_CONV_ID or not parts[1].strip():
        raise CommandSyntaxError(f"Command /{command_name} requires a conversation_id")

    conversation_id = parts[1].strip()
    reason = parts[2].strip() if len(parts) > _MIN_PARTS_FOR_CONV_ID else None

    if command_name == "pause":
        return OperatorCommand(action="pause", conversation_id=conversation_id, reason=reason)
    if command_name == "resume":
        if reason:
            raise CommandSyntaxError("/resume does not accept additional arguments")
        return OperatorCommand(action="resume", conversation_id=conversation_id)
    if command_name == "close":
        return OperatorCommand(action="close", conversation_id=conversation_id, reason=reason)
    # status
    return OperatorCommand(action="status", conversation_id=conversation_id)
