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


_MIXED_LINE = re.compile(
    r"^(?P<hc>(?:[ปมอ]\S*?\s*)?[0-9๐-๙]{1,2}\s*/\s*[0-9๐-๙]{1,2})[\s,]+(?:เลขที่\s*)?(?P<no>[0-9๐-๙]{1,3})[.)]?[\s,]+(?P<name>\S.*)$"
)


def parse_mixed_roster(text: str, grade_label: str = "") -> list[tuple[str, int, str]]:
    """Class list of a ห้องคละ: each line is "ห้อง  เลขที่  ชื่อ", e.g. "ม.3/2<TAB>5<TAB>ด.ช. ก้อง ใจดี".

    Returns (home_class, number, name) sorted by home class then number. Raises ValueError (Thai)."""
    from app.services.home_class import label, normalize_home_class, sort_key

    rows: list[tuple[str, int, str]] = []
    seen: set[tuple[str, int]] = set()
    for raw in text.splitlines():
        line = re.sub(r"\s+", " ", raw.replace("\t", " ").replace(" ", " ")).strip()
        if not line:
            continue
        m = _MIXED_LINE.match(line)
        if m is None:
            if not rows and re.search(r"ห้อง|เลขที่|ชื่อ", line) and len(line) < 40:
                continue  # header row
            raise ValueError(f"บรรทัด \"{line[:40]}\" ไม่ครบ ต้องเป็น ห้อง เลขที่ ชื่อ เช่น ม.3/2  5  ด.ช.ก้อง ใจดี")
        try:
            hc = normalize_home_class(m.group("hc"), grade_label)
        except ValueError:
            raise ValueError(f"ห้อง \"{m.group('hc')}\" ไม่ถูกต้อง ต้องเป็นแบบ ม.3/2") from None
        no = int(m.group("no").translate(str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")))
        name = m.group("name").strip()
        if not 1 <= no <= MAX_STUDENTS:
            raise ValueError(f"เลขที่ {no} ไม่อยู่ในช่วง 1-{MAX_STUDENTS}")
        if (hc, no) in seen:
            raise ValueError(f"{label(hc, no)} ซ้ำกัน")
        if len(name) > 120:
            raise ValueError(f"ชื่อของ {label(hc, no)} ยาวเกินไป")
        seen.add((hc, no))
        rows.append((hc, no, name))
    if len(rows) > MAX_STUDENTS:
        raise ValueError(f"ใส่รายชื่อได้ไม่เกิน {MAX_STUDENTS} คน")
    return sorted(rows, key=lambda r: sort_key(r[0], r[1]))
