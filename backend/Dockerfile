# Backend image: FastAPI + FFmpeg-capable Python.
#
# ffmpeg is not installed via apt: imageio-ffmpeg ships a static build with libass,
# which is what burns the captions. That keeps the image small and reproducible.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    ACA_ENVIRONMENT=production \
    ACA_STORAGE_ROOT=/data

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run as a non-root user; /data is the only writable location.
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /data \
    && chown -R appuser:appuser /app /data
USER appuser
VOLUME ["/data"]

EXPOSE 8000

# Apply migrations, then serve. Use the same command for the worker container but
# override it with: python -m app.workers.worker
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1"]
