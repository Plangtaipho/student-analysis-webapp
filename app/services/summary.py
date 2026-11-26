"""Class summary: counts and percentages per assessment item, and the four learner groups.

The grouping rule is a DEFAULT until the customer confirms the real criteria.
It lives only in `auto_group()`, so changing it later touches one function.
"""
from app.models import Classroom, LearnerGroup, Rating, Submission
from app.services.form_definition import ASSESSMENT_DOMAINS
from app.services.home_class import ordered

RATING_POINTS = {Rating.good: 3, Rating.fair: 2, Rating.improve: 1}

GROUP_LABELS = {
    LearnerGroup.high: "กลุ่มผู้เรียนที่มีความพร้อมสูงทุกด้าน",
    LearnerGroup.medium: "กลุ่มผู้เรียนที่มีความพร้อมปานกลาง",
    LearnerGroup.low: "กลุ่มผู้เรียนที่ไม่มีความพร้อม",
    LearnerGroup.disability: "กลุ่มผู้เรียนที่บกพร่องทางการเรียนรู้",
}
GROUP_ORDER = (LearnerGroup.high, LearnerGroup.medium, LearnerGroup.low, LearnerGroup.disability)

ITEM_CODES = tuple(code for _, _, items in ASSESSMENT_DOMAINS for code, _ in items)


def auto_group(ratings: list[Rating]) -> LearnerGroup:
    """Grouping rule confirmed by the user (2026-11-21): average of good=3, fair=2, improve=1.

    average >= 2.5 -> high, average < 1.5 -> low, otherwise medium.
    "Learning disability" is never automatic: only the teacher can set it.
    """
    if not ratings:
        return LearnerGroup.medium
    avg = sum(RATING_POINTS[r] for r in ratings) / len(ratings)
    if avg >= 2.5:
        return LearnerGroup.high
    if avg < 1.5:
        return LearnerGroup.low
    return LearnerGroup.medium


def group_of(sub: Submission) -> LearnerGroup | None:
    ev = sub.evaluation
    if ev is None:
        return None
    if ev.group_override is not None:
        return ev.group_override
    return auto_group([s.rating for s in ev.scores])


def pct(n: int, total: int) -> float:
    return round(n * 100 / total, 2) if total else 0.0


def classroom_summary(room: Classroom) -> dict:
    evaluated = [s for s in ordered(room.submissions) if s.evaluation is not None]
    total = len(evaluated)
    counts = {code: {r: 0 for r in Rating} for code in ITEM_CODES}
    for sub in evaluated:
        for score in sub.evaluation.scores:
            if score.item_code in counts:
                counts[score.item_code][score.rating] += 1

    domains = []
    for domain_no, domain_name, items in ASSESSMENT_DOMAINS:
        rows = []
        for code, label in items:
            c = counts[code]
            rows.append(
                {
                    "code": code,
                    "label": label,
                    **{r.value: c[r] for r in Rating},
                    **{f"{r.value}_pct": pct(c[r], total) for r in Rating},
                }
            )
        domains.append({"domain_no": domain_no, "domain_name": domain_name, "items": rows})

    groups: dict[str, list[dict]] = {g.value: [] for g in GROUP_ORDER}
    for sub in evaluated:
        groups[group_of(sub).value].append(
            {"home_class": sub.home_class, "student_no": sub.student_no, "full_name": sub.full_name}
        )

    class_size = len(room.roster) or len(room.submissions)
    return {
        "class_size": class_size,
        "submitted": sum(1 for s in room.submissions if not s.created_by_teacher),
        "evaluated": total,
        "domains": domains,
        "groups": [
            {"key": g.value, "label": GROUP_LABELS[g], "students": groups[g.value]} for g in GROUP_ORDER
        ],
    }
