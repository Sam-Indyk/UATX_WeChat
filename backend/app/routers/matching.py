"""The bronze nontrivial piece: course-history-based matching.

Given a signed-in user, return active listings for the books in the courses
they're currently enrolled in, ranked by how likely the listing's edition
matches what their professor will assign.

Ranking inputs, in order of weight:
  1. Seller course recency. A seller who took the same course last semester
     used a recent edition; a seller from four semesters ago might be on an
     older edition. We map terms to a numeric "term index" and use the
     seller's most recent enrollment in the matching course.
  2. Listing freshness. Newer listings rank higher within the same recency
     bucket — fresher posts are more likely still available.
  3. Lower price first.

Edge cases that matter (covered in tests/test_matching.py):
  - User has no current enrollments → empty list.
  - User's own listings are always excluded.
  - Listings with status != 'active' never appear.
  - A listing's seller might have multiple past enrollments in the course;
    we take the most recent one.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.auth import require_user
from app.db import get_db
from app.models import Course, Enrollment, Listing, User
from app.schemas.common import MatchedListingOut


router = APIRouter(prefix="/api", tags=["matching"])


_TERM_PATTERN = re.compile(r"(?P<season>spring|summer|fall|winter)\s+(?P<year>\d{4})", re.I)
_SEASON_ORDER = {"spring": 0, "summer": 1, "fall": 2, "winter": 3}


def _term_index(term: str) -> int:
    """Map a term string like 'Fall 2024' to a sortable integer.

    Higher is more recent. Unknown formats sort lowest (0). Centralizing this
    here means the matching algorithm doesn't depend on the exact string
    format we store — if we later switch to (year, season) columns, only this
    function changes.
    """
    if not term:
        return 0
    m = _TERM_PATTERN.search(term)
    if not m:
        return 0
    year = int(m.group("year"))
    season = m.group("season").lower()
    return year * 10 + _SEASON_ORDER.get(season, 0)


@dataclass
class _Ranked:
    listing: Listing
    seller_term: str | None
    recency: int
    score: float

    def rationale(self) -> str:
        if self.seller_term:
            return (
                f"Seller took {self.listing.course.code} in {self.seller_term}"
                if self.listing.course
                else f"Seller took the matching course in {self.seller_term}"
            )
        return "Seller hasn't taken this course (matched by book only)"


def match_listings_for_user(db: Session, user: User) -> list[_Ranked]:
    """The matching algorithm. Pure-ish: takes a session and user, returns ranked rows.

    Exposed as a function (not a route handler) so tests can call it directly
    without going through HTTP, and so silver/gold variants can reuse the
    same primitives.
    """
    # 1. Courses the user is currently enrolled in.
    current_course_ids = list(
        db.execute(
            select(Enrollment.course_id).where(
                Enrollment.user_id == user.id, Enrollment.is_current.is_(True)
            )
        ).scalars()
    )
    if not current_course_ids:
        return []

    # 2. Active listings tied to those courses, excluding the user's own.
    listings = list(
        db.execute(
            select(Listing)
            .options(joinedload(Listing.seller), joinedload(Listing.course))
            .where(
                Listing.course_id.in_(current_course_ids),
                Listing.status == "active",
                Listing.seller_id != user.id,
            )
        ).scalars()
    )
    if not listings:
        return []

    # 3. For each (seller, course) pair we need, look up the seller's most
    #    recent enrollment term. Batch the query.
    seller_course_pairs = {(l.seller_id, l.course_id) for l in listings if l.course_id}
    seller_terms: dict[tuple[str, object], str] = {}
    if seller_course_pairs:
        seller_ids = {sid for sid, _ in seller_course_pairs}
        course_ids = {cid for _, cid in seller_course_pairs}
        rows = db.execute(
            select(Enrollment.user_id, Enrollment.course_id, Enrollment.term).where(
                Enrollment.user_id.in_(seller_ids),
                Enrollment.course_id.in_(course_ids),
            )
        ).all()
        # Keep the most-recent term for each (user, course) pair.
        for sid, cid, term in rows:
            key = (sid, cid)
            current_best = seller_terms.get(key)
            if current_best is None or _term_index(term) > _term_index(current_best):
                seller_terms[key] = term

    # 4. Score each listing.
    now = datetime.now(timezone.utc)
    ranked: list[_Ranked] = []
    for listing in listings:
        seller_term = seller_terms.get((listing.seller_id, listing.course_id))
        recency = _term_index(seller_term) if seller_term else 0

        # Composite score: recency dominates, then freshness, then a small
        # price penalty. The exact weights are not magic — they're chosen so
        # that recency strictly beats freshness, and freshness strictly beats
        # price within reasonable ranges, while still letting price break
        # otherwise-tied recommendations.
        freshness_days = max(
            0.0, (now - listing.created_at.replace(tzinfo=timezone.utc)).total_seconds() / 86400.0
        )
        freshness_score = max(0.0, 30.0 - freshness_days)  # newer in last 30 days helps
        price_penalty = listing.price_cents / 10000.0  # $1 = 0.0001 weight

        score = (recency * 1000.0) + (freshness_score * 10.0) - price_penalty

        ranked.append(_Ranked(listing=listing, seller_term=seller_term, recency=recency, score=score))

    ranked.sort(key=lambda r: r.score, reverse=True)
    return ranked


@router.get("/match", response_model=list[MatchedListingOut])
def get_match_feed(
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> list[MatchedListingOut]:
    ranked = match_listings_for_user(db, user)
    # Hand-construct the response so we can attach `rationale` and `score`.
    return [
        MatchedListingOut(
            id=r.listing.id,
            seller=r.listing.seller,
            course=r.listing.course,
            book_title=r.listing.book_title,
            book_author=r.listing.book_author,
            book_edition=r.listing.book_edition,
            condition=r.listing.condition,
            price_cents=r.listing.price_cents,
            description=r.listing.description,
            status=r.listing.status,
            created_at=r.listing.created_at,
            rationale=r.rationale(),
            score=round(r.score, 3),
        )
        for r in ranked
    ]
