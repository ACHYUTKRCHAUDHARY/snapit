"""SQLAlchemy models for durable relational persistence."""

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy declarative models."""


# Portable UUID type (String(36) for SQLite, native UUID for Postgres)
GUID = UUID(as_uuid=True).with_variant(String(36), "sqlite")
# Portable JSON type (JSONB for Postgres, JSON for SQLite)
PORTABLE_JSON = JSONB().with_variant(JSON(), "sqlite")


class BusinessProfileModel(Base):
    """SQLAlchemy model mapping to business_profiles table."""

    __tablename__ = "business_profiles"
    __table_args__ = (
        UniqueConstraint("business_id", "version", name="uq_business_profiles_business_version"),
    )

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=lambda: str(uuid4()))
    business_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    languages: Mapped[list[str]] = mapped_column(PORTABLE_JSON, nullable=False, default=list)
    approved_facts: Mapped[dict[str, Any]] = mapped_column(
        PORTABLE_JSON, nullable=False, default=dict
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ConversationModel(Base):
    """SQLAlchemy model mapping to conversations table."""

    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    business_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    customer_id: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    handover_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    messages: Mapped[list["MessageModel"]] = relationship(
        "MessageModel", back_populates="conversation", cascade="all, delete-orphan"
    )


class MessageModel(Base):
    """SQLAlchemy model mapping to messages table."""

    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint(
            "business_id", "provider_message_id", name="uq_messages_business_provider_msg_id"
        ),
    )

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=lambda: str(uuid4()))
    business_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    conversation_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    message_type: Mapped[str] = mapped_column(String(32), nullable=False, default="text")
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    intent: Mapped[str | None] = mapped_column(String(64), nullable=True)
    delivery_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    conversation: Mapped["ConversationModel"] = relationship(
        "ConversationModel", back_populates="messages"
    )
