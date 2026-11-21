"""Teacher payments (PromptPay + slip upload) and the admin's review of slips."""
import io

import segno
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.config import get_settings
from app.database import get_db
from app.deps import (
    current_academic_term,
    get_current_user,
    require_admin,
    today,
    verify_csrf,
)
from app.models import (
    Classroom,
    PaymentSlip,
    Role,
    Subscription,
    SubscriptionStatus,
    User,
    utcnow,
)
from app.services import promptpay
from app.services.billing import STATUS_TEXT, term_subscription
from app.services.retention import purge_on

router = APIRouter(prefix="/api/billing", tags=["billing"], dependencies=[Depends(verify_csrf)])
admin_router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(verify_csrf)])

MAX_SLIP_BYTES = 8 * 1024 * 1024
SLIP_MAX_SIDE = 1800
Image.MAX_IMAGE_PIXELS = 40_000_000  # refuse decompression bombs


def _term_out(sub: Subscription | None, year: int, semester: int, rooms: int) -> dict:
    return {
        "academic_year": year,
        "semester": semester,
        "rooms": rooms,
        "status": sub.status.value if sub else "none",
        "status_text": STATUS_TEXT[sub.status if sub else None],
        "reject_reason": sub.reject_reason if sub else "",
        "submitted_at": sub.submitted_at.isoformat() + "Z" if sub and sub.submitted_at else None,
        "subscription_id": sub.id if sub else None,
        "has_slip": bool(sub and sub.slip is not None),
    }


@router.get("")
def billing_overview(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Price, PromptPay details and the payment state of every term the teacher has paid rooms in."""
    s = get_settings()
    rows = db.execute(
        select(Classroom.academic_year, Classroom.semester, func.count())
        .where(Classroom.teacher_id == user.id, Classroom.is_trial.is_(False))
        .group_by(Classroom.academic_year, Classroom.semester)
    ).all()
    terms = {(y, sem): n for y, sem, n in rows}
    terms.setdefault(current_academic_term(), 0)
    for sub in db.scalars(select(Subscription).where(Subscription.teacher_id == user.id)):
        terms.setdefault((sub.academic_year, sub.semester), 0)
    now = today()
    out = []
    for (year, sem), n in sorted(terms.items(), reverse=True):
        if purge_on(year, sem) <= now:
            continue  # data for that term is already deleted
        out.append(_term_out(term_subscription(db, user.id, year, sem), year, sem, n))
    return {
        "price": s.price_per_term,
        "promptpay_ready": bool(s.promptpay_id),
        "promptpay_name": s.promptpay_name,
        "terms": out,
    }


@router.get("/qr.svg")
def promptpay_qr(user: User = Depends(get_current_user)):
    s = get_settings()
    if not s.promptpay_id:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "ยังไม่ได้ตั้งค่าบัญชี PromptPay")
    qr = segno.make(promptpay.payload(s.promptpay_id, s.price_per_term), error="m")
    buf = io.BytesIO()
    qr.save(buf, kind="svg", scale=6, border=2, dark="#15315b")
    return Response(buf.getvalue(), media_type="image/svg+xml")


def _clean_slip(raw: bytes) -> bytes:
    """Decode the upload as an image and re-encode it as JPEG: drops metadata and anything that is not a picture."""
    try:
        with Image.open(io.BytesIO(raw)) as im:
            if im.format not in ("JPEG", "PNG", "WEBP"):
                raise ValueError
            im.load()
            im = im.convert("RGB")
            im.thumbnail((SLIP_MAX_SIDE, SLIP_MAX_SIDE))
            out = io.BytesIO()
            im.save(out, "JPEG", quality=82, optimize=True)
            return out.getvalue()
    except (UnidentifiedImageError, ValueError, OSError, Image.DecompressionBombError):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "ไฟล์สลิปต้องเป็นรูปภาพ JPG, PNG หรือ WEBP"
        ) from None


@router.post("/slip", status_code=status.HTTP_201_CREATED)
async def upload_slip(
    academic_year: int = Form(ge=2560, le=2700),
    semester: int = Form(ge=1, le=2),
    file: UploadFile = File(),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if purge_on(academic_year, semester) <= today():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "ภาคเรียนนี้จบไปแล้ว ไม่ต้องชำระค่าบริการ")
    raw = await file.read(MAX_SLIP_BYTES + 1)
    if len(raw) > MAX_SLIP_BYTES:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "ไฟล์ใหญ่เกิน 8 MB")
    data = _clean_slip(raw)

    sub = term_subscription(db, user.id, academic_year, semester)
    if sub is not None and sub.status == SubscriptionStatus.approved:
        raise HTTPException(status.HTTP_409_CONFLICT, "ภาคเรียนนี้ชำระและอนุมัติแล้ว")
    if sub is None:
        sub = Subscription(
            teacher_id=user.id,
            academic_year=academic_year,
            semester=semester,
            amount=get_settings().price_per_term,
        )
        db.add(sub)
    sub.status = SubscriptionStatus.pending
    sub.reject_reason = ""
    sub.submitted_at = utcnow()
    sub.amount = get_settings().price_per_term
    if sub.slip is None:
        sub.slip = PaymentSlip(data=data, mime="image/jpeg")
    else:
        sub.slip.data, sub.slip.created_at = data, utcnow()
    db.commit()
    return _term_out(sub, academic_year, semester, 0)


def _slip_response(sub: Subscription | None) -> Response:
    if sub is None or sub.slip is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "ไม่พบสลิป")
    return Response(
        sub.slip.data,
        media_type=sub.slip.mime,
        headers={"Content-Disposition": "inline", "Cache-Control": "private, no-store"},
    )


@router.get("/slips/{subscription_id}")
def my_slip(subscription_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sub = db.get(Subscription, subscription_id)
    if sub is None or sub.teacher_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "ไม่พบสลิป")
    return _slip_response(sub)


# --- Admin ------------------------------------------------------------------------------


def _admin_sub_out(sub: Subscription) -> dict:
    t = sub.teacher
    return {
        "id": sub.id,
        "teacher": {"id": t.id, "full_name": t.full_name, "email": t.email, "school_name": t.school_name},
        "academic_year": sub.academic_year,
        "semester": sub.semester,
        "amount": float(sub.amount),
        "status": sub.status.value,
        "status_text": STATUS_TEXT[sub.status],
        "reject_reason": sub.reject_reason,
        "submitted_at": sub.submitted_at.isoformat() + "Z" if sub.submitted_at else None,
        "approved_at": sub.approved_at.isoformat() + "Z" if sub.approved_at else None,
    }


@admin_router.get("/subscriptions")
def admin_subscriptions(
    status_filter: str = "pending", _: User = Depends(require_admin), db: Session = Depends(get_db)
):
    q = select(Subscription).options(selectinload(Subscription.teacher)).order_by(Subscription.submitted_at.desc())
    if status_filter != "all":
        try:
            q = q.where(Subscription.status == SubscriptionStatus(status_filter))
        except ValueError:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "สถานะไม่ถูกต้อง") from None
    return [_admin_sub_out(s) for s in db.scalars(q)]


@admin_router.get("/subscriptions/{subscription_id}/slip")
def admin_slip(subscription_id: int, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    return _slip_response(db.get(Subscription, subscription_id))


class RejectIn(BaseModel):
    reason: str = Field(min_length=2, max_length=200)


def _get_sub(db: Session, subscription_id: int) -> Subscription:
    sub = db.get(Subscription, subscription_id)
    if sub is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "ไม่พบรายการนี้")
    return sub


@admin_router.post("/subscriptions/{subscription_id}/approve")
def admin_approve(subscription_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    sub = _get_sub(db, subscription_id)
    sub.status = SubscriptionStatus.approved
    sub.reject_reason = ""
    sub.approved_by, sub.approved_at = admin.id, utcnow()
    db.commit()
    return _admin_sub_out(sub)


@admin_router.post("/subscriptions/{subscription_id}/reject")
def admin_reject(
    subscription_id: int, body: RejectIn, _: User = Depends(require_admin), db: Session = Depends(get_db)
):
    sub = _get_sub(db, subscription_id)
    sub.status = SubscriptionStatus.rejected
    sub.reject_reason = body.reason.strip()
    sub.approved_by, sub.approved_at = None, None
    db.commit()
    return _admin_sub_out(sub)


@admin_router.get("/teachers")
def admin_teachers(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    rooms = dict(db.execute(select(Classroom.teacher_id, func.count()).group_by(Classroom.teacher_id)).all())
    paid = dict(
        db.execute(
            select(Subscription.teacher_id, func.count())
            .where(Subscription.status == SubscriptionStatus.approved)
            .group_by(Subscription.teacher_id)
        ).all()
    )
    teachers = db.scalars(select(User).where(User.role == Role.teacher).order_by(User.created_at.desc())).all()
    return [
        {
            "id": t.id,
            "full_name": t.full_name,
            "email": t.email,
            "school_name": t.school_name,
            "created_at": t.created_at.isoformat() + "Z",
            "rooms": rooms.get(t.id, 0),
            "paid_terms": paid.get(t.id, 0),
            "is_active": t.is_active,
        }
        for t in teachers
    ]
