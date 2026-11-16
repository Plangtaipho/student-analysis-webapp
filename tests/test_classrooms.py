import pytest

from app.services.roster import parse_roster
from tests.conftest import Teacher


def test_first_room_is_trial_and_listed(teacher):
    a = teacher.make_room()
    b = teacher.make_room(grade_label="มัธยมศึกษาปีที่ 6/2")
    assert a["is_trial"] is True and b["is_trial"] is False
    assert a["student_link"].startswith("https://example.test/f/")
    rooms = teacher.get("/api/classrooms").json()
    assert {r["id"] for r in rooms} == {a["id"], b["id"]}


def test_create_room_validation(teacher):
    r = teacher.post("/api/classrooms", {"subject_name": "", "grade_label": "ม.1", "academic_year": 2569, "semester": 3})
    assert r.status_code == 422


def test_other_teacher_cannot_see_or_change_room(teacher):
    room = teacher.make_room()
    other = Teacher(email="other@example.com", name="ครูคนอื่น")
    rid = room["id"]
    assert other.get(f"/api/classrooms/{rid}").status_code == 404
    assert other.patch(f"/api/classrooms/{rid}", {"is_open": False}).status_code == 404
    assert other.get(f"/api/classrooms/{rid}/submissions").status_code == 404
    assert other.get(f"/api/classrooms/{rid}/qr.svg").status_code == 404
    assert other.put(f"/api/classrooms/{rid}/roster", {"text": "1 ก"}).status_code == 404
    assert other.delete(f"/api/classrooms/{rid}").status_code == 404
    assert other.get("/api/classrooms").json() == []


def test_open_close_and_delete(teacher):
    room = teacher.make_room()
    r = teacher.patch(f"/api/classrooms/{room['id']}", {"is_open": False})
    assert r.json()["is_open"] is False
    assert teacher.c.patch(f"/api/classrooms/{room['id']}", json={"is_open": True}).status_code == 403  # no CSRF
    assert teacher.delete(f"/api/classrooms/{room['id']}").status_code == 204
    assert teacher.get(f"/api/classrooms/{room['id']}").status_code == 404


def test_qr_is_svg(teacher):
    room = teacher.make_room()
    r = teacher.get(f"/api/classrooms/{room['id']}/qr.svg")
    assert r.status_code == 200 and r.headers["content-type"].startswith("image/svg+xml")
    assert r.text.startswith("<svg") and "xmlns" in r.text[:200]


def test_roster_replace_and_clear(teacher):
    room = teacher.make_room()
    url = f"/api/classrooms/{room['id']}/roster"
    r = teacher.put(url, {"text": "เลขที่\tชื่อ-สกุล\n1\tนายหนึ่ง ใจดี\n2\tนางสาวสอง สดใส\n"})
    assert r.status_code == 200 and len(r.json()) == 2
    assert teacher.get(f"/api/classrooms/{room['id']}").json()["roster_count"] == 2
    assert teacher.put(url, {"text": "1 ก\n1 ข"}).status_code == 422
    assert teacher.put(url, {"text": ""}).json() == []


@pytest.mark.parametrize(
    "text,expected",
    [
        ("1\tนายก ข\n2\tนางสาวค ง", [(1, "นายก ข"), (2, "นางสาวค ง")]),
        ("นายก ข\nนางสาวค ง", [(1, "นายก ข"), (2, "นางสาวค ง")]),
        ("3. นายก ข\n\n5) นางสาวค ง", [(3, "นายก ข"), (5, "นางสาวค ง")]),
        ("10, เด็กชายเอ บี", [(10, "เด็กชายเอ บี")]),
    ],
)
def test_parse_roster(text, expected):
    assert parse_roster(text) == expected


def test_parse_roster_rejects_out_of_range():
    with pytest.raises(ValueError):
        parse_roster("0 ศูนย์")
