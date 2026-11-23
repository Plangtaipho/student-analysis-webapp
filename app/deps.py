"""Shared FastAPI dependencies: current user, ownership checks, CSRF check."""
import secrets
from datetime import date, datetime
from zoneinfo import ZoneInfo

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import Classroom, Role, User


def today() -> date:
    """Today's date in Thailand (the server itself runs in UTC)."""
    return datetime.now(ZoneInfo(get_settings().timezone)).date()


def current_academic_term(d: date | None = None) -> tuple[int, int]:
    """Best guess of the Thai academic year and semester for a date.

    Semester 1 runs about May-October, semester 2 about November-March.
    January-April still belong to semester 2 of the previous academic year.
    """
    d = d or today()
    be_year = d.year + 543
    if d.month >= 11:
        return be_year, 2
    if d.month <= 4:
        return be_year - 1, 2
    return be_year, 1


def client_ip(request: Request) -> str:
    # Railway's edge proxy APPENDS the address it saw. Anything before it was sent by the
    # client and can be faked, so only the last entry is trusted (rate limits depend on it).
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


def get_optional_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        request.session.clear()
        return None
    return user


def get_current_user(user: User | None = Depends(get_optional_user)) -> User:
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "กรุณาเข้าสู่ระบบ")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != Role.admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "เฉพาะผู้ดูแลระบบเท่านั้น")
    return user


def get_owned_classroom(classroom_id: int, user: User, db: Session) -> Classroom:
    """A classroom the current teacher owns. Someone else's room looks the same as a missing one."""
    room = db.get(Classroom, classroom_id)
    if room is None or room.teacher_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "ไม่พบห้องเรียนนี้")
    return room


def verify_csrf(request: Request) -> None:
    """State-changing calls from a logged-in teacher must echo the session's CSRF token."""
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return
    expected = request.session.get("csrf")
    sent = request.headers.get("X-CSRF-Token", "")
    if not expected or not secrets.compare_digest(expected, sent):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "คำขอไม่ถูกต้อง กรุณารีเฟรชหน้าแล้วลองใหม่")
