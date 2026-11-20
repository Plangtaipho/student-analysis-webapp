# วิเคราะห์ผู้เรียนรายบุคคล (Student Analysis Web App)

เว็บกลาง (SaaS) ให้ครูสร้างห้องรายวิชา ส่งลิงก์ให้นักเรียนกรอก "แบบบันทึกการวิเคราะห์ผู้เรียนเป็นรายบุคคล" บนมือถือ
ครูประเมินรายคน แล้วระบบสรุปเป็นจำนวน/ร้อยละ และส่งออก PDF

สเปกโปรเจกต์ฉบับเต็มอยู่ใน Claude Doc ของโปรเจกต์ ความคืบหน้าดู [PROJECT_STATUS.md](PROJECT_STATUS.md)

## Tech stack

| ส่วน | ใช้ |
| --- | --- |
| Backend | Python 3.13, FastAPI, Pydantic, SQLAlchemy 2, Alembic |
| Frontend | HTML + CSS + JavaScript (ไม่มี build step) ผ่าน Jinja2 templates |
| Database | MySQL 8 (production บน Railway), SQLite (เครื่อง dev / เทสต์) |
| PDF | WeasyPrint + ฟอนต์ Sarabun (OFL, อยู่ใน `app/static/fonts`) |
| ฟอนต์หน้าเว็บ | IBM Plex Sans Thai Looped (OFL, เก็บในเครื่อง ไม่โหลดจากภายนอก) |
| QR Code | segno |
| Hosting | Railway (Dockerfile) |

## โครงสร้างโฟลเดอร์

```
app/
  main.py              # FastAPI app, middleware (session, security headers), error handlers
  config.py            # ค่าตั้งค่าจาก environment variables
  database.py          # engine + session
  models.py            # ตาราง 8 ตาราง
  schemas.py           # Pydantic: ตรวจข้อมูลขาเข้า
  security.py          # hash รหัสผ่าน, token, rate limiter
  deps.py              # dependency: ผู้ใช้ปัจจุบัน, ตรวจเจ้าของห้อง, CSRF
  routers/
    auth.py            # /api/auth/*        สมัคร ล็อกอิน โปรไฟล์ครู
    classrooms.py      # /api/classrooms/*  ห้อง รายชื่อ QR คำตอบ
    student.py         # /api/f/{token}/*   ฟอร์มนักเรียน (ไม่ต้องล็อกอิน)
    evaluations.py     # ครูประเมินรายคน, สรุปห้อง
    reports.py         # PDF รายบุคคล / ฉบับเต็ม
    pages.py           # หน้า HTML
  services/
    form_definition.py # หัวข้อแบบฟอร์มทั้งหมด (แก้ที่นี่ที่เดียว)
    roster.py          # อ่านรายชื่อที่วางจาก Excel
    summary.py         # นับจำนวน/ร้อยละ + เกณฑ์แบ่งกลุ่ม (auto_group)
    records.py, pdf.py # ข้อมูลและการสร้าง PDF
  templates/, static/
alembic/               # migration ฐานข้อมูล
tests/                 # pytest
e2e/                   # Playwright (เปิดเบราว์เซอร์จริง)
```

## รันบนเครื่อง

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env            # แก้ SECRET_KEY
alembic upgrade head            # สร้างตาราง + ใส่หัวข้อประเมิน 16 ข้อ
uvicorn app.main:app --reload   # เปิด http://localhost:8000
```

WeasyPrint ต้องมีไลบรารี Pango ในเครื่อง (macOS: `brew install pango`, Ubuntu: `apt install libpango-1.0-0 libpangoft2-1.0-0`)

API docs (Swagger): http://localhost:8000/docs (ปิดใน production)

## ทดสอบ

```bash
python -m pytest -q                                   # unit + API tests
BASE_URL=http://localhost:8000 node e2e/week1_flow.cjs # เบราว์เซอร์จริง (ต้องติดตั้ง playwright)
python -m scripts.seed_demo                           # ข้อมูลตัวอย่าง: demo@example.com / demo12345
BASE_URL=http://localhost:8000 node e2e/week2_flow.cjs # ประเมิน → สรุป → PDF ฉบับเต็ม
BASE_URL=http://localhost:8000 node e2e/screens.cjs     # ถ่ายภาพทุกหน้า (จอคอม + มือถือ) ไว้ตรวจหน้าตา
```

## Environment variables

| ชื่อ | ความหมาย |
| --- | --- |
| `ENV` | `production` เปิด secure cookie, HSTS, ปิด /docs |
| `DATABASE_URL` | เช่น `mysql://user:pass@host:3306/db` (Railway ใช้ค่า `MYSQL_URL`) |
| `SECRET_KEY` | สตริงสุ่มยาว ใช้เซ็น session cookie (ต้องตั้งใน production) |
| `PUBLIC_BASE_URL` | โดเมนจริง ใช้ในลิงก์และ QR ของนักเรียน |
| `INITIAL_ADMIN_EMAIL`, `INITIAL_ADMIN_PASSWORD` | สร้างแอดมินคนแรกตอนเริ่มระบบ |

## ความปลอดภัยที่ทำแล้ว

- รหัสผ่านและรหัสแก้ไขของนักเรียนเก็บแบบ bcrypt hash
- Session cookie: HttpOnly, SameSite=Lax, Secure (production) + CSRF token ทุกคำขอที่แก้ข้อมูลของครู
- ครูเห็นเฉพาะห้องของตัวเอง (ห้องของคนอื่นตอบ 404 เหมือนไม่มีอยู่)
- ลิงก์นักเรียนเป็น token สุ่ม ~128 bit, จำกัดการเดารหัสแก้ไข 5 ครั้ง/ชั่วโมง
- Content-Security-Policy ไม่อนุญาต inline script/style, ข้อความจากนักเรียน escape ทุกจุด
- ข้อมูลที่อยู่/สุขภาพไม่บังคับกรอก, นักเรียนต้องกดยินยอมก่อนส่ง, ครูลบห้องและข้อมูลได้

ยังไม่ได้ทำ: ระบบลบข้อมูลอัตโนมัติตามระยะเวลา, rate limit แบบใช้ร่วมหลาย instance, การตรวจทานนโยบายความเป็นส่วนตัวโดยนักกฎหมาย
