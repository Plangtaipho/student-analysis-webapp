"""Lists of education service areas (สพป./สพม.) and their schools, used as suggestions at sign-up.

Data: app/data/edu_areas.json, built by scripts/build_edu_areas.py from Thai Wikipedia.
It may miss a school, so teachers can still type any school name.
"""
import json
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Response, status

router = APIRouter(prefix="/api/edu", tags=["edu"])
DATA = Path(__file__).resolve().parent.parent / "data" / "edu_areas.json"
CACHE = {"Cache-Control": "public, max-age=86400"}


@lru_cache(maxsize=1)
def _areas() -> dict[str, dict]:
    return {a["name"]: a for a in json.loads(DATA.read_text(encoding="utf-8"))["areas"]}


@router.get("/areas")
def areas(response: Response):
    response.headers.update(CACHE)
    return [{"name": a["name"], "short": a["short"], "kind": a["kind"]} for a in _areas().values()]


@router.get("/schools")
def schools(response: Response, area: str = Query(max_length=200)):
    a = _areas().get(area.strip())
    if a is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "ไม่พบเขตพื้นที่การศึกษานี้")
    response.headers.update(CACHE)
    return a["schools"]
