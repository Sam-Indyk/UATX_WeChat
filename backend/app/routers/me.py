from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.auth import require_user
from app.db import get_db
from app.models import Enrollment, User
from app.schemas.common import EnrollmentIn, EnrollmentOut, UserOut


router = APIRouter(prefix="/api/me", tags=["me"])


@router.get("", response_model=UserOut)
def get_me(user: User = Depends(require_user)) -> User:
    return user


@router.get("/enrollments", response_model=list[EnrollmentOut])
def list_my_enrollments(
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> list[Enrollment]:
    stmt = (
        select(Enrollment)
        .options(joinedload(Enrollment.course))
        .where(Enrollment.user_id == user.id)
        .order_by(Enrollment.is_current.desc(), Enrollment.term.desc())
    )
    return list(db.execute(stmt).scalars().all())


@router.post("/enrollments", response_model=EnrollmentOut, status_code=201)
def add_enrollment(
    payload: EnrollmentIn,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> Enrollment:
    enr = Enrollment(
        user_id=user.id,
        course_id=payload.course_id,
        term=payload.term,
        is_current=payload.is_current,
    )
    db.add(enr)
    db.commit()
    db.refresh(enr)
    # Eager-load course for the response model
    db.refresh(enr, attribute_names=["course"])
    return enr
