"""After paying, a teacher's name and school are locked until the term ends (one account = one teacher)."""
from datetime import timedelta

from app.database import SessionLocal
from app.models import Subscription
from tests.conftest import Teacher
from tests.test_billing import make_admin, upload

PROFILE = {
    "full_name": "นางสาวใจดี ตั้งใจสอน",
    "position": "ครู",
    "department": "กลุ่มบริหารวิชาการ",
    "learning_area": "กลุ่มสาระการเรียนรู้คณิตศาสตร์",
    "school_name": "โรงเรียนทดสอบวิทยา",
    "school_location": "",
}


def _pay(t: Teacher, hours_ago: float = 48):
    room = t.make_room()
    assert upload(t, room).status_code == 201
    with SessionLocal() as db:
        for s in db.query(Subscription).filter_by(teacher_id=t.user["id"]):
            s.submitted_at = s.submitted_at - timedelta(hours=hours_ago)
        db.commit()
    return room


def test_unpaid_teacher_can_change_name(teacher):
    assert teacher.get("/api/auth/me").json()["name_lock"] is None
    r = teacher.put("/api/auth/profile", {**PROFILE, "full_name": "นายสมชาย ใจกล้า"})
    assert r.status_code == 200 and r.json()["user"]["full_name"] == "นายสมชาย ใจกล้า"


def test_name_editable_within_24_hours_of_paying(teacher):
    _pay(teacher, hours_ago=1)
    assert teacher.get("/api/auth/me").json()["name_lock"] is None
    assert teacher.put("/api/auth/profile", {**PROFILE, "full_name": "นางสาวใจดี ตั้งใจสอนดี"}).status_code == 200


def test_paid_teacher_cannot_change_name_or_school(teacher):
    _pay(teacher)
    lock = teacher.get("/api/auth/me").json()["name_lock"]
    assert lock and lock["term"] and lock["until"]
    r = teacher.put("/api/auth/profile", {**PROFILE, "full_name": "นายสมชาย ใจกล้า"})
    assert r.status_code == 409 and "ล็อก" in r.json()["detail"]
    assert teacher.put("/api/auth/profile", {**PROFILE, "school_name": "โรงเรียนอื่น"}).status_code == 409
    # Other details can still change, and saving the same name is fine.
    r = teacher.put("/api/auth/profile", {**PROFILE, "department": "กลุ่มบริหารงานบุคคล"})
    assert r.status_code == 200
    assert teacher.get("/api/auth/me").json()["user"]["full_name"] == PROFILE["full_name"]


def test_rejected_slip_unlocks(teacher):
    _pay(teacher)
    admin = make_admin()
    sub_id = admin.get("/api/admin/subscriptions").json()[0]["id"]
    assert admin.post(f"/api/admin/subscriptions/{sub_id}/reject", {"reason": "สลิปไม่ชัด"}).status_code == 200
    assert teacher.get("/api/auth/me").json()["name_lock"] is None


def test_admin_fixes_locked_name(teacher):
    _pay(teacher)
    admin = make_admin()
    url = f"/api/admin/teachers/{teacher.user['id']}/name"
    assert teacher.put(url, {"full_name": "นายแอบ แก้", "school_name": "โรงเรียนเอ"}).status_code == 403
    r = admin.put(url, {"full_name": "นางสาวใจดี ตั้งใจสอนมาก", "school_name": "โรงเรียนทดสอบวิทยา"})
    assert r.status_code == 200
    assert teacher.get("/api/auth/me").json()["user"]["full_name"] == "นางสาวใจดี ตั้งใจสอนมาก"


def test_lock_ends_with_the_term(teacher):
    from app.services.billing import name_lock
    from app.services.retention import term_end

    room = _pay(teacher)
    end = term_end(room["academic_year"], room["semester"])
    with SessionLocal() as db:
        assert name_lock(db, teacher.user["id"], end) is not None
        assert name_lock(db, teacher.user["id"], end + timedelta(days=1)) is None
