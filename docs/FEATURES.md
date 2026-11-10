# Feature status

An honest inventory. Anything marked **implemented** is covered by the test suite or was
verified manually end to end.

---

## Implemented

### Accounts
- Register, login, logout, session restore on reload
- PBKDF2-HMAC-SHA256 password hashing (240 000 iterations, random salt per hash)
- Server-side sessions in an HttpOnly, SameSite=Lax cookie; token stored hashed
- Logout revokes the session server-side immediately
- Per-IP login rate limiting; identical error for unknown email and wrong password
- Per-user settings (default platform, clip length, caption toggles, creator persona)

### Projects and uploads
- Create / rename / delete projects (deleting removes files, clips and thumbnails)
- Upload MP4, MOV, M4V, WEBM, MKV
- Extension allow-list, size limit enforced during streaming, server-generated filenames
- Immediate FFmpeg probe: duration, dimensions, fps, audio presence
- Rejection of files that are not really video (422, file deleted)
- Video playback in the browser with HTTP Range support

### Video intelligence
- Audio decode, RMS envelope, speech-band activity (300–3400 Hz)
- Moment detection ranked by measured energy × novelty, with a written reason per suggestion
- Scene-cut detection (HSV histogram distance)
- Transcription adapters: faster-whisper (optional) → sidecar `.txt/.srt/.vtt` → pasted text → none
- The app states when no transcript exists; it never fabricates speech

### Clips
- Render from a suggested moment or explicit start/end
- 1080×1920, 1080×1080, 1920×1080 (and 16:9 letterbox) presets
- Loudness normalisation to −14 LUFS
- Subtitles as SRT + VTT sidecars, and burned in from a per-resolution ASS file
- Adjust timestamps after rendering (re-renders the same clip row)
- Download MP4 and SRT
- Validation: zero/negative length, too short, past end of video → 422

### Thumbnails
- Three layout styles rendered with Pillow from a real frame
- Cover and blur-pad framing depending on the target aspect
- Five-sub-score OpenCV analysis with human-readable reasons
- Upload your own image (validated, dimension-checked)
- Download as JPG, delete

### Content
- Three title options, description, hashtags, caption, per-platform variants
- Deterministic template engine by default; optional OpenAI-compatible LLM
- Every result records `source: offline | llm` and explains which engine ran
- Persisted per clip, selectable, copy-to-clipboard in the UI

### Agents
- Six agents: video_intelligence, editing, design, seo, analytics, community
- Central orchestrator: creates tasks, records logs, tracks progress and attempts
- Retry on transient failure (up to 3), immediate failure on bad input
- Human approval gate for the Community agent — enforced in the API
- Full task history with expandable logs and JSON output
- Full pipeline (analyse → cut → design → copy) in one call

### Infrastructure
- SQLAlchemy models for 12 tables with FKs, indexes and timestamps
- Alembic migrations, verified by applying to an empty database
- Background worker with an atomic DB-backed job queue
- Local analytics (production statistics only, clearly labelled)
- Dockerfile for backend, nginx image for frontend, docker-compose for the whole stack
- 43 backend tests; strict TypeScript frontend build

---

## Partial

| Feature | What works | What is missing |
|---|---|---|
| Speech-to-text | faster-whisper adapter, tested via sidecar and pasted paths | Whisper itself is off by default and not covered by CI (model download) |
| Caption timing | proportional to speech length, per-platform limits | word-level alignment without Whisper word timestamps |
| LLM copy | adapter, JSON contract, graceful fallback | not exercised in CI (needs a key) |
| Rate limiting | per-IP in-process limiter on login | not shared across multiple API instances |
| Analytics | own production statistics, 7-day activity | no platform API import (deliberate) |
| Storage | local disk with path-traversal guards | no S3/object storage backend |

---

## Not built

- **Publishing to platforms** — no YouTube/TikTok/Instagram upload. Everything stops at a
  downloadable file. This is the largest remaining piece.
- **Platform analytics import** — no OAuth, no engagement metrics.
- **AI image generation** — thumbnails are composed from real frames plus text, and the UI
  says so rather than implying a generative model.
- **Learned models** — moment scoring and thumbnail scoring are measured heuristics, not
  trained models. There is no training data yet.
- **Multi-user teams / sharing** — one account owns its own content.
- **Video stitching** — the app cuts one take; it does not join several takes together.

---

## Where the honesty is enforced

Not just in documentation:

- `app/services/segments.py` writes "Measured from the audio track; this is a signal, not a
  prediction" into every suggestion's reason string.
- `app/services/transcription.py` returns `source: "none"` rather than inventing a transcript.
- `app/services/seo.py` returns `source: "offline"` and a note explaining the template engine.
- `app/services/analytics.py` carries `source_note` on every response.
- `app/agents/community.py` sets `awaiting_approval: True` and says nothing is published.
- `app/agents/design.py` reports `subject_method` (`haar` or `skin-salience`) so you know
  which detector ran.
