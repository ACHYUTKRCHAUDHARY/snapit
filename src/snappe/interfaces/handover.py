"""Handover management API for authorized operators."""

from collections.abc import Mapping
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from snappe.adapters.auth import AuthenticatedUser, get_current_user
from snappe.application.commands import CommandSyntaxError, parse_operator_command
from snappe.application.handover import HandoverManager

router = APIRouter(prefix="/handover", tags=["handover"])

_manager = HandoverManager(set())


def get_handover_manager() -> HandoverManager:
    """Return the process-wide handover manager."""
    return _manager


class HandoverStateResponse(BaseModel):
    """Current handover state for a conversation."""

    paused: bool
    reason: str
    status: str = "active"


class PauseRequest(BaseModel):
    """Payload for pausing a conversation."""

    reason: str = Field(min_length=1)


class ResumeRequest(BaseModel):
    """Payload for resuming a conversation."""

    command: str = Field(min_length=1)


class CloseRequest(BaseModel):
    """Payload for closing a conversation."""

    reason: str | None = None


class CommandRequest(BaseModel):
    """Slash command string sent by operator."""

    command: str = Field(min_length=1)


@router.get("/{conversation_id}", response_model=HandoverStateResponse)
def get_handover_state(
    conversation_id: str,
    user: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    manager: HandoverManager = Depends(get_handover_manager),  # noqa: B008
) -> Mapping[str, Any]:
    """Return the current handover state for a conversation."""
    state = manager.state(conversation_id)
    return {"paused": state.paused, "reason": state.reason, "status": state.status}


@router.post("/{conversation_id}/pause", response_model=HandoverStateResponse)
def pause_conversation(
    conversation_id: str,
    body: PauseRequest,
    user: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    manager: HandoverManager = Depends(get_handover_manager),  # noqa: B008
) -> Mapping[str, Any]:
    """Pause a conversation for human handover."""
    try:
        state = manager.pause(conversation_id, body.reason)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error
    return {"paused": state.paused, "reason": state.reason, "status": state.status}


@router.post("/{conversation_id}/resume", response_model=HandoverStateResponse)
def resume_conversation(
    conversation_id: str,
    body: ResumeRequest,
    user: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    manager: HandoverManager = Depends(get_handover_manager),  # noqa: B008
) -> Mapping[str, Any]:
    """Resume a paused conversation with an explicit authorized command."""
    try:
        state = manager.resume(conversation_id, user.user_id, body.command)
    except PermissionError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(error),
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error
    return {"paused": state.paused, "reason": state.reason, "status": state.status}


@router.post("/{conversation_id}/close", response_model=HandoverStateResponse)
def close_conversation(
    conversation_id: str,
    body: CloseRequest | None = None,
    user: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    manager: HandoverManager = Depends(get_handover_manager),  # noqa: B008
) -> Mapping[str, Any]:
    """Close a conversation as resolved by an operator."""
    reason = body.reason if body else None
    try:
        state = manager.close(conversation_id, user.user_id, reason)
    except PermissionError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(error),
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error
    return {"paused": state.paused, "reason": state.reason, "status": state.status}


@router.post("/command", response_model=HandoverStateResponse)
def execute_command(
    body: CommandRequest,
    user: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    manager: HandoverManager = Depends(get_handover_manager),  # noqa: B008
) -> Mapping[str, Any]:
    """Execute an operator slash-command (/pause, /resume, /close, /status)."""
    try:
        cmd = parse_operator_command(body.command)
    except CommandSyntaxError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error

    try:
        if cmd.action == "pause":
            state = manager.pause(cmd.conversation_id, cmd.reason or "operator pause")
        elif cmd.action == "resume":
            resume_cmd = f"/resume {cmd.conversation_id}"
            state = manager.resume(cmd.conversation_id, user.user_id, resume_cmd)
        elif cmd.action == "close":
            state = manager.close(cmd.conversation_id, user.user_id, cmd.reason)
        else:  # status
            state = manager.state(cmd.conversation_id)
    except PermissionError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(error),
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error

    return {"paused": state.paused, "reason": state.reason, "status": state.status}
