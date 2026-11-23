import io

from PIL import Image

from app.config import get_settings
from app.database import SessionLocal
from app.models import Role, User
from app.services import promptpay
from tests.conftest import Teacher, student_payload, token_of


def png_bytes(size=(60, 90)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, (200, 220, 240)).save(buf, "PNG")
    return buf.getvalue()


def upload(t: Teacher, room: dict, data: bytes = None, name="slip.png"):
    return t.c.post(
        "/api/billing/slip",
        data={"academic_year": room["academic_year"], "semester": room["semester"]},
        files={"file": (name, data if data is not None else png_bytes(), "image/png")},
        headers=t._h(),
    )


def make_admin() -> Teacher:
    a = Teacher(email="admin@example.com", name="ผู้ดูแล ระบบ")
    with SessionLocal() as db:
        db.get(User, a.user["id"]).role = Role.admin
        db.commit()
    return a


def test_crc_and_payload():
    assert promptpay.crc16("123456789") == "29B1"  # CRC-16/CCITT-FALSE check value
    p = promptpay.payload("081-234-5678", 129)
    assert p.startswith("000201010212")
    assert "0016A00000067701011101130066812345678" in p
    assert "5406129.00" in p and "5802TH" in p and "5303764" in p
    assert p[-4:] == promptpay.crc16(p[:-4])
    assert "0213" + "1234567890123" in promptpay.payload("1234567890123")


def test_first_room_free_second_locked_until_slip(teacher, student):
    trial = teacher.make_room()
    paid = teacher.make_room(subject_name="ภาษาไทย")
    assert trial["is_trial"] and trial["is_active"]
    assert not paid["is_trial"] and not paid["is_active"]

    url = f"/api/f/{token_of(paid)}/submissions"
    assert student.post(url, json=student_payload(1)).status_code == 403
    assert student.get(f"/api/f/{token_of(paid)}").json()["is_active"] is False
    assert teacher.get(f"/api/classrooms/{paid['id']}/pdf/individual").status_code == 402

    r = upload(teacher, paid)
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "approved"  # the QR fixes the amount: no admin approval needed
    assert teacher.get(f"/api/classrooms/{paid['id']}").json()["is_active"] is True
    assert student.post(url, json=student_payload(1)).status_code == 201

    overview = teacher.get("/api/billing").json()
    assert overview["price"] == get_settings().price_per_term == 99
    assert overview["price_full"] == 139 and overview["trial_student_limit"] == 5
    term = overview["terms"][0]
    assert term["status"] == "approved" and term["rooms"] == 2 and term["has_slip"]


def test_admin_approve_and_reject(teacher):
    teacher.make_room()
    paid = teacher.make_room(subject_name="ภาษาไทย")
    sub_id = upload(teacher, paid).json()["subscription_id"]
    admin = make_admin()

    listed = admin.get("/api/admin/subscriptions").json()
    assert [s["id"] for s in listed] == [sub_id] and listed[0]["status"] == "approved"
    slip = admin.get(f"/api/admin/subscriptions/{sub_id}/slip")
    assert slip.status_code == 200 and slip.headers["content-type"] == "image/jpeg"

    r = admin.post(f"/api/admin/subscriptions/{sub_id}/reject", {"reason": "ยอดเงินไม่ตรง"})
    assert r.status_code == 200 and r.json()["status"] == "rejected"
    assert teacher.get(f"/api/classrooms/{paid['id']}").json()["is_active"] is False
    assert teacher.get("/api/billing").json()["terms"][0]["reject_reason"] == "ยอดเงินไม่ตรง"

    # The admin can switch a rejected term back on.
    assert admin.post(f"/api/admin/subscriptions/{sub_id}/approve").json()["status"] == "approved"
    assert teacher.get(f"/api/classrooms/{paid['id']}").json()["is_active"] is True
    assert upload(teacher, paid).status_code == 409  # already paid
    admin.post(f"/api/admin/subscriptions/{sub_id}/reject", {"reason": "สลิปซ้ำ"})
    assert upload(teacher, paid).json()["status"] == "approved"  # a new slip unlocks again

    teachers = admin.get("/api/admin/teachers").json()
    assert {t["email"] for t in teachers} == {"kru@example.com"}
    assert teachers[0]["paid_terms"] == 1 and teachers[0]["rooms"] == 2


def test_admin_api_is_admin_only(teacher):
    assert teacher.get("/api/admin/subscriptions").status_code == 403
    assert teacher.get("/api/admin/teachers").status_code == 403
    assert teacher.post("/api/admin/subscriptions/1/approve").status_code == 403


def test_slip_must_be_an_image_and_private(teacher):
    teacher.make_room()
    paid = teacher.make_room(subject_name="ภาษาไทย")
    assert upload(teacher, paid, b"%PDF-1.4 not an image", "slip.pdf").status_code == 422
    assert upload(teacher, paid, b"<svg xmlns='http://www.w3.org/2000/svg'/>", "x.svg").status_code == 422
    sub_id = upload(teacher, paid).json()["subscription_id"]
    other = Teacher(email="other@example.com")
    assert other.get(f"/api/billing/slips/{sub_id}").status_code == 404
    assert teacher.get(f"/api/billing/slips/{sub_id}").status_code == 200


def test_upload_needs_csrf(teacher):
    teacher.make_room()
    paid = teacher.make_room(subject_name="ภาษาไทย")
    r = teacher.c.post(
        "/api/billing/slip",
        data={"academic_year": paid["academic_year"], "semester": paid["semester"]},
        files={"file": ("s.png", png_bytes(), "image/png")},
    )
    assert r.status_code == 403



def test_trial_room_takes_five_students_until_paid(teacher, student):
    trial = teacher.make_room()
    assert trial["student_limit"] == 5
    url = f"/api/f/{token_of(trial)}/submissions"
    for no in range(1, 6):
        assert student.post(url, json=student_payload(no)).status_code == 201
    assert student.get(f"/api/f/{token_of(trial)}").json()["is_full"] is True
    r = student.post(url, json=student_payload(6))
    assert r.status_code == 403 and "5 คน" in r.text
    # Editing an earlier answer still works when the room is full.
    room = teacher.get(f"/api/classrooms/{trial['id']}").json()
    assert room["submitted_count"] == 5 and room["is_active"]
    # The teacher cannot add a sixth student by hand either.
    r = teacher.post(f"/api/classrooms/{trial['id']}/submissions/manual", {"student_no": 7, "full_name": "เด็กหญิงเจ็ด ทดสอบ"})
    assert r.status_code == 402
    # Reports still work for the five.
    assert teacher.get(f"/api/classrooms/{trial['id']}/pdf/individual").status_code != 402

    assert upload(teacher, trial).json()["status"] == "approved"
    assert teacher.get(f"/api/classrooms/{trial['id']}").json()["student_limit"] is None
    assert student.post(url, json=student_payload(6)).status_code == 201
