"""Pydantic request/response models."""
import re
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.security import MAX_PASSWORD_BYTES
from app.services.form_definition import (
    LEARNING_METHOD_LABELS,
    MIN_RANKED_METHODS,
    OPEN_QUESTION_KEYS,
    PERSONAL_FIELDS,
)


def _clean(s: str) -> str:
    # Collapse runs of whitespace; strip control characters.
    s = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", s)
    return re.sub(r"[ \t]+", " ", s).strip()


# Official letters need full agency names, so common short forms are spelled out.
AREA_OFFICE_ABBREVIATIONS = (
    (r"สพม\.?", "สำนักงานเขตพื้นที่การศึกษามัธยมศึกษา"),
    (r"สพป\.?", "สำนักงานเขตพื้นที่การศึกษาประถมศึกษา"),
    (r"สพฐ\.?", "สำนักงานคณะกรรมการการศึกษาขั้นพื้นฐาน"),
    (r"สช\.", "สำนักงานคณะกรรมการส่งเสริมการศึกษาเอกชน"),
)


def expand_area_office(s: str) -> str:
    """'สพม.เลย หนองบัวลำภู' -> 'สำนักงานเขตพื้นที่การศึกษามัธยมศึกษาเลย หนองบัวลำภู'."""
    s = _clean(s)
    for short, full in AREA_OFFICE_ABBREVIATIONS:
        s = re.sub(rf"(?<![\u0E00-\u0E7F]){short}\s*", full, s)
    return s


# --- Teacher accounts --------------------------------------------------------------


# กลุ่มงาน (printed as ส่วนราชการ in the memo) and กลุ่มสาระ are separate choices.
WORK_GROUPS = ("กลุ่มบริหารวิชาการ", "กลุ่มบริหารงบประมาณ", "กลุ่มบริหารงานบุคคล", "กลุ่มบริหารงานทั่วไป")
LEARNING_AREAS = (
    "กลุ่มสาระการเรียนรู้ภาษาไทย",
    "กลุ่มสาระการเรียนรู้คณิตศาสตร์",
    "กลุ่มสาระการเรียนรู้วิทยาศาสตร์และเทคโนโลยี",
    "กลุ่มสาระการเรียนรู้สังคมศึกษา ศาสนาและวัฒนธรรม",
    "กลุ่มสาระการเรียนรู้สุขศึกษาและพลศึกษา",
    "กลุ่มสาระการเรียนรู้ศิลปะ",
    "กลุ่มสาระการเรียนรู้การงานอาชีพ",
    "กลุ่มสาระการเรียนรู้ภาษาต่างประเทศ",
    "กิจกรรมพัฒนาผู้เรียน",
)
POSITIONS = ("ครู", "พนักงานราชการ", "อัตราจ้าง")
Position = Literal["ครู", "พนักงานราชการ", "อัตราจ้าง"]
WorkGroup = Literal["กลุ่มบริหารวิชาการ", "กลุ่มบริหารงบประมาณ", "กลุ่มบริหารงานบุคคล", "กลุ่มบริหารงานทั่วไป"]
LearningArea = Literal[
    "กลุ่มสาระการเรียนรู้ภาษาไทย",
    "กลุ่มสาระการเรียนรู้คณิตศาสตร์",
    "กลุ่มสาระการเรียนรู้วิทยาศาสตร์และเทคโนโลยี",
    "กลุ่มสาระการเรียนรู้สังคมศึกษา ศาสนาและวัฒนธรรม",
    "กลุ่มสาระการเรียนรู้สุขศึกษาและพลศึกษา",
    "กลุ่มสาระการเรียนรู้ศิลปะ",
    "กลุ่มสาระการเรียนรู้การงานอาชีพ",
    "กลุ่มสาระการเรียนรู้ภาษาต่างประเทศ",
    "กิจกรรมพัฒนาผู้เรียน",
]


class Password(BaseModel):
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def _len_bytes(cls, v: str) -> str:
        if len(v.encode("utf-8")) > MAX_PASSWORD_BYTES:
            raise ValueError("รหัสผ่านยาวเกินไป")
        return v


class RegisterIn(Password):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=120)
    position: Position
    department: WorkGroup
    learning_area: LearningArea
    school_name: str = Field(min_length=2, max_length=160)
    # Asked again at sign-up (2026-11-24), picked from the list of 245 areas. Not printed on documents.
    area_office: str = Field(min_length=3, max_length=200)

    @field_validator("area_office")
    @classmethod
    def _full_area_office(cls, v: str | None) -> str | None:
        return expand_area_office(v) if v else v
    accept_terms: bool

    @field_validator("full_name", "school_name")
    @classmethod
    def _strip(cls, v: str) -> str:
        return _clean(v)

    @field_validator("accept_terms")
    @classmethod
    def _must_accept(cls, v: bool) -> bool:
        if not v:
            raise ValueError("กรุณายอมรับเงื่อนไขการใช้งานและนโยบายความเป็นส่วนตัว")
        return v


class GoogleRegisterIn(BaseModel):
    """Finish a Google sign-up: the details a report needs (email comes from Google)."""

    full_name: str = Field(min_length=2, max_length=120)
    position: Position
    department: WorkGroup
    learning_area: LearningArea
    school_name: str = Field(min_length=2, max_length=160)
    # Asked again at sign-up (2026-11-24), picked from the list of 245 areas. Not printed on documents.
    area_office: str = Field(min_length=3, max_length=200)

    @field_validator("area_office")
    @classmethod
    def _full_area_office(cls, v: str | None) -> str | None:
        return expand_area_office(v) if v else v
    accept_terms: bool

    @field_validator("full_name", "school_name")
    @classmethod
    def _strip(cls, v: str) -> str:
        return _clean(v)

    @field_validator("accept_terms")
    @classmethod
    def _must_accept(cls, v: bool) -> bool:
        if not v:
            raise ValueError("กรุณายอมรับเงื่อนไขการใช้งานและนโยบายความเป็นส่วนตัว")
        return v


class LoginIn(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=128)


class ProfileIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    position: Position
    department: WorkGroup
    learning_area: LearningArea
    school_name: str = Field(min_length=2, max_length=160)
    school_location: str = Field(default="", max_length=160)
    # None = keep the saved value.
    area_office: str | None = Field(default=None, max_length=200)

    @field_validator("area_office")
    @classmethod
    def _full_area_office(cls, v: str | None) -> str | None:
        return expand_area_office(v) if v else v

    @field_validator("full_name", "school_name", "school_location")
    @classmethod
    def _strip(cls, v: str) -> str:
        return _clean(v)


class ChangePasswordIn(Password):
    current_password: str = Field(max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    full_name: str
    position: str
    department: str
    learning_area: str
    school_name: str
    school_location: str
    area_office: str
    role: str
    has_password: bool = True
    google_linked: bool = False

    @model_validator(mode="before")
    @classmethod
    def _flags(cls, v):
        if hasattr(v, "password_hash"):
            return {
                **{k: getattr(v, k) for k in cls.model_fields if hasattr(v, k)},
                "has_password": bool(v.password_hash),
                "google_linked": bool(getattr(v, "google_sub", None)),
            }
        return v


# --- Classrooms ----------------------------------------------------------------------


class ClassroomIn(BaseModel):
    subject_name: str = Field(min_length=1, max_length=120)
    subject_code: str = Field(default="", max_length=20)
    grade_label: str = Field(min_length=1, max_length=40)
    academic_year: int = Field(ge=2560, le=2700)
    semester: int = Field(ge=1, le=2)

    @field_validator("subject_name", "subject_code", "grade_label")
    @classmethod
    def _strip(cls, v: str) -> str:
        return _clean(v)


class ClassroomPatch(BaseModel):
    is_open: bool | None = None
    subject_name: str | None = Field(default=None, min_length=1, max_length=120)
    subject_code: str | None = Field(default=None, max_length=20)
    grade_label: str | None = Field(default=None, min_length=1, max_length=40)


class ClassroomOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    subject_name: str
    subject_code: str
    grade_label: str
    academic_year: int
    semester: int
    is_open: bool
    is_trial: bool
    student_link: str = ""
    submitted_count: int = 0
    roster_count: int = 0
    evaluated_count: int = 0
    # Retention: the day this classroom and its answers are deleted, and whether the term has ended.
    purge_on: date | None = None
    # False for a non-trial room whose semester is not paid (see app/services/billing.py).
    is_active: bool = True
    student_limit: int | None = None
    term_ended: bool = False


class RosterIn(BaseModel):
    # Text pasted from Excel: one student per line, "number<TAB>name" or just "name".
    text: str = Field(max_length=20_000)


class RosterEntryOut(BaseModel):
    student_no: int
    full_name: str


# --- Student form --------------------------------------------------------------------


def clean_personal_info(raw: dict) -> dict:
    """Keep only known fields, trimmed and range-checked. Raises ValueError in Thai."""
    out: dict = {}
    for key, value in (raw or {}).items():
        f = PERSONAL_FIELDS.get(key)
        if f is None or value is None or value == "":
            continue
        if f.kind == "number":
            try:
                num = float(value)
            except (TypeError, ValueError):
                raise ValueError(f"{f.label}: กรุณากรอกเป็นตัวเลข") from None
            if (f.min_value is not None and num < f.min_value) or (f.max_value is not None and num > f.max_value):
                raise ValueError(f"{f.label}: ตัวเลขไม่อยู่ในช่วงที่เป็นไปได้")
            out[key] = int(num) if num.is_integer() and key != "prev_gpa" else round(num, 2)
        elif f.kind == "date":
            try:
                d = date.fromisoformat(str(value))
            except ValueError:
                raise ValueError(f"{f.label}: รูปแบบวันที่ไม่ถูกต้อง") from None
            if not (1990 <= d.year <= 2030):
                raise ValueError(f"{f.label}: กรุณาเลือกวันเกิดเป็นปี ค.ศ. ในปฏิทิน")
            out[key] = d.isoformat()
        elif f.kind == "select":
            if value not in f.options:
                raise ValueError(f"{f.label}: ตัวเลือกไม่ถูกต้อง")
            out[key] = value
        else:
            text = _clean(str(value))
            if len(text) > f.max_len:
                raise ValueError(f"{f.label}: ยาวเกิน {f.max_len} ตัวอักษร")
            if text:
                out[key] = text
    if out.get("parent_status") != "อื่นๆ":
        out.pop("parent_status_other", None)
    return out


def clean_open_answers(v: dict[str, str]) -> dict[str, str]:
    out = {}
    for key in OPEN_QUESTION_KEYS:
        text = _clean(v.get(key, "") or "")
        if len(text) > 300:
            raise ValueError("คำตอบแต่ละข้อยาวได้ไม่เกิน 300 ตัวอักษร")
        if text:
            out[key] = text
    return out


class SubmissionIn(BaseModel):
    student_no: int = Field(ge=1, le=200)
    full_name: str = Field(min_length=2, max_length=120)
    nickname: str = Field(default="", max_length=40)
    personal_info: dict = Field(default_factory=dict)
    open_answers: dict[str, str] = Field(default_factory=dict)
    learning_prefs: list[str] = Field(default_factory=list)
    consent: bool
    # Present when a student edits answers they sent before.
    edit_code: str | None = Field(default=None, max_length=6)

    @field_validator("full_name", "nickname")
    @classmethod
    def _strip(cls, v: str) -> str:
        return _clean(v)

    @field_validator("consent")
    @classmethod
    def _must_consent(cls, v: bool) -> bool:
        if not v:
            raise ValueError("กรุณากดยินยอมก่อนส่งแบบฟอร์ม")
        return v

    @field_validator("personal_info")
    @classmethod
    def _personal(cls, v: dict) -> dict:
        return clean_personal_info(v)

    @field_validator("open_answers")
    @classmethod
    def _answers(cls, v: dict[str, str]) -> dict[str, str]:
        return clean_open_answers(v)

    @field_validator("learning_prefs")
    @classmethod
    def _prefs(cls, v: list[str]) -> list[str]:
        if len(set(v)) != len(v) or any(k not in LEARNING_METHOD_LABELS for k in v):
            raise ValueError("การเรียงลำดับวิธีการเรียนไม่ถูกต้อง")
        if len(v) < MIN_RANKED_METHODS:
            raise ValueError(f"กรุณาเลือกวิธีการเรียนที่ชอบอย่างน้อย {MIN_RANKED_METHODS} อันดับ")
        return v


class SubmissionEditIn(BaseModel):
    """The teacher corrects a student's record (wrong number or name, or wrong answers).
    personal_info / open_answers left out (None) are kept as they are."""

    student_no: int = Field(ge=1, le=200)
    full_name: str = Field(min_length=2, max_length=120)
    nickname: str = Field(default="", max_length=40)
    personal_info: dict | None = None
    open_answers: dict[str, str] | None = None

    @field_validator("full_name", "nickname")
    @classmethod
    def _strip(cls, v: str) -> str:
        return _clean(v)

    @field_validator("personal_info")
    @classmethod
    def _personal(cls, v: dict | None) -> dict | None:
        return None if v is None else clean_personal_info(v)

    @field_validator("open_answers")
    @classmethod
    def _answers(cls, v: dict[str, str] | None) -> dict[str, str] | None:
        return None if v is None else clean_open_answers(v)


class LookupIn(BaseModel):
    student_no: int = Field(ge=1, le=200)
    edit_code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class SubmissionSummary(BaseModel):
    id: int
    student_no: int
    full_name: str
    nickname: str
    submitted_at: str
    status: str  # submitted | evaluated


# --- Teacher evaluation ---------------------------------------------------------------


class ScoreIn(BaseModel):
    rating: str = Field(pattern=r"^(good|fair|improve)$")
    note: str = Field(default="", max_length=200)

    @field_validator("note")
    @classmethod
    def _strip(cls, v: str) -> str:
        return _clean(v)


class EvaluationIn(BaseModel):
    scores: dict[str, ScoreIn]
    last_grade: str = Field(default="", max_length=10)
    teacher_comment: str = Field(default="", max_length=2000)
    # null = use the automatic group; or high | medium | low | disability
    group_override: str | None = Field(default=None, pattern=r"^(high|medium|low|disability)$")

    @field_validator("last_grade")
    @classmethod
    def _grade(cls, v: str) -> str:
        return _clean(v)

    @field_validator("teacher_comment")
    @classmethod
    def _comment(cls, v: str) -> str:
        return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", v).strip()


class ManualSubmissionIn(BaseModel):
    """A record the teacher creates for a student who cannot fill in the form."""

    student_no: int = Field(ge=1, le=200)
    full_name: str = Field(min_length=2, max_length=120)

    @field_validator("full_name")
    @classmethod
    def _strip(cls, v: str) -> str:
        return _clean(v)
