import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, or_, desc, update
from sqlalchemy.orm import Session, joinedload, selectinload

from app.auth import require_user
from app.db import get_db
from app.models import Conversation, Listing, Message, User
from app.schemas.common import ConversationOut, MarkReadOut, MessageIn, MessageOut


router = APIRouter(prefix="/api", tags=["messages"])


def _user_in_conversation(conv: Conversation, user_id: str) -> bool:
    # `other_user_id` is populated for both listing convos (= seller_id) and
    # DMs (= the other party), so this one check works for both kinds.
    return user_id == conv.buyer_id or user_id == conv.other_user_id


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
        conv = Conversation(
            listing_id=listing_id,
            buyer_id=user.id,
            other_user_id=listing.seller_id,
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)

    db.refresh(conv, attribute_names=["listing", "buyer", "other_user"])
    return conv


@router.post("/users/{other_user_id}/dm", response_model=ConversationOut, status_code=201)
def start_or_get_dm(
    other_user_id: str,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> Conversation:
    """Start (or resume) a direct-message conversation with another user.

    Used from the Classmates page — click a classmate to chat without a
    listing as context. Idempotent: calling A→B then B→A returns the same
    conversation (we canonicalize so the smaller user_id is `buyer_id`).
    """
    if other_user_id == user.id:
        raise HTTPException(status_code=400, detail="Can't DM yourself")

    other = db.get(User, other_user_id)
    if other is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Canonicalize the pair so (A→B) and (B→A) hit the same row.
    a, b = sorted([user.id, other.id])

    conv = db.execute(
        select(Conversation).where(
            Conversation.listing_id.is_(None),
            Conversation.buyer_id == a,
            Conversation.other_user_id == b,
        )
    ).scalar_one_or_none()

    if conv is None:
        conv = Conversation(listing_id=None, buyer_id=a, other_user_id=b)
        db.add(conv)
        db.commit()
        db.refresh(conv)

    db.refresh(conv, attribute_names=["listing", "buyer", "other_user"])
    return conv


@router.get("/conversations", response_model=list[ConversationOut])
def list_my_conversations(
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> list[Conversation]:
    """Conversations the user is part of — listing-scoped AND DMs."""
    stmt = (
        select(Conversation)
        .options(
            joinedload(Conversation.listing).joinedload(Listing.seller),
            joinedload(Conversation.listing).joinedload(Listing.course),
            joinedload(Conversation.buyer),
            joinedload(Conversation.other_user),
        )
        .where(or_(Conversation.buyer_id == user.id, Conversation.other_user_id == user.id))
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


@router.post(
    "/conversations/{conversation_id}/read",
    response_model=MarkReadOut,
)
def mark_conversation_read(
    conversation_id: uuid.UUID,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> MarkReadOut:
    """Mark all messages in this conversation from the OTHER party as read.

    Idempotent: re-calling on a fully-read conversation returns marked_read=0.
    Called by the frontend when the user opens a conversation thread.
    """
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
        update(Message)
        .where(
            Message.conversation_id == conversation_id,
            Message.sender_id != user.id,
            Message.read_at.is_(None),
        )
        .values(read_at=datetime.now(timezone.utc))
    )
    result = db.execute(stmt)
    db.commit()
    return MarkReadOut(marked_read=result.rowcount or 0)
