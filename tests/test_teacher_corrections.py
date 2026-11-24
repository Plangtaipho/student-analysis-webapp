"""The teacher fixes records students filled in wrongly, and takes moved-away students off the class list."""
from tests.conftest import Teacher, student_payload, token_of


def _room_with(teacher, student, nos):
    room = teacher.make_room()
    for no in nos:
        assert student.post(f"/api/f/{token_of(room)}/submissions", json=student_payload(no=no)).status_code == 201
    subs = {s["student_no"]: s["id"] for s in teacher.get(f"/api/classrooms/{room['id']}/submissions").json() if s.get("id")}
    return room, subs


def test_teacher_corrects_number_name_and_answers(teacher, student):
    room, subs = _room_with(teacher, student, [1, 2])
    url = f"/api/classrooms/{room['id']}/submissions/{subs[2]}"
    r = teacher.put(url, {"student_no": 3, "full_name": " เด็กชายเอ ตัวจริง ", "nickname": "เอ",
                          "personal_info": {"age": "13"}, "open_answers": {"q1": "วาดรูป", "zz": "x"}})
    assert r.status_code == 200, r.text
    s = teacher.get(url).json()
    assert (s["student_no"], s["full_name"], s["nickname"]) == (3, "เด็กชายเอ ตัวจริง", "เอ")
    assert s["open_answers"] == {"q1": "วาดรูป"}
    # Identity only: the answers stay as they were.
    assert teacher.put(url, {"student_no": 3, "full_name": "เด็กชายเอ ตัวจริง"}).status_code == 200
    assert teacher.get(url).json()["open_answers"] == {"q1": "วาดรูป"}


def test_number_already_taken_is_refused(teacher, student):
    room, subs = _room_with(teacher, student, [1, 2])
    r = teacher.put(f"/api/classrooms/{room['id']}/submissions/{subs[2]}", {"student_no": 1, "full_name": "ใครสักคน"})
    assert r.status_code == 409 and "เลขที่ 1" in r.text


def test_other_teacher_cannot_edit(teacher, student):
    room, subs = _room_with(teacher, student, [1])
    other = Teacher(email="other@example.com")
    r = other.put(f"/api/classrooms/{room['id']}/submissions/{subs[1]}", {"student_no": 5, "full_name": "แอบแก้"})
    assert r.status_code == 404


def test_moved_student_is_taken_off_the_class_list(teacher, student):
    room, _ = _room_with(teacher, student, [])
    base = f"/api/classrooms/{room['id']}"
    teacher.put(f"{base}/roster", {"text": "1\tเด็กชายหนึ่ง สมมุติ\n2\tเด็กหญิงสอง สมมุติ"})
    url = f"/api/f/{token_of(room)}/submissions"
    assert student.post(url, json=student_payload(no=1, full_name="เด็กชายหนึ่ง สมมุติ")).status_code == 201
    assert teacher.get(base).json()["roster_count"] == 2
    assert teacher.delete(f"{base}/roster/2").status_code == 204
    assert teacher.get(base).json()["roster_count"] == 1
    rows = teacher.get(f"{base}/submissions").json()
    assert [r["student_no"] for r in rows] == [1]
    assert teacher.delete(f"{base}/roster/2").status_code == 404
    assert Teacher(email="x@example.com").delete(f"{base}/roster/1").status_code == 404
