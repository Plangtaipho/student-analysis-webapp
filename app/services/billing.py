"""Who may use which classroom.

Rules (agreed with the user, updated 2026-11-23):
- A teacher's first classroom is a free trial for one subject, limited to
  TRIAL_STUDENT_LIMIT students until its semester is paid.
- Every other classroom needs a payment for its semester: one payment covers
  all of that teacher's classrooms in that semester, with no limit on how many.
- After paying, the teacher's name and school are locked until the paid term
  ends (decision 2026-11-26), so one paid account cannot print reports for
  several teachers by changing the name. They may still fix typos for
  NAME_EDIT_GRACE after paying; later the admin corrects them.
- The PromptPay QR fixes the amount, so an uploaded slip is accepted at once
  (no admin approval). The admin can still reject a bad slip, which locks again.
"""
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Classroom, Subscription, SubscriptionStatus, utcnow
from app.services.retention import term_end

UNLOCKING = (SubscriptionStatus.pending, SubscriptionStatus.approved)

STATUS_TEXT = {
    None: "ยังไม่ได้ชำระ",
    SubscriptionStatus.pending: "ชำระแล้ว",
    SubscriptionStatus.approved: "ชำระแล้ว",
    SubscriptionStatus.rejected: "สลิปไม่ผ่าน",
}

LOCKED_MESSAGE = "ห้องนี้ยังไม่ได้เปิดใช้งาน กรุณาชำระค่าบริการของภาคเรียนนี้ที่เมนู 'ชำระเงิน'"


def term_subscription(db: Session, teacher_id: int, academic_year: int, semester: int) -> Subscription | None:
    return db.scalar(
        select(Subscription).where(
            Subscription.teacher_id == teacher_id,
            Subscription.academic_year == academic_year,
            Subscription.semester == semester,
        )
    )


def term_is_paid(db: Session, room: Classroom) -> bool:
    sub = term_subscription(db, room.teacher_id, room.academic_year, room.semester)
    return sub is not None and sub.status in UNLOCKING


def room_is_active(db: Session, room: Classroom) -> bool:
    return room.is_trial or term_is_paid(db, room)


def student_limit(db: Session, room: Classroom) -> int | None:
    """How many students the room accepts, or None for no limit."""
    if room.is_trial and not term_is_paid(db, room):
        return get_settings().trial_student_limit
    return None


def trial_full_message(limit: int) -> str:
    return f"ห้องทดลองใช้ฟรีรับนักเรียนได้ {limit} คน ชำระค่าบริการภาคเรียนนี้ที่เมนู 'ชำระเงิน' เพื่อรับนักเรียนได้ไม่จำกัด"


NAME_EDIT_GRACE = timedelta(hours=24)


def name_lock(db: Session, teacher_id: int, on: date) -> dict | None:
    """When the teacher's name and school may not change, the term that locks them and until when.

    Locked by any paid term that has not ended yet, once NAME_EDIT_GRACE has passed since paying."""
    now = utcnow()
    best = None
    for sub in db.scalars(
        select(Subscription).where(Subscription.teacher_id == teacher_id, Subscription.status.in_(UNLOCKING))
    ):
        until = term_end(sub.academic_year, sub.semester)
        if until < on:
            continue
        paid_at = sub.submitted_at or sub.approved_at or sub.created_at
        if paid_at and now - paid_at < NAME_EDIT_GRACE:
            continue
        if best is None or until > best["until"]:
            best = {"until": until, "term": f"{sub.semester}/{sub.academic_year}"}
    return best


def name_lock_out(lock: dict | None) -> dict | None:
    if lock is None:
        return None
    return {"until": lock["until"].isoformat(), "term": lock["term"]}


NAME_LOCKED_MESSAGE = (
    "ชื่อ-สกุลและโรงเรียนถูกล็อกไว้จนจบภาคเรียน {term} เพราะชำระค่าบริการแล้ว "
    "(1 บัญชีใช้ได้กับครู 1 คน) ถ้าพิมพ์ผิด ทักเพจ KruFlow ให้แอดมินแก้ให้"
)
