"""Teacher API: classrooms, class list, student link/QR, and received submissions."""
import io

import segno
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.deps import (
    current_academic_term,
    get_current_user,
    get_owned_classroom,
    today,
    verify_csrf,
)
from app.models import Classroom, Evaluation, RosterEntry, Submission, User
from app.schemas import (
    ClassroomIn,
    ClassroomOut,
    ClassroomPatch,
    RosterEntryOut,
    RosterIn,
)
from app.security import hash_edit_code, new_edit_code, new_public_token
from app.services.billing import room_is_active
from app.services.form_definition import LEARNING_METHOD_LABELS
from app.services.retention import purge_on, term_end
from app.services.roster import parse_roster

router = APIRouter(prefix="/api/classrooms", tags=["classrooms"], dependencies=[Depends(verify_csrf)])


def student_link(request: Request, room: Classroom) -> str:
    base = get_settings().public_base_url.rstrip("/") or str(request.base_url).rstrip("/")
    return f"{base}/f/{room.public_token}"


def _out(request: Request, db: Session, room: Classroom) -> ClassroomOut:
    submitted = db.scalar(select(func.count()).select_from(Submission).where(Submission.classroom_id == room.id)) or 0
    roster = db.scalar(select(func.count()).select_from(RosterEntry).where(RosterEntry.classroom_id == room.id)) or 0
    evaluated = (
        db.scalar(
            select(func.count())
            .select_from(Evaluation)
            .join(Submission, Submission.id == Evaluation.submission_id)
            .where(Submission.classroom_id == room.id)
        )
        or 0
    )
    out = ClassroomOut.model_validate(room)
    out.student_link = student_link(request, room)
    out.submitted_count, out.roster_count, out.evaluated_count = submitted, roster, evaluated
    out.purge_on = purge_on(room.academic_year, room.semester)
    out.is_active = room_is_active(db, room)
    out.term_ended = today() > term_end(room.academic_year, room.semester)
    return out


@router.get("/term-default")
def term_default():
    """Academic year and semester to pre-fill in the 'new classroom' form."""
    year, semester = current_academic_term()
    return {"academic_year": year, "semester": semester}


@router.get("", response_model=list[ClassroomOut])
def list_classrooms(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rooms = db.scalars(
        select(Classroom)
        .where(Classroom.teacher_id == user.id)
        .order_by(Classroom.academic_year.desc(), Classroom.semester.desc(), Classroom.created_at.desc())
    ).all()
    return [_out(request, db, r) for r in rooms]


@router.post("", response_model=ClassroomOut, status_code=status.HTTP_201_CREATED)
def create_classroom(
    body: ClassroomIn, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    if purge_on(body.academic_year, body.semester) <= today():
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"ภาคเรียนที่ {body.semester}/{body.academic_year} จบไปนานแล้ว ระบบเก็บข้อมูลไว้แค่ 45 วันหลังจบภาคเรียน",
        )
    has_any = db.scalar(select(func.count()).select_from(Classroom).where(Classroom.teacher_id == user.id))
    room = Classroom(
        teacher_id=user.id,
        subject_name=body.subject_name,
        subject_code=body.subject_code,
        grade_label=body.grade_label,
        academic_year=body.academic_year,
        semester=body.semester,
        public_token=new_public_token(),
        # The first classroom is the free trial. Paid-term checks arrive with the payment module.
        is_trial=not has_any,
    )
    db.add(room)
    db.commit()
    return _out(request, db, room)


@router.get("/{classroom_id}", response_model=ClassroomOut)
def get_classroom(
    classroom_id: int, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return _out(request, db, get_owned_classroom(classroom_id, user, db))


@router.patch("/{classroom_id}", response_model=ClassroomOut)
def update_classroom(
    classroom_id: int,
    body: ClassroomPatch,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    room = get_owned_classroom(classroom_id, user, db)
    for key, value in body.model_dump(exclude_none=True).items():
        setattr(room, key, value.strip() if isinstance(value, str) else value)
    db.commit()
    return _out(request, db, room)


@router.delete("/{classroom_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_classroom(classroom_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Deletes the classroom and every student answer in it (PDPA: the teacher can erase data)."""
    room = get_owned_classroom(classroom_id, user, db)
    db.delete(room)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{classroom_id}/qr.svg")
def classroom_qr(
    classroom_id: int, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    room = get_owned_classroom(classroom_id, user, db)
    qr = segno.make(student_link(request, room), error="m")
    buf = io.BytesIO()
    qr.save(buf, kind="svg", scale=8, border=2, dark="#111827", xmldecl=False)
    return Response(buf.getvalue(), media_type="image/svg+xml", headers={"Cache-Control": "private, max-age=300"})


# --- Class list ------------------------------------------------------------------------


@router.get("/{classroom_id}/roster", response_model=list[RosterEntryOut])
def get_roster(classroom_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    room = get_owned_classroom(classroom_id, user, db)
    return [RosterEntryOut(student_no=r.student_no, full_name=r.full_name) for r in room.roster]


@router.put("/{classroom_id}/roster", response_model=list[RosterEntryOut])
def replace_roster(
    classroom_id: int, body: RosterIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Replace the whole class list. An empty text removes it (students then type their own name)."""
    room = get_owned_classroom(classroom_id, user, db)
    try:
        rows = parse_roster(body.text)
    except ValueError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(e)) from None
    db.execute(delete(RosterEntry).where(RosterEntry.classroom_id == room.id))
    db.add_all(RosterEntry(classroom_id=room.id, student_no=no, full_name=name) for no, name in rows)
    db.commit()
    return [RosterEntryOut(student_no=no, full_name=name) for no, name in rows]


# --- Submissions ---------------------------------------------------------------------


@router.get("/{classroom_id}/submissions")
def list_submissions(classroom_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Everyone in the class: submitted, evaluated, or (when a class list exists) not yet submitted."""
    room = get_owned_classroom(classroom_id, user, db)
    by_no: dict[int, dict] = {}
    for r in room.roster:
        by_no[r.student_no] = {"student_no": r.student_no, "full_name": r.full_name, "status": "missing", "id": None}
    for s in room.submissions:
        by_no[s.student_no] = {
            "id": s.id,
            "student_no": s.student_no,
            "full_name": s.full_name,
            "nickname": s.nickname,
            "submitted_at": s.submitted_at.isoformat() + "Z",
            "status": "evaluated" if s.evaluation else "submitted",
            "by_teacher": s.created_by_teacher,
            "in_roster": not room.roster or any(r.student_no == s.student_no for r in room.roster),
        }
    return [by_no[k] for k in sorted(by_no)]


def get_owned_submission(classroom_id: int, submission_id: int, user: User, db: Session) -> Submission:
    room = get_owned_classroom(classroom_id, user, db)
    sub = db.get(Submission, submission_id)
    if sub is None or sub.classroom_id != room.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "ไม่พบคำตอบนี้")
    return sub


@router.get("/{classroom_id}/submissions/{submission_id}")
def get_submission(
    classroom_id: int, submission_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    s = get_owned_submission(classroom_id, submission_id, user, db)
    return {
        "id": s.id,
        "student_no": s.student_no,
        "full_name": s.full_name,
        "nickname": s.nickname,
        "personal_info": s.personal_info,
        "open_answers": s.open_answers,
        "learning_prefs": [{"key": k, "label": LEARNING_METHOD_LABELS.get(k, k)} for k in s.learning_prefs],
        "submitted_at": s.submitted_at.isoformat() + "Z",
        "updated_at": s.updated_at.isoformat() + "Z",
    }


@router.delete("/{classroom_id}/submissions/{submission_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_submission(
    classroom_id: int, submission_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Remove a wrong or duplicate answer so the student can send again."""
    db.delete(get_owned_submission(classroom_id, submission_id, user, db))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{classroom_id}/submissions/{submission_id}/edit-code")
def reset_edit_code(
    classroom_id: int, submission_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Issue a new edit code for a student who lost theirs. The old one stops working."""
    s = get_owned_submission(classroom_id, submission_id, user, db)
    code = new_edit_code()
    s.edit_code_hash = hash_edit_code(code)
    db.commit()
    return {"edit_code": code}
