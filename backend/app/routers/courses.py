from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Course
from app.schemas.common import CourseOut


router = APIRouter(prefix="/api/courses", tags=["courses"])


@router.get("", response_model=list[CourseOut])
def list_courses(db: Session = Depends(get_db)) -> list[Course]:
    """List all UATX courses. Public so the onboarding picker works pre-signin."""
    stmt = select(Course).order_by(Course.code)
    return list(db.execute(stmt).scalars().all())
