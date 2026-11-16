from tests.conftest import student_payload, token_of


def test_form_info_and_unknown_token(teacher, student):
    room = teacher.make_room()
    info = student.get(f"/api/f/{token_of(room)}").json()
    assert info["subject_name"] == "คณิตศาสตร์" and info["is_open"] is True
    assert info["teacher_name"] == "ครูนางสาวใจดี ตั้งใจสอน"
    assert student.get("/api/f/not-a-real-token").status_code == 404
    assert student.get(f"/f/{token_of(room)}").status_code == 200
    assert student.get("/f/not-a-real-token").status_code == 404


def test_submit_cleans_data_and_returns_edit_code(teacher, student):
    room = teacher.make_room()
    r = student.post(f"/api/f/{token_of(room)}/submissions", json=student_payload())
    assert r.status_code == 201, r.text
    code = r.json()["edit_code"]
    assert len(code) == 6 and code.isdigit()

    subs = teacher.get(f"/api/classrooms/{room['id']}/submissions").json()
    assert [s["status"] for s in subs] == ["submitted"]
    detail = teacher.get(f"/api/classrooms/{room['id']}/submissions/{subs[0]['id']}").json()
    assert "unknown_field" not in detail["personal_info"]
    assert detail["personal_info"]["age"] == 17 and detail["personal_info"]["weight_kg"] == 55.5
    assert detail["open_answers"] == {"q1": "วาดรูป", "q10": "วิศวกร"}
    assert [p["label"] for p in detail["learning_prefs"]] == ["แบบทดลอง", "แบบโครงงาน", "กระบวนการกลุ่ม"]


def test_duplicate_number_needs_edit_code(teacher, student):
    room = teacher.make_room()
    url = f"/api/f/{token_of(room)}"
    code = student.post(f"{url}/submissions", json=student_payload()).json()["edit_code"]
    assert student.post(f"{url}/submissions", json=student_payload()).status_code == 409

    wrong = "000000" if code != "000000" else "111111"
    assert student.post(f"{url}/lookup", json={"student_no": 1, "edit_code": wrong}).status_code == 403
    loaded = student.post(f"{url}/lookup", json={"student_no": 1, "edit_code": code})
    assert loaded.status_code == 200 and loaded.json()["nickname"] == "ต้น"

    r = student.post(f"{url}/submissions", json=student_payload(nickname="ต้นไม้", edit_code=code))
    assert r.status_code == 201 and r.json()["updated"] is True and r.json()["edit_code"] is None
    sid = teacher.get(f"/api/classrooms/{room['id']}/submissions").json()[0]["id"]
    assert teacher.get(f"/api/classrooms/{room['id']}/submissions/{sid}").json()["nickname"] == "ต้นไม้"


def test_wrong_edit_codes_are_rate_limited(teacher, student):
    room = teacher.make_room()
    url = f"/api/f/{token_of(room)}"
    code = student.post(f"{url}/submissions", json=student_payload()).json()["edit_code"]
    wrong = "000000" if code != "000000" else "111111"
    for _ in range(5):
        student.post(f"{url}/lookup", json={"student_no": 1, "edit_code": wrong})
    assert student.post(f"{url}/lookup", json={"student_no": 1, "edit_code": code}).status_code == 429


def test_closed_room_rejects_submissions(teacher, student):
    room = teacher.make_room()
    teacher.patch(f"/api/classrooms/{room['id']}", {"is_open": False})
    r = student.post(f"/api/f/{token_of(room)}/submissions", json=student_payload())
    assert r.status_code == 403


def test_roster_limits_numbers_and_uses_roster_name(teacher, student):
    room = teacher.make_room()
    teacher.put(f"/api/classrooms/{room['id']}/roster", {"text": "1\tนายจริง ในรายชื่อ\n2\tนางสาวสอง สดใส"})
    url = f"/api/f/{token_of(room)}/submissions"
    assert student.post(url, json=student_payload(no=9)).status_code == 422
    r = student.post(url, json=student_payload(no=1, full_name="นายจิง สะกดผิด"))
    assert r.json()["full_name"] == "นายจริง ในรายชื่อ"
    rows = teacher.get(f"/api/classrooms/{room['id']}/submissions").json()
    assert [(x["student_no"], x["status"]) for x in rows] == [(1, "submitted"), (2, "missing")]


def test_validation_errors(teacher, student):
    room = teacher.make_room()
    url = f"/api/f/{token_of(room)}/submissions"
    assert student.post(url, json=student_payload(consent=False)).status_code == 422
    assert student.post(url, json=student_payload(learning_prefs=["lecture"])).status_code == 422
    assert student.post(url, json=student_payload(learning_prefs=["lecture", "lecture", "project"])).status_code == 422
    bad = student_payload()
    bad["personal_info"] = {"blood_type": "Z"}
    assert student.post(url, json=bad).status_code == 422
    bad["personal_info"] = {"weight_kg": "9999"}
    assert student.post(url, json=bad).status_code == 422
    bad["personal_info"] = {"birth_date": "2569-01-01"}  # Buddhist year typed into a date field
    assert student.post(url, json=bad).status_code == 422
    assert student.post(url, json=student_payload(open_answers={"q1": "ก" * 301})).status_code == 422


def test_teacher_can_reset_code_and_delete(teacher, student):
    room = teacher.make_room()
    url = f"/api/f/{token_of(room)}"
    old = student.post(f"{url}/submissions", json=student_payload()).json()["edit_code"]
    sid = teacher.get(f"/api/classrooms/{room['id']}/submissions").json()[0]["id"]
    new = teacher.post(f"/api/classrooms/{room['id']}/submissions/{sid}/edit-code").json()["edit_code"]
    if new != old:
        assert student.post(f"{url}/lookup", json={"student_no": 1, "edit_code": old}).status_code == 403
    assert student.post(f"{url}/lookup", json={"student_no": 1, "edit_code": new}).status_code == 200
    assert teacher.delete(f"/api/classrooms/{room['id']}/submissions/{sid}").status_code == 204
    assert student.post(f"{url}/submissions", json=student_payload()).status_code == 201


def test_student_answers_are_escaped_in_teacher_page_data(teacher, student):
    room = teacher.make_room()
    payload = student_payload(full_name="<script>alert(1)</script>")
    student.post(f"/api/f/{token_of(room)}/submissions", json=payload)
    # The API returns raw text; pages insert it with textContent / API.esc, never as HTML.
    rows = teacher.get(f"/api/classrooms/{room['id']}/submissions").json()
    assert rows[0]["full_name"] == "<script>alert(1)</script>"
