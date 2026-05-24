import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, or_, desc
from sqlalchemy.orm import Session, joinedload, selectinload

from app.auth import require_user
from app.db import get_db
from app.models import Conversation, Listing, Message, User
from app.schemas.common import ConversationOut, MessageIn, MessageOut


router = APIRouter(prefix="/api", tags=["messages"])


def _user_in_conversation(conv: Conversation, user_id: str) -> bool:
    return user_id == conv.buyer_id or user_id == conv.listing.seller_id


@router.post("/listings/{listing_id}/contact", response_model=ConversationOut, status_code=201)
def start_or_get_conversation(
    listing_id: uuid.UUID,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> Conversation:
    """A buyer starts (or resumes) a conversation about a listing.

    Idempotent: if a conversation between this buyer and this listing already
    exists, return it.
    """
    listing = db.get(Listing, listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.seller_id == user.id:
        raise HTTPException(status_code=400, detail="Can't message yourself about your own listing")

    conv = db.execute(
        select(Conversation).where(
            Conversation.listing_id == listing_id,
            Conversation.buyer_id == user.id,
        )
    ).scalar_one_or_none()

    if conv is None:
        conv = Conversation(listing_id=listing_id, buyer_id=user.id)
        db.add(conv)
        db.commit()
        db.refresh(conv)

    db.refresh(conv, attribute_names=["listing", "buyer"])
    return conv


@router.get("/conversations", response_model=list[ConversationOut])
def list_my_conversations(
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> list[Conversation]:
    """Conversations the user is part of, as either buyer or seller."""
    stmt = (
        select(Conversation)
        .options(
            joinedload(Conversation.listing).joinedload(Listing.seller),
            joinedload(Conversation.listing).joinedload(Listing.course),
            joinedload(Conversation.buyer),
        )
        .join(Listing, Conversation.listing_id == Listing.id)
        .where(or_(Conversation.buyer_id == user.id, Listing.seller_id == user.id))
        .order_by(desc(Conversation.updated_at))
    )
    return list(db.execute(stmt).scalars().unique().all())


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageOut])
def list_messages(
    conversation_id: uuid.UUID,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> list[Message]:
    conv = db.execute(
        select(Conversation)
        .options(joinedload(Conversation.listing))
        .where(Conversation.id == conversation_id)
    ).scalar_one_or_none()
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if not _user_in_conversation(conv, user.id):
        raise HTTPException(status_code=403, detail="Not your conversation")

    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    return list(db.execute(stmt).scalars().all())


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessageOut,
    status_code=201,
)
def send_message(
    conversation_id: uuid.UUID,
    payload: MessageIn,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> Message:
    conv = db.execute(
        select(Conversation)
        .options(joinedload(Conversation.listing))
        .where(Conversation.id == conversation_id)
    ).scalar_one_or_none()
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if not _user_in_conversation(conv, user.id):
        raise HTTPException(status_code=403, detail="Not your conversation")

    msg = Message(conversation_id=conv.id, sender_id=user.id, body=payload.body)
    db.add(msg)
    # Bump updated_at so the inbox re-sorts.
    conv.updated_at = msg.created_at or conv.updated_at
    db.commit()
    db.refresh(msg)
    return msg
