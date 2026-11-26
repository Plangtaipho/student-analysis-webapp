import pytest

from app.database import SessionLocal
from app.models import Rating, User
from app.services.summary import ITEM_CODES, auto_group
from tests.conftest import Teacher, student_payload, token_of


def all_scores(rating="fair", **overrides):
    s = {c: {"rating": rating, "note": ""} for c in ITEM_CODES}
    for code, r in overrides.items():
        s[code] = {"rating": r, "note": "ฝึกเพิ่ม" if r == "improve" else ""}
    return s


def setup_room(teacher, student, n=3):
    room = teacher.make_room()
    url = f"/api/f/{token_of(room)}/submissions"
    for i in range(1, n + 1):
        assert student.post(url, json=student_payload(no=i)).status_code == 201
    subs = teacher.get(f"/api/classrooms/{room['id']}/submissions").json()
    return room, [s["id"] for s in subs]


def ev_url(room, sid):
    return f"/api/classrooms/{room['id']}/submissions/{sid}/evaluation"


def test_sixteen_items():
    assert len(ITEM_CODES) == 16


def test_save_and_read_evaluation(teacher, student):
    room, ids = setup_room(teacher, student)
    r = teacher.get(ev_url(room, ids[0])).json()
    assert r["evaluated"] is False and r["next_pending_id"] == ids[1]
    body = {"scores": all_scores("good", d3_3="improve"), "last_grade": "3.5", "teacher_comment": "ตั้งใจเรียน", "group_override": None}
    r = teacher.put(ev_url(room, ids[0]), body)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["evaluated"] and data["scores"]["d3_3"] == {"rating": "improve", "note": "ฝึกเพิ่ม"}
    assert data["group"] == "high" and data["next_pending_id"] == ids[1]
    # Update in place.
    body["scores"] = all_scores("fair")
    assert teacher.put(ev_url(room, ids[0]), body).json()["group"] == "medium"
    rows = teacher.get(f"/api/classrooms/{room['id']}/submissions").json()
    assert [x["status"] for x in rows] == ["evaluated", "submitted", "submitted"]


def test_evaluation_must_be_complete_and_valid(teacher, student):
    room, ids = setup_room(teacher, student, 1)
    partial = all_scores()
    partial.pop("d5_3")
    assert teacher.put(ev_url(room, ids[0]), {"scores": partial}).status_code == 422
    bad = all_scores() | {"zz": {"rating": "good"}}
    assert teacher.put(ev_url(room, ids[0]), {"scores": bad}).status_code == 422
    bad = all_scores() | {"d1_1": {"rating": "excellent"}}
    assert teacher.put(ev_url(room, ids[0]), {"scores": bad}).status_code == 422
    assert teacher.put(ev_url(room, ids[0]), {"scores": all_scores(), "group_override": "vip"}).status_code == 422
    assert teacher.c.put(ev_url(room, ids[0]), json={"scores": all_scores()}).status_code == 403  # no CSRF


def test_other_teacher_cannot_evaluate(teacher, student):
    room, ids = setup_room(teacher, student, 1)
    other = Teacher(email="o@example.com", name="ครูโอ")
    assert other.get(ev_url(room, ids[0])).status_code == 404
    assert other.put(ev_url(room, ids[0]), {"scores": all_scores()}).status_code == 404
    assert other.get(f"/api/classrooms/{room['id']}/summary").status_code == 404
    assert other.get(f"/api/classrooms/{room['id']}/pdf/full").status_code == 404


@pytest.mark.parametrize(
    "ratings,group",
    [
        (["good"] * 16, "high"),
        (["good"] * 8 + ["fair"] * 8, "high"),  # avg 2.5
        (["good"] * 7 + ["fair"] * 9, "medium"),
        (["fair"] * 14 + ["improve"] * 2, "medium"),  # like the sample class: 2 x improve stays medium
        (["improve"] * 9 + ["fair"] * 7, "medium"),  # avg 1.4375 -> low? check below
        (["improve"] * 16, "low"),
    ],
)
def test_auto_group_default_rule(ratings, group):
    values = [Rating(r) for r in ratings]
    avg = sum({"good": 3, "fair": 2, "improve": 1}[r] for r in ratings) / len(ratings)
    expected = "high" if avg >= 2.5 else "low" if avg < 1.5 else "medium"
    assert auto_group(values).value == expected
    if ratings != ["improve"] * 9 + ["fair"] * 7:
        assert expected == group


def test_summary_counts_percentages_and_groups(teacher, student):
    room, ids = setup_room(teacher, student, 3)
    teacher.put(ev_url(room, ids[0]), {"scores": all_scores("good")})
    teacher.put(ev_url(room, ids[1]), {"scores": all_scores("fair", d1_1="good")})
    teacher.put(ev_url(room, ids[2]), {"scores": all_scores("fair"), "group_override": "disability"})
    s = teacher.get(f"/api/classrooms/{room['id']}/summary").json()
    assert s["evaluated"] == 3 and s["submitted"] == 3
    first = s["domains"][0]["items"][0]
    assert first["code"] == "d1_1" and first["good"] == 2 and first["fair"] == 1 and first["improve"] == 0
    assert first["good_pct"] == 66.67 and first["fair_pct"] == 33.33
    groups = {g["key"]: [x["student_no"] for x in g["students"]] for g in s["groups"]}
    assert groups == {"high": [1], "medium": [2], "low": [], "disability": [3]}
    assert sum(len(d["items"]) for d in s["domains"]) == 16


def test_summary_ignores_unevaluated(teacher, student):
    room, ids = setup_room(teacher, student, 2)
    teacher.put(ev_url(room, ids[0]), {"scores": all_scores("improve")})
    s = teacher.get(f"/api/classrooms/{room['id']}/summary").json()
    assert s["evaluated"] == 1
    assert s["domains"][0]["items"][0]["improve_pct"] == 100.0


def test_manual_record_for_student_without_phone(teacher, student):
    room = teacher.make_room()
    teacher.put(f"/api/classrooms/{room['id']}/roster", {"text": "1\tนายหนึ่ง ใจดี\n2\tนางสาวสอง สดใส"})
    r = teacher.post(f"/api/classrooms/{room['id']}/submissions/manual", {"student_no": 2, "full_name": "ชื่อพิมพ์"})
    assert r.status_code == 201
    sid = r.json()["id"]
    assert teacher.post(f"/api/classrooms/{room['id']}/submissions/manual", {"student_no": 2, "full_name": "ซ้ำ"}).status_code == 409
    rows = teacher.get(f"/api/classrooms/{room['id']}/submissions").json()
    assert rows[1]["full_name"] == "นางสาวสอง สดใส" and rows[1]["by_teacher"] is True
    assert teacher.put(ev_url(room, sid), {"scores": all_scores()}).status_code == 200
    # The student can no longer submit with that number (the teacher record holds it).
    assert student.post(f"/api/f/{token_of(room)}/submissions", json=student_payload(no=2)).status_code == 409
    assert teacher.get(f"/api/classrooms/{room['id']}/summary").json()["submitted"] == 0


def test_clear_evaluation(teacher, student):
    room, ids = setup_room(teacher, student, 1)
    teacher.put(ev_url(room, ids[0]), {"scores": all_scores()})
    assert teacher.delete(ev_url(room, ids[0])).status_code == 204
    assert teacher.get(ev_url(room, ids[0])).json()["evaluated"] is False


def test_full_report_pdf(teacher, student):
    room, ids = setup_room(teacher, student, 2)
    url = f"/api/classrooms/{room['id']}/pdf/full"
    assert teacher.get(url).status_code == 409  # nobody assessed yet
    teacher.put(ev_url(room, ids[0]), {"scores": all_scores("good"), "teacher_comment": "ดีมาก"})
    r = teacher.get(url, params={"doc_no": "417/2569", "to": "ผู้อำนวยการโรงเรียนทดสอบ"})
    assert r.status_code == 200 and r.content.startswith(b"%PDF")
    assert teacher.get(url).status_code == 422  # doc number is required
    assert teacher.get(url, params={"doc_no": "  "}).status_code == 422


def test_full_report_needs_department(teacher, student):
    room, ids = setup_room(teacher, student, 1)
    teacher.put(ev_url(room, ids[0]), {"scores": all_scores("good")})
    with SessionLocal() as db:
        db.get(User, teacher.user["id"]).department = ""
        db.commit()
    r = teacher.get(f"/api/classrooms/{room['id']}/pdf/full", params={"doc_no": "1/2569"})
    assert r.status_code == 409 and "กลุ่มงาน" in r.text


def test_full_report_works_without_area_office(teacher, student):
    room, ids = setup_room(teacher, student, 1)
    teacher.put(ev_url(room, ids[0]), {"scores": all_scores("good")})
    with SessionLocal() as db:
        db.get(User, teacher.user["id"]).area_office = ""
        db.commit()
    r = teacher.get(f"/api/classrooms/{room['id']}/pdf/full", params={"doc_no": "1/2569"})
    assert r.status_code == 200 and r.content[:4] == b"%PDF"


def test_full_report_leaves_out_area_office(teacher, student, monkeypatch):
    """Even teachers who filled in the area office at sign-up get it left out of the memo (decision 2026-11-24)."""
    from app.routers import reports

    seen = {}
    monkeypatch.setattr(reports, "render_pdf", lambda name, **ctx: seen.update(ctx) or b"%PDF-fake")
    room, ids = setup_room(teacher, student, 1)
    teacher.put(ev_url(room, ids[0]), {"scores": all_scores("good")})
    with SessionLocal() as db:
        assert db.get(User, teacher.user["id"]).area_office  # set by the fixture
    r = teacher.get(f"/api/classrooms/{room['id']}/pdf/full", params={"doc_no": "1/2569"})
    assert r.status_code == 200
    assert "เขตพื้นที่" not in seen["memo"]["dept"]
    assert seen["memo"]["dept"].startswith("กลุ่มบริหารวิชาการ")


def test_memo_uses_thai_digits_everywhere(teacher, student, monkeypatch):
    """Feedback 2026-11-26: every number in the memo is in Thai digits, even ones typed in Arabic digits."""
    import re

    from app.routers import reports
    from app.services import pdf

    captured = {}

    def fake_render(template, **ctx):
        captured["html"] = pdf._env.get_template(template).render(font_dir="", **ctx)
        return b"%PDF-fake"

    monkeypatch.setattr(reports, "render_pdf", fake_render)
    room = teacher.make_room(subject_name="คณิตศาสตร์ 2", subject_code="ค23102")
    url = f"/api/f/{token_of(room)}/submissions"
    assert student.post(url, json=student_payload(no=1)).status_code == 201
    sid = teacher.get(f"/api/classrooms/{room['id']}/submissions").json()[0]["id"]
    teacher.put(ev_url(room, sid), {"scores": all_scores("good")})
    with SessionLocal() as db:
        u = db.get(User, teacher.user["id"])
        u.school_name, u.school_location = "บ้านหนองบัว 2", "อำเภอเมือง จังหวัดเลย 42000"
        db.commit()
    r = teacher.get(
        f"/api/classrooms/{room['id']}/pdf/full",
        params={"doc_no": "417/2569", "to": "ผู้อำนวยการโรงเรียนบ้านหนองบัว 2"},
    )
    assert r.status_code == 200
    html = captured["html"]
    memo = html[html.index('<section class="page memo">') : html.index("</section>", html.index('<section class="page memo">'))]
    text = re.sub(r"<[^>]+>", " ", memo)  # tag attributes (CSS, image data) are not printed
    assert not re.search(r"[0-9]", text), re.findall(r".{0,20}[0-9].{0,20}", text)
    assert "๔๑๗/๒๕๖๙" in text and "บ้านหนองบัว ๒" in text and "ค๒๓๑๐๒" in text
