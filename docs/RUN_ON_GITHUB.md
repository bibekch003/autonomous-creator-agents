# Run it on GitHub, with nothing installed

GitHub cannot host a *running* FastAPI app on Pages — Pages only serves static files, and
this app needs Python, FFmpeg and a database. What GitHub gives you instead is **Codespaces**:
a full Linux machine in your browser with the app running on a forwarded URL. That is the
"work on it easily" route.

---

## One click

1. Open https://github.com/bibekch003/autonomous-creator-agents
2. Green **Code** button → **Codespaces** tab → **Create codespace on main**
3. Wait for setup (~2–3 minutes the first time). The container installs the Python
   dependencies, applies the database migrations, **and starts the server for you**.
4. A popup offers to open port **8000** — click **Open in Browser**.

That's the whole app: the web interface *and* the API on one URL, because the backend serves
the prebuilt frontend from `frontend/dist`.

If the popup doesn't appear: open the **Ports** tab at the bottom, find port 8000, click the
globe icon.

**To share it with someone else:** Ports tab → right-click port 8000 → **Port Visibility** →
**Public**. The URL then works without a GitHub login.

---

## Why this works without Node

`frontend/dist` is committed to the repository — a production build of the React app. So the
container needs only Python, and `uvicorn` serves both the SPA and the API. No `npm install`,
no Node feature to download, nothing to fail.

If you change anything in `frontend/src`, rebuild the bundle and commit it again:

```bash
cd frontend
npm install          # first time only; needs Node 20
npm run build        # writes frontend/dist
cd .. && git add frontend/dist && git commit -m "Rebuild frontend" && git push
```

Or install Node inside the codespace once: `sudo apt-get update && sudo apt-get install -y nodejs npm`.

---

## Working in the codespace

```bash
# restart the server after a backend change
pkill -f 'uvicorn app.main'; cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000

# run the tests (43 of them)
cd /workspaces/autonomous-creator-agents && pytest -q

# apply a new migration
cd backend && alembic revision --autogenerate -m "describe the change" && alembic upgrade head
```

Logs from the auto-started server: `/tmp/aca-server.log`.

**Your data in a codespace lives on the codespace's own disk.** It survives while the
codespace exists and is deleted when you delete the codespace. That is fine for development;
it is why the deployed version needs PostgreSQL (see [FREE_TIER.md](FREE_TIER.md)).

---

## Stopping the free hours

A codespace stops itself after 30 minutes of inactivity, but it still counts against your
monthly quota while it exists. When you're done for the day:

- Close the browser tab (it will idle-stop), or
- https://github.com/codespaces → `...` next to it → **Stop codespace**
- To reclaim storage: same menu → **Delete**

Free tier is ~120 core-hours per month for personal accounts. A 2-core codespace running
2 hours a day uses ~120 hours a month, so stop it when you're not using it.

---

## If the codespace fails to build

| Symptom | Fix |
|---|---|
| "You have reached your codespaces limit" | Free hours used up. https://github.com/codespaces shows usage; the quota resets monthly, or delete old codespaces |
| Build fails at `pip install` | Open the creation log; usually a transient network error — delete and recreate the codespace |
| Port 8000 shows nothing | The auto-start failed. Run the restart command above and read `/tmp/aca-server.log` |
| `ModuleNotFoundError: app` | You are not in `backend/` — `cd /workspaces/autonomous-creator-agents/backend` |
| Codespaces greyed out on the Code button | Not signed in, or Codespaces is disabled for your account: https://github.com/settings/codespaces |

Paste the failing log line and it can be fixed — the container definition is a single small
file (`.devcontainer/devcontainer.json`).
