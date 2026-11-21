# ขึ้นเว็บจริงบน Railway

ใช้เวลาประมาณ 20 นาที ทำผ่านหน้าเว็บ railway.com ทั้งหมด ไม่ต้องใช้คำสั่งในเครื่อง

## 1. สร้างโปรเจกต์จาก GitHub

1. เข้า railway.com แล้วกด **New Project** → **Deploy from GitHub repo**
2. ถ้าเป็นครั้งแรก ให้กดอนุญาตให้ Railway เข้าถึง repo `student-analysis-webapp`
3. เลือก repo นี้ Railway จะเจอ `Dockerfile` และ `railway.json` แล้วเริ่ม build เอง
4. ที่ service ที่ได้ ไปที่ **Settings → Source → Branch** แล้วเลือก branch ที่จะใช้
   (ตอนนี้งานทั้งหมดอยู่ที่ `claude/project-thread-92ceqh` ถ้า merge เข้า `main` แล้วให้เลือก `main`)

ครั้งแรกจะยัง deploy ไม่ผ่าน เพราะยังไม่มีฐานข้อมูล ทำข้อ 2 ต่อได้เลย

## 2. เพิ่มฐานข้อมูล MySQL

1. ในโปรเจกต์ กด **+ Create** → **Database** → **MySQL**
2. รอจนขึ้นสถานะ Active

## 3. ตั้งค่า Variables ของเว็บ

ไปที่ service ของเว็บ (ไม่ใช่ MySQL) → **Variables** → **Raw Editor** แล้ววางข้อความนี้ แก้ค่าในวงเล็บให้เป็นของจริง

```
DATABASE_URL=${{MySQL.MYSQL_URL}}
SECRET_KEY=${{secret(48)}}
INITIAL_ADMIN_EMAIL=(อีเมลแอดมิน)
INITIAL_ADMIN_PASSWORD=(รหัสผ่านแอดมิน อย่างน้อย 12 ตัว)
PROMPTPAY_ID=(เบอร์มือถือหรือเลขบัตรประชาชนที่ผูก PromptPay)
PROMPTPAY_NAME=(ชื่อบัญชีที่ให้ครูเห็นก่อนโอน)
PRICE_PER_TERM=129
```

- `${{MySQL.MYSQL_URL}}` และ `${{secret(48)}}` ให้พิมพ์ตามนี้เลย Railway จะแทนค่าให้เอง
  (`secret(48)` คือสุ่มรหัสลับยาว 48 ตัวให้)
- ค่าพวกนี้อยู่ใน Railway เท่านั้น ไม่ได้อยู่ในโค้ดบน GitHub
- บัญชีแอดมินจะถูกสร้างตอนเว็บเปิดครั้งแรก หลังเข้าได้แล้ว ลบ `INITIAL_ADMIN_PASSWORD` ออกได้

กด **Deploy** (หรือรอให้ Railway deploy ใหม่เอง) ระบบจะสร้างตารางในฐานข้อมูลให้อัตโนมัติก่อนเปิดเว็บ

## 4. เปิดโดเมน

1. service ของเว็บ → **Settings → Networking → Generate Domain** จะได้ที่อยู่แบบ `xxxx.up.railway.app`
2. กลับไปที่ **Variables** เพิ่ม `PUBLIC_BASE_URL=https://xxxx.up.railway.app` (ใส่ที่อยู่ที่ได้)
   ค่านี้ใช้ทำลิงก์และ QR ให้นักเรียน
3. ถ้ามีโดเมนของตัวเอง เพิ่มได้ที่ **Custom Domain** แล้วเปลี่ยน `PUBLIC_BASE_URL` ตาม

## 5. ตรวจว่าใช้ได้

1. เปิด `https://xxxx.up.railway.app/healthz` ต้องขึ้น `{"status":"ok"}`
2. เข้าสู่ระบบด้วยอีเมลแอดมิน จะเห็นเมนู **แอดมิน**
3. สมัครบัญชีครูอีกบัญชี สร้าง 2 ห้อง ห้องที่ 2 จะขึ้นว่ารอชำระเงิน
4. เข้าเมนู **ชำระเงิน** สแกน QR ด้วยแอปธนาคาร ตรวจว่าชื่อบัญชีและยอด 129 บาทถูกต้อง (ยังไม่ต้องโอนจริง)
5. เปิดลิงก์นักเรียนด้วยมือถือ กรอกฟอร์ม ประเมิน แล้วดาวน์โหลด PDF

## ค่าใช้จ่าย

Railway คิดตามการใช้งานจริง แผน Hobby เริ่มที่ 5 ดอลลาร์ต่อเดือน (รวมเว็บและ MySQL)
ดูยอดได้ที่ **Usage** ของบัญชี

## การสำรองข้อมูล

ฐานข้อมูล MySQL ของ Railway มีเมนู **Backups** ให้เปิดสำรองอัตโนมัติ แนะนำให้เปิดไว้
