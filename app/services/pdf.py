"""Render report HTML to PDF with WeasyPrint, using the bundled Sarabun font.

WeasyPrint needs the Pango library on the server (see Dockerfile). Thai line
breaking comes from Pango/libthai, so long Thai text wraps at word boundaries.
"""
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.services.home_class import long_form

APP_DIR = Path(__file__).resolve().parent.parent
FONT_DIR = APP_DIR / "static" / "fonts"

_env = Environment(
    loader=FileSystemLoader(str(APP_DIR / "templates" / "pdf")),
    autoescape=select_autoescape(["html"]),
)


def thai_number(n) -> str:
    return str(n).translate(str.maketrans("0123456789", "๐๑๒๓๔๕๖๗๘๙"))


_env.filters["thai"] = thai_number
_env.filters["long_class"] = long_form


def render_pdf(template: str, **context) -> bytes:
    # Imported here so the web app still starts (and tests run) where Pango is missing.
    from weasyprint import HTML

    html = _env.get_template(template).render(font_dir=FONT_DIR.as_uri(), **context)
    return HTML(string=html, base_url=str(APP_DIR)).write_pdf()
