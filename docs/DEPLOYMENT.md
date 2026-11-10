# Deployment guide

The app is three pieces: a static frontend, a FastAPI backend, and a worker. All three can
run from the images in this repository.

---

## 0. What you must provide (and what I cannot do for you)

Deploying needs **your** accounts. Nothing here is deployed automatically:

| Thing | Where | Cost |
|---|---|---|
| Frontend hosting | Vercel / Netlify (free tier) or the included nginx image | ₹0 |
| Backend host | Render / Fly.io / Railway / any VPS with Docker | ₹0 tiers exist |
| PostgreSQL | Neon / Supabase free tier, or the `postgres` service in docker-compose | ₹0 |
| Domain (optional) | Any registrar | paid |

Never commit `.env`. Every secret below is set in the host's dashboard.

---

## 1. Generate a production secret

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Set it as `ACA_SECRET_KEY` on the backend. Without it, sessions are signed with a key
generated on first boot — fine locally, wrong for production (restarts would invalidate
sessions, and multiple instances would disagree).

---

## 2. Backend

### Docker (recommended)

```bash
docker build -t aca-backend ./backend
docker run -p 8000:8000 \
  -e ACA_ENVIRONMENT=production \
  -e ACA_SECRET_KEY="<your-secret>" \
  -e ACA_COOKIE_SECURE=true \
  -e ACA_DATABASE_URL="postgresql+psycopg://user:pass@host:5432/aca" \
  -e ACA_CORS_ORIGINS="https://your-frontend.vercel.app" \
  -v aca_data:/data \
  aca-backend
```

The container runs `alembic upgrade head` before starting, so the schema is always current.

### Worker (same image, different command)

```bash
docker run \
  -e ACA_ENVIRONMENT=production -e ACA_SECRET_KEY="<your-secret>" \
  -e ACA_DATABASE_URL="postgresql+psycopg://..." \
  -v aca_data:/data \
  aca-backend python -m app.workers.worker
```

Both containers must mount the **same** volume: the worker reads uploads written by the API.

### Render / Fly.io notes

- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Add a pre-deploy command: `alembic upgrade head`
- Free tiers sleep when idle: the first request afterwards takes ~30 s. Mention it to anyone
  reviewing the app.
- Free-tier disks are ephemeral. Uploads vanish on redeploy; the app handles missing files
  gracefully (410) but do not promise persistence you do not have.

---

## 3. Frontend

### Vercel

1. Import the repository, set **Root Directory** to `frontend`.
2. Framework preset: **Vite**. Build `npm run build`, output `dist`.
3. Environment variable: none needed if you proxy `/api` (see below).

Because the frontend calls `/api/...` on its own origin, add a rewrite so Vercel forwards it
to the backend. `frontend/vercel.json`:

```json
{
  "rewrites": [
    { "source": "/api/(.*)", "destination": "https://your-backend.example.com/api/$1" }
  ]
}
```

Cross-origin cookies then need the backend to allow the frontend origin
(`ACA_CORS_ORIGINS`) **and** `ACA_COOKIE_SECURE=true` with HTTPS on both sides.

### nginx image (same origin, simplest cookies)

```bash
docker build -t aca-frontend ./frontend
docker run -p 8080:80 aca-frontend
```

`frontend/nginx.conf` already proxies `/api/` to the `backend` service and falls back to
`index.html` for client-side routes.

### Single-container option

The backend serves `frontend/dist` if it exists, with an SPA fallback:

```bash
cd frontend && npm ci && npm run build && cd ..
cd backend && uvicorn app.main:app --port 8000
# open http://localhost:8000
```

That gives one origin, one cookie, one deploy target — handy for a small VPS.

---

## 4. Database (PostgreSQL)

See [POSTGRES_MIGRATION.md](POSTGRES_MIGRATION.md). Short version:

```bash
pip install "psycopg[binary]"
export ACA_DATABASE_URL="postgresql+psycopg://user:pass@host:5432/aca"
alembic upgrade head
```

---

## 5. Storage

Local disk today (`ACA_STORAGE_ROOT`, mounted volume). For object storage, replace the four
functions in `backend/app/services/storage.py` (`save_stream`, `resolve_within`,
`safe_delete`, `disk_usage_mb`) — every route goes through them, so nothing else changes.

---

## 6. Production checklist

- [ ] `ACA_ENVIRONMENT=production`
- [ ] `ACA_SECRET_KEY` set to a fresh 48-byte random value
- [ ] `ACA_COOKIE_SECURE=true` and HTTPS on both frontend and backend
- [ ] `ACA_CORS_ORIGINS` lists only your real frontend origin
- [ ] `ACA_DATABASE_URL` points at PostgreSQL, `alembic upgrade head` has run
- [ ] `ACA_STORAGE_ROOT` is a persistent volume, shared by API and worker
- [ ] Worker container running (otherwise queued jobs never process)
- [ ] `ACA_MAX_UPLOAD_MB` sized for your disk and RAM
- [ ] Reverse proxy `client_max_body_size` ≥ your upload limit
- [ ] Backups configured for the database **and** the storage volume
- [ ] `ACA_DEBUG=false`, no `.env` in git
- [ ] Health check wired to `/api/health`
- [ ] Rate limiting reviewed (in-process; use Redis if you run several API instances)
- [ ] You have tested register → upload → clip → download **on the deployed instance**

---

## 7. Scaling notes

- The API is stateless apart from sessions in the DB: run several instances behind a proxy.
- In-process rate limiting assumes one instance; move it to Redis before scaling out.
- The worker claims jobs with a conditional UPDATE, so several workers are safe.
- FFmpeg is CPU-bound: size the worker, not the API, for rendering throughput.
