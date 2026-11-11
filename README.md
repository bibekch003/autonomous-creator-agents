# Autonomous Creator Agents

[![CI](https://github.com/bibekch003/autonomous-creator-agents/actions/workflows/ci.yml/badge.svg)](https://github.com/bibekch003/autonomous-creator-agents/actions/workflows/ci.yml)
[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/bibekch003/autonomous-creator-agents)
[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/bibekch003/autonomous-creator-agents)

**Your AI-powered creative production team.**

Upload one long video. Six specialised AI agents find the moments worth clipping, cut them
for every platform, write the copy and design the thumbnails. You review, adjust, download.

A real full-stack application — FastAPI + React + FFmpeg — not a UI mock-up. Every button
does something, and every number on screen comes from a measured signal.

| | |
|---|---|
| **Stack** | FastAPI · SQLAlchemy · SQLite/PostgreSQL · React · TypeScript · Vite · Tailwind · FFmpeg |
| **Tests** | 43 backend tests passing (auth, workflow, security, agents, units) |
| **Frontend** | strict TypeScript, production build verified (1590 modules) |
| **Cost to run** | ₹0 — no paid API required, no GPU, works fully offline |
| **Docs** | [Windows setup](docs/SETUP_WINDOWS.md) · [Deployment](docs/DEPLOYMENT.md) · [PostgreSQL](docs/POSTGRES_MIGRATION.md) · [Feature status](docs/FEATURES.md) |

---

## 1. What it does

The workflow, end to end:

```
register → create project → upload video → analyse → review moments
        → render clips → design thumbnails → generate copy → download
```

**Video Intelligence agent** probes the file, decodes the audio and ranks every 3-second
window by *measured* energy and novelty. It tells you where the emphasis is, with a reason
for each suggestion — and says plainly that this is a signal, not a prediction of virality.

**Editing agent** cuts those moments with FFmpeg into 1080×1920 (Shorts/Reels/TikTok),
1080×1080 or 1920×1080, loudness-normalised to −14 LUFS, with subtitles burned in from a
per-resolution ASS file so the text fits the frame.

**Design agent** renders thumbnail concepts from a real frame and scores each on five named
sub-scores — contrast, colourfulness, subject presence, text legibility, clutter — with
human-readable reasons.

**SEO agent** writes three titles, a description, hashtags and per-platform captions. Uses
the deterministic template engine by default, or your own LLM endpoint if configured. The
result always records which engine ran.

**Analytics agent** reports your own production statistics from the app's database, and
says explicitly that no platform analytics were imported.

**Community agent** drafts replies in your voice and **stops**. Nothing is published without
human approval — that gate is enforced in the API, not just the UI.

The **orchestrator** assigns work, records every task with its inputs, output, attempts and
log lines, retries transient failures, and fails deterministic ones immediately.

## 2. Architecture

```
frontend/  React + TS + Vite + Tailwind
    │  fetch /api (session cookie, HttpOnly)
    ▼
backend/  FastAPI
    ├── api/           routes: auth · projects · videos · clips · content · thumbnails · agents · analytics
    ├── core/          config · database · security (PBKDF2, sessions, rate limit) · logging
    ├── models/        SQLAlchemy: User, UserSession, UserSettings, Project, Video, Transcript,
    │                  Clip, GeneratedContent, Thumbnail, AgentTask, AgentLog, Job
    ├── schemas/       Pydantic request/response contracts
    ├── services/      video (probe/audio/captions/render) · segments · clips · thumbnails · seo · analytics · storage
    ├── agents/        six agents + orchestrator (base class, retries, logs, approval gate)
    ├── workers/       standalone worker process claiming jobs from the DB queue
    └── ai/            optional LLM adapter with deterministic fallback
    ▼
storage/  uploads/ · clips/ · thumbnails/ · temp/ · aca.db
```

Long video work never blocks a request: the API writes a `Job` row and returns immediately,
and `python -m app.workers.worker` claims it with an atomic UPDATE. The same code path runs
synchronously with `?sync=true`, which is what the tests and small files use.

## 3. Quick start (Windows, from zero)

Full beginner-level walkthrough: **[docs/SETUP_WINDOWS.md](docs/SETUP_WINDOWS.md)**.

Short version — you need **Git** and **Python 3.11+**:

```powershell
git clone <this-repo-url> autonomous-creator-agents
cd autonomous-creator-agents

# backend
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# frontend (second terminal)
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**, register an account, create a project, upload a video.

`ffmpeg` does **not** need a separate install — `imageio-ffmpeg` ships a static binary.

### Run it in the cloud, with nothing installed

Click **Open in GitHub Codespaces** above (or repo → **Code → Codespaces → Create
codespace on main**). The devcontainer installs Python, Node and all dependencies, then
applies the migrations — about three minutes the first time. Then, in its terminal:

```bash
cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000     # terminal 1
cd frontend && npm run dev                                        # terminal 2
```

GitHub forwards both ports and offers to open the app in your browser. To share it, right
click port 5173 → **Port Visibility → Public**.

No ffmpeg install is needed there either: `imageio-ffmpeg` ships the static binary with
libass, which is what burns the captions.

### Everything in Docker instead

```bash
docker compose up --build          # http://localhost:8080
```

### What CI checks

Every push runs [`.github/workflows/ci.yml`](.github/workflows/ci.yml): the 43 backend
tests against Python 3.12, a migration applied to an empty database, and a strict
type-check plus production build of the frontend. A green badge means the code in this
repository actually runs.

## 4. Tests

```bash
cd backend
pytest -q            # 43 tests
```

| File | Covers |
|---|---|
| `tests/test_auth.py` | register/login/logout, duplicate email, short password, identical errors for wrong email vs wrong password, HttpOnly cookie |
| `tests/test_workflow.py` | upload → probe → analyse → transcript → clip with captions → thumbnail → SEO copy → download; timestamp adjustment; invalid ranges; full pipeline |
| `tests/test_security.py` | upload type/size validation, fake-video rejection, cross-user access on 7 endpoints, path traversal, SQL-injection payloads, 404s not 500s |
| `tests/test_agents.py` | agent catalogue, unknown agent, approval gate, logs and progress, clean failure on missing input |
| `tests/test_units.py` | PBKDF2 hashing, rate limiter, filename cleaning, upload rules, SEO engine, moment maths, transcription honesty, thumbnail scoring |

The suite generates its own sample MP4 with FFmpeg, so there is nothing to download.

## 5. API

Interactive docs at **http://localhost:8000/api/docs** once the backend runs.

| Method | Route | Purpose |
|---|---|---|
| POST | `/api/auth/register` · `/login` · `/logout` | session cookie auth |
| GET | `/api/auth/me` · `/api/auth/session` | current user / probe |
| GET/POST | `/api/projects` | list / create |
| GET/PATCH/DELETE | `/api/projects/{id}` | read / rename / delete (files too) |
| POST | `/api/projects/{id}/videos` | upload (validated, streamed, probed) |
| GET | `/api/videos/{id}` · `/stream` | detail (incl. transcript) / play |
| POST | `/api/videos/{id}/transcript` | paste a transcript |
| POST | `/api/videos/{id}/analyse` | Video Intelligence only |
| POST | `/api/videos/{id}/pipeline` | analyse → cut → design → copy |
| GET/POST | `/api/videos/{id}/clips` · `/api/clips` | list / render a clip |
| PATCH/DELETE | `/api/clips/{id}` | adjust timestamps (re-renders) / delete |
| GET | `/api/clips/{id}/download` · `/subtitles` | MP4 / SRT |
| POST | `/api/thumbnails/render` · `/upload` | generate concepts / attach your own |
| POST | `/api/content/generate` | titles, description, hashtags, captions |
| GET | `/api/agents` · `/agents/tasks` | catalogue / execution log |
| POST | `/api/agents/run` · `/agents/tasks/{id}/approve` | run one agent / human approval |
| GET | `/api/analytics/overview` · `/detail` | local production statistics |
| GET/PATCH | `/api/settings` | per-user defaults |

## 6. Database

Twelve tables with foreign keys, indexes and timestamps — see `backend/app/models/`.

```
users ─┬─ user_sessions
       ├─ user_settings
       └─ projects ─┬─ videos ─┬─ transcripts
                    │          └─ clips ─┬─ thumbnails
                    │                   └─ generated_content
                    └─ clips
agent_tasks ── agent_logs          jobs (worker queue)
```

Schema changes go through **Alembic** (`backend/alembic/`). An initial migration is
included; production runs `alembic upgrade head` on deploy. Migrating to PostgreSQL is a
connection-string change plus one command — see
[docs/POSTGRES_MIGRATION.md](docs/POSTGRES_MIGRATION.md).

## 7. Security

- Passwords hashed with **PBKDF2-HMAC-SHA256** (240 000 iterations, per-hash random salt).
  No bcrypt wheel to compile on Windows.
- **Server-side sessions** in an HttpOnly, SameSite=Lax cookie; the token is stored hashed,
  and logout revokes it immediately.
- **Every** resource route re-checks ownership; another user's project returns **404**, not
  403, so existence is not leaked.
- Uploads: extension allow-list, size limit enforced *while streaming*, written to a
  server-generated filename, then probed with FFmpeg. A file that is not really video is
  rejected and deleted.
- Path traversal blocked by `resolve_within()`; media is served only through owner-checked
  routes, never as a static directory.
- Login rate limiting; identical error text for unknown email and wrong password.
- No secret ever reaches the frontend; `.env` is gitignored.

## 8. What is implemented, partial, and future

Full detail in [docs/FEATURES.md](docs/FEATURES.md). Summary:

**Implemented** — auth, projects, upload with validation, audio-based moment detection,
transcription (Whisper adapter / sidecar / pasted), clip rendering in three aspect ratios
with burned captions, thumbnail rendering + scoring, SEO copy, six agents with orchestrator,
logs, retries and approval gate, local analytics, settings, Alembic migrations, Docker.

**Partial** — speech-to-text is optional (`ACA_ENABLE_WHISPER=true` + `faster-whisper`);
LLM copy needs a key and falls back cleanly; caption timing is proportional to speech unless
Whisper word timestamps are available; single-worker rate limiting.

**Not built** — publishing to platforms, platform analytics import, learned scoring models,
AI image generation (thumbnails are composed from real frames + text, and the UI says so).

## 9. Honest limitations

- Moment suggestions are a **measured signal** (audio energy + speech density), not a
  virality prediction. Every suggestion says so in its own text.
- The SEO engine is **templates**, not a language model, unless you configure one. Results
  are labelled `offline` or `llm` accordingly.
- Analytics are **your own production numbers**, not platform engagement data.
- Thumbnails are **composed**, not AI-generated.
- No job runs in the background until you start the worker; with `?sync=true` the request
  waits for the render.

## 10. Deployment

### One public URL, in about four clicks (free, no card)

Click **Deploy to Render** above, or open:

**https://render.com/deploy?repo=https://github.com/bibekch003/autonomous-creator-agents**

1. Sign in with GitHub (Render's free plan needs no payment details).
2. It reads `render.yaml` from this repository and shows one web service — click **Apply**.
3. Wait ~4 minutes for the first build. You get `https://<name>.onrender.com`.

The root `Dockerfile` builds the React app and serves it **and** the API from one FastAPI
process, so there is a single URL, one origin and no CORS configuration. `ACA_SECRET_KEY`
is generated by Render; migrations run automatically on boot.

Free-plan behaviour worth knowing before you share the link: the instance **sleeps after
~15 minutes idle** (the next visit takes ~30 s to wake) and its filesystem is ephemeral, so
uploads and rendered clips disappear on restart. The app handles that gracefully, but do not
promise persistence you do not have. For real persistence, set `ACA_DATABASE_URL` to a
PostgreSQL instance and attach a disk.

### Other targets

- **Frontend** → Vercel (or the included nginx image).
- **Backend** → any Docker host (Fly.io, Railway, a VPS) with the root `Dockerfile`.
- **Worker** → the same image with `python -m app.workers.worker` as the command.
- **Database** → PostgreSQL via `ACA_DATABASE_URL`.
- **Storage** → local volume now; swap `app/services/storage.py` for S3 later.

Step-by-step, including the production checklist: **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)**.

## 11. Project structure

```
autonomous-creator-agents/
├── backend/
│   ├── app/{api,agents,ai,core,models,schemas,services,workers}/
│   ├── alembic/                 migrations
│   ├── Dockerfile · requirements.txt · requirements-dev.txt
├── frontend/
│   ├── src/{components,hooks,layouts,pages,services,types}/
│   ├── Dockerfile · nginx.conf · package.json · vite.config.ts · tailwind.config.js
├── tests/                       pytest suite (43 tests)
├── docs/                        setup · deployment · postgres · feature status
├── docker-compose.yml · .env.example · .gitignore
└── README.md
```

## 12. Licence

MIT.
