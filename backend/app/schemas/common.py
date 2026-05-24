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


class CourseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    title: str


class EnrollmentIn(BaseModel):
    course_id: uuid.UUID
    term: str = Field(min_length=1, max_length=20)
    is_current: bool = False


class EnrollmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    course: CourseOut
    term: str
    is_current: bool


Condition = Literal["new", "like_new", "good", "fair", "poor"]
ListingStatus = Literal["active", "reserved", "sold", "withdrawn"]


class ListingCreate(BaseModel):
    course_id: uuid.UUID | None = None
    book_title: str = Field(min_length=1, max_length=200)
    book_author: str = Field(min_length=1, max_length=200)
    book_edition: str | None = Field(default=None, max_length=40)
    condition: Condition
    price_cents: int = Field(ge=0)
    description: str = Field(default="", max_length=2000)


class ListingUpdate(BaseModel):
    status: ListingStatus | None = None
    price_cents: int | None = Field(default=None, ge=0)
    description: str | None = Field(default=None, max_length=2000)


class ListingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    seller: UserOut
    course: CourseOut | None = None
    book_title: str
    book_author: str
    book_edition: str | None
    condition: Condition
    price_cents: int
    description: str
    status: ListingStatus
    created_at: datetime


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
    listing: ListingOut
    buyer: UserOut
    updated_at: datetime
    last_message: MessageOut | None = None
