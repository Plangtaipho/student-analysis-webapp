"""Turn a submission (+ evaluation) into what the individual-record PDF prints."""
from datetime import date

from app.models import Submission

THAI_MONTHS = (
    "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
    "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม",
)


def thai_date(iso: str | None) -> str:
    if not iso:
        return ""
    try:
        d = date.fromisoformat(iso)
    except ValueError:
        return ""
    return f"{d.day} {THAI_MONTHS[d.month - 1]} {d.year + 543}"


def individual_record(sub: Submission) -> dict:
    ev = sub.evaluation
    scores = {s.item_code: s for s in ev.scores} if ev else {}
    totals = {"good": 0, "fair": 0, "improve": 0}
    for s in scores.values():
        totals[s.rating.value] += 1
    return {
        "sub": sub,
        "birth_text": thai_date(sub.personal_info.get("birth_date")),
        "ranks": {key: i for i, key in enumerate(sub.learning_prefs, start=1)},
        "scores": {k: {"rating": v.rating.value, "improvement_note": v.improvement_note} for k, v in scores.items()},
        "totals": totals,
        "last_grade": ev.last_grade if ev else "",
        "comment": ev.teacher_comment if ev else "",
    }
