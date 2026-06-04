from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, joinedload

from app.auth import require_user
from app.db import get_db
from app.models import Listing, User
from app.schemas.common import PublicUserOut


router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/{user_id}", response_model=PublicUserOut)
def get_public_profile(
    user_id: str,
    _viewer: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> User:
    """Public profile for a single user, plus their active listings.

    Powers the /users/:id seller-profile page reachable from any listing's
    seller-name link. Requires sign-in (we don't expose any user data to
    anonymous traffic), but returns the same payload regardless of who's
    asking — there's no per-viewer customization here. The viewer can be
    the profile's owner; the UI handles the "you" indicator.
    """
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")

    listings = (
        db.execute(
            select(Listing)
            .options(joinedload(Listing.seller), joinedload(Listing.course))
            .where(
                Listing.seller_id == user_id,
                Listing.status == "active",
            )
            .order_by(desc(Listing.created_at))
        )
        .scalars()
        .unique()
        .all()
    )

    # Stamp a non-model attribute that PublicUserOut.from_attributes will
    # pick up. Same pattern me.py uses for unread_count on listings.
    target.active_listings = list(listings)
    return target
