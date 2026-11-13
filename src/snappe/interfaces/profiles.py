"""Business profile management API."""

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from snappe.adapters.auth import AuthenticatedUser, get_current_user
from snappe.adapters.profiles import InMemoryProfileRepository
from snappe.application.profiles import ProfileService
from snappe.domain.profile import ApprovedFacts, ProfileValidationError

router = APIRouter(prefix="/profiles", tags=["profiles"])

_repository = InMemoryProfileRepository()
_service = ProfileService(_repository)


def get_profile_service() -> ProfileService:
    """Return the process-wide profile service."""
    return _service


class CreateProfileRequest(BaseModel):
    """Payload for creating a new business profile draft."""

    display_name: str = Field(min_length=1)
    languages: tuple[str, ...] = ("English",)
    approved_facts: dict[str, str | int | float | bool] = Field(default_factory=dict)


class ActivateProfileRequest(BaseModel):
    """Payload for activating a profile version."""

    approved_at: datetime | None = None


class ProfileResponse(BaseModel):
    """Serialized business profile."""

    business_id: str
    version: int
    display_name: str
    languages: tuple[str, ...]
    approved_facts: Mapping[str, str | int | float | bool]
    active: bool
    approved_at: datetime | None


@router.get("/{business_id}", response_model=list[ProfileResponse])
def list_profiles(
    business_id: str,
    user: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    service: ProfileService = Depends(get_profile_service),  # noqa: B008
) -> Sequence[Mapping[str, Any]]:
    """List all profile versions for a business."""
    profiles = list(service._repository.list_for_business(business_id))
    return [
        {
            "business_id": profile.business_id,
            "version": profile.version,
            "display_name": profile.display_name,
            "languages": profile.languages,
            "approved_facts": dict(profile.approved_facts),
            "active": profile.active,
            "approved_at": profile.approved_at,
        }
        for profile in profiles
    ]


@router.get("/{business_id}/active", response_model=ProfileResponse)
def get_active_profile(
    business_id: str,
    user: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    service: ProfileService = Depends(get_profile_service),  # noqa: B008
) -> Mapping[str, Any]:
    """Return the currently active profile for a business."""
    profile = service.active_profile(business_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="no active profile",
        )
    return {
        "business_id": profile.business_id,
        "version": profile.version,
        "display_name": profile.display_name,
        "languages": profile.languages,
        "approved_facts": dict(profile.approved_facts),
        "active": profile.active,
        "approved_at": profile.approved_at,
    }


@router.post(
    "/{business_id}",
    response_model=ProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_profile(
    business_id: str,
    body: CreateProfileRequest,
    user: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    service: ProfileService = Depends(get_profile_service),  # noqa: B008
) -> Mapping[str, Any]:
    """Create a new inactive profile draft for a business."""
    try:
        facts: ApprovedFacts = body.approved_facts
        profile = service.create_draft(
            business_id,
            body.display_name,
            body.languages,
            facts,
        )
    except ProfileValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error
    return {
        "business_id": profile.business_id,
        "version": profile.version,
        "display_name": profile.display_name,
        "languages": profile.languages,
        "approved_facts": dict(profile.approved_facts),
        "active": profile.active,
        "approved_at": profile.approved_at,
    }


@router.post("/{business_id}/{version}/activate", response_model=ProfileResponse)
def activate_profile(
    business_id: str,
    version: int,
    body: ActivateProfileRequest | None = None,
    user: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    service: ProfileService = Depends(get_profile_service),  # noqa: B008
) -> Mapping[str, Any]:
    """Approve and activate a specific profile version."""
    try:
        approved_at = body.approved_at if body else None
        profile = service.activate(business_id, version, approved_at)
    except ProfileValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error
    return {
        "business_id": profile.business_id,
        "version": profile.version,
        "display_name": profile.display_name,
        "languages": profile.languages,
        "approved_facts": dict(profile.approved_facts),
        "active": profile.active,
        "approved_at": profile.approved_at,
    }
