"""Delete classrooms whose retention period has ended (the web app also does this by itself).

    python -m scripts.purge_expired
"""
from app.database import SessionLocal
from app.deps import today
from app.services.retention import purge_expired

if __name__ == "__main__":
    with SessionLocal() as db:
        print(f"Deleted {purge_expired(db, today())} classroom(s)")
