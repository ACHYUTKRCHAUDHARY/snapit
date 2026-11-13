"""Handover management API for authorized operators."""

from collections.abc import Mapping
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from snappe.adapters.auth import AuthenticatedUser, get_current_user
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


class PauseRequest(BaseModel):
    """Payload for pausing a conversation."""

    reason: str = Field(min_length=1)


class ResumeRequest(BaseModel):
    """Payload for resuming a conversation."""

    command: str = Field(min_length=1)


@router.get("/{conversation_id}", response_model=HandoverStateResponse)
def get_handover_state(
    conversation_id: str,
    user: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    manager: HandoverManager = Depends(get_handover_manager),  # noqa: B008
) -> Mapping[str, Any]:
    """Return the current handover state for a conversation."""
    state = manager.state(conversation_id)
    return {"paused": state.paused, "reason": state.reason}


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
    return {"paused": state.paused, "reason": state.reason}


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
    return {"paused": state.paused, "reason": state.reason}
