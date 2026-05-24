import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.auth import require_user
from app.db import get_db
from app.models import Listing, User
from app.schemas.common import ListingCreate, ListingOut, ListingUpdate


router = APIRouter(prefix="/api/listings", tags=["listings"])


@router.get("", response_model=list[ListingOut])
def list_listings(
    course_id: uuid.UUID | None = Query(default=None),
    status_: str = Query(default="active", alias="status"),
    db: Session = Depends(get_db),
) -> list[Listing]:
    stmt = (
        select(Listing)
        .options(joinedload(Listing.seller), joinedload(Listing.course))
        .where(Listing.status == status_)
        .order_by(Listing.created_at.desc())
    )
    if course_id is not None:
        stmt = stmt.where(Listing.course_id == course_id)
    return list(db.execute(stmt).scalars().all())


@router.get("/{listing_id}", response_model=ListingOut)
def get_listing(listing_id: uuid.UUID, db: Session = Depends(get_db)) -> Listing:
    stmt = (
        select(Listing)
        .options(joinedload(Listing.seller), joinedload(Listing.course))
        .where(Listing.id == listing_id)
    )
    listing = db.execute(stmt).scalar_one_or_none()
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing


@router.post("", response_model=ListingOut, status_code=201)
def create_listing(
    payload: ListingCreate,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> Listing:
    listing = Listing(
        seller_id=user.id,
        course_id=payload.course_id,
        book_title=payload.book_title,
        book_author=payload.book_author,
        book_edition=payload.book_edition,
        condition=payload.condition,
        price_cents=payload.price_cents,
        description=payload.description,
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)
    db.refresh(listing, attribute_names=["seller", "course"])
    return listing


@router.patch("/{listing_id}", response_model=ListingOut)
def update_listing(
    listing_id: uuid.UUID,
    payload: ListingUpdate,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> Listing:
    listing = db.get(Listing, listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.seller_id != user.id:
        raise HTTPException(status_code=403, detail="Not your listing")

    if payload.status is not None:
        listing.status = payload.status
    if payload.price_cents is not None:
        listing.price_cents = payload.price_cents
    if payload.description is not None:
        listing.description = payload.description

    db.commit()
    db.refresh(listing)
    db.refresh(listing, attribute_names=["seller", "course"])
    return listing
