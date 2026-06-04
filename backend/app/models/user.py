from datetime import datetime

from sqlalchemy import Boolean, String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(80), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Stripe Connect Express account ID (acct_xxx). Created lazily the
    # first time the user clicks "Set up Stripe payments" in /settings;
    # null until then. Unique because each user gets exactly one.
    stripe_account_id: Mapped[str | None] = mapped_column(
        String(64), unique=True, nullable=True
    )
    # Flips to true once Stripe's account.updated webhook reports the
    # account as fully onboarded (details_submitted + charges_enabled).
    # Drives whether "Pay with Stripe" shows on this seller's listings.
    stripe_onboarded: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false", default=False
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
