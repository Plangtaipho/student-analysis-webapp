from datetime import date

from app.database import SessionLocal
from app.models import Classroom, Submission
from app.services.retention import purge_expired, purge_on, term_end
from tests.conftest import student_payload, token_of


def test_term_dates():
    assert term_end(2569, 1) == date(2026, 10, 31)
    assert term_end(2569, 2) == date(2027, 3, 31)
    assert purge_on(2569, 1) == date(2026, 12, 15)
    assert purge_on(2569, 2) == date(2027, 5, 15)


def test_room_shows_purge_date(teacher):
    room = teacher.make_room()
    assert room["purge_on"] == purge_on(room["academic_year"], room["semester"]).isoformat()
    assert room["term_ended"] is False


def test_cannot_create_room_for_purged_term(teacher):
    r = teacher.post("/api/classrooms", {"subject_name": "ไทย", "grade_label": "ม.1", "academic_year": 2565, "semester": 1})
    assert r.status_code == 422
    assert "45 วัน" in r.text


def test_purge_deletes_only_expired_rooms(teacher):
    room = teacher.make_room()
    teacher.c.post(f"/api/f/{token_of(room)}/submissions", json=student_payload(1))
    end = purge_on(room["academic_year"], room["semester"])
    with SessionLocal() as db:
        assert purge_expired(db, date.fromordinal(end.toordinal() - 1)) == 0
        assert db.query(Submission).count() == 1
        assert purge_expired(db, end) == 1
        assert db.query(Classroom).count() == 0
        assert db.query(Submission).count() == 0


def test_student_can_skip_all_personal_info(teacher):
    room = teacher.make_room()
    body = student_payload(2) | {"personal_info": {}, "nickname": ""}
    r = teacher.c.post(f"/api/f/{token_of(room)}/submissions", json=body)
    assert r.status_code == 201, r.text
