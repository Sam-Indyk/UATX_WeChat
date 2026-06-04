import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, Integer, Text, CheckConstraint, Index, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


CONDITIONS = ("new", "like_new", "good", "fair", "poor")
STATUSES = ("active", "reserved", "sold", "withdrawn")
CATEGORIES = (
    "book",
    "furniture",
    "electronics",
    "clothing",
    "kitchen",
    "decor",
    "sports",
    "transportation",
    "other",
)
PAYMENT_METHODS = ("cash", "venmo", "zelle", "paypal", "stripe")


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
        CheckConstraint(
            "category IN ('book', 'furniture', 'electronics', 'clothing', "
            "'kitchen', 'decor', 'sports', 'transportation', 'other')",
            name="ck_listing_category",
        ),
        CheckConstraint("price_cents >= 0", name="ck_listing_price_nonneg"),
        Index("ix_listings_course_status", "course_id", "status"),
        Index("ix_listings_seller_created", "seller_id", "created_at"),
        Index("ix_listings_category_status", "category", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    seller_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    course_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("courses.id", ondelete="RESTRICT"), nullable=True
    )

    # 'book' vs 'furniture'/'electronics'/etc. Books additionally set
    # author/edition/course_id; general items leave those nullable.
    category: Mapped[str] = mapped_column(String(20), nullable=False, default="book")

    # Used by all listings — book titles, item names, whatever.
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    # Book-specific. Nullable so non-book listings don't need to invent
    # a value.
    author: Mapped[str | None] = mapped_column(String(200), nullable=True)
    edition: Mapped[str | None] = mapped_column(String(40), nullable=True)

    condition: Mapped[str] = mapped_column(String(20), nullable=False)
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Methods the seller is willing to accept (cash / venmo / zelle /
    # paypal / stripe). Enforced at the API layer via Pydantic Literal;
    # no Postgres CHECK on array contents. Empty array = seller didn't
    # specify (the UI just hides the "Accepts:" line then).
    payment_methods: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, server_default="{}", default=list
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

    seller = relationship("User")
    course = relationship("Course")
