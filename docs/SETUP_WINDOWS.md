# Windows setup, from zero

Written for a Windows 11 laptop with no GPU and no prior setup. Every command is copy-paste.

---

## 1. Install the two prerequisites

**Git for Windows** — https://git-scm.com/download/win → run the installer → Next through
the defaults.

**Python 3.12** — https://www.python.org/downloads/windows/ → "Windows installer (64-bit)".
On the first screen, **tick "Add python.exe to PATH"** before Install.

> **Do not use Python 3.15.** Several packages (`opencv-python-headless`, `PyYAML`,
> `watchfiles`) publish no wheels for it yet, so pip tries to compile them and fails with
> `error: Microsoft Visual C++ 14.0 or greater is required`. 3.12 is the version this
> project is tested on.

Then turn off the Microsoft Store alias, or `python` keeps opening the Store:
**Settings → Apps → Advanced app settings → App execution aliases → off** for `python.exe`
and `python3.exe`.

**Close PowerShell and open a new window** — PATH changes only reach new terminals. Verify:

```powershell
git --version      # git version 2.x
python --version   # Python 3.12.x
```

---

## 2. Get the code

```powershell
cd $HOME
git clone <this-repo-url> autonomous-creator-agents
cd autonomous-creator-agents
```

No Git? Download the ZIP from the repository page (**Code → Download ZIP**), extract it, and
`cd` into the extracted folder.

---

## 3. Backend

```powershell
cd backend
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
```

Your prompt should now start with `(.venv)`. Confirm:

```powershell
python --version   # 3.12.x
```

Install and set up the database:

```powershell
pip install -r requirements.txt
alembic upgrade head
```

You do **not** need to install FFmpeg — `imageio-ffmpeg` ships a static binary with libass,
which is what burns the captions in.

Start the API:

```powershell
uvicorn app.main:app --reload --port 8000
```

Leave this window running. Check http://localhost:8000/api/health — you should see
`"status": "ok"` and `"caption_burn_in": true`.

---

## 4. Frontend (second PowerShell window)

```powershell
cd $HOME\autonomous-creator-agents\frontend
npm install
npm run dev
```

Open **http://localhost:5173**. The Vite dev server proxies `/api` to port 8000, so the
session cookie works without CORS games.

---

## 5. First run

1. **Create account** — name, email, any password of 8+ characters.
2. **My Projects → New project** — e.g. "Test shoot".
3. **Upload video** — an MP4/MOV/WEBM/MKV under 500 MB.
4. Open **Video Studio** → **Analyse video**. You get suggested moments with scores and
   reasons.
5. **Transcript** — paste the words spoken in the video, save. (Or enable Whisper, below.)
6. **AI Clip Generator** — click *Use this* on a moment, or set your own start/end → the
   clip renders with captions burned in.
7. **Thumbnail Studio** → type a headline → render concepts → download a JPG.
8. **Content Manager** → generate titles, description, hashtags.
9. **Analytics** → your own production numbers.

---

## Optional: enable real speech-to-text

```powershell
pip install faster-whisper
```

Then in `.env` (copy `.env.example` to `.env` in the repo root):

```
ACA_ENABLE_WHISPER=true
ACA_WHISPER_MODEL=base
```

Restart the backend. The first transcription downloads the model (~140 MB) and runs on CPU;
a 10-minute video takes a few minutes on a Ryzen 7. Without it, paste a transcript instead —
the app works either way and never invents speech.

---

## Optional: background worker

By default the API can run jobs inline (`?sync=true`, what the UI uses for small files). For
long videos, run the worker in a third window:

```powershell
cd backend
.venv\Scripts\Activate.ps1
python -m app.workers.worker
```

The worker claims queued jobs and processes them without blocking the API.

---

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `Activate.ps1 cannot be loaded` | Run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that window first |
| `python` opens the Microsoft Store | Store alias still on (step 1), or PATH not refreshed — open a new window |
| `Microsoft Visual C++ 14.0 or greater is required` | You are on Python 3.14/3.15. Install 3.12, delete `.venv`, rebuild |
| `No module named app` | You are not inside `backend/` |
| `pip` / `uvicorn` not recognised | The venv is not active — look for `(.venv)` in the prompt |
| Frontend loads but every request fails | Backend is not running on port 8000, or it crashed — check that window |
| `Address already in use` | `uvicorn app.main:app --port 8010`, and set `VITE_API_TARGET` accordingly |
| Upload rejected: "Could not read this file as video" | The file is corrupt or is not really video, despite the extension |
| Clip renders but has no captions | No transcript exists. Paste one, or enable Whisper |
| ffmpeg not found | `pip install imageio-ffmpeg`, or install ffmpeg and set `FFMPEG_BIN` |
