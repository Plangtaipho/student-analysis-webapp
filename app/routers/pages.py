"""Server-rendered HTML pages. Data is loaded by the page's JavaScript from the JSON API."""
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_optional_user
from app.models import User
from app.routers.student import get_room_by_token, room_info
from app.services.form_definition import (
    LEARNING_METHODS,
    MIN_RANKED_METHODS,
    OPEN_QUESTIONS,
    PERSONAL_SECTIONS,
)

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))
router = APIRouter(include_in_schema=False)


def _teacher_page(request: Request, user: User | None, name: str, **ctx):
    if user is None:
        return RedirectResponse(f"/login?next={request.url.path}", status_code=303)
    return templates.TemplateResponse(request, name, {"user": user, **ctx})


@router.get("/", response_class=HTMLResponse)
def home(request: Request, user: User | None = Depends(get_optional_user)):
    return templates.TemplateResponse(request, "home.html", {"user": user})


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, user: User | None = Depends(get_optional_user)):
    if user:
        return RedirectResponse("/app", status_code=303)
    return templates.TemplateResponse(request, "login.html", {"user": None})


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request, user: User | None = Depends(get_optional_user)):
    if user:
        return RedirectResponse("/app", status_code=303)
    return templates.TemplateResponse(request, "register.html", {"user": None})


@router.get("/privacy", response_class=HTMLResponse)
def privacy_page(request: Request, user: User | None = Depends(get_optional_user)):
    return templates.TemplateResponse(request, "privacy.html", {"user": user})


@router.get("/app", response_class=HTMLResponse)
def dashboard(request: Request, user: User | None = Depends(get_optional_user)):
    return _teacher_page(request, user, "teacher/dashboard.html")


@router.get("/app/profile", response_class=HTMLResponse)
def profile(request: Request, user: User | None = Depends(get_optional_user)):
    return _teacher_page(request, user, "teacher/profile.html")


@router.get("/app/classrooms/{classroom_id}", response_class=HTMLResponse)
def classroom_page(classroom_id: int, request: Request, user: User | None = Depends(get_optional_user)):
    return _teacher_page(request, user, "teacher/classroom.html", classroom_id=classroom_id)


@router.get("/app/classrooms/{classroom_id}/submissions/{submission_id}", response_class=HTMLResponse)
def submission_page(
    classroom_id: int, submission_id: int, request: Request, user: User | None = Depends(get_optional_user)
):
    return _teacher_page(
        request,
        user,
        "teacher/submission.html",
        classroom_id=classroom_id,
        submission_id=submission_id,
        sections=PERSONAL_SECTIONS,
        questions=OPEN_QUESTIONS,
    )


@router.get("/f/{token}", response_class=HTMLResponse)
def student_form(token: str, request: Request, db: Session = Depends(get_db)):
    try:
        room = get_room_by_token(token, db)
    except HTTPException:
        return templates.TemplateResponse(request, "student/not_found.html", {}, status_code=404)
    return templates.TemplateResponse(
        request,
        "student/form.html",
        {
            "token": token,
            "room": room_info(room),
            "sections": PERSONAL_SECTIONS,
            "questions": OPEN_QUESTIONS,
            "methods": LEARNING_METHODS,
            "min_ranked": MIN_RANKED_METHODS,
        },
    )


@router.get("/app/classrooms/{classroom_id}/submissions/{submission_id}/evaluate", response_class=HTMLResponse)
def evaluate_page(
    classroom_id: int, submission_id: int, request: Request, user: User | None = Depends(get_optional_user)
):
    return _teacher_page(
        request,
        user,
        "teacher/evaluate.html",
        classroom_id=classroom_id,
        submission_id=submission_id,
        questions=OPEN_QUESTIONS,
    )


@router.get("/app/classrooms/{classroom_id}/summary", response_class=HTMLResponse)
def summary_page(classroom_id: int, request: Request, user: User | None = Depends(get_optional_user)):
    return _teacher_page(request, user, "teacher/summary.html", classroom_id=classroom_id)
