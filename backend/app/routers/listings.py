import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.auth import require_user
from app.db import get_db
from app.models import Listing, User
from app.schemas.common import ListingCreate, ListingOut, ListingUpdate
from app.storage import ALLOWED_CONTENT_TYPES, MAX_FILE_SIZE_BYTES, upload_listing_image


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


@router.post("/{listing_id}/image", response_model=ListingOut)
async def upload_image(
    listing_id: uuid.UUID,
    file: UploadFile = File(...),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> Listing:
    """Attach a photo to a listing. Only the seller can upload.

    Stored in Supabase Storage; the public URL is written to
    `listings.image_url`. Replaces any previous image (old object is
    left orphaned in storage — fine for now, can sweep later).
    """
    listing = db.get(Listing, listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.seller_id != user.id:
        raise HTTPException(status_code=403, detail="Not your listing")

    # Up-front validation so we don't read 50 MB into memory just to
    # throw it away. We re-check inside the uploader as a belt-and-
    # suspenders measure.
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported content type: {file.content_type!r}. Use JPEG, PNG, or WebP.",
        )

    data = await file.read()
    if len(data) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 5 MB)")

    public_url = upload_listing_image(
        listing_id=listing.id,
        content_type=file.content_type,
        data=data,
    )

    listing.image_url = public_url
    db.commit()
    db.refresh(listing)
    db.refresh(listing, attribute_names=["seller", "course"])
    return listing
