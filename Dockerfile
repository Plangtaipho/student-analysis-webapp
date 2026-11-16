# Production image (Railway builds this automatically when it finds a Dockerfile).
FROM python:3.13-slim

# WeasyPrint needs Pango (text layout, incl. Thai word breaking via libthai).
RUN apt-get update \
 && apt-get install -y --no-install-recommends libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 libthai0 fontconfig \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

ENV ENV=production PYTHONUNBUFFERED=1
# Apply database migrations, then start the web server on Railway's $PORT.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
