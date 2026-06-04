import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    display_name: str
    avatar_url: str | None = None
    # True once the user has finished Stripe Connect onboarding (their
    # account can charge). Drives whether the "Pay with Stripe" button
    # shows on this user's listings. Not sensitive — it's just a flag.
    stripe_onboarded: bool = False


class MeUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=80)


class UnreadCountOut(BaseModel):
    count: int


class UnreadCountsOut(BaseModel):
    """Per-context breakdown of unread messages for the viewer.

    Drives the upcoming three-badge nav (My Listings / My Inquiries /
    Classmates DMs) — see CLAUDE.md → Phase 2 → UX restructuring.
    """

    listings: int  # I'm the seller on these listing conversations
    inquiries: int  # I'm the buyer on these listing conversations
    dms: int  # direct-message conversations (no listing)
    total: int  # listings + inquiries + dms


class MarkReadOut(BaseModel):
    marked_read: int


class CourseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    title: str


EnrollmentKind = Literal["past", "current", "upcoming"]


class EnrollmentIn(BaseModel):
    course_id: uuid.UUID
    term: str = Field(min_length=1, max_length=20)
    kind: EnrollmentKind


class EnrollmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    course: CourseOut
    term: str
    kind: EnrollmentKind


Condition = Literal["new", "like_new", "good", "fair", "poor"]
ListingStatus = Literal["active", "reserved", "sold", "withdrawn"]
ListingCategory = Literal[
    "book",
    "furniture",
    "electronics",
    "clothing",
    "kitchen",
    "decor",
    "sports",
    "transportation",
    "other",
]
PaymentMethod = Literal["cash", "venmo", "zelle", "paypal", "stripe"]


class ListingCreate(BaseModel):
    # 'book' (default for the Sell-a-book form) or one of the Everything
    # Else categories. Determines which other fields are required.
    category: ListingCategory = "book"
    course_id: uuid.UUID | None = None
    title: str = Field(min_length=1, max_length=200)
    author: str | None = Field(default=None, max_length=200)
    edition: str | None = Field(default=None, max_length=40)
    condition: Condition
    price_cents: int = Field(ge=0)
    description: str = Field(default="", max_length=2000)
    # Methods the seller is willing to accept. Empty list = unspecified
    # (the UI hides the "Accepts:" line in that case).
    payment_methods: list[PaymentMethod] = Field(default_factory=list)


class ListingUpdate(BaseModel):
    # All fields optional — Settings tab on /my-listings/:id sends only
    # the ones that changed. Status can transition active → reserved →
    # sold → withdrawn ("Take down" sets status='withdrawn').
    status: ListingStatus | None = None
    price_cents: int | None = Field(default=None, ge=0)
    description: str | None = Field(default=None, max_length=2000)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    author: str | None = Field(default=None, max_length=200)
    edition: str | None = Field(default=None, max_length=40)
    condition: Condition | None = None
    course_id: uuid.UUID | None = None  # set to null to unlink from a course
    # Category changes are unusual but allowed (e.g., re-categorize an item).
    category: ListingCategory | None = None
    # Send an empty list to clear all accepted methods; omit to leave
    # them unchanged.
    payment_methods: list[PaymentMethod] | None = None


class ListingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    seller: UserOut
    course: CourseOut | None = None
    category: ListingCategory
    title: str
    author: str | None
    edition: str | None
    condition: Condition
    price_cents: int
    description: str
    status: ListingStatus
    image_url: str | None = None
    payment_methods: list[PaymentMethod] = Field(default_factory=list)
    created_at: datetime
    # Populated by GET /api/me/listings — count of incoming messages across
    # this listing's conversations the seller hasn't read. 0 elsewhere.
    unread_count: int = 0


class MatchedListingOut(ListingOut):
    rationale: str
    score: float


class MessageIn(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    sender_id: str
    body: str
    created_at: datetime
    read_at: datetime | None = None


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    # None for direct-message conversations (a DM started from the
    # Classmates page is not tied to any listing).
    listing: ListingOut | None = None
    buyer: UserOut
    other_user: UserOut
    updated_at: datetime
    last_message: MessageOut | None = None
    # Incoming messages addressed to the viewer that aren't yet read.
    # Populated by the conversations list endpoint per row; 0 elsewhere.
    unread_count: int = 0


class SharedCourseOut(CourseOut):
    """A course shared with a classmate, annotated with the OTHER user's
    enrollment kind for that course (past / current / upcoming). Lets
    the frontend color-code each chip so viewers can tell at a glance
    whether a classmate took the class, is taking it now, or will take
    it. The viewer's own kind for the course is always 'current' — those
    are the courses the classmates query is scoped to."""

    kind: EnrollmentKind


class ClassmateOut(BaseModel):
    id: str
    display_name: str
    avatar_url: str | None = None
    shared_courses: list[SharedCourseOut]
    # Populated by GET /api/classmates so the Classmates page can render
    # an inline DM thread without an extra round-trip. null = no DM has
    # been started with this classmate yet (clicking creates one).
    dm_conversation_id: uuid.UUID | None = None
    # Count of incoming messages in that DM the viewer hasn't read.
    unread_count: int = 0
