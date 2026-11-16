import os
import tempfile

# Point the app at a throwaway SQLite file BEFORE it is imported.
_db_file = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_file}"
os.environ["ENV"] = "development"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["INITIAL_ADMIN_EMAIL"] = ""
os.environ["PUBLIC_BASE_URL"] = "https://example.test"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import AssessmentItem  # noqa: E402
from app.security import edit_code_limiter, login_limiter, register_limiter, submit_limiter  # noqa: E402
from app.services.form_definition import assessment_item_rows  # noqa: E402

PASSWORD = "password123"


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        db.add_all(AssessmentItem(**row) for row in assessment_item_rows())
        db.commit()
    for limiter in (login_limiter, edit_code_limiter, submit_limiter, register_limiter):
        limiter.clear()
    yield


class Teacher:
    """TestClient wrapper: signs up a teacher and sends the CSRF header like the browser does."""

    def __init__(self, email: str = "kru@example.com", name: str = "นางสาวใจดี ตั้งใจสอน"):
        self.c = TestClient(app)
        r = self.c.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": PASSWORD,
                "full_name": name,
                "school_name": "โรงเรียนทดสอบวิทยา",
                "accept_terms": True,
            },
        )
        assert r.status_code == 201, r.text
        self.csrf = r.json()["csrf"]
        self.user = r.json()["user"]

    def _h(self):
        return {"X-CSRF-Token": self.csrf}

    def get(self, url, **kw):
        return self.c.get(url, **kw)

    def post(self, url, json=None):
        return self.c.post(url, json=json if json is not None else {}, headers=self._h())

    def put(self, url, json=None):
        return self.c.put(url, json=json, headers=self._h())

    def patch(self, url, json=None):
        return self.c.patch(url, json=json, headers=self._h())

    def delete(self, url):
        return self.c.delete(url, headers=self._h())

    def make_room(self, **kw):
        body = {
            "subject_name": "คณิตศาสตร์",
            "subject_code": "ค33101",
            "grade_label": "มัธยมศึกษาปีที่ 6/1",
            "academic_year": 2569,
            "semester": 2,
        } | kw
        r = self.post("/api/classrooms", body)
        assert r.status_code == 201, r.text
        return r.json()


def token_of(room: dict) -> str:
    return room["student_link"].rsplit("/", 1)[1]


def student_payload(no: int = 1, **kw) -> dict:
    return {
        "student_no": no,
        "full_name": f"เด็กชายทดสอบ คนที่{no}",
        "nickname": "ต้น",
        "personal_info": {
            "birth_date": "2009-05-14",
            "age": "17",
            "blood_type": "O",
            "father_name": "นายพ่อ ทดสอบ",
            "parent_status": "อยู่ด้วยกัน",
            "weight_kg": "55.5",
            "unknown_field": "should be dropped",
        },
        "open_answers": {"q1": "วาดรูป", "q10": "วิศวกร", "qx": "dropped"},
        "learning_prefs": ["experiment", "project", "group"],
        "consent": True,
    } | kw


@pytest.fixture
def teacher():
    return Teacher()


@pytest.fixture
def student():
    return TestClient(app)
