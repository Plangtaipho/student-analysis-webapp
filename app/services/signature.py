"""Turn a photo or scan of a signature on paper into a clean, transparent PNG.

Teachers sign on paper, then scan it or take a phone photo. The photo has a
grey or uneven paper background, so we:

1. fix the phone's rotation (EXIF) and work on a grey copy,
2. estimate the paper brightness around every point (a heavily blurred copy
   with the ink strokes removed), so shadows and uneven light do not count as ink,
3. treat "darker than the paper nearby" as ink and turn that into transparency,
4. paint all ink one even pen colour (taken from the photo, so blue pen stays blue),
5. crop to the signature with a small margin and shrink it.

The result is printed over the dotted "ลงชื่อ......" line in the PDF reports.
"""
import base64
import io

from PIL import Image, ImageChops, ImageFilter, ImageOps, UnidentifiedImageError

Image.MAX_IMAGE_PIXELS = 40_000_000  # refuse decompression bombs

MAX_UPLOAD_BYTES = 8 * 1024 * 1024
WORK_SIDE = 1600  # longest side used while cleaning
OUT_MAX = (900, 320)  # stored PNG fits in this box


class SignatureError(ValueError):
    """The upload is not a usable signature picture. The message is shown to the teacher."""


def _ink_colour(rgb: Image.Image, alpha: Image.Image) -> tuple[int, int, int]:
    """Average colour of the strongest ink pixels, darkened to look like fresh pen ink."""
    mask = alpha.point(lambda a: 255 if a >= 200 else 0)
    if not mask.getbbox():
        mask = alpha.point(lambda a: 255 if a >= 100 else 0)
    stat = [0, 0, 0]
    hist = rgb.histogram(mask=mask)
    count = sum(hist[0:256]) or 1
    for ch in range(3):
        stat[ch] = sum(i * n for i, n in enumerate(hist[ch * 256 : ch * 256 + 256])) / count
    r, g, b = stat
    # Darken so the brightest channel is at most 110: grey pencil-looking photos
    # become black, a washed-out blue becomes a clear pen blue.
    top = max(r, g, b, 1)
    k = min(1.0, 110 / top)
    r, g, b = r * k, g * k, b * k
    # Nearly grey ink: print plain near-black.
    if max(r, g, b) - min(r, g, b) < 18:
        return (20, 20, 25)
    return (int(r), int(g), int(b))


def clean_signature(raw: bytes) -> bytes:
    """Return a transparent PNG of the signature found in the uploaded image."""
    try:
        with Image.open(io.BytesIO(raw)) as im:
            if im.format not in ("JPEG", "PNG", "WEBP"):
                raise SignatureError("ไฟล์ลายเซ็นต้องเป็นรูปภาพ JPG, PNG หรือ WEBP")
            im.load()
            im = ImageOps.exif_transpose(im)
            if im.mode in ("RGBA", "LA", "P"):
                im = im.convert("RGBA")
                white = Image.new("RGBA", im.size, (255, 255, 255, 255))
                im = Image.alpha_composite(white, im)
            rgb = im.convert("RGB")
    except SignatureError:
        raise
    except (UnidentifiedImageError, ValueError, OSError, Image.DecompressionBombError):
        raise SignatureError("ไฟล์ลายเซ็นต้องเป็นรูปภาพ JPG, PNG หรือ WEBP") from None

    rgb.thumbnail((WORK_SIDE, WORK_SIDE))
    if min(rgb.size) < 20:
        raise SignatureError("รูปเล็กเกินไป กรุณาถ่ายลายเซ็นให้ใหญ่และชัดขึ้น")
    grey = rgb.convert("L")
    w, h = grey.size

    # Paper brightness near each point: shrink, keep the brightest nearby value
    # (removes pen strokes), blur, and grow back.
    sw, sh = max(1, w // 16), max(1, h // 16)
    paper = grey.resize((sw, sh), Image.Resampling.BOX)
    paper = paper.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(2))
    paper = paper.resize((w, h), Image.Resampling.BILINEAR)

    # How much darker than the paper nearby. Light noise is cut off later.
    dark = ImageChops.subtract(paper, grey)
    dark = dark.filter(ImageFilter.MedianFilter(3))

    hist = dark.histogram()
    total = w * h
    # Strength of the ink: the value that only the darkest 0.5% of pixels reach.
    acc, strong = 0, 0
    for v in range(255, -1, -1):
        acc += hist[v]
        if acc >= total * 0.005:
            strong = v
            break
    if strong < 40:
        raise SignatureError("ไม่พบลายเซ็นในรูป กรุณาเซ็นด้วยปากกาสีเข้มบนกระดาษขาว แล้วถ่ายให้ชัด")

    lo = max(18, int(strong * 0.22))  # below this is paper texture or noise
    hi = max(lo + 10, int(strong * 0.6))  # above this is solid ink
    span = hi - lo
    alpha = dark.point(lambda v: 0 if v <= lo else 255 if v >= hi else int((v - lo) * 255 / span))
    alpha = _drop_broad_shadows(alpha)

    # Bounding box of solid ink, ignoring single specks left over from noise.
    solid = alpha.point(lambda a: 255 if a >= 128 else 0).filter(ImageFilter.MinFilter(3))
    bbox = solid.getbbox()
    if not bbox:
        raise SignatureError("ไม่พบลายเซ็นในรูป กรุณาเซ็นด้วยปากกาสีเข้มบนกระดาษขาว แล้วถ่ายให้ชัด")
    left, top, right, bottom = bbox
    pad = max(4, int(0.04 * max(right - left, bottom - top)))
    bbox = (max(0, left - pad), max(0, top - pad), min(w, right + pad), min(h, bottom + pad))
    # Ink spread over almost the whole picture means a dark photo, not a signature.
    if (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]) > 0.97 * total and _coverage(alpha) > 0.25:
        raise SignatureError("รูปมืดหรือมีพื้นหลังเยอะเกินไป กรุณาถ่ายลายเซ็นบนกระดาษขาวในที่สว่าง")

    colour = _ink_colour(rgb, alpha)
    alpha = alpha.crop(bbox)
    out = Image.new("RGBA", alpha.size, colour + (0,))
    out.putalpha(alpha)
    out.thumbnail(OUT_MAX, Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    out.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def _drop_broad_shadows(alpha: Image.Image) -> Image.Image:
    """Keep thin pen strokes, remove wide dark areas (a shadow, the table past the
    paper's edge). A morphological opening (min then max filter) wipes out
    anything thinner than the filter, so what survives it is a broad area; we
    subtract that. Done at half size to keep it fast."""
    w, h = alpha.size
    half = alpha.resize((max(1, w // 2), max(1, h // 2)), Image.Resampling.BOX)
    mask = half.point(lambda a: 255 if a >= 40 else 0)
    broad = mask.filter(ImageFilter.MinFilter(15)).filter(ImageFilter.MaxFilter(15))
    if not broad.getbbox():
        return alpha
    # Grow it so the soft rim of the broad area goes too, then cut it out.
    broad = broad.filter(ImageFilter.MaxFilter(9)).resize((w, h), Image.Resampling.BILINEAR)
    return ImageChops.multiply(alpha, ImageChops.invert(broad))


def _coverage(alpha: Image.Image) -> float:
    hist = alpha.histogram()
    return sum(hist[128:]) / max(1, alpha.size[0] * alpha.size[1])


def data_uri(png: bytes | None) -> str:
    """Inline the PNG for WeasyPrint, which then needs no file or URL for it."""
    if not png:
        return ""
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")
