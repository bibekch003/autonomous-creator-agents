# All-in-one image: builds the React app, then serves both the API and the SPA
# from a single FastAPI process. One service, one URL, no CORS, no separate frontend host.
#
#   docker build -t aca .
#   docker run -p 8000:8000 -e ACA_SECRET_KEY=... -v aca_data:/data aca
#
# The backend serves frontend/dist when it exists (see app/main.py), which is exactly
# what stage 2 copies in.

# ---------- stage 1: build the frontend ----------
FROM node:20-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---------- stage 2: python runtime ----------
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    ACA_ENVIRONMENT=production \
    ACA_STORAGE_ROOT=/data

WORKDIR /app

# Dependencies first, so the layer caches when only source changes.
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install -r backend/requirements.txt

COPY backend/ ./backend/

# The SPA. app/main.py resolves FRONTEND_DIST as <repo root>/frontend/dist.
COPY --from=frontend /app/frontend/dist ./frontend/dist

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /data \
    && chown -R appuser:appuser /app /data
USER appuser
VOLUME ["/data"]

WORKDIR /app/backend
EXPOSE 8000

# Migrate, then serve. $PORT is provided by Render/Fly/Railway; 8000 locally.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
