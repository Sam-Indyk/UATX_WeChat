import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, joinedload

from app.auth import require_user
from app.db import get_db
from app.models import Conversation, Listing, Message, User
from app.schemas.common import ConversationOut, ListingCreate, ListingOut, ListingUpdate
from app.storage import (
    ALLOWED_CONTENT_TYPES,
    MAX_FILE_SIZE_BYTES,
    delete_stored_image,
    upload_listing_image,
)


router = APIRouter(prefix="/api/listings", tags=["listings"])


@router.get("", response_model=list[ListingOut])
def list_listings(
    course_id: uuid.UUID | None = Query(default=None),
    category: str | None = Query(default=None),
    status_: str = Query(default="active", alias="status"),
    db: Session = Depends(get_db),
) -> list[Listing]:
    """Browse listings.

    - `?category=book` → Browse page (books only).
    - `?category=furniture,electronics,...` → not supported in this PR;
      Everything Else filters with `?category=non-book` (a sentinel)
      OR client passes a single non-book category at a time. The
      simplest server semantics: if `category` is the literal string
      `non-book`, exclude books; otherwise filter to that exact value.
      Falls back to "all categories" when omitted (used by My Listings).
    """
    stmt = (
        select(Listing)
        .options(joinedload(Listing.seller), joinedload(Listing.course))
        .where(Listing.status == status_)
        .order_by(Listing.created_at.desc())
    )
    if course_id is not None:
        stmt = stmt.where(Listing.course_id == course_id)
    if category == "non-book":
        stmt = stmt.where(Listing.category != "book")
        # Everything Else only displays items WITH an image — required at
        # create time on the frontend. Hide ones where the upload failed.
        stmt = stmt.where(Listing.image_url.is_not(None))
    elif category is not None:
        stmt = stmt.where(Listing.category == category)
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
        category=payload.category,
        course_id=payload.course_id if payload.category == "book" else None,
        title=payload.title.strip(),
        author=payload.author.strip() if payload.author else None,
        edition=payload.edition.strip() if payload.edition else None,
        condition=payload.condition,
        price_cents=payload.price_cents,
        description=payload.description,
        payment_methods=list(payload.payment_methods),
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
    if payload.title is not None:
        listing.title = payload.title.strip()
    if payload.author is not None:
        listing.author = payload.author.strip() or None
    if payload.edition is not None:
        listing.edition = payload.edition.strip() or None
    if payload.condition is not None:
        listing.condition = payload.condition
    if payload.course_id is not None:
        listing.course_id = payload.course_id
    if payload.category is not None:
        listing.category = payload.category
    if payload.payment_methods is not None:
        # Empty list is valid (means: clear all methods). Distinguish
        # from None (means: leave unchanged) — Pydantic does this for us.
        listing.payment_methods = list(payload.payment_methods)

    db.commit()
    db.refresh(listing)
    db.refresh(listing, attribute_names=["seller", "course"])
    return listing


@router.delete("/{listing_id}", status_code=204)
def delete_listing(
    listing_id: uuid.UUID,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> None:
    """Take down a listing — fully delete it.

    Cascades via ON DELETE CASCADE on conversations.listing_id, so any
    buyer conversations + their messages also go away. The listing's
    image (if any) is best-effort removed from Supabase Storage so we
    don't accumulate orphaned bytes.

    Only the seller can delete. This is destructive; the UI confirms
    before calling it.
    """
    listing = db.get(Listing, listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.seller_id != user.id:
        raise HTTPException(status_code=403, detail="Not your listing")

    image_url = listing.image_url
    db.delete(listing)
    db.commit()

    # After the row is gone, best-effort clean up the image. Doing it
    # after commit means a failed delete doesn't roll back the row.
    delete_stored_image(image_url)


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


@router.get("/{listing_id}/conversations", response_model=list[ConversationOut])
def list_listing_conversations(
    listing_id: uuid.UUID,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> list[Conversation]:
    """All conversations on this listing. Only the seller can call this —
    buyers don't get to see OTHER buyers' threads.

    Powers the My Listings → Chat subtab: shows each buyer as a row with
    their last message and unread count.
    """
    listing = db.get(Listing, listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.seller_id != user.id:
        raise HTTPException(
            status_code=403, detail="Only the seller can see all buyers' conversations"
        )

    convs = list(
        db.execute(
            select(Conversation)
            .options(
                joinedload(Conversation.listing).joinedload(Listing.seller),
                joinedload(Conversation.listing).joinedload(Listing.course),
                joinedload(Conversation.buyer),
                joinedload(Conversation.other_user),
            )
            .where(Conversation.listing_id == listing_id)
            .order_by(desc(Conversation.updated_at))
        )
        .scalars()
        .unique()
        .all()
    )

    # Per-conversation unread, same pattern as list_my_conversations.
    if convs:
        conv_ids = [c.id for c in convs]
        rows = db.execute(
            select(Message.conversation_id, func.count(Message.id))
            .where(
                Message.conversation_id.in_(conv_ids),
                Message.sender_id != user.id,
                Message.read_at.is_(None),
            )
            .group_by(Message.conversation_id)
        ).all()
        unread_by_conv = {cid: count for cid, count in rows}
        for c in convs:
            c.unread_count = unread_by_conv.get(c.id, 0)

    return convs
