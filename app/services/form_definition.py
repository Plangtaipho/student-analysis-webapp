"""The fixed analysis form, taken from the school's paper form
"แบบบันทึกการวิเคราะห์ผู้เรียนเป็นรายบุคคล".

Everything the form asks lives here, so a later change of wording or a new
question is made in one place. Student answers are stored as JSON keyed by
the `key` values below, so changing a label never breaks old answers.
"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Field:
    key: str
    label: str
    kind: str = "text"  # text | number | date | select | textarea
    max_len: int = 120
    required: bool = False
    options: tuple[str, ...] = ()
    sensitive: bool = False  # health / contact data: optional, marked in the UI
    width: str = "half"  # half | full | third (layout hint for the form)
    min_value: float | None = None
    max_value: float | None = None


@dataclass(frozen=True)
class Section:
    key: str
    title: str
    fields: tuple[Field, ...] = field(default_factory=tuple)
    note: str = ""


# --- Part 0: personal information -------------------------------------------------

PARENT_STATUS = ("สมรส", "อยู่ด้วยกัน", "แยกกันอยู่", "หย่า", "อื่นๆ")
BLOOD_TYPES = ("A", "B", "AB", "O", "ไม่ทราบ")

PERSONAL_SECTIONS: tuple[Section, ...] = (
    Section(
        "self",
        "ข้อมูลส่วนตัว",
        (
            Field("birth_date", "วันเกิด", "date", width="half"),
            Field("age", "อายุ (ปี)", "number", width="half", min_value=5, max_value=30),
            Field("blood_type", "หมู่โลหิต", "select", options=BLOOD_TYPES, sensitive=True, width="half"),
            Field("prev_grade_level", "ผลการเรียนปีที่ผ่านมา ระดับชั้น", width="half", max_len=30),
            Field("prev_gpa", "ผลการเรียนเฉลี่ย (GPA)", "number", width="half", min_value=0, max_value=4),
        ),
    ),
    Section(
        "family",
        "ข้อมูลครอบครัว",
        (
            Field("father_name", "ชื่อบิดา", width="half"),
            Field("father_job", "อาชีพบิดา", width="half", max_len=80),
            Field("mother_name", "ชื่อมารดา", width="half"),
            Field("mother_job", "อาชีพมารดา", width="half", max_len=80),
            Field("parent_status", "สถานภาพของบิดา-มารดา", "select", options=PARENT_STATUS, width="half"),
            Field("parent_status_other", "ถ้าเลือก อื่นๆ โปรดระบุ", width="half", max_len=80),
            Field("lives_with", "ปัจจุบันพักอาศัยอยู่กับ", width="half", max_len=80),
            Field("lives_with_relation", "เกี่ยวข้องเป็น", width="half", max_len=40),
        ),
    ),
    Section(
        "address",
        "ที่อยู่ปัจจุบัน",
        (
            Field("house_no", "บ้านเลขที่", width="third", max_len=20, sensitive=True),
            Field("moo", "หมู่ที่", width="third", max_len=10, sensitive=True),
            Field("village", "บ้าน", width="third", max_len=80, sensitive=True),
            Field("subdistrict", "ตำบล", width="third", max_len=80, sensitive=True),
            Field("district", "อำเภอ", width="third", max_len=80, sensitive=True),
            Field("province", "จังหวัด", width="third", max_len=80, sensitive=True),
            Field("postcode", "รหัสไปรษณีย์", width="half", max_len=5, sensitive=True),
            Field("phone", "โทรศัพท์", width="half", max_len=20, sensitive=True),
        ),
        note="ไม่บังคับกรอก",
    ),
    Section(
        "health",
        "ข้อมูลด้านสุขภาพ",
        (
            Field("weight_kg", "น้ำหนัก (กิโลกรัม)", "number", width="third", min_value=10, max_value=250, sensitive=True),
            Field("height_cm", "ส่วนสูง (เซนติเมตร)", "number", width="third", min_value=50, max_value=250, sensitive=True),
            Field("chronic_disease", "โรคประจำตัว", width="third", max_len=120, sensitive=True),
        ),
        note="ไม่บังคับกรอก",
    ),
)

PERSONAL_FIELDS: dict[str, Field] = {f.key: f for s in PERSONAL_SECTIONS for f in s.fields}

# --- Part 1: open questions ------------------------------------------------------------

OPEN_QUESTIONS: tuple[Field, ...] = (
    Field("q1", "1.1 ความสามารถพิเศษของนักเรียนคือ", "textarea", max_len=300, width="full"),
    Field("q2", "1.2 วิชาที่นักเรียนชอบมากที่สุดคือ", "textarea", max_len=300, width="full"),
    Field("q3", "1.3 กีฬาที่ชอบมากที่สุดคือ", "textarea", max_len=300, width="full"),
    Field("q4", "1.4 ประเภทของหนังสือที่นักเรียนชอบอ่านมากที่สุด", "textarea", max_len=300, width="full"),
    Field("q5", "1.5 สิ่งที่ประทับใจมากที่สุดในชีวิตคือ", "textarea", max_len=300, width="full"),
    Field("q6", "1.6 ลักษณะเพื่อนที่นักเรียนชอบมากที่สุดได้แก่", "textarea", max_len=300, width="full"),
    Field("q7", "1.7 นักเรียนชอบครูที่มีลักษณะอย่างไร", "textarea", max_len=300, width="full"),
    Field("q8", "1.8 สิ่งที่นักเรียนคิดว่าตนเองควรปรับปรุงมากที่สุดได้แก่", "textarea", max_len=300, width="full"),
    Field("q9", "1.9 นักเรียนอยากให้โรงเรียนมีลักษณะอย่างไร", "textarea", max_len=300, width="full"),
    Field("q10", "1.10 อนาคตนักเรียนอยากประกอบอาชีพอะไร", "textarea", max_len=300, width="full"),
)
OPEN_QUESTION_KEYS = tuple(q.key for q in OPEN_QUESTIONS)

# --- Part 2: preferred learning methods (ranked) ----------------------------------

LEARNING_METHODS: tuple[tuple[str, str], ...] = (
    ("lecture", "แบบบรรยาย"),
    ("discussion", "แบบอภิปราย"),
    ("mindmap", "แบบสร้างแผนผังความคิด"),
    ("questioning", "แบบใช้คำถาม"),
    ("project", "แบบโครงงาน"),
    ("roleplay", "แบบแสดงบทบาทสมมุติ"),
    ("experiment", "แบบทดลอง"),
    ("group", "กระบวนการกลุ่ม"),
    ("integrated", "แบบบูรณาการ"),
    ("brainstorm", "แบบระดมสมอง"),
    ("fieldtrip", "ไปทัศนศึกษา"),
    ("cooperative", "แบบร่วมมือร่วมใจ"),
    ("demonstration", "แบบสาธิต"),
    ("problem_solving", "กระบวนการแก้ปัญหา"),
    ("community", "ไปเรียนในแหล่งเรียนรู้ในชุมชน"),
    ("inquiry", "กระบวนการสืบเสาะหาความรู้"),
)
LEARNING_METHOD_LABELS = dict(LEARNING_METHODS)
MIN_RANKED_METHODS = 3

# --- Part 3: teacher assessment (5 domains x 3 items) ----------------------------

ASSESSMENT_DOMAINS: tuple[tuple[int, str, tuple[tuple[str, str], ...]], ...] = (
    (1, "ด้านความรู้ความสามารถและประสบการณ์", (
        ("d1_1", "ความรู้พื้นฐาน"),
        ("d1_2", "ความสามารถในการแก้ปัญหา"),
        ("d1_3", "ความสนใจ และการมีสมาธิในการเรียนรู้"),
    )),
    (2, "ความพร้อมด้านสติปัญญา", (
        ("d2_1", "ความคิดริเริ่มสร้างสรรค์"),
        ("d2_2", "ความมีเหตุมีผล"),
        ("d2_3", "ความสามารถในการเรียนรู้"),
    )),
    (3, "ความพร้อมด้านพฤติกรรม", (
        ("d3_1", "การแสดงออก"),
        ("d3_2", "การควบคุมอารมณ์"),
        ("d3_3", "ความมุ่งมั่นขยันหมั่นเพียร"),
        ("d3_4", "ความรับผิดชอบ"),
    )),
    (4, "ความพร้อมด้านร่างกายและจิตใจ", (
        ("d4_1", "สุขภาพร่างกายแข็งแรง"),
        ("d4_2", "การเจริญเติบโตสมวัย"),
        ("d4_3", "ความสมบูรณ์ทางด้านสุขภาพจิต"),
    )),
    (5, "ความพร้อมด้านสังคม", (
        ("d5_1", "การปรับตัวเข้ากับผู้อื่น"),
        ("d5_2", "การเสียสละไม่เห็นแก่ตัว"),
        ("d5_3", "มีระเบียบวินัยเคารพกฎกติกา"),
    )),
)


def assessment_item_rows() -> list[dict]:
    """Rows for the assessment_items table, in report order."""
    rows, order = [], 0
    for domain_no, domain_name, items in ASSESSMENT_DOMAINS:
        for item_no, (code, label) in enumerate(items, start=1):
            order += 1
            rows.append(
                {
                    "code": code,
                    "domain_no": domain_no,
                    "domain_name": domain_name,
                    "item_no": item_no,
                    "label": label,
                    "sort_order": order,
                }
            )
    return rows
