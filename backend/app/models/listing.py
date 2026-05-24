import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, Integer, Text, CheckConstraint, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


CONDITIONS = ("new", "like_new", "good", "fair", "poor")
STATUSES = ("active", "reserved", "sold", "withdrawn")


class Listing(Base):
    __tablename__ = "listings"
    __table_args__ = (
        CheckConstraint(
            "condition IN ('new', 'like_new', 'good', 'fair', 'poor')",
            name="ck_listing_condition",
        ),
        CheckConstraint(
            "status IN ('active', 'reserved', 'sold', 'withdrawn')",
            name="ck_listing_status",
        ),
        CheckConstraint("price_cents >= 0", name="ck_listing_price_nonneg"),
        Index("ix_listings_course_status", "course_id", "status"),
        Index("ix_listings_seller_created", "seller_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    seller_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    course_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("courses.id", ondelete="RESTRICT"), nullable=True
    )

    book_title: Mapped[str] = mapped_column(String(200), nullable=False)
    book_author: Mapped[str] = mapped_column(String(200), nullable=False)
    book_edition: Mapped[str | None] = mapped_column(String(40), nullable=True)

    condition: Mapped[str] = mapped_column(String(20), nullable=False)
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    seller = relationship("User")
    course = relationship("Course")
