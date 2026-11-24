"""Build the public sample report shown on the home page (made-up teacher, school and students).

Usage:  python -m scripts.make_sample_report
Writes: app/static/sample/kruflow-sample-report.pdf and page previews app/static/sample/page-*.jpg
        (previews need `pdftoppm` from poppler-utils).

`seed()` is also used by e2e/demo_video to prepare the classroom shown in the demo clip.
Every name here is invented. Do not put real students in this file: the output is public.
"""
import os
import random
import shutil
import subprocess
import tempfile
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "app" / "static" / "sample"
EMAIL, PASSWORD = "sample@kruflow.example", "sample-report-1"

STUDENTS = [
    ("นาย", "ก้องภพ", "ตัวอย่างดี", "ก้อง"), ("นางสาว", "ใจดี", "ทดลองใช้", "ใจ"),
    ("นาย", "ภูมิใจ", "สมมุติชื่อ", "ภูมิ"), ("นางสาว", "ฟ้าใส", "ตัวอย่างงาม", "ฟ้า"),
    ("นาย", "ตั้งใจ", "เรียนดี", "ตั้ง"), ("นางสาว", "ขยัน", "ตัวอย่างยิ่ง", "ขิม"),
    ("นาย", "มานะ", "สมมุติวงศ์", "นะ"), ("นางสาว", "ปิติ", "ทดลองสุข", "ปิ่น"),
    ("นาย", "ชูใจ", "ตัวอย่างไทย", "ชู"), ("นางสาว", "วีณา", "สมมุติศรี", "วี"),
    ("นาย", "สมหวัง", "ทดลองเรียน", "หวัง"), ("นางสาว", "พอใจ", "ตัวอย่างแก้ว", "พอ"),
]
TALENTS = ["ร้องเพลง", "วาดรูป", "เล่นฟุตบอล", "เล่นดนตรีไทย", "เขียนเรียงความ", "ทำอาหาร"]
SUBJECTS = ["คณิตศาสตร์", "วิทยาศาสตร์", "ภาษาอังกฤษ", "ศิลปะ", "พลศึกษา"]
SPORTS = ["ฟุตบอล", "วอลเลย์บอล", "แบดมินตัน", "ตะกร้อ", "ว่ายน้ำ"]
BOOKS = ["การ์ตูนความรู้", "นิยาย", "หนังสือวิทยาศาสตร์", "นิตยสารกีฬา"]
JOBS = ["ครู", "พยาบาล", "วิศวกร", "ตำรวจ", "นักออกแบบ", "โปรแกรมเมอร์"]
METHODS = ["lecture", "discussion", "mindmap", "questioning", "project", "roleplay", "experiment", "group"]


def seed(c, submit: int = len(STUDENTS), evaluate: int = len(STUDENTS)) -> tuple[int, dict]:
    """Register the sample teacher and fill one classroom. Returns (classroom id, CSRF header)."""
    from app.deps import current_academic_term
    from app.services.summary import ITEM_CODES

    rnd = random.Random(2569)
    profile = {
        "full_name": "นางสาวกานดา ตัวอย่าง", "position": "ครู", "department": "กลุ่มบริหารวิชาการ",
        "learning_area": "กลุ่มสาระการเรียนรู้คณิตศาสตร์", "school_name": "โรงเรียนตัวอย่างวิทยาคม",
        "area_office": "สำนักงานเขตพื้นที่การศึกษามัธยมศึกษาตัวอย่าง",
    }
    r = c.post("/api/auth/register", json={"email": EMAIL, "password": PASSWORD, "accept_terms": True, **profile})
    r.raise_for_status()
    h = {"X-CSRF-Token": r.json()["csrf"]}
    c.put("/api/auth/profile", headers=h,
          json={**profile, "school_location": "อำเภอเมือง จังหวัดตัวอย่าง"}).raise_for_status()
    year, sem = current_academic_term()
    room = c.post("/api/classrooms", headers=h, json={"subject_name": "คณิตศาสตร์พื้นฐาน", "subject_code": "ค23101",
                  "grade_label": "มัธยมศึกษาปีที่ 3/1", "academic_year": year, "semester": sem}).json()
    names = [f"{t}{f} {l}" for t, f, l, _ in STUDENTS]
    c.put(f"/api/classrooms/{room['id']}/roster", headers=h,
          json={"text": "\n".join(f"{i}\t{n}" for i, n in enumerate(names, 1))}).raise_for_status()
    token = room["student_link"].rsplit("/", 1)[1]
    for i, (_, _, last, nick) in enumerate(STUDENTS[:submit], 1):
        c.post(f"/api/f/{token}/submissions", json={
            "student_no": i, "full_name": names[i - 1], "nickname": nick,
            "personal_info": {
                "age": 15, "prev_grade_level": "ม.2", "prev_gpa": round(rnd.uniform(2.4, 3.9), 2),
                "father_name": f"นาย{rnd.choice(['สมชาย', 'สมศักดิ์', 'ประเสริฐ'])} {last}",
                "father_job": rnd.choice(["เกษตรกร", "รับจ้าง", "ค้าขาย"]),
                "mother_name": f"นาง{rnd.choice(['สมศรี', 'มาลี', 'บุญมี'])} {last}",
                "mother_job": rnd.choice(["เกษตรกร", "แม่บ้าน", "ค้าขาย"]),
                "parent_status": "อยู่ด้วยกัน", "lives_with": "บิดามารดา",
            },
            "open_answers": {
                "q1": rnd.choice(TALENTS), "q2": rnd.choice(SUBJECTS), "q3": rnd.choice(SPORTS), "q4": rnd.choice(BOOKS),
                "q5": "ได้ไปทัศนศึกษากับเพื่อน", "q6": "เพื่อนที่จริงใจและช่วยเหลือกัน", "q7": "ครูที่ใจดีและอธิบายเข้าใจง่าย",
                "q8": rnd.choice(["ความรับผิดชอบในการส่งงาน", "การบริหารเวลา", "ความกล้าแสดงออก"]),
                "q9": "มีพื้นที่ร่มรื่นและห้องสมุดที่ทันสมัย", "q10": rnd.choice(JOBS),
            },
            "learning_prefs": rnd.sample(METHODS, 4), "consent": True}).raise_for_status()
    subs = [s for s in c.get(f"/api/classrooms/{room['id']}/submissions").json() if s.get("id")]
    for k, s in enumerate(subs[:evaluate]):
        base = "good" if k < 4 else "fair"
        scores = {code: {"rating": base if rnd.random() > 0.25 else rnd.choice(["good", "fair"]), "note": ""}
                  for code in ITEM_CODES}
        if k in (7, 10):
            scores["d3_3"] = scores["d3_4"] = {"rating": "improve", "note": "ส่งงานไม่ตรงเวลา"}
        c.put(f"/api/classrooms/{room['id']}/submissions/{s['id']}/evaluation", headers=h,
              json={"scores": scores, "last_grade": rnd.choice(["2.5", "3", "3.5", "4"]),
                    "teacher_comment": "ควรส่งเสริมการทำงานกลุ่มและการนำเสนอหน้าชั้นเรียน"}).raise_for_status()
    return room["id"], h


def main() -> Path:
    tmp = tempfile.mkdtemp()
    os.environ["DATABASE_URL"] = f"sqlite:///{tmp}/sample.db"
    os.environ.setdefault("SECRET_KEY", "sample-report")
    os.environ["TRIAL_STUDENT_LIMIT"] = "100"  # the sample class is bigger than a trial room
    from fastapi.testclient import TestClient

    from app.database import Base, engine
    from app.main import app

    Base.metadata.create_all(engine)
    c = TestClient(app, base_url="https://kruflow.example")
    room_id, _ = seed(c)
    pdf = c.get(f"/api/classrooms/{room_id}/pdf/full", params={"doc_no": "123/2569"})
    pdf.raise_for_status()
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / "kruflow-sample-report.pdf"
    target.write_bytes(pdf.content)
    if shutil.which("pdftoppm"):
        for page in (1, 2, 3, 4):
            subprocess.run(["pdftoppm", "-jpeg", "-jpegopt", "quality=80", "-r", "90", "-f", str(page), "-l", str(page),
                            "-singlefile", str(target), str(OUT / f"page-{page}")], check=True)
    shutil.rmtree(tmp, ignore_errors=True)
    print(target)
    return target


if __name__ == "__main__":
    main()
