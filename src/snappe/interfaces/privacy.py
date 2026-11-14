"""Privacy and retention endpoints for data protection compliance."""

from collections.abc import Mapping
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from snappe.adapters.auth import AuthenticatedUser, get_current_user
from snappe.adapters.sql_conversations import ConversationRepository
from snappe.application.data_protection import purge_expired
from snappe.config import Settings, get_settings
from snappe.interfaces.webhook import get_conversation_repository

router = APIRouter(prefix="/privacy", tags=["privacy"])


class PurgeExpiredResponse(BaseModel):
    """Result of running expired data retention cleanup."""

    retention_days: int
    purged_messages_count: int


class CustomerPurgeRequest(BaseModel):
    """Request payload to delete all data belonging to a customer."""

    customer_id: str = Field(min_length=1)


class CustomerPurgeResponse(BaseModel):
    """Result of customer data erasure."""

    business_id: str
    customer_id: str
    purged_messages_count: int


@router.post("/retention/purge", response_model=PurgeExpiredResponse)
def purge_expired_records(
    settings: Settings = Depends(get_settings),  # noqa: B008
    user: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    repo: ConversationRepository = Depends(get_conversation_repository),  # noqa: B008
) -> Mapping[str, Any]:
    """Execute the configured retention period purge."""
    count = purge_expired(repo, settings.retention_days)
    return {
        "retention_days": settings.retention_days,
        "purged_messages_count": count,
    }


@router.post("/customers/{business_id}/purge", response_model=CustomerPurgeResponse)
def purge_customer_records(
    business_id: str,
    body: CustomerPurgeRequest,
    user: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    repo: ConversationRepository = Depends(get_conversation_repository),  # noqa: B008
) -> Mapping[str, Any]:
    """Right to erasure (GDPR / DPDP) request for a customer."""
    count = repo.purge_customer_data(business_id, body.customer_id)
    return {
        "business_id": business_id,
        "customer_id": body.customer_id,
        "purged_messages_count": count,
    }
