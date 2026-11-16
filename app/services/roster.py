"""Parse a class list pasted from Excel or typed by hand."""
import re

MAX_STUDENTS = 200


def parse_roster(text: str) -> list[tuple[int, str]]:
    """Each non-empty line is one student: "12<TAB>ด.ช. ก้อง ใจดี", "12 ก้อง ใจดี" or just "ก้อง ใจดี".

    Lines without a number are numbered after the previous line. Raises ValueError (Thai)
    for duplicate numbers or too many students.
    """
    rows: list[tuple[int, str]] = []
    seen: set[int] = set()
    last_no = 0
    for raw in text.splitlines():
        line = raw.replace(" ", " ").strip()
        if not line:
            continue
        cells = [c.strip() for c in re.split(r"\t|,|\s{2,}", line) if c.strip()]
        no: int | None = None
        if cells and cells[0].isdigit():
            no = int(cells.pop(0))
        elif re.match(r"^\d+[.)]?\s", line):
            m = re.match(r"^(\d+)[.)]?\s+(.*)$", line)
            no, cells = int(m.group(1)), [m.group(2)]
        # Skip a header row such as "เลขที่ ชื่อ-สกุล".
        if no is None and not rows and re.search(r"เลขที่|ชื่อ", line) and len(line) < 40:
            continue
        name = re.sub(r"\s+", " ", " ".join(cells)).strip()
        if not name:
            continue
        if no is None:
            no = last_no + 1
        if not 1 <= no <= MAX_STUDENTS:
            raise ValueError(f"เลขที่ {no} ไม่อยู่ในช่วง 1-{MAX_STUDENTS}")
        if no in seen:
            raise ValueError(f"เลขที่ {no} ซ้ำกัน")
        if len(name) > 120:
            raise ValueError(f"ชื่อของเลขที่ {no} ยาวเกินไป")
        seen.add(no)
        rows.append((no, name))
        last_no = no
    if len(rows) > MAX_STUDENTS:
        raise ValueError(f"ใส่รายชื่อได้ไม่เกิน {MAX_STUDENTS} คน")
    return sorted(rows)
