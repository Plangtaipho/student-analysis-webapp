"""Teacher sign-up, login, logout, profile and password."""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import client_ip, get_current_user, verify_csrf
from app.models import User
from app.schemas import ChangePasswordIn, LoginIn, ProfileIn, RegisterIn, UserOut
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
    user.school_location = body.school_location
    user.school_name = body.school_name
    user.area_office = body.area_office
    db.commit()
    return {"user": UserOut.model_validate(user)}


@router.put("/password", dependencies=[Depends(verify_csrf)])
def change_password(body: ChangePasswordIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.merge(user)
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "รหัสผ่านปัจจุบันไม่ถูกต้อง")
    user.password_hash = hash_password(body.password)
    db.commit()
    return {"ok": True}
