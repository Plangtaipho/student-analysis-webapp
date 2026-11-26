"""Teacher signature: upload (cleaned to a transparent PNG), owner-only read, delete, printed in PDFs."""
import io
import math

import pytest
from PIL import Image, ImageDraw, ImageFilter

from app.services.signature import SignatureError, clean_signature


def _photo(ink=(30, 45, 140), paper=(225, 220, 205), shadow=True, fmt="JPEG") -> bytes:
    """A phone-photo-like signature: off-white paper, a shadowed corner, blue pen."""
    w, h = 1600, 1000
    im = Image.new("RGB", (w, h), paper)
    d = ImageDraw.Draw(im)
    if shadow:
        d.polygon([(1100, 0), (w, 0), (w, h), (700, h)], fill=tuple(int(c * 0.6) for c in paper))
    pts = [(400 + i * 2, 500 + int(80 * math.sin(i / 20))) for i in range(300)]
    d.line(pts, fill=ink, width=7)
    im = im.filter(ImageFilter.GaussianBlur(1))
    buf = io.BytesIO()
    im.save(buf, fmt, quality=75) if fmt == "JPEG" else im.save(buf, fmt)
    return buf.getvalue()


def test_clean_signature_makes_paper_transparent_and_crops():
    png = clean_signature(_photo())
    im = Image.open(io.BytesIO(png))
    assert im.format == "PNG" and im.mode == "RGBA"
    assert im.size[0] <= 900 and im.size[1] <= 320
    # Cropped close to the stroke (wide, not tall), shadow not kept.
    assert im.size[0] > im.size[1] * 2
    alpha = im.getchannel("A")
    assert alpha.getpixel((0, 0)) == 0  # corner is clear paper
    ink = [im.getpixel((x, y)) for x in range(im.size[0]) for y in range(im.size[1]) if im.getpixel((x, y))[3] > 200]
    assert ink, "the stroke must survive"
    r, g, b, _ = ink[0]
    assert b > r and b > g  # blue pen stays blue


def test_clean_signature_rejects_blank_paper_and_non_images():
    buf = io.BytesIO()
    Image.new("RGB", (800, 400), (222, 218, 205)).save(buf, "JPEG")
    with pytest.raises(SignatureError):
        clean_signature(buf.getvalue())
    with pytest.raises(SignatureError):
        clean_signature(b"%PDF-1.4 not an image")


def _upload(client, data: bytes, name="sig.jpg"):
    return client.put("/api/auth/signature", files={"file": (name, data, "image/jpeg")})


def _put_sig(teacher, data: bytes):
    return teacher.c.put(
        "/api/auth/signature", files={"file": ("sig.jpg", data, "image/jpeg")}, headers=teacher._h()
    )


def test_upload_read_and_delete_signature(teacher):
    assert teacher.get("/api/auth/signature").status_code == 404
    r = _put_sig(teacher, _photo())
    assert r.status_code == 200, r.text
    r = teacher.get("/api/auth/signature")
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"
    assert "no-store" in r.headers["cache-control"]
    # Replacing works too.
    assert _put_sig(teacher, _photo(ink=(20, 20, 20), shadow=False)).status_code == 200
    assert teacher.delete("/api/auth/signature").status_code == 200
    assert teacher.get("/api/auth/signature").status_code == 404


def test_signature_needs_login_csrf_and_a_real_signature(teacher):
    from fastapi.testclient import TestClient

    from app.main import app

    anon = TestClient(app)
    assert anon.get("/api/auth/signature").status_code == 401
    # No CSRF header: refused.
    r = teacher.c.put("/api/auth/signature", files={"file": ("sig.jpg", _photo(), "image/jpeg")})
    assert r.status_code == 403
    buf = io.BytesIO()
    Image.new("RGB", (800, 400), (240, 240, 240)).save(buf, "PNG")
    r = _put_sig(teacher, buf.getvalue())
    assert r.status_code == 422 and "ไม่พบลายเซ็น" in r.json()["detail"]
    assert _put_sig(teacher, b"x" * (8 * 1024 * 1024 + 1)).status_code == 413


def test_signature_is_private_to_its_teacher(teacher):
    from tests.conftest import Teacher

    _put_sig(teacher, _photo())
    other = Teacher(email="other@example.com", name="ครูอื่น")
    assert other.get("/api/auth/signature").status_code == 404


def test_signature_printed_in_pdfs_unless_turned_off(teacher, student):
    from tests.conftest import student_payload, token_of

    room = teacher.make_room()
    student.post(f"/api/f/{token_of(room)}/submissions", json=student_payload())
    base = f"/api/classrooms/{room['id']}/pdf/individual"
    plain = teacher.get(base)
    assert plain.status_code == 200
    _put_sig(teacher, _photo())
    signed = teacher.get(base)
    unsigned = teacher.get(base + "?sign=false")
    assert signed.status_code == unsigned.status_code == 200
    # The embedded picture makes the signed file clearly larger; turned off it matches no signature.
    assert len(signed.content) > len(unsigned.content) + 2000
    assert abs(len(unsigned.content) - len(plain.content)) < 200


def test_signature_in_full_report(teacher, student):
    from tests.test_evaluations import all_scores, ev_url, setup_room

    room, ids = setup_room(teacher, student, 1)
    teacher.put(ev_url(room, ids[0]), {"scores": all_scores("good")})
    url = f"/api/classrooms/{room['id']}/pdf/full"
    params = {"doc_no": "417/2569", "date": "26 พฤศจิกายน 2569"}
    _put_sig(teacher, _photo())
    signed = teacher.get(url, params=params)
    unsigned = teacher.get(url, params={**params, "sign": "false"})
    assert signed.status_code == unsigned.status_code == 200
    assert len(signed.content) > len(unsigned.content) + 2000
