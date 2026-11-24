"""Build app/data/edu_areas.json: the 245 education service areas and the OBEC schools of each.

Source: Thai Wikipedia (CC BY-SA 4.0), pages "เขตพื้นที่การศึกษา" and "รายชื่อโรงเรียนในจังหวัด...".
data.go.th refuses requests from outside Thailand, so Wikipedia is used. The lists are suggestions only.
Usage:  python scripts/build_edu_areas.py            (downloads into a temp folder, about 2 minutes)
"""
import json, os, re, sys, collections, tempfile, time, urllib.parse, urllib.request
from pathlib import Path

W = tempfile.mkdtemp()
UA = "KruFlowDataImport/1.0 (educational data import)"
OUT = Path(__file__).resolve().parent.parent / "app" / "data" / "edu_areas.json"


def fetch(title, dest):
    url = "https://th.wikipedia.org/w/index.php?title=" + urllib.parse.quote(title) + "&action=raw"
    for attempt in range(4):
        try:
            Path(dest).write_bytes(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60).read())
            return
        except Exception as e:  # noqa: BLE001
            print(title, "retry", e, file=sys.stderr)
            time.sleep(20 * (attempt + 1))


fetch("เขตพื้นที่การศึกษา", f"{W}/area.txt")
os.makedirs(f"{W}/prov", exist_ok=True)
for _p in sorted(set(re.findall(r"^;\[\[จังหวัด([^\]|]+)", open(f"{W}/area.txt").read(), re.M))) + ["กรุงเทพมหานคร"]:
    fetch("รายชื่อโรงเรียนในกรุงเทพมหานคร" if _p == "กรุงเทพมหานคร" else f"รายชื่อโรงเรียนในจังหวัด{_p}", f"{W}/prov/{_p}.txt")
    time.sleep(1.5)
P, M = 'สำนักงานเขตพื้นที่การศึกษาประถมศึกษา', 'สำนักงานเขตพื้นที่การศึกษามัธยมศึกษา'

def clean(s):
    s = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", s)
    s = re.sub(r"\{\{(?:อำ|ข|รร)\|([^}|]*)[^}]*\}\}", r"\1", s)
    s = re.sub(r"\{\{[^}]*\}\}", "", s)
    s = re.sub(r"<[^>]+>", "", s).replace("'''", "").replace("''", "")
    return re.sub(r"\s+", " ", s).strip()

def full(short):
    short = short.strip().replace("สพม. ", "สพม.").replace("สพป. ", "สพป.")
    if short.startswith("สพป."): return P + short[4:]
    if short.startswith("สพม."): return M + short[4:]
    return short

# ---- areas
t = open(f'{W}/area.txt').read()
pri = t[t.index('== เขตพื้นที่การศึกษาประถมศึกษา =='):t.index('== เขตพื้นที่การศึกษามัธยมศึกษา ==')]
sec = t[t.index('=== 62 เขต'):t.index('== อ้างอิง ==')]
areas = []
prov = None
for line in pri.splitlines():
    m = re.match(r'^;\[\[จังหวัด([^\]|]+)', line) or re.match(r'^;\[\[(กรุงเทพมหานคร)', line)
    if m: prov = m.group(1); continue
    m = re.match(r'^\* (สพป\.[^-–]+?)\s*[-–]\s*(.*)$', line)
    if m:
        name, rest = full(clean(m.group(1))), clean(m.group(2))
        if 'ทุกอำเภอ' in rest or 'ทุกเขต' in rest or 'ทั้ง' in rest: dists = ['*']
        else:
            rest = re.sub(r'^(อำเภอ|เขต)', '', rest)
            dists = [d.replace('อำเภอ', '').strip() for d in re.split(r'\s+|และ', rest.replace('และ', ' ')) if d.strip()]
        areas.append({'name': name, 'kind': 'p', 'provinces': [prov], 'districts': dists})
PROVS = sorted({a['provinces'][0] for a in areas} | {'กรุงเทพมหานคร'}, key=len, reverse=True)
for line in sec.splitlines():
    m = re.match(r"^\* '''(.+?)'''", line)
    if not m: continue
    name = full(clean(m.group(1)))
    tail = name[len(M):]
    provs = []
    rest = re.sub(r'เขต \d+$', '', tail).strip()
    for part in rest.split():
        provs.append(part)
    areas.append({'name': name, 'kind': 's', 'provinces': provs, 'districts': ['*']})
print('areas', len(areas), collections.Counter(a['kind'] for a in areas), file=sys.stderr)
bad = [a for a in areas if not a['provinces'][0] or any(p not in PROVS for p in a['provinces'])]
print('bad provinces', [(a['name'], a['provinces']) for a in bad], file=sys.stderr)
names = {a['name'] for a in areas}
KEY = lambda n: re.sub(r'\s+', '', n.replace('เขด', 'เขต').replace('\u200b', ''))
BYKEY = {KEY(n): n for n in names}

# ---- schools
def area_of_heading(h, province):
    h = clean(h)
    if 'มัธยมศึกษา' in h and 'เขตพื้นที่' in h:
        m = re.search(r'(สำนักงานเขตพื้นที่การศึกษามัธยมศึกษา\S.*)$', h) or re.search(r'(สพม\.\s?.+)$', h)
        if m:
            n = full(m.group(1)) if m.group(1).startswith('สพม') else m.group(1)
            if KEY(n) in BYKEY: return BYKEY[KEY(n)]
        cands = [a['name'] for a in areas if a['kind'] == 's' and province in a['provinces']]
        return cands[0] if len(cands) == 1 else ('?s', h)
    if 'ประถมศึกษา' in h and 'เขตพื้นที่' in h:
        m = re.search(r'(สำนักงานเขตพื้นที่การศึกษาประถมศึกษา\S.*)$', h) or re.search(r'(สพป\.\s?.+)$', h)
        if m:
            n = full(m.group(1)) if m.group(1).startswith('สพป') else m.group(1)
            if KEY(n) in BYKEY: return BYKEY[KEY(n)]
        return ('?p', h)
    return None

schools = collections.defaultdict(list)
unknown = collections.Counter()
for p in PROVS:
    try: txt = open(f'{W}/prov/{p}.txt').read()
    except FileNotFoundError: print('missing page', p, file=sys.stderr); continue
    cur = None
    for line in txt.splitlines():
        hm = re.match(r'^(={2,5})\s*(.*?)\s*\1\s*$', line)
        if hm:
            h = hm.group(2)
            if any(k in h for k in ('ท้องถิ่น', 'เอกชน', 'อ้างอิง', 'อาชีวศึกษา', 'อุดมศึกษา', 'ตชด', 'ตำรวจ', 'กรุงเทพมหานคร (สำนัก', 'สำนักการศึกษา', 'พระพุทธศาสนา', 'สาธิต')):
                cur = None; continue
            a = area_of_heading(h, p)
            if a is not None: cur = a
            if isinstance(cur, tuple): unknown[(p,) + cur] += 1; cur = None
            continue
        if cur and line.startswith('|') and not line.startswith(('|-', '|}', '|+')):
            cell = line[1:].split('||')[0]
            cell = cell.split('|', 1)[-1] if re.match(r'^\s*(style|align|rowspan|colspan)=', cell) else cell
            rr = re.search(r"\{\{รร\|([^}|]+)", cell)
            name = ('โรงเรียน' + rr.group(1).strip()) if rr else clean(cell)
            name = re.sub(r'\s*\[\d+\]$', '', name).strip()
            if name.startswith('โรงเรียน') and 8 < len(name) < 90:
                schools[cur].append(name)
print('unknown headings', list(unknown)[:30], file=sys.stderr)
out = []
for a in areas:
    lst = sorted(set(schools.get(a['name'], [])))
    out.append({**a, 'schools': lst})
total = sum(len(a['schools']) for a in out)
print('schools', total, 'areas with 0:', [a['name'] for a in out if not a['schools']][:40], len([a for a in out if not a['schools']]), file=sys.stderr)
P_, M_ = P, M
rows = []
for x in out:
    short = ("สพป." + x["name"][len(P_):]) if x["kind"] == "p" else ("สพม." + x["name"][len(M_):])
    rows.append({"name": x["name"], "short": short, "kind": x["kind"], "provinces": x["provinces"], "schools": x["schools"]})
rows.sort(key=lambda r: (r["kind"] != "p", r["short"]))
doc = {"source": "Thai Wikipedia: เขตพื้นที่การศึกษา and รายชื่อโรงเรียนในจังหวัด... pages (CC BY-SA 4.0), fetched " + time.strftime("%Y-%m-%d"),
       "note": "Suggestions only. Teachers may type a school that is not listed.", "areas": rows}
OUT.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
print(OUT, file=sys.stderr)
