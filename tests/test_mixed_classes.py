"""ห้องคละ: an elective whose students come from several classes, so numbers repeat across classes."""
import pytest

from tests.conftest import student_payload, token_of
from tests.test_evaluations import all_scores, ev_url

from app.services.home_class import normalize_home_class, sort_key
from app.services.roster import parse_mixed_roster


def mixed_room(teacher, **kw):
    return teacher.make_room(subject_name="ชุมนุมดนตรี", grade_label="มัธยมศึกษาปีที่ 3", mixed_classes=True, **kw)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("ม.3/2", "ม.3/2"),
        ("ม 3/2", "ม.3/2"),
        ("3/2", "ม.3/2"),
        ("ม.๓/๒", "ม.3/2"),
        ("มัธยมศึกษาปีที่ 3/12", "ม.3/12"),
        ("ป.6/1", "ป.6/1"),
    ],
)
def test_normalize_home_class(raw, expected):
    assert normalize_home_class(raw, "มัธยมศึกษาปีที่ 3") == expected


@pytest.mark.parametrize("raw", ["", "ม.3", "ห้องสาม", "ม.9/1"])
def test_normalize_home_class_rejects(raw):
    with pytest.raises(ValueError):
        normalize_home_class(raw)


def test_sort_order_rooms_numerically():
    rows = [("ม.3/10", 1), ("ม.3/2", 5), ("ม.3/2", 1), ("ม.2/9", 3)]
    assert sorted(rows, key=lambda r: sort_key(*r)) == [("ม.2/9", 3), ("ม.3/2", 1), ("ม.3/2", 5), ("ม.3/10", 1)]


def test_parse_mixed_roster():
    rows = parse_mixed_roster("ห้อง\tเลขที่\tชื่อ\nม.3/2\t5\tด.ช. ก้อง ใจดี\nม.3/10\t5\tเอ บี\n3/2 1 ซี ดี", "มัธยมศึกษาปีที่ 3")
    assert rows == [("ม.3/2", 1, "ซี ดี"), ("ม.3/2", 5, "ด.ช. ก้อง ใจดี"), ("ม.3/10", 5, "เอ บี")]
    with pytest.raises(ValueError, match="ซ้ำ"):
        parse_mixed_roster("ม.3/2 5 ก\nม 3/2 5 ข")
    with pytest.raises(ValueError, match="ไม่ครบ"):
        parse_mixed_roster("ม.3/2 ก้อง")


def test_same_number_from_different_classes(teacher, student):
    room = mixed_room(teacher)
    assert room["mixed_classes"] is True
    url = f"/api/f/{token_of(room)}/submissions"
    assert student.get(f"/api/f/{token_of(room)}").json()["mixed_classes"] is True
    a = student.post(url, json=student_payload(no=5, home_class="ม.3/2", full_name="เด็กชายเอ ห้องสอง"))
    b = student.post(url, json=student_payload(no=5, home_class="3/1", full_name="เด็กหญิงบี ห้องหนึ่ง"))
    assert a.status_code == 201 and b.status_code == 201, (a.text, b.text)
    assert b.json()["home_class"] == "ม.3/1"
    # Same class and number again: refused, with the class in the message.
    dup = student.post(url, json=student_payload(no=5, home_class="ม.๓/๒"))
    assert dup.status_code == 409 and "ม.3/2 เลขที่ 5" in dup.json()["detail"]
    # Home class is required in a ห้องคละ.
    r = student.post(url, json=student_payload(no=7))
    assert r.status_code == 422 and "ห้องเดิม" in r.json()["detail"]
    rows = teacher.get(f"/api/classrooms/{room['id']}/submissions").json()
    assert [(r["home_class"], r["student_no"]) for r in rows] == [("ม.3/1", 5), ("ม.3/2", 5)]

    # Edit with the code needs the right class too.
    code = a.json()["edit_code"]
    look = f"/api/f/{token_of(room)}/lookup"
    assert student.post(look, json={"home_class": "ม.3/1", "student_no": 5, "edit_code": code}).status_code == 403
    r = student.post(look, json={"home_class": "ม.3/2", "student_no": 5, "edit_code": code})
    assert r.status_code == 200 and r.json()["full_name"] == "เด็กชายเอ ห้องสอง"


def test_normal_room_ignores_home_class(teacher, student):
    room = teacher.make_room()
    assert room["mixed_classes"] is False
    url = f"/api/f/{token_of(room)}/submissions"
    assert student.post(url, json=student_payload(no=5, home_class="ม.3/2")).status_code == 201
    assert student.post(url, json=student_payload(no=5, home_class="ม.3/1")).status_code == 409
    rows = teacher.get(f"/api/classrooms/{room['id']}/submissions").json()
    assert rows[0]["home_class"] == ""


def test_mixed_roster_and_missing_list(teacher, student):
    room = mixed_room(teacher)
    base = f"/api/classrooms/{room['id']}"
    r = teacher.put(f"{base}/roster", {"text": "ม.3/2\t5\tด.ช.เอ ห้องสอง\nม.3/1\t5\tด.ญ.บี ห้องหนึ่ง\nม.3/10\t1\tด.ช.ซี สิบ"})
    assert r.status_code == 200, r.text
    assert [(x["home_class"], x["student_no"]) for x in r.json()] == [("ม.3/1", 5), ("ม.3/2", 5), ("ม.3/10", 1)]
    url = f"/api/f/{token_of(room)}/submissions"
    # Not on the list: refused with class and number.
    bad = student.post(url, json=student_payload(no=6, home_class="ม.3/2"))
    assert bad.status_code == 422 and "ม.3/2 เลขที่ 6" in bad.json()["detail"]
    ok = student.post(url, json=student_payload(no=5, home_class="ม.3/2", full_name="พิมพ์ชื่อผิด"))
    assert ok.status_code == 201 and ok.json()["full_name"] == "ด.ช.เอ ห้องสอง"
    rows = teacher.get(f"{base}/submissions").json()
    assert [(x["home_class"], x["student_no"], x["status"]) for x in rows] == [
        ("ม.3/1", 5, "missing"),
        ("ม.3/2", 5, "submitted"),
        ("ม.3/10", 1, "missing"),
    ]
    # Take one off the list by class + number.
    assert teacher.delete(f"{base}/roster/5?home_class=ม.3/1").status_code == 204
    assert teacher.delete(f"{base}/roster/5?home_class=ม.3/1").status_code == 404
    left = [(x["home_class"], x["student_no"]) for x in teacher.get(f"{base}/roster").json()]
    assert left == [("ม.3/2", 5), ("ม.3/10", 1)]
    # Teacher adds a record for a student without a phone.
    r = teacher.post(f"{base}/submissions/manual", {"home_class": "ม.3/10", "student_no": 1, "full_name": "ใครก็ได้"})
    assert r.status_code == 201
    dup = teacher.post(f"{base}/submissions/manual", {"home_class": "ม 3/10", "student_no": 1, "full_name": "ซ้ำ"})
    assert dup.status_code == 409


def test_teacher_edits_home_class(teacher, student):
    room = mixed_room(teacher)
    base = f"/api/classrooms/{room['id']}"
    url = f"/api/f/{token_of(room)}/submissions"
    student.post(url, json=student_payload(no=5, home_class="ม.3/2"))
    student.post(url, json=student_payload(no=5, home_class="ม.3/1"))
    sid = [x["id"] for x in teacher.get(f"{base}/submissions").json() if x["home_class"] == "ม.3/2"][0]
    body = {"home_class": "ม.3/1", "student_no": 5, "full_name": "เด็กชายย้าย ห้อง"}
    r = teacher.put(f"{base}/submissions/{sid}", body)
    assert r.status_code == 409 and "ม.3/1 เลขที่ 5" in r.json()["detail"]
    r = teacher.put(f"{base}/submissions/{sid}", body | {"home_class": "ม.3/4"})
    assert r.status_code == 200 and r.json()["home_class"] == "ม.3/4"


def test_turn_mixed_on_and_off(teacher, student):
    room = teacher.make_room()
    base = f"/api/classrooms/{room['id']}"
    url = f"/api/f/{token_of(room)}/submissions"
    assert student.post(url, json=student_payload(no=1)).status_code == 201
    r = teacher.patch(base, {"mixed_classes": True})
    assert r.status_code == 200 and r.json()["mixed_classes"] is True
    # The earlier answer has no class yet; the teacher can still edit it without one.
    sid = teacher.get(f"{base}/submissions").json()[0]["id"]
    assert teacher.put(f"{base}/submissions/{sid}", {"student_no": 1, "full_name": "เด็กชายเก่า ก่อนคละ"}).status_code == 200
    # Back to normal is fine while nobody has a class...
    assert teacher.patch(base, {"mixed_classes": False}).status_code == 200
    teacher.patch(base, {"mixed_classes": True})
    assert student.post(url, json=student_payload(no=1, home_class="ม.6/2")).status_code == 201
    # ...but not once numbers could repeat.
    r = teacher.patch(base, {"mixed_classes": False})
    assert r.status_code == 409


def test_reports_sorted_by_class_then_number(teacher, student, monkeypatch):
    from app.routers import reports
    from app.services import pdf

    captured = {}

    def fake_render(template, **ctx):
        captured["html"] = pdf._env.get_template(template).render(font_dir="", **ctx)
        return b"%PDF-fake"

    monkeypatch.setattr(reports, "render_pdf", fake_render)
    room = mixed_room(teacher)
    base = f"/api/classrooms/{room['id']}"
    url = f"/api/f/{token_of(room)}/submissions"
    for hc, no, name in [("ม.3/10", 1, "เด็กชายสิบ หนึ่ง"), ("ม.3/2", 7, "เด็กชายสอง เจ็ด"), ("ม.3/2", 3, "เด็กหญิงสอง สาม")]:
        assert student.post(url, json=student_payload(no=no, home_class=hc, full_name=name)).status_code == 201
    subs = teacher.get(f"{base}/submissions").json()
    assert [x["full_name"] for x in subs] == ["เด็กหญิงสอง สาม", "เด็กชายสอง เจ็ด", "เด็กชายสิบ หนึ่ง"]
    for x in subs:
        teacher.put(ev_url(room, x["id"]), {"scores": all_scores("good")})
    ev = teacher.get(ev_url(room, subs[0]["id"])).json()
    assert ev["home_class"] == "ม.3/2" and ev["next_id"] == subs[1]["id"]
    summary = teacher.get(f"{base}/summary").json()
    names = [s["full_name"] for g in summary["groups"] for s in g["students"]]
    assert names == ["เด็กหญิงสอง สาม", "เด็กชายสอง เจ็ด", "เด็กชายสิบ หนึ่ง"]

    r = teacher.get(f"{base}/pdf/full", params={"doc_no": "1/2569", "date": "26 พฤศจิกายน 2569"})
    assert r.status_code == 200, r.text
    html = captured["html"]
    assert html.index("เด็กหญิงสอง สาม") < html.index("เด็กชายสอง เจ็ด") < html.index("เด็กชายสิบ หนึ่ง")
    assert "เด็กหญิงสอง สาม (ม.3/2)" in html  # group table shows the home class
    assert "มัธยมศึกษาปีที่ 3/10" in html  # individual record: the student's own class
    r = teacher.get(f"{base}/submissions/{subs[2]['id']}/pdf")
    assert r.status_code == 200 and "%E0%B8%A1.3-10-" in r.headers["content-disposition"]
