# Moving from SQLite to PostgreSQL

The models use no SQLite-specific types, so the only changes are a driver, a connection
string, and one migration command.

---

## 1. Install the driver

```bash
pip install "psycopg[binary]"
```

`psycopg` (version 3) is what the `postgresql+psycopg://` URL uses. `psycopg2-binary` works
too with `postgresql+psycopg2://`.

---

## 2. Point the app at PostgreSQL

In `.env`:

```
ACA_DATABASE_URL=postgresql+psycopg://aca:acapassword@localhost:5432/aca
```

Nothing else in the code changes: `app/core/database.py` switches connection arguments
based on the URL (SQLite gets `check_same_thread` and WAL pragmas; PostgreSQL gets a pooled
connection with `pool_pre_ping`).

---

## 3. Create the schema

```bash
cd backend
alembic upgrade head
```

That runs the same migration used locally. Check it worked:

```bash
python -c "from app.core.database import engine; from sqlalchemy import inspect; \
print(sorted(inspect(engine).get_table_names()))"
```

You should see `agent_logs, agent_tasks, alembic_version, clips, generated_content, jobs,
projects, thumbnails, transcripts, user_sessions, user_settings, users, videos`.

---

## 4. Local PostgreSQL with Docker (optional)

```bash
docker compose --profile postgres up -d
```

Then set `ACA_DATABASE_URL=postgresql+psycopg://aca:acapassword@localhost:5432/aca` and run
the migration.

---

## 5. Migrating existing SQLite data

If you already have projects worth keeping, copy them across row by row (the schema is
identical, so this is a straight copy). A small script:

```python
# migrate_sqlite_to_pg.py — run from backend/ with both URLs available
import os
from sqlalchemy import create_engine, insert, select, MetaData

from app.core.database import Base
from app import models  # noqa: F401  (register tables)

sqlite = create_engine("sqlite:///../storage/aca.db")
pg = create_engine(os.environ["ACA_DATABASE_URL"])

Base.metadata.create_all(pg)   # or use alembic upgrade head first
meta = MetaData()
meta.reflect(bind=sqlite)

# Parents before children, or the foreign keys will fail.
order = ["users", "user_settings", "projects", "videos", "transcripts", "clips",
         "thumbnails", "generated_content", "agent_tasks", "agent_logs", "jobs"]

with sqlite.connect() as src, pg.begin() as dst:
    for table in order:
        rows = [dict(r._mapping) for r in src.execute(select(meta.tables[table]))]
        if rows:
            dst.execute(insert(Base.metadata.tables[table]), rows)
        print(f"{table}: {len(rows)} rows")
```

Uploaded files are untouched — they live on disk under `ACA_STORAGE_ROOT`. If the new host
uses a different path, copy `storage/uploads`, `storage/clips` and `storage/thumbnails`
across and keep `ACA_STORAGE_ROOT` pointing at the parent.

---

## 6. Differences to be aware of

| | SQLite (dev) | PostgreSQL (prod) |
|---|---|---|
| Concurrency | one writer at a time | many, MVCC |
| JSON columns | stored as text | native `jsonb`-capable |
| Timestamps | returned **naive** | returned **timezone-aware** |
| Enums / constraints | loose | enforced |

The timestamp difference is handled: `app/models/base.py::as_utc()` normalises both, and
`tests/test_auth.py` exercises the session-expiry comparison that depends on it.

---

## 7. Production indexes

The models already declare the indexes that matter (`ix_projects_user_created`,
`ix_clips_video`, `ix_jobs_status_created`, `ix_user_sessions_token_hash` via unique
constraint). If you grow past a few hundred thousand rows, the first things to add are a
composite `(user_id, created_at)` on `videos` and `clips`, and `pg_trgm` on
`generated_content.body` if you add search.
