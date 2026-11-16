"""PDF downloads for the teacher."""
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, get_owned_classroom
from app.models import User
from app.routers.classrooms import get_owned_submission
from app.services.form_definition import ASSESSMENT_DOMAINS, LEARNING_METHODS, OPEN_QUESTIONS
from app.services.pdf import render_pdf
from app.services.records import individual_record

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
