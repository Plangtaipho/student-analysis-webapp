from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import PASSWORD, Teacher


def test_register_logs_in_and_me_works(teacher):
    r = teacher.get("/api/auth/me")
    assert r.status_code == 200
    assert r.json()["user"]["email"] == "kru@example.com"
    assert r.json()["user"]["position"] == "ครู"


def test_register_duplicate_email_is_rejected_case_insensitive(teacher):
    c = TestClient(app)
    r = c.post("/api/auth/register", json={
        "email": "KRU@example.com", "password": PASSWORD, "full_name": "ครูอีกคน", "position": "ครู", "department": "กลุ่มบริหารวิชาการ",
        "learning_area": "กลุ่มสาระการเรียนรู้ศิลปะ", "school_name": "โรงเรียนอื่น", "area_office": "สพม.เลย", "accept_terms": True,
    })
    assert r.status_code == 409


def test_register_requires_terms_and_valid_input():
    c = TestClient(app)
    base = {"email": "a@example.com", "password": PASSWORD, "full_name": "ครูเอ", "position": "ครู",
            "department": "กลุ่มบริหารวิชาการ", "learning_area": "กิจกรรมพัฒนาผู้เรียน", "school_name": "โรงเรียนเอ",
            "area_office": "สพม.เลย หนองบัวลำภู"}
    assert c.post("/api/auth/register", json=base | {"accept_terms": False}).status_code == 422
    assert c.post("/api/auth/register", json=base | {"accept_terms": True, "password": "short"}).status_code == 422
    assert c.post("/api/auth/register", json=base | {"accept_terms": True, "email": "not-an-email"}).status_code == 422
    assert c.post("/api/auth/register", json=base | {"accept_terms": True, "position": ""}).status_code == 422
    assert c.post("/api/auth/register", json=base | {"accept_terms": True, "position": "ครูชำนาญการ"}).status_code == 422
    assert c.post("/api/auth/register", json=base | {"accept_terms": True, "department": ""}).status_code == 422
    # กลุ่มงาน is one of the four groups only; a กลุ่มสาระ is not a กลุ่มงาน.
    bad_dept = base | {"accept_terms": True, "department": "กลุ่มสาระการเรียนรู้คณิตศาสตร์"}
    assert c.post("/api/auth/register", json=bad_dept).status_code == 422
    assert c.post("/api/auth/register", json=base | {"accept_terms": True, "learning_area": ""}).status_code == 422
    assert c.post("/api/auth/register", json=base | {"accept_terms": True, "area_office": ""}).status_code == 422
    r = c.post("/api/auth/register", json=base | {"accept_terms": True})
    assert r.status_code == 201 and r.json()["user"]["department"] == "กลุ่มบริหารวิชาการ"
    assert r.json()["user"]["learning_area"] == "กิจกรรมพัฒนาผู้เรียน"
    assert r.json()["user"]["area_office"] == "สำนักงานเขตพื้นที่การศึกษามัธยมศึกษาเลย หนองบัวลำภู"


def test_login_logout_and_wrong_password(teacher):
    c = TestClient(app)
    assert c.post("/api/auth/login", json={"email": "kru@example.com", "password": "wrong-pass"}).status_code == 401
    r = c.post("/api/auth/login", json={"email": " KRU@example.com ", "password": PASSWORD})
    assert r.status_code == 200
    assert c.get("/api/auth/me").status_code == 200
    c.post("/api/auth/logout")
    assert c.get("/api/auth/me").status_code == 401


def test_login_is_rate_limited(teacher):
    c = TestClient(app)
    for _ in range(5):
        c.post("/api/auth/login", json={"email": "kru@example.com", "password": "wrong-pass"})
    r = c.post("/api/auth/login", json={"email": "kru@example.com", "password": PASSWORD})
    assert r.status_code == 429


def test_profile_update_needs_csrf(teacher):
    body = {"full_name": "นางพรธิดา โพธิ์สิงห์", "position": "ครู", "department": "กลุ่มบริหารงานทั่วไป", "learning_area": "กลุ่มสาระการเรียนรู้คณิตศาสตร์", "school_name": "โรงเรียนหนองสวรรค์วิทยาคาร", "area_office": "สพม.เลย หนองบัวลำภู"}
    assert teacher.c.put("/api/auth/profile", json=body).status_code == 403
    r = teacher.put("/api/auth/profile", body)
    assert r.status_code == 200
    assert r.json()["user"]["position"] == "ครู"
    assert r.json()["user"]["department"] == "กลุ่มบริหารงานทั่วไป"
    assert r.json()["user"]["learning_area"] == "กลุ่มสาระการเรียนรู้คณิตศาสตร์"


def test_change_password(teacher):
    assert teacher.put("/api/auth/password", {"current_password": "nope-nope", "password": "newpassword1"}).status_code == 400
    assert teacher.put("/api/auth/password", {"current_password": PASSWORD, "password": "newpassword1"}).status_code == 200
    c = TestClient(app)
    assert c.post("/api/auth/login", json={"email": "kru@example.com", "password": "newpassword1"}).status_code == 200


def test_teacher_pages_redirect_when_logged_out():
    c = TestClient(app)
    r = c.get("/app", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"].startswith("/login")
    assert c.get("/").status_code == 200
    assert c.get("/privacy").status_code == 200


def test_security_headers():
    r = TestClient(app).get("/")
    assert "default-src 'self'" in r.headers["content-security-policy"]
    assert r.headers["x-frame-options"] == "DENY"


def test_bad_initial_admin_password_does_not_crash(monkeypatch):
    """A placeholder pasted as INITIAL_ADMIN_PASSWORD (e.g. long Thai text) must not stop the site."""
    from app import main

    monkeypatch.setattr(main.settings, "initial_admin_email", "admin@example.com")
    monkeypatch.setattr(main.settings, "initial_admin_password", "(รหัสผ่านแอดมิน อย่างน้อย 12 ตัว)")
    main.bootstrap_admin()  # no exception, no admin
    with TestClient(main.app) as c:
        assert c.get("/healthz").status_code == 200


def test_public_base_url_gets_scheme():
    from app.config import Settings

    assert Settings(public_base_url=" kruflow.up.railway.app/ ").public_base_url == "https://kruflow.up.railway.app"
    assert Settings(public_base_url="http://localhost:8000").public_base_url == "http://localhost:8000"
    assert Settings(env=" Production ").is_production


def test_area_office_short_forms_are_spelled_out():
    from app.schemas import expand_area_office

    assert expand_area_office("สพม.เลย หนองบัวลำภู") == "สำนักงานเขตพื้นที่การศึกษามัธยมศึกษาเลย หนองบัวลำภู"
    assert expand_area_office("สพป. หนองบัวลำภู เขต 1") == "สำนักงานเขตพื้นที่การศึกษาประถมศึกษาหนองบัวลำภู เขต 1"
    assert expand_area_office("สพปหนองบัวลำภู เขต 2") == "สำนักงานเขตพื้นที่การศึกษาประถมศึกษาหนองบัวลำภู เขต 2"
    full = "สำนักงานเขตพื้นที่การศึกษามัธยมศึกษาเลย หนองบัวลำภู"
    assert expand_area_office(full) == full
    c = TestClient(app)
    r = c.post("/api/auth/register", json={
        "email": "b@example.com", "password": PASSWORD, "full_name": "ครูบี", "position": "ครู",
        "department": "กลุ่มบริหารวิชาการ", "learning_area": "กลุ่มสาระการเรียนรู้ศิลปะ",
        "school_name": "โรงเรียนบี", "area_office": "สพม.เลย หนองบัวลำภู", "accept_terms": True,
    })
    assert r.json()["user"]["area_office"] == full


def test_spoofed_forwarded_for_does_not_reset_login_limit(teacher):
    c = TestClient(app)
    for i in range(5):
        c.post("/api/auth/login", json={"email": "kru@example.com", "password": "wrong-pass"},
               headers={"X-Forwarded-For": f"10.0.0.{i}, 203.0.113.7"})
    # A new fake first address does not help: the last (proxy-added) address is what counts.
    r = c.post("/api/auth/login", json={"email": "kru@example.com", "password": PASSWORD},
               headers={"X-Forwarded-For": "10.9.9.9, 203.0.113.7"})
    assert r.status_code == 429


def test_account_limit_across_many_ips(teacher):
    c = TestClient(app)
    for i in range(20):
        c.post("/api/auth/login", json={"email": "kru@example.com", "password": "wrong-pass"},
               headers={"X-Forwarded-For": f"198.51.100.{i}"})
    r = c.post("/api/auth/login", json={"email": "kru@example.com", "password": PASSWORD},
               headers={"X-Forwarded-For": "198.51.100.250"})
    assert r.status_code == 429


def test_railway_counts_as_production(monkeypatch):
    from app.config import Settings

    monkeypatch.setenv("RAILWAY_ENVIRONMENT_NAME", "production")
    assert Settings(env="development").is_production
