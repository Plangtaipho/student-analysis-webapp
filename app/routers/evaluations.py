"""Teacher API: assess each student (16 items), class summary, and manual records."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, get_owned_classroom, verify_csrf
from app.models import Evaluation, EvaluationScore, LearnerGroup, Rating, Submission, User
from app.routers.classrooms import get_owned_submission
from app.schemas import EvaluationIn, ManualSubmissionIn
from app.services.billing import student_limit, trial_full_message
from app.services.form_definition import ASSESSMENT_DOMAINS
from app.services.home_class import for_room, label, ordered
from app.services.summary import ITEM_CODES, auto_group, classroom_summary, group_of

router = APIRouter(prefix="/api/classrooms", tags=["evaluations"], dependencies=[Depends(verify_csrf)])


def _evaluation_out(sub: Submission) -> dict:
    ev = sub.evaluation
    room = sub.classroom
    subs = ordered(room.submissions)
    order = [s.id for s in subs]
    pending = [s.id for s in subs if s.evaluation is None and s.id != sub.id]
    later = [i for i in pending if order.index(i) > order.index(sub.id)]
    return {
        "submission_id": sub.id,
        "home_class": sub.home_class,
        "student_no": sub.student_no,
        "full_name": sub.full_name,
        "nickname": sub.nickname,
        "created_by_teacher": sub.created_by_teacher,
        "domains": [
            {"domain_no": n, "domain_name": name, "items": [{"code": c, "label": lbl} for c, lbl in items]}
            for n, name, items in ASSESSMENT_DOMAINS
        ],
        "evaluated": ev is not None,
        "scores": {s.item_code: {"rating": s.rating.value, "note": s.improvement_note} for s in ev.scores} if ev else {},
        "last_grade": ev.last_grade if ev else "",
        "teacher_comment": ev.teacher_comment if ev else "",
        "group_override": ev.group_override.value if ev and ev.group_override else None,
        "group": group_of(sub).value if ev else None,
        # Next student still waiting for an assessment (after this one, else from the top).
        "next_pending_id": (later or pending or [None])[0],
        "prev_id": order[order.index(sub.id) - 1] if order.index(sub.id) > 0 else None,
        "next_id": order[order.index(sub.id) + 1] if order.index(sub.id) + 1 < len(order) else None,
    }


@router.get("/{classroom_id}/submissions/{submission_id}/evaluation")
def get_evaluation(
    classroom_id: int, submission_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return _evaluation_out(get_owned_submission(classroom_id, submission_id, user, db))


@router.put("/{classroom_id}/submissions/{submission_id}/evaluation")
def save_evaluation(
    classroom_id: int,
    submission_id: int,
    body: EvaluationIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Save all 16 ratings at once (a half-done assessment would skew the class summary)."""
    sub = get_owned_submission(classroom_id, submission_id, user, db)
    unknown = set(body.scores) - set(ITEM_CODES)
    missing = [c for c in ITEM_CODES if c not in body.scores]
    if unknown:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "มีหัวข้อประเมินที่ไม่รู้จัก")
    if missing:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, f"กรุณาประเมินให้ครบทุกข้อ (ยังขาด {len(missing)} ข้อ)"
        )
    ev = sub.evaluation
    if ev is None:
        ev = Evaluation(submission_id=sub.id)
        db.add(ev)
        sub.evaluation = ev
    ev.last_grade = body.last_grade
    ev.teacher_comment = body.teacher_comment
    ev.group_override = LearnerGroup(body.group_override) if body.group_override else None
    by_code = {s.item_code: s for s in ev.scores}
    for code in ITEM_CODES:
        given = body.scores[code]
        score = by_code.get(code)
        if score is None:
            score = EvaluationScore(item_code=code, rating=Rating(given.rating), improvement_note=given.note)
            ev.scores.append(score)
        else:
            score.rating = Rating(given.rating)
            score.improvement_note = given.note
    db.commit()
    db.refresh(sub)
    return _evaluation_out(sub)


@router.delete("/{classroom_id}/submissions/{submission_id}/evaluation", status_code=status.HTTP_204_NO_CONTENT)
def clear_evaluation(
    classroom_id: int, submission_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    sub = get_owned_submission(classroom_id, submission_id, user, db)
    if sub.evaluation is not None:
        db.delete(sub.evaluation)
        db.commit()


@router.post("/{classroom_id}/submissions/manual", status_code=status.HTTP_201_CREATED)
def create_manual_submission(
    classroom_id: int, body: ManualSubmissionIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """For a student without a phone: an empty record the teacher can assess."""
    room = get_owned_classroom(classroom_id, user, db)
    try:
        home_class = for_room(room, body.home_class)
    except ValueError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(e)) from None
    exists = db.scalar(
        select(Submission).where(
            Submission.classroom_id == room.id,
            Submission.home_class == home_class,
            Submission.student_no == body.student_no,
        )
    )
    if exists:
        what = label(home_class, body.student_no) + " " if room.mixed_classes else "เลขที่นี้"
        raise HTTPException(status.HTTP_409_CONFLICT, f"{what}มีข้อมูลอยู่แล้ว")
    limit = student_limit(db, room)
    if limit is not None and len(room.submissions) >= limit:
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, trial_full_message(limit))
    roster_name = next(
        (r.full_name for r in room.roster if (r.home_class, r.student_no) == (home_class, body.student_no)), None
    )
    sub = Submission(
        classroom_id=room.id,
        home_class=home_class,
        student_no=body.student_no,
        full_name=roster_name or body.full_name,
        created_by_teacher=True,
    )
    db.add(sub)
    db.commit()
    return {"id": sub.id}


@router.get("/{classroom_id}/summary")
def get_summary(classroom_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    room = get_owned_classroom(classroom_id, user, db)
    return classroom_summary(room)


@router.get("/{classroom_id}/auto-group-preview")
def auto_group_preview(ratings: str = "", user: User = Depends(get_current_user)):
    """Which group a set of ratings falls in (lets the page show the group live while assessing)."""
    try:
        values = [Rating(r) for r in ratings.split(",") if r]
    except ValueError:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "ค่าไม่ถูกต้อง") from None
    return {"group": auto_group(values).value}
