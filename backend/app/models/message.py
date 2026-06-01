import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, Text, Index, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        # Listing convos: one (listing, buyer) pair per conversation.
        Index(
            "uq_conversation_listing",
            "listing_id",
            "buyer_id",
            unique=True,
            postgresql_where=text("listing_id IS NOT NULL"),
        ),
        # DMs: one (buyer, other_user) pair per conversation. The application
        # canonicalizes buyer_id < other_user_id so (A,B) and (B,A) collide.
        Index(
            "uq_conversation_dm",
            "buyer_id",
            "other_user_id",
            unique=True,
            postgresql_where=text("listing_id IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # NULL for direct-message conversations between two students. NOT NULL
    # for listing-scoped buyer↔seller chats.
    listing_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("listings.id", ondelete="CASCADE"), nullable=True
    )
    buyer_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # The other party. For listing convos, equals listing.seller_id (we
    # store it denormalized so membership checks don't have to join). For
    # DMs, the application canonicalizes so buyer_id < other_user_id.
    other_user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    listing = relationship("Listing")
    buyer = relationship("User", foreign_keys=[buyer_id])
    other_user = relationship("User", foreign_keys=[other_user_id])
    messages = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan"
    )


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        Index("ix_messages_conversation_created", "conversation_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    sender_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    conversation = relationship("Conversation", back_populates="messages")
    sender = relationship("User")
