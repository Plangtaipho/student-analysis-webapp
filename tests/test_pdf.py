from tests.conftest import student_payload, token_of


def test_individual_pdf(teacher, student):
    room = teacher.make_room()
    student.post(f"/api/f/{token_of(room)}/submissions", json=student_payload())
    sid = teacher.get(f"/api/classrooms/{room['id']}/submissions").json()[0]["id"]
    r = teacher.get(f"/api/classrooms/{room['id']}/submissions/{sid}/pdf")
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF")
    r = teacher.get(f"/api/classrooms/{room['id']}/pdf/individual")
    assert r.status_code == 200 and r.content.startswith(b"%PDF")


def test_pdf_requires_owner(teacher, student):
    from tests.conftest import Teacher

    room = teacher.make_room()
    student.post(f"/api/f/{token_of(room)}/submissions", json=student_payload())
    other = Teacher(email="x@example.com", name="ครูเอกซ์")
    assert other.get(f"/api/classrooms/{room['id']}/pdf/individual").status_code == 404


def test_all_pdf_with_no_submissions_is_404(teacher):
    room = teacher.make_room()
    assert teacher.get(f"/api/classrooms/{room['id']}/pdf/individual").status_code == 404
