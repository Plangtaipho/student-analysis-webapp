"""ห้องคละ: an elective subject whose students come from several classes.

In such a room two students can share the same เลขที่ (number in their own class),
so a student is told apart by home class + number, e.g. "ม.3/2 เลขที่ 5".
In a normal room home_class is "" and only the number counts.
"""
import re

_THAI_DIGITS = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")
MAX_LEN = 20
HOME_CLASS_HINT = "กรอกห้องเดิมให้ถูกต้อง เช่น ม.3/2"


def _level_of(text: str) -> str:
    """"ป" or "ม" from a label such as "มัธยมศึกษาปีที่ 3/2", "ม.3" or "ประถมศึกษาปีที่ 6"."""
    t = text.replace(" ", "")
    if t.startswith("อ") or "อนุบาล" in t:
        return "อ"
    if t.startswith("ป") or "ประถม" in t:
        return "ป"
    if t.startswith("ม") or "มัธยม" in t:
        return "ม"
    return ""


def normalize_home_class(raw: str, grade_label: str = "") -> str:
    """Turn what a student typed ("ม.3/2", "ม 3/2", "3/2", "ม.๓/๒", "มัธยมศึกษาปีที่ 3/2")
    into the short form "ม.3/2". Without ป/ม in the text, the level of the room is used.
    Raises ValueError (Thai) when no "year/room" is found."""
    text = (raw or "").translate(_THAI_DIGITS).strip()
    m = re.search(r"(\d{1,2})\s*/\s*(\d{1,2})", text)
    if not m:
        raise ValueError(HOME_CLASS_HINT)
    year, room = int(m.group(1)), int(m.group(2))
    if not (1 <= year <= 6 and 1 <= room <= 99):
        raise ValueError(HOME_CLASS_HINT)
    level = _level_of(text[: m.start()]) or _level_of(grade_label) or "ม"
    return f"{level}.{year}/{room}"


def sort_key(home_class: str, student_no: int) -> tuple:
    """Order by level (อ, ป, ม), year, room, then number. An empty home class comes first."""
    m = re.match(r"^(\S)\.(\d+)/(\d+)$", home_class or "")
    if not m:
        return (0, 0, 0, 0, student_no) if not home_class else (9, 0, 0, home_class, student_no)
    return (1, "อปม".find(m.group(1)), int(m.group(2)), int(m.group(3)), student_no)


def label(home_class: str, student_no: int) -> str:
    """"ม.3/2 เลขที่ 5", or "เลขที่ 5" in a normal room."""
    return f"{home_class} เลขที่ {student_no}" if home_class else f"เลขที่ {student_no}"


def for_room(room, raw: str, required: bool = True) -> str:
    """The home class to store for a student of `room`: always "" in a normal room.
    In a ห้องคละ it is required from students; the teacher may leave it blank
    (records sent before the room became ห้องคละ). Raises ValueError (Thai)."""
    if not room.mixed_classes:
        return ""
    if not (raw or "").strip() and not required:
        return ""
    if not (raw or "").strip():
        raise ValueError("กรุณากรอกห้องเดิมของนักเรียน เช่น ม.3/2")
    return normalize_home_class(raw, room.grade_label)


def ordered(items):
    """Submissions or roster entries in report order: home class (ม.3/2 before ม.3/10), then number."""
    return sorted(items, key=lambda x: sort_key(x.home_class, x.student_no))


_LONG = {"ม": "มัธยมศึกษาปีที่", "ป": "ประถมศึกษาปีที่", "อ": "อนุบาลปีที่"}


def long_form(home_class: str) -> str:
    """"ม.3/2" -> "มัธยมศึกษาปีที่ 3/2", as the ชั้น line of the individual record prints it."""
    m = re.match(r"^(\S)\.(\d+/\d+)$", home_class or "")
    return f"{_LONG.get(m.group(1), m.group(1))} {m.group(2)}" if m else home_class
