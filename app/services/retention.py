"""Data retention: student data is kept for one semester.

The user's rule (2026-11-21): a classroom and every answer in it are deleted
45 days after its semester ends, so the teacher has time to download the PDF.

Thai school terms differ a little between schools, so the end dates here are
the latest usual ones: semester 1 ends 31 October, semester 2 ends 31 March.
"""
import asyncio
import logging
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Classroom

log = logging.getLogger(__name__)

KEEP_DAYS_AFTER_TERM = 45
PURGE_INTERVAL_SECONDS = 6 * 3600


def term_end(academic_year: int, semester: int) -> date:
    """Last day of a Thai school term. academic_year is the Buddhist year, e.g. 2569."""
    ce = academic_year - 543
    return date(ce, 10, 31) if semester == 1 else date(ce + 1, 3, 31)


def purge_on(academic_year: int, semester: int) -> date:
    """The day the classroom's data is deleted."""
    return term_end(academic_year, semester) + timedelta(days=KEEP_DAYS_AFTER_TERM)


def purge_expired(db: Session, on: date) -> int:
    """Delete every classroom whose purge date has come. Returns how many were deleted."""
    rooms = db.scalars(select(Classroom)).all()
    expired = [r for r in rooms if purge_on(r.academic_year, r.semester) <= on]
    for room in expired:
        db.delete(room)  # cascades to roster, submissions, evaluations and scores
    if expired:
        db.commit()
        log.info("Retention: deleted %d classroom(s) past their purge date", len(expired))
    return len(expired)


async def purge_loop() -> None:
    """Runs in the web process: purge at start-up, then every few hours."""
    from app.database import SessionLocal
    from app.deps import today

    while True:
        try:
            with SessionLocal() as db:
                await asyncio.to_thread(purge_expired, db, today())
        except Exception:  # keep the loop alive; the next run tries again
            log.exception("Retention purge failed")
        await asyncio.sleep(PURGE_INTERVAL_SECONDS)
