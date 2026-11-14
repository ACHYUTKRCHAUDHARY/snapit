"""WhatsApp webhook verification and message ingestion API."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from snappe.adapters.channel import EventDeduplicator, verify_signature
from snappe.adapters.database import Database
from snappe.adapters.llm import create_llm_client
from snappe.adapters.sql_conversations import ConversationRepository, SQLConversationRepository
from snappe.adapters.whatsapp import create_whatsapp_sender
from snappe.application.brain import BrainService
from snappe.application.handover import HandoverManager
from snappe.application.orchestration import (
    Brain,
    InboundMessage,
    MessageOrchestrator,
    ResponseResult,
    WhatsAppSender,
)
from snappe.application.profiles import ProfileService
from snappe.application.resilience import RateLimiter, RateLimitExceeded
from snappe.config import Settings, get_settings
from snappe.interfaces.handover import get_handover_manager
from snappe.interfaces.profiles import get_profile_service

router = APIRouter(prefix="/webhook", tags=["webhook"])

_deduplicator = EventDeduplicator()
_rate_limiter = RateLimiter(default_rate=50.0, default_capacity=100.0)


def get_event_deduplicator() -> EventDeduplicator:
    """Return the process-wide event deduplicator."""
    return _deduplicator


def get_rate_limiter() -> RateLimiter:
    """Return the process-wide webhook rate limiter."""
    return _rate_limiter


def get_brain(settings: Settings = Depends(get_settings)) -> Brain:  # noqa: B008
    """Return the configured brain instance."""
    return BrainService(create_llm_client(settings))


def get_whatsapp_sender(
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> WhatsAppSender:
    """Return the configured WhatsApp outbound sender."""
    return create_whatsapp_sender(settings)


def get_conversation_repository(
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> ConversationRepository:
    """Return the configured conversation repository."""
    db = Database(settings)
    db.create_tables()
    return SQLConversationRepository(db)


@dataclass(frozen=True)
class WebhookDependencies:
    """Grouped dependencies for webhook message processing."""

    settings: Settings
    deduplicator: EventDeduplicator
    profile_service: ProfileService
    handover_manager: HandoverManager
    brain: Brain
    sender: WhatsAppSender
    conversation_repo: ConversationRepository
    rate_limiter: RateLimiter


def get_webhook_dependencies(  # noqa: PLR0913, PLR0917
    settings: Settings = Depends(get_settings),  # noqa: B008
    deduplicator: EventDeduplicator = Depends(get_event_deduplicator),  # noqa: B008
    profile_service: ProfileService = Depends(get_profile_service),  # noqa: B008
    handover_manager: HandoverManager = Depends(get_handover_manager),  # noqa: B008
    brain: Brain = Depends(get_brain),  # noqa: B008
    sender: WhatsAppSender = Depends(get_whatsapp_sender),  # noqa: B008
    conversation_repo: ConversationRepository = Depends(get_conversation_repository),  # noqa: B008
    rate_limiter: RateLimiter = Depends(get_rate_limiter),  # noqa: B008
) -> WebhookDependencies:
    """Resolve all runtime dependencies required by the webhook."""
    return WebhookDependencies(
        settings=settings,
        deduplicator=deduplicator,
        profile_service=profile_service,
        handover_manager=handover_manager,
        brain=brain,
        sender=sender,
        conversation_repo=conversation_repo,
        rate_limiter=rate_limiter,
    )


class WebhookVerifyParams(BaseModel):
    """Query parameters for the Meta webhook verification challenge."""

    hub_mode: str = Field(alias="hub.mode")
    hub_verify_token: str = Field(alias="hub.verify_token")
    hub_challenge: str = Field(alias="hub.challenge")


class WebhookMessagePayload(BaseModel):
    """Simplified inbound webhook message from a channel provider."""

    event_id: str
    business_id: str
    conversation_id: str
    sender_id: str
    text: str = ""
    message_type: str = "text"
    media_url: str | None = None


class WebhookResponse(BaseModel):
    """Response after processing a webhook message."""

    reply: str | None
    handover_required: bool
    reason: str | None = None
    delivered: bool = False


@router.get("")
async def verify_webhook(
    request: Request,
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> Response:
    """Handle the Meta webhook verification challenge."""
    params = dict(request.query_params)
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if not mode or not token or not challenge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing verification parameters",
        )

    if mode != "subscribe":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid verification mode",
        )

    if settings.meta_verify_token is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="META_VERIFY_TOKEN is not configured",
        )

    if token != settings.meta_verify_token.get_secret_value():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verification token mismatch",
        )

    return Response(content=challenge, media_type="text/plain")


@router.post("", response_model=WebhookResponse)
async def receive_webhook(
    request: Request,
    body: WebhookMessagePayload,
    deps: WebhookDependencies = Depends(get_webhook_dependencies),  # noqa: B008
) -> Mapping[str, Any]:
    """Receive and process an inbound webhook message."""
    if deps.settings.meta_app_secret is not None:
        signature = request.headers.get("X-Hub-Signature-256", "")
        raw_body = await request.body()
        if not verify_signature(
            raw_body, signature, deps.settings.meta_app_secret.get_secret_value()
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature",
            )

    if not deps.deduplicator.accept("meta", body.event_id):
        return {"reply": None, "handover_required": False, "reason": "duplicate event"}

    try:
        deps.rate_limiter.acquire(body.business_id)
    except RateLimitExceeded as error:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(error),
        ) from error

    orchestrator = MessageOrchestrator(
        deps.profile_service._repository,
        deps.handover_manager,
        deps.brain,
        deps.sender,
        auditor=deps.conversation_repo,
    )

    text_content = body.text
    if body.message_type in ("image", "document", "audio", "video") and not text_content.strip():
        text_content = f"[{body.message_type} received]"

    message = InboundMessage(
        business_id=body.business_id,
        conversation_id=body.conversation_id,
        sender_id=body.sender_id,
        text=text_content,
    )
    result: ResponseResult = orchestrator.handle(message, event_id=body.event_id)
    return {
        "reply": result.reply,
        "handover_required": result.handover_required,
        "reason": result.reason,
        "delivered": result.delivered,
    }
