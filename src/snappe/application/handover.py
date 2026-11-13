"""Conversation handover state and explicitly authorized resume commands."""

from dataclasses import dataclass
from threading import RLock


@dataclass(frozen=True)
class HandoverState:
    """Current human-handover state for one conversation."""

    paused: bool
    reason: str


class HandoverManager:
    """Keep conversations paused until an authorized explicit resume."""

    def __init__(self, authorized_users: set[str]) -> None:
        self._authorized_users = frozenset(authorized_users)
        self._states: dict[str, HandoverState] = {}
        self._lock = RLock()

    def pause(self, conversation_id: str, reason: str) -> HandoverState:
        if not conversation_id.strip() or not reason.strip():
            raise ValueError("conversation_id and reason are required")
        state = HandoverState(paused=True, reason=reason.strip())
        with self._lock:
            self._states[conversation_id] = state
        return state

    def state(self, conversation_id: str) -> HandoverState:
        with self._lock:
            return self._states.get(conversation_id, HandoverState(False, ""))

    def resume(self, conversation_id: str, actor_user_id: str, command: str) -> HandoverState:
        if actor_user_id not in self._authorized_users:
            raise PermissionError("actor is not authorized to resume handover")
        expected = f"/resume {conversation_id}"
        if command.strip() != expected:
            raise ValueError("resume requires the exact explicit command")
        state = HandoverState(False, "")
        with self._lock:
            self._states[conversation_id] = state
        return state
