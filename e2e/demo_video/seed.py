"""Prepare the classroom shown in the demo clip: 11 of 12 made-up students done, student 12 fills in on camera.

Usage (empty database, TRIAL_STUDENT_LIMIT above 12):
  DATABASE_URL=sqlite:///./demo.db TRIAL_STUDENT_LIMIT=100 python -m e2e.demo_video.seed
"""
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app
from scripts.make_sample_report import seed

if __name__ == "__main__":
    Base.metadata.create_all(engine)
    room_id, _ = seed(TestClient(app), submit=11, evaluate=11)
    print(room_id)
