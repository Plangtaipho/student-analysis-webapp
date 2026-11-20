"""PDF downloads for the teacher."""
from datetime import date
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, get_owned_classroom, today
from app.models import User
from app.routers.classrooms import get_owned_submission
from app.services.form_definition import ASSESSMENT_DOMAINS, LEARNING_METHODS, OPEN_QUESTIONS
from app.services.pdf import render_pdf, thai_number
from app.services.records import THAI_MONTHS, individual_record
from app.services.summary import classroom_summary

router = APIRouter(prefix="/api/classrooms", tags=["reports"])


def _pdf_response(data: bytes, filename: str) -> Response:
    return Response(
        data,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"inline; filename=\"report.pdf\"; filename*=UTF-8''{quote(filename)}",
            "Cache-Control": "no-store",
        },
    )


def _render_individual(room, teacher, subs) -> bytes:
    return render_pdf(
        "individual.html",
        records=[individual_record(s) for s in subs],
        room=room,
        teacher=teacher,
        questions=OPEN_QUESTIONS,
        methods=LEARNING_METHODS,
        domains=ASSESSMENT_DOMAINS,
    )


@router.get("/{classroom_id}/submissions/{submission_id}/pdf")
def individual_pdf(
    classroom_id: int, submission_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    sub = get_owned_submission(classroom_id, submission_id, user, db)
    room = sub.classroom
    data = _render_individual(room, user, [sub])
    return _pdf_response(data, f"วิเคราะห์ผู้เรียน-{room.grade_label}-เลขที่{sub.student_no}.pdf")


@router.get("/{classroom_id}/pdf/individual")
def all_individual_pdf(classroom_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Every student's record in one file, in class-number order."""
    room = get_owned_classroom(classroom_id, user, db)
    if not room.submissions:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "ยังไม่มีนักเรียนส่งแบบฟอร์ม")
    data = _render_individual(room, user, room.submissions)
    return _pdf_response(data, f"วิเคราะห์ผู้เรียนรายบุคคล-{room.subject_name}-{room.grade_label}.pdf")


def school_text(name: str) -> str:
    name = (name or "").strip()
    return name if name.startswith("โรงเรียน") or not name else f"โรงเรียน{name}"


def grade_text(label: str) -> str:
    label = (label or "").strip()
    return label if label.startswith("ชั้น") else f"ชั้น{label}"


@router.get("/{classroom_id}/pdf/full")
def full_report_pdf(
    classroom_id: int,
    doc_no: str = Query(default="", max_length=60),
    doc_date: date | None = None,
    to: str = Query(default="", max_length=200),
    dept: str = Query(default="", max_length=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """The complete set sent to the academic department:
    memo, summary table, learner groups, then every assessed student's individual record."""
    room = get_owned_classroom(classroom_id, user, db)
    summary = classroom_summary(room)
    if summary["evaluated"] == 0:
        raise HTTPException(status.HTTP_409_CONFLICT, "ยังไม่มีนักเรียนที่ประเมินแล้ว กรุณาประเมินอย่างน้อย 1 คนก่อนออกรายงาน")
    school = school_text(user.school_name)
    d = doc_date or today()
    memo = {
        "dept": dept.strip() or f"กลุ่มบริหารวิชาการ {school}",
        "doc_no": doc_no.strip() or "............................",
        "date_text": thai_number(f"{d.day} {THAI_MONTHS[d.month - 1]} {d.year + 543}"),
        "to": to.strip() or f"ผู้อำนวยการ{school}",
    }
    evaluated = [s for s in room.submissions if s.evaluation is not None]
    data = render_pdf(
        "full.html",
        room=room,
        teacher=user,
        school=school,
        grade_text=grade_text(room.grade_label),
        memo=memo,
        summary=summary,
        group_rows=max(10, max(len(g["students"]) for g in summary["groups"])),
        records=[individual_record(s) for s in evaluated],
        questions=OPEN_QUESTIONS,
        methods=LEARNING_METHODS,
        domains=ASSESSMENT_DOMAINS,
    )
    return _pdf_response(data, f"รายงานวิเคราะห์ผู้เรียน-{room.subject_name}-{room.grade_label}.pdf")
