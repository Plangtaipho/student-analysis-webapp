"""Sign in with Google: start, callback, linking, finishing sign-up, safety checks."""
import base64
import json
import time
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.services import google_oauth
from tests.conftest import PASSWORD, Teacher

DETAILS = {
    "full_name": "นายสมชาย ใจกว้าง",
    "position": "พนักงานราชการ",
    "department": "กลุ่มบริหารวิชาการ",
    "learning_area": "กลุ่มสาระการเรียนรู้คณิตศาสตร์",
    "school_name": "โรงเรียนทดสอบวิทยา",
    "area_office": "สพป.หนองบัวลำภู เขต 1",
    "accept_terms": True,
}


@pytest.fixture
def google(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "google_client_id", "cid.apps.googleusercontent.com")
    monkeypatch.setattr(s, "google_client_secret", "secret")
    account = {"sub": "1001", "email": "somchai@gmail.com", "name": "Somchai"}

    def fake_exchange(code, client_id, client_secret, redirect_uri):
        assert code == "good-code"
        assert redirect_uri == "https://example.test/api/auth/google/callback"
        return dict(account)

    monkeypatch.setattr(google_oauth, "exchange_code", fake_exchange)
    return account


def _sign_in(c: TestClient, next_url: str | None = None, code: str = "good-code"):
    r = c.get("/api/auth/google/start" + (f"?next={next_url}" if next_url else ""), follow_redirects=False)
    assert r.status_code == 303
    q = parse_qs(urlparse(r.headers["location"]).query)
    assert q["client_id"] == ["cid.apps.googleusercontent.com"]
    assert q["redirect_uri"] == ["https://example.test/api/auth/google/callback"]
    return c.get(f"/api/auth/google/callback?code={code}&state={q['state'][0]}", follow_redirects=False)


def test_hidden_when_not_configured():
    c = TestClient(app)
    assert c.get("/api/auth/google/start", follow_redirects=False).status_code == 404
    assert "btn-google" not in c.get("/login").text


def test_button_shown_when_configured(google):
    c = TestClient(app)
    assert "เข้าสู่ระบบด้วย Google" in c.get("/login").text
    assert "สมัครด้วย Google" in c.get("/register").text


def test_new_teacher_finishes_sign_up(google):
    c = TestClient(app)
    r = _sign_in(c)
    assert r.headers["location"] == "/register?google=1"
    assert c.get("/api/auth/me").status_code == 401  # not logged in until details are given
    p = c.get("/api/auth/google/pending").json()
    assert p["email"] == "somchai@gmail.com"
    # Without the pending token the sign-up is refused.
    assert c.post("/api/auth/google/register", json=DETAILS).status_code == 403
    r = c.post("/api/auth/google/register", json=DETAILS, headers={"X-CSRF-Token": p["csrf"]})
    assert r.status_code == 201, r.text
    user = r.json()["user"]
    assert user["email"] == "somchai@gmail.com" and user["position"] == "พนักงานราชการ"
    assert user["has_password"] is False and user["google_linked"] is True
    assert c.get("/api/auth/me").status_code == 200
    # Pending data is gone, so it cannot be reused.
    assert c.get("/api/auth/google/pending").status_code == 404

    # Next time Google logs straight in.
    c2 = TestClient(app)
    r = _sign_in(c2, next_url="/app/billing")
    assert r.headers["location"] == "/app/billing"
    assert c2.get("/api/auth/me").json()["user"]["email"] == "somchai@gmail.com"

    # A Google-only account can set a first password without a current one, then use it.
    csrf = c2.get("/api/auth/me").json()["csrf"]
    r = c2.put("/api/auth/password", json={"current_password": "", "password": "newpass123"}, headers={"X-CSRF-Token": csrf})
    assert r.status_code == 200
    assert TestClient(app).post("/api/auth/login", json={"email": "somchai@gmail.com", "password": "newpass123"}).status_code == 200


def test_google_only_account_cannot_password_login(google):
    c = TestClient(app)
    _sign_in(c)
    p = c.get("/api/auth/google/pending").json()
    c.post("/api/auth/google/register", json=DETAILS, headers={"X-CSRF-Token": p["csrf"]})
    r = TestClient(app).post("/api/auth/login", json={"email": "somchai@gmail.com", "password": ""})
    assert r.status_code in (401, 422)


def test_links_existing_password_account(google):
    t = Teacher(email="somchai@gmail.com")
    c = TestClient(app)
    r = _sign_in(c)
    assert r.headers["location"] == "/app"
    me = c.get("/api/auth/me").json()["user"]
    assert me["id"] == t.user["id"] and me["google_linked"] is True and me["has_password"] is True
    # Password login still works too.
    assert TestClient(app).post("/api/auth/login", json={"email": "somchai@gmail.com", "password": PASSWORD}).status_code == 200


def test_bad_state_is_rejected(google):
    c = TestClient(app)
    c.get("/api/auth/google/start", follow_redirects=False)
    r = c.get("/api/auth/google/callback?code=good-code&state=forged", follow_redirects=False)
    assert r.headers["location"] == "/login?google=failed"
    assert c.get("/api/auth/me").status_code == 401


def test_callback_without_start_is_rejected(google):
    r = TestClient(app).get("/api/auth/google/callback?code=good-code&state=x", follow_redirects=False)
    assert r.headers["location"] == "/login?google=failed"


def test_next_cannot_leave_site(google):
    Teacher(email="somchai@gmail.com")
    r = _sign_in(TestClient(app), next_url="//evil.example/app")
    assert r.headers["location"] == "/app"


def test_google_error_is_handled(google, monkeypatch):
    def boom(*a, **k):
        raise google_oauth.GoogleAuthError("x")

    monkeypatch.setattr(google_oauth, "exchange_code", boom)
    r = _sign_in(TestClient(app))
    assert r.headers["location"] == "/login?google=failed"


def _jwt(claims: dict) -> str:
    def enc(d: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()

    return f"{enc({'alg': 'RS256'})}.{enc(claims)}.sig"


@pytest.mark.parametrize(
    "change, ok",
    [
        ({}, True),
        ({"aud": "someone-else"}, False),
        ({"iss": "evil.example"}, False),
        ({"email_verified": False}, False),
        ({"exp": 1}, False),
    ],
)
def test_exchange_checks_claims(monkeypatch, change, ok):
    claims = {
        "iss": "https://accounts.google.com",
        "aud": "cid",
        "sub": "42",
        "email": "A@Gmail.com",
        "email_verified": True,
        "exp": int(time.time()) + 600,
        "name": "A",
    }
    claims.update(change)
    monkeypatch.setattr(google_oauth, "_post_token", lambda data: {"id_token": _jwt(claims)})
    if ok:
        assert google_oauth.exchange_code("c", "cid", "s", "r") == {"sub": "42", "email": "a@gmail.com", "name": "A"}
    else:
        with pytest.raises(google_oauth.GoogleAuthError):
            google_oauth.exchange_code("c", "cid", "s", "r")
