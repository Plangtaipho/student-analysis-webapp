"""Who may use which classroom.

Rules (agreed with the user, updated 2026-11-23):
- A teacher's first classroom is a free trial for one subject, limited to
  TRIAL_STUDENT_LIMIT students until its semester is paid.
- Every other classroom needs a payment for its semester: one payment covers
  all of that teacher's classrooms in that semester, with no limit on how many.
- The PromptPay QR fixes the amount, so an uploaded slip is accepted at once
  (no admin approval). The admin can still reject a bad slip, which locks again.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Classroom, Subscription, SubscriptionStatus

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
