"""SQLAlchemy models. See docs in README.md (Database section) for the ERD."""
import enum
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    LargeBinary,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Role(str, enum.Enum):
    teacher = "teacher"
    admin = "admin"


class SubscriptionStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class Rating(str, enum.Enum):
    good = "good"  # ดี
    fair = "fair"  # ปานกลาง
    improve = "improve"  # ปรับปรุง


class LearnerGroup(str, enum.Enum):
    high = "high"  # มีความพร้อมสูงทุกด้าน
    medium = "medium"  # มีความพร้อมปานกลาง
    low = "low"  # ไม่มีความพร้อม
    disability = "disability"  # บกพร่องทางการเรียนรู้


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    # Empty for accounts created with Google that never set a password.
    password_hash: Mapped[str] = mapped_column(String(100))
    # Google account id ("sub"), set when the teacher signs in with Google.
    google_sub: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    role: Mapped[Role] = mapped_column(Enum(Role, native_enum=False, length=16), default=Role.teacher)
    full_name: Mapped[str] = mapped_column(String(120))
    position: Mapped[str] = mapped_column(String(80), default="ครู")
    school_name: Mapped[str] = mapped_column(String(160), default="")
    # กลุ่มงาน / กลุ่มสาระ, printed as ส่วนราชการ in the memo, e.g. "กลุ่มบริหารวิชาการ".
    department: Mapped[str] = mapped_column(String(120), default="", server_default="")
    # อำเภอ / จังหวัด of the school, appended to ส่วนราชการ, e.g. "อำเภอเมือง จังหวัดหนองบัวลำภู".
    school_location: Mapped[str] = mapped_column(String(160), default="", server_default="")
    area_office: Mapped[str] = mapped_column(String(200), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    classrooms: Mapped[list["Classroom"]] = relationship(back_populates="teacher", cascade="all, delete-orphan")


class Subscription(Base):
    """One paid term of use for one teacher."""

    __tablename__ = "subscriptions"
    __table_args__ = (UniqueConstraint("teacher_id", "academic_year", "semester", name="uq_subscription_term"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    academic_year: Mapped[int] = mapped_column(SmallInteger)  # Buddhist year, e.g. 2569
    semester: Mapped[int] = mapped_column(SmallInteger)  # 1 or 2
    amount: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus, native_enum=False, length=16), default=SubscriptionStatus.pending
    )
    slip_path: Mapped[str] = mapped_column(String(255), default="")  # unused: slips are kept in payment_slips
    # Why the admin rejected the slip, shown to the teacher.
    reject_reason: Mapped[str] = mapped_column(String(200), default="", server_default="")
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    # Time of the latest slip upload (a rejected slip can be sent again).
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    teacher: Mapped["User"] = relationship(foreign_keys=[teacher_id])
    slip: Mapped["PaymentSlip | None"] = relationship(
        back_populates="subscription", cascade="all, delete-orphan", uselist=False, lazy="select"
    )


class PaymentSlip(Base):
    """The transfer slip image for a subscription, kept in the database because
    Railway's disk is wiped on every deploy. Re-encoded as JPEG on upload."""

    __tablename__ = "payment_slips"

    subscription_id: Mapped[int] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="CASCADE"), primary_key=True
    )
    mime: Mapped[str] = mapped_column(String(40), default="image/jpeg")
    data: Mapped[bytes] = mapped_column(LargeBinary(length=16_777_215))  # MEDIUMBLOB on MySQL
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    subscription: Mapped[Subscription] = relationship(back_populates="slip")


class Classroom(Base):
    """One subject taught to one class in one term, e.g. คณิตศาสตร์ ม.6/1 ภาคเรียนที่ 1/2569."""

    __tablename__ = "classrooms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    subject_name: Mapped[str] = mapped_column(String(120))
    subject_code: Mapped[str] = mapped_column(String(20), default="")
    grade_label: Mapped[str] = mapped_column(String(40))  # e.g. "มัธยมศึกษาปีที่ 6/1"
    academic_year: Mapped[int] = mapped_column(SmallInteger)
    semester: Mapped[int] = mapped_column(SmallInteger)
    # Random, unguessable part of the student link /f/<public_token>.
    public_token: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    is_open: Mapped[bool] = mapped_column(Boolean, default=True)
    is_trial: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    teacher: Mapped[User] = relationship(back_populates="classrooms")
    roster: Mapped[list["RosterEntry"]] = relationship(
        back_populates="classroom", cascade="all, delete-orphan", order_by="RosterEntry.student_no"
    )
    submissions: Mapped[list["Submission"]] = relationship(
        back_populates="classroom", cascade="all, delete-orphan", order_by="Submission.student_no"
    )


class RosterEntry(Base):
    """Optional class list pasted by the teacher."""

    __tablename__ = "roster_entries"
    __table_args__ = (UniqueConstraint("classroom_id", "student_no", name="uq_roster_no"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    classroom_id: Mapped[int] = mapped_column(ForeignKey("classrooms.id", ondelete="CASCADE"), index=True)
    student_no: Mapped[int] = mapped_column(SmallInteger)
    full_name: Mapped[str] = mapped_column(String(120))

    classroom: Mapped[Classroom] = relationship(back_populates="roster")


class Submission(Base):
    """One student's self-analysis in one classroom."""

    __tablename__ = "submissions"
    __table_args__ = (UniqueConstraint("classroom_id", "student_no", name="uq_submission_no"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    classroom_id: Mapped[int] = mapped_column(ForeignKey("classrooms.id", ondelete="CASCADE"), index=True)
    student_no: Mapped[int] = mapped_column(SmallInteger)
    full_name: Mapped[str] = mapped_column(String(120))
    nickname: Mapped[str] = mapped_column(String(40), default="")
    personal_info: Mapped[dict] = mapped_column(JSON, default=dict)
    open_answers: Mapped[dict] = mapped_column(JSON, default=dict)
    # Ordered list of learning-method keys, most preferred first.
    learning_prefs: Mapped[list] = mapped_column(JSON, default=list)
    consent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Empty for a record the teacher created for a student without a phone.
    edit_code_hash: Mapped[str] = mapped_column(String(100), default="")
    created_by_teacher: Mapped[bool] = mapped_column(Boolean, default=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    classroom: Mapped[Classroom] = relationship(back_populates="submissions")
    evaluation: Mapped["Evaluation | None"] = relationship(
        back_populates="submission", cascade="all, delete-orphan", uselist=False
    )


class AssessmentItem(Base):
    """The 16 assessment items of part 3 (seeded by the first migration)."""

    __tablename__ = "assessment_items"

    code: Mapped[str] = mapped_column(String(10), primary_key=True)
    domain_no: Mapped[int] = mapped_column(SmallInteger)
    domain_name: Mapped[str] = mapped_column(String(120))
    item_no: Mapped[int] = mapped_column(SmallInteger)
    label: Mapped[str] = mapped_column(String(120))
    sort_order: Mapped[int] = mapped_column(SmallInteger)


class Evaluation(Base):
    """The teacher's assessment of one submission."""

    __tablename__ = "evaluations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    submission_id: Mapped[int] = mapped_column(
        ForeignKey("submissions.id", ondelete="CASCADE"), unique=True, index=True
    )
    last_grade: Mapped[str] = mapped_column(String(10), default="")
    teacher_comment: Mapped[str] = mapped_column(Text, default="")
    # Set when the teacher overrides the automatic group, or marks a learning disability.
    group_override: Mapped[LearnerGroup | None] = mapped_column(
        Enum(LearnerGroup, native_enum=False, length=16), nullable=True
    )
    evaluated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    submission: Mapped[Submission] = relationship(back_populates="evaluation")
    scores: Mapped[list["EvaluationScore"]] = relationship(back_populates="evaluation", cascade="all, delete-orphan")


class EvaluationScore(Base):
    __tablename__ = "evaluation_scores"

    evaluation_id: Mapped[int] = mapped_column(ForeignKey("evaluations.id", ondelete="CASCADE"), primary_key=True)
    item_code: Mapped[str] = mapped_column(ForeignKey("assessment_items.code"), primary_key=True)
    rating: Mapped[Rating] = mapped_column(Enum(Rating, native_enum=False, length=10))
    improvement_note: Mapped[str] = mapped_column(String(200), default="")

    evaluation: Mapped[Evaluation] = relationship(back_populates="scores")
