"""SQLAlchemy-backed conversation and message persistence."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from snappe.adapters.database import Database
from snappe.adapters.models import ConversationModel, MessageModel


@dataclass(frozen=True)
class PersistedConversation:
    """Read-only view of a persisted conversation."""

    id: str
    business_id: str
    customer_id: str
    status: str
    handover_reason: str | None
    last_message_at: datetime | None


@dataclass(frozen=True)
class PersistedMessage:
    """Read-only view of a persisted message."""

    id: str
    business_id: str
    conversation_id: str
    direction: str
    content: str
    provider_message_id: str | None = None
    message_type: str = "text"
    language: str | None = None
    intent: str | None = None
    delivery_status: str | None = None
    created_at: datetime | None = None


class ConversationRepository(Protocol):
    """Port for conversation persistence."""

    def get_or_create(
        self,
        conversation_id: str,
        business_id: str,
        customer_id: str,
    ) -> PersistedConversation:
        """Fetch existing conversation or create a new one."""

    def update_status(
        self,
        conversation_id: str,
        status: str,
        reason: str | None = None,
    ) -> None:
        """Update conversation status and handover reason."""

    def record_message(  # noqa: PLR0913, PLR0917
        self,
        business_id: str,
        conversation_id: str,
        direction: str,
        content: str,
        provider_message_id: str | None = None,
        delivery_status: str | None = None,
        intent: str | None = None,
    ) -> PersistedMessage:
        """Append an inbound or outbound message to the conversation."""

    def list_messages(
        self,
        conversation_id: str,
        limit: int = 50,
    ) -> list[PersistedMessage]:
        """Fetch recent messages for a conversation ordered by creation time."""


class SQLConversationRepository(ConversationRepository):
    """Persist conversations and messages into SQL database."""

    def __init__(self, database: Database) -> None:
        self._session_factory = sessionmaker(bind=database.engine, expire_on_commit=False)

    def _to_conv(self, model: ConversationModel) -> PersistedConversation:
        last_msg = model.last_message_at
        if last_msg is not None and last_msg.tzinfo is None:
            last_msg = last_msg.replace(tzinfo=UTC)
        return PersistedConversation(
            id=model.id,
            business_id=model.business_id,
            customer_id=model.customer_id,
            status=model.status,
            handover_reason=model.handover_reason,
            last_message_at=last_msg,
        )

    def _to_msg(self, model: MessageModel) -> PersistedMessage:
        created_at = model.created_at
        if created_at is not None and created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        return PersistedMessage(
            id=str(model.id),
            business_id=model.business_id,
            conversation_id=model.conversation_id,
            direction=model.direction,
            content=model.content,
            provider_message_id=model.provider_message_id,
            message_type=model.message_type,
            language=model.language,
            intent=model.intent,
            delivery_status=model.delivery_status,
            created_at=created_at,
        )

    def get_or_create(
        self,
        conversation_id: str,
        business_id: str,
        customer_id: str,
    ) -> PersistedConversation:
        with self._session_factory() as session:
            stmt = select(ConversationModel).where(ConversationModel.id == conversation_id)
            model = session.scalar(stmt)
            if model is None:
                model = ConversationModel(
                    id=conversation_id,
                    business_id=business_id,
                    customer_id=customer_id,
                    status="active",
                )
                session.add(model)
                session.commit()
            return self._to_conv(model)

    def update_status(
        self,
        conversation_id: str,
        status: str,
        reason: str | None = None,
    ) -> None:
        with self._session_factory() as session:
            stmt = select(ConversationModel).where(ConversationModel.id == conversation_id)
            model = session.scalar(stmt)
            if model is not None:
                model.status = status
                model.handover_reason = reason
                session.commit()

    def record_message(  # noqa: PLR0913, PLR0917
        self,
        business_id: str,
        conversation_id: str,
        direction: str,
        content: str,
        provider_message_id: str | None = None,
        delivery_status: str | None = None,
        intent: str | None = None,
    ) -> PersistedMessage:
        with self._session_factory() as session:
            now = datetime.now(UTC)
            # Check for existing message with same business_id and provider_message_id
            if provider_message_id is not None:
                existing_stmt = select(MessageModel).where(
                    MessageModel.business_id == business_id,
                    MessageModel.provider_message_id == provider_message_id,
                )
                existing = session.scalar(existing_stmt)
                if existing is not None:
                    return self._to_msg(existing)

            # Update conversation last_message_at
            conv_stmt = select(ConversationModel).where(ConversationModel.id == conversation_id)
            conv = session.scalar(conv_stmt)
            if conv is not None:
                conv.last_message_at = now

            msg = MessageModel(
                business_id=business_id,
                conversation_id=conversation_id,
                direction=direction,
                content=content,
                provider_message_id=provider_message_id,
                delivery_status=delivery_status,
                intent=intent,
                created_at=now,
            )
            session.add(msg)
            session.commit()
            return self._to_msg(msg)

    def list_messages(
        self,
        conversation_id: str,
        limit: int = 50,
    ) -> list[PersistedMessage]:
        with self._session_factory() as session:
            stmt = (
                select(MessageModel)
                .where(MessageModel.conversation_id == conversation_id)
                .order_by(MessageModel.created_at.asc())
                .limit(limit)
            )
            models = session.scalars(stmt).all()
            return [self._to_msg(m) for m in models]
