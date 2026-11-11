# Running on a free hosting tier

Free tiers are fine for showing the app. They are not fine for keeping data or for video
encoding. This page explains exactly what breaks, why, and the two fixes that actually work.

---

## What goes wrong, and why

| Symptom | Cause | Fix |
|---|---|---|
| "No account" after signing up successfully | The database is SQLite on the container filesystem. Free tiers attach **no disk**, so every restart / wake-from-sleep recreates the container and the database is gone. | Connect PostgreSQL (§1) |
| Logged out constantly | Same thing: session rows live in that database. | Connect PostgreSQL (§1) |
| Service crashes during upload or render | Free instances get **512 MB RAM** and **0.1 CPU**. FFmpeg + OpenCV + an upload exceeds it. | Cap uploads, render smaller (§2) |
| Rendering takes minutes for a 10 s clip | 0.1 CPU is roughly 1/20th of a laptop core. x264 at 1080×1920 is expensive. | Render smaller + ultrafast preset (§2), or move host (§3) |

You can confirm all of this from the app itself — `GET /api/health` reports:

```json
"database": "sqlite",
"persistent_storage": false,
"export": { "preset": "veryfast", "crf": 23, "scale": 1.0 }
```

`persistent_storage: false` means "your data will disappear on the next restart". That is
the honest signal; there is no way to make SQLite persistent on a free tier without a disk.

---

## §1 Connect a free PostgreSQL (fixes accounts disappearing)

Neon and Supabase both have free tiers with no card. Neon is the quicker of the two.

1. Sign up at https://neon.tech (GitHub login works).
2. Create a project → it gives you a connection string like:
   `postgresql://user:password@ep-xxx.ap-southeast-1.aws.neon.tech/neondb?sslmode=require`
3. Convert it for SQLAlchemy by changing the scheme to `postgresql+psycopg://` and keeping
   the rest:
   ```
   postgresql+psycopg://user:password@ep-xxx.ap-southeast-1.aws.neon.tech/neondb?sslmode=require
   ```
4. On Render → your service → **Environment** → add:
   - `ACA_DATABASE_URL` = the string above
   - `ACA_SECRET_KEY` = any 48+ character random string
5. Save. Render redeploys; the container runs `alembic upgrade head` on boot, so the schema
   is created automatically in Neon.

Verify: `/api/health` now reports `"database": "postgresql"` and
`"persistent_storage": true`. Register an account, force a redeploy, and it will still be
there.

The driver is already listed as an optional extra. If the build fails with
`ModuleNotFoundError: psycopg`, add `psycopg[binary]` to `backend/requirements.txt`.

Uploads still disappear on restart (they live on the ephemeral disk). The database now
remembers *that* a video existed, and the app returns a clean `410 Gone` for a missing file
rather than a 500 — re-upload to continue.

---

## §2 Make rendering viable on 0.1 CPU (fixes slowness and crashes)

Set these on the service (Render → Environment), then redeploy:

| Variable | Value | Effect |
|---|---|---|
| `ACA_MAX_UPLOAD_MB` | `100` | Stops a large upload from OOM-killing the container |
| `ACA_EXPORT_SCALE` | `0.6` | Renders 648×1152 instead of 1080×1920 — ~3× less pixel work |
| `ACA_EXPORT_PRESET` | `ultrafast` | x264's fastest mode, several times quicker than `veryfast` |
| `ACA_EXPORT_CRF` | `28` | Smaller files, faster encode, slightly softer image |

A 10-second vertical clip that took minutes should land in tens of seconds. Keep test clips
under ~30 seconds while you are on a free instance.

Everything else — moment detection, thumbnails, copy — is already cheap and unaffected.

---

## §3 Move to a host with real CPU (best experience, still free)

Hugging Face Spaces gives a free CPU instance with **2 vCPU and 16 GB RAM**, which is
roughly 20× the CPU of Render's free tier and plenty for FFmpeg.

1. https://huggingface.co/new-space → name it, **SDK: Docker**, hardware **CPU basic
   (free)**, visibility Public.
2. The repository's root `Dockerfile` already builds the frontend and serves everything
   from one process. Spaces expects port **7860**, so add an environment variable
   `PORT=7860` in the Space settings (the Dockerfile reads `$PORT`).
3. Push the repository to the Space:
   ```bash
   git remote add space https://huggingface.co/spaces/<your-username>/<space-name>
   git push space main
   ```
   Hugging Face asks for a **write token** (Settings → Access Tokens → New token → write).

Combine with §1 so accounts survive restarts. Spaces' storage is also ephemeral on the free
tier, so the database still needs to be external.

---

## The short version

- Free tier + SQLite = **data loss on every restart**. That is the "no account" bug.
- Free tier CPU = **slow renders**. Scale down and use `ultrafast`.
- Want both fixed properly: **Neon for the database, Spaces for the CPU.** Both free.
- For anything you would show to an employer, a ₹500/month VPS with a real disk and 2 vCPU
  is less trouble than fighting free-tier limits.
