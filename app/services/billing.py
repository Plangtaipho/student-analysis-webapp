"""Who may use which classroom.

Rules (agreed with the user, 2026-11-21):
- A teacher's first classroom is a free trial and always works.
- Every other classroom needs a payment for its semester: one payment covers
  all of that teacher's classrooms in that semester, with no limit on how many.
- A slip waiting for review already unlocks the classrooms, so teachers are not
  stuck waiting for the admin. A rejected slip locks them again.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Classroom, Subscription, SubscriptionStatus

UNLOCKING = (SubscriptionStatus.pending, SubscriptionStatus.approved)

STATUS_TEXT = {
    None: "ยังไม่ได้ชำระ",
    SubscriptionStatus.pending: "รอตรวจสอบสลิป",
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


def room_is_active(db: Session, room: Classroom) -> bool:
    if room.is_trial:
        return True
    sub = term_subscription(db, room.teacher_id, room.academic_year, room.semester)
    return sub is not None and sub.status in UNLOCKING
