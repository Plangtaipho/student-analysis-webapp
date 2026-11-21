"""Public API used by students through the classroom link /f/<token>. No login."""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import client_ip
from app.models import Classroom, RosterEntry, Submission, utcnow
from app.schemas import LookupIn, SubmissionIn
from app.security import (
    DUMMY_HASH,
    edit_code_limiter,
    hash_edit_code,
    new_edit_code,
    submit_limiter,
    verify_password,
)
from app.services.billing import room_is_active

router = APIRouter(prefix="/api/f", tags=["student"])


def get_room_by_token(token: str, db: Session) -> Classroom:
    room = db.scalar(select(Classroom).where(Classroom.public_token == token)) if len(token) <= 32 else None
    if room is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "ไม่พบแบบฟอร์มนี้ กรุณาตรวจสอบลิงก์จากครู")
    return room


def room_info(room: Classroom, db: Session) -> dict:
    t = room.teacher
    return {
        "subject_name": room.subject_name,
        "subject_code": room.subject_code,
        "grade_label": room.grade_label,
        "academic_year": room.academic_year,
        "semester": room.semester,
        "teacher_name": f"{t.position}{t.full_name}" if t.position == "ครู" else t.full_name,
        "school_name": t.school_name,
        "is_open": room.is_open,
        "is_active": room_is_active(db, room),
        "has_roster": bool(room.roster),
    }


def _require_open(room: Classroom) -> None:
    if not room.is_open:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "ครูปิดรับคำตอบของห้องนี้แล้ว หากต้องการส่งหรือแก้ไข กรุณาติดต่อครู")


def _check_code(room: Classroom, sub: Submission | None, student_no: int, code: str, request: Request) -> Submission:
    key = f"{room.id}|{student_no}"
    ip_key = f"ip|{client_ip(request)}"
    if edit_code_limiter.is_blocked(key) or edit_code_limiter.is_blocked(ip_key):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS, "ใส่รหัสผิดหลายครั้งเกินไป กรุณารอ 1 ชั่วโมง หรือขอรหัสใหม่จากครู"
        )
    ok = verify_password(code, sub.edit_code_hash if sub else DUMMY_HASH)
    if not sub or not ok:
        edit_code_limiter.record_failure(key)
        edit_code_limiter.record_failure(ip_key)
        raise HTTPException(status.HTTP_403_FORBIDDEN, "เลขที่หรือรหัสแก้ไขไม่ถูกต้อง")
    edit_code_limiter.reset(key)
    return sub


@router.get("/{token}")
def get_form(token: str, db: Session = Depends(get_db)):
    return room_info(get_room_by_token(token, db), db)


@router.post("/{token}/submissions", status_code=status.HTTP_201_CREATED)
def submit(token: str, body: SubmissionIn, request: Request, db: Session = Depends(get_db)):
    """Send the form. With `edit_code`, replaces the answers sent before by the same student number."""
    room = get_room_by_token(token, db)
    _require_open(room)
    if not room_is_active(db, room):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "ห้องนี้ยังไม่เปิดใช้งาน กรุณาแจ้งครูผู้สอน")

    roster_name = None
    if room.roster:
        entry = db.scalar(
            select(RosterEntry).where(RosterEntry.classroom_id == room.id, RosterEntry.student_no == body.student_no)
        )
        if entry is None:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT, "ไม่พบเลขที่นี้ในรายชื่อของห้อง กรุณาตรวจสอบเลขที่ หรือแจ้งครู"
            )
        roster_name = entry.full_name

    existing = db.scalar(
        select(Submission).where(Submission.classroom_id == room.id, Submission.student_no == body.student_no)
    )
    new_code: str | None = None
    if body.edit_code:
        sub = _check_code(room, existing, body.student_no, body.edit_code, request)
    else:
        if existing is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "เลขที่นี้ส่งแบบฟอร์มแล้ว ถ้าต้องการแก้ไข ให้กด 'แก้ไขคำตอบเดิม' แล้วใส่รหัสแก้ไข หรือแจ้งครู",
            )
        ip = client_ip(request)
        if submit_limiter.is_blocked(ip):
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "ส่งบ่อยเกินไป กรุณาลองใหม่ภายหลัง")
        submit_limiter.record_failure(ip)
        new_code = new_edit_code()
        sub = Submission(classroom_id=room.id, student_no=body.student_no, edit_code_hash=hash_edit_code(new_code))
        db.add(sub)

    sub.full_name = roster_name or body.full_name
    sub.nickname = body.nickname
    sub.personal_info = body.personal_info
    sub.open_answers = body.open_answers
    sub.learning_prefs = body.learning_prefs
    sub.consent_at = utcnow()
    db.commit()
    return {"student_no": sub.student_no, "full_name": sub.full_name, "edit_code": new_code, "updated": new_code is None}


@router.post("/{token}/lookup")
def lookup(token: str, body: LookupIn, request: Request, db: Session = Depends(get_db)):
    """Load a student's earlier answers so they can edit them, after checking the edit code."""
    room = get_room_by_token(token, db)
    _require_open(room)
    existing = db.scalar(
        select(Submission).where(Submission.classroom_id == room.id, Submission.student_no == body.student_no)
    )
    sub = _check_code(room, existing, body.student_no, body.edit_code, request)
    return {
        "student_no": sub.student_no,
        "full_name": sub.full_name,
        "nickname": sub.nickname,
        "personal_info": sub.personal_info,
        "open_answers": sub.open_answers,
        "learning_prefs": sub.learning_prefs,
    }
