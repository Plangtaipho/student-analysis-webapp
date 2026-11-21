"""Teacher sign-up, login (password or Google), logout, profile and password."""
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.deps import client_ip, get_current_user, verify_csrf
from app.models import User
from app.schemas import ChangePasswordIn, GoogleRegisterIn, LoginIn, ProfileIn, RegisterIn, UserOut
from app.services import google_oauth
from app.security import (
    DUMMY_HASH,
    hash_password,
    login_limiter,
    new_csrf_token,
    register_limiter,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _start_session(request: Request, user: User) -> str:
    request.session.clear()
    request.session["user_id"] = user.id
    csrf = new_csrf_token()
    request.session["csrf"] = csrf
    return csrf


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(body: RegisterIn, request: Request, db: Session = Depends(get_db)):
    """Create a teacher account and log in."""
    ip = client_ip(request)
    if register_limiter.is_blocked(ip):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "สมัครบ่อยเกินไป กรุณาลองใหม่ภายหลัง")
    email = body.email.lower()
    if db.scalar(select(User).where(func.lower(User.email) == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "อีเมลนี้มีบัญชีอยู่แล้ว กรุณาเข้าสู่ระบบ")
    user = User(
        email=email,
        password_hash=hash_password(body.password),
        full_name=body.full_name,
        position=body.position,
        department=body.department,
        learning_area=body.learning_area,
        school_name=body.school_name,
    )
    db.add(user)
    db.commit()
    register_limiter.record_failure(ip)  # counts sign-ups, not failures
    csrf = _start_session(request, user)
    return {"user": UserOut.model_validate(user), "csrf": csrf}


@router.post("/login")
def login(body: LoginIn, request: Request, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    key = f"{email}|{client_ip(request)}"
    if login_limiter.is_blocked(key):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "ลองผิดหลายครั้งเกินไป กรุณารอ 15 นาทีแล้วลองใหม่")
    user = db.scalar(select(User).where(func.lower(User.email) == email))
    ok = verify_password(body.password, user.password_hash if user else DUMMY_HASH)
    if not user or not ok or not user.is_active:
        login_limiter.record_failure(key)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "อีเมลหรือรหัสผ่านไม่ถูกต้อง")
    login_limiter.reset(key)
    csrf = _start_session(request, user)
    return {"user": UserOut.model_validate(user), "csrf": csrf}


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return {"ok": True}


@router.get("/me")
def me(request: Request, user: User = Depends(get_current_user)):
    if "csrf" not in request.session:
        request.session["csrf"] = new_csrf_token()
    return {"user": UserOut.model_validate(user), "csrf": request.session["csrf"]}


@router.put("/profile", dependencies=[Depends(verify_csrf)])
def update_profile(body: ProfileIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """School and teacher details printed on the reports."""
    user = db.merge(user)
    user.full_name = body.full_name
    user.position = body.position
    user.department = body.department
    user.learning_area = body.learning_area
    user.school_location = body.school_location
    user.school_name = body.school_name
    user.area_office = body.area_office
    db.commit()
    return {"user": UserOut.model_validate(user)}


@router.put("/password", dependencies=[Depends(verify_csrf)])
def change_password(body: ChangePasswordIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.merge(user)
    # A Google-only account has no password yet: it may set one without the old one.
    if user.password_hash and not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "รหัสผ่านปัจจุบันไม่ถูกต้อง")
    user.password_hash = hash_password(body.password)
    db.commit()
    return {"ok": True}


# --- Sign in with Google -------------------------------------------------------------

PENDING_KEY = "google_pending"


def _redirect_uri(request: Request) -> str:
    base = get_settings().public_base_url.rstrip("/") or str(request.base_url).rstrip("/")
    return f"{base}/api/auth/google/callback"


def _safe_next(value: str | None) -> str:
    return value if value and value.startswith("/app") and not value.startswith("//") else "/app"


def _require_google():
    if not get_settings().google_enabled:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "ยังไม่ได้เปิดการเข้าสู่ระบบด้วย Google")


@router.get("/google/start", dependencies=[Depends(_require_google)])
def google_start(request: Request, next: str | None = None):
    state = secrets.token_urlsafe(24)
    request.session["google_state"] = state
    request.session["google_next"] = _safe_next(next)
    url = google_oauth.authorize_url(get_settings().google_client_id, _redirect_uri(request), state)
    return RedirectResponse(url, status_code=303)


@router.get("/google/callback", dependencies=[Depends(_require_google)])
def google_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    expected = request.session.pop("google_state", None)
    next_url = request.session.pop("google_next", "/app")
    if error or not code or not state or not expected or not secrets.compare_digest(state, expected):
        return RedirectResponse("/login?google=failed", status_code=303)
    settings = get_settings()
    try:
        info = google_oauth.exchange_code(
            code, settings.google_client_id, settings.google_client_secret, _redirect_uri(request)
        )
    except google_oauth.GoogleAuthError:
        return RedirectResponse("/login?google=failed", status_code=303)

    user = db.scalar(select(User).where(User.google_sub == info["sub"]))
    if user is None:
        # Same verified email as an existing password account: link the two.
        user = db.scalar(select(User).where(func.lower(User.email) == info["email"]))
        if user is not None and user.google_sub is None:
            user.google_sub = info["sub"]
            db.commit()
        elif user is not None:
            return RedirectResponse("/login?google=failed", status_code=303)
    if user is not None:
        if not user.is_active:
            return RedirectResponse("/login?google=inactive", status_code=303)
        _start_session(request, user)
        return RedirectResponse(next_url, status_code=303)

    # New teacher: keep Google's details for a moment and ask for the report details.
    request.session.clear()
    request.session[PENDING_KEY] = {**info, "csrf": new_csrf_token()}
    return RedirectResponse("/register?google=1", status_code=303)


@router.get("/google/pending")
def google_pending(request: Request):
    pending = request.session.get(PENDING_KEY)
    if not pending:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "ไม่พบข้อมูลจาก Google กรุณากดเข้าสู่ระบบด้วย Google อีกครั้ง")
    return {"email": pending["email"], "name": pending["name"], "csrf": pending["csrf"]}


@router.post("/google/register", status_code=status.HTTP_201_CREATED)
def google_register(body: GoogleRegisterIn, request: Request, db: Session = Depends(get_db)):
    pending = request.session.get(PENDING_KEY)
    token = request.headers.get("x-csrf-token", "")
    if not pending or not secrets.compare_digest(token, pending.get("csrf", "")):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "ไม่พบข้อมูลจาก Google กรุณากดเข้าสู่ระบบด้วย Google อีกครั้ง")
    ip = client_ip(request)
    if register_limiter.is_blocked(ip):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "สมัครบ่อยเกินไป กรุณาลองใหม่ภายหลัง")
    email = pending["email"]
    taken = db.scalar(
        select(User).where((func.lower(User.email) == email) | (User.google_sub == pending["sub"]))
    )
    if taken:
        raise HTTPException(status.HTTP_409_CONFLICT, "อีเมลนี้มีบัญชีอยู่แล้ว กรุณาเข้าสู่ระบบ")
    user = User(
        email=email,
        password_hash="",
        google_sub=pending["sub"],
        full_name=body.full_name,
        position=body.position,
        department=body.department,
        learning_area=body.learning_area,
        school_name=body.school_name,
    )
    db.add(user)
    db.commit()
    register_limiter.record_failure(ip)  # counts sign-ups, not failures
    csrf = _start_session(request, user)
    return {"user": UserOut.model_validate(user), "csrf": csrf}
