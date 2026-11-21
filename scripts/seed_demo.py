"""Create a demo teacher with one classroom of 19 students (most of them assessed).

Usage:  python -m scripts.seed_demo            (uses DATABASE_URL)
Login:  demo@example.com / demo12345
"""
import random

from fastapi.testclient import TestClient

from app.main import app
from app.services.summary import ITEM_CODES
from app.deps import current_academic_term

NAMES = [
    "นายนนทพัทธ์ ภูแซมโชติ", "นางสาวสุดธิดา ทองคำแสน", "นางสาวศิริรัตน์ พรมาแข้", "นางสาวกมลชนก จูมจะนะ",
    "นางสาวบัญฑิตา พิมพ์โพธิ์", "นายพิสิษฐ์ แสงกล้า", "นางสาวโชติกา เลพล", "นางสาวสุดารัตน์ ศรีทุม",
    "นางสาวอลิสรา ศรีพันธ์", "นายเจษฎา สัจจะนวน", "นายนฤเบศก์ มูลพงศ์", "นายนันทพง หอมเนตร",
    "นางสาวกรพิณ ปุยติ", "นางสาววันนิสา ศรีพรมมา", "นายภูวดล ทองน้อย", "นางสาวฑิฆัมพร พรมฤทธิ์",
    "นางสาวธนพร ปัญญาสิทธิ์", "นางสาวประฎาวัน คนเล็ก", "นางสาวปริญญา เบียบสันเทียะ",
]


def main(email="demo@example.com", password="demo12345", assess=17):
    rnd = random.Random(7)
    c = TestClient(app)
    r = c.post("/api/auth/register", json={"email": email, "password": password, "full_name": "นางพรธิดา โพธิ์สิงห์",
                                          "school_name": "โรงเรียนหนองสวรรค์วิทยาคาร", "accept_terms": True})
    if r.status_code == 409:
        r = c.post("/api/auth/login", json={"email": email, "password": password})
    h = {"X-CSRF-Token": r.json()["csrf"]}
    c.put("/api/auth/profile", headers=h, json={"full_name": "นางพรธิดา โพธิ์สิงห์", "position": "ครู",
          "school_name": "โรงเรียนหนองสวรรค์วิทยาคาร", "area_office": "สำนักงานเขตพื้นที่การศึกษามัธยมศึกษาเลย หนองบัวลำภู"})
    room = c.post("/api/classrooms", headers=h, json={"subject_name": "คณิตศาสตร์พื้นฐาน", "subject_code": "ค33101",
                  "grade_label": "มัธยมศึกษาปีที่ 6/1", "academic_year": current_academic_term()[0], "semester": current_academic_term()[1]}).json()
    c.put(f"/api/classrooms/{room['id']}/roster", headers=h, json={"text": "\n".join(f"{i}\t{n}" for i, n in enumerate(NAMES, 1))})
    token = room["student_link"].rsplit("/", 1)[1]
    methods = ["lecture", "discussion", "mindmap", "questioning", "project", "roleplay", "experiment", "group"]
    for i, name in enumerate(NAMES, 1):
        c.post(f"/api/f/{token}/submissions", json={
            "student_no": i, "full_name": name, "nickname": rnd.choice(["ต้น", "ฝ้าย", "แบม", "บอส", "มิ้นท์"]),
            "personal_info": {"age": 17, "parent_status": "อยู่ด้วยกัน", "lives_with": "บิดามารดา", "weight_kg": rnd.randint(42, 70)},
            "open_answers": {"q1": rnd.choice(["ร้องเพลง", "วาดรูป", "เล่นกีฬา"]), "q2": "คณิตศาสตร์", "q10": rnd.choice(["ครู", "พยาบาล", "วิศวกร"])},
            "learning_prefs": rnd.sample(methods, 4), "consent": True})
    subs = c.get(f"/api/classrooms/{room['id']}/submissions").json()
    for k, s in enumerate(subs[:assess]):
        base = "good" if k < 4 else "fair"
        scores = {code: {"rating": base if rnd.random() > 0.25 else rnd.choice(["good", "fair"]), "note": ""} for code in ITEM_CODES}
        if k in (6, 9):
            scores["d3_3"] = scores["d3_4"] = {"rating": "improve", "note": "ส่งงานไม่ตรงเวลา"}
        c.put(f"/api/classrooms/{room['id']}/submissions/{s['id']}/evaluation", headers=h,
              json={"scores": scores, "last_grade": rnd.choice(["2.5", "3", "3.5", "4"]), "teacher_comment": "ควรส่งเสริมการทำงานกลุ่ม"})
    print(f"room {room['id']}: {email} / {password}")
    return room["id"]


if __name__ == "__main__":
    main()
