"""SQLAlchemy engine and session management.

SQLite for local development, PostgreSQL for production — the only difference is the
URL. No SQLite-specific types are used in the models, and `pool_pre_ping` keeps
long-lived Postgres connections healthy.
"""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

_connect_args: dict = {}
_engine_kwargs: dict = {"future": True, "pool_pre_ping": True}

if settings.db_url.startswith("sqlite"):
    # SQLite needs this because the worker thread and request threads share the file.
    _connect_args = {"check_same_thread": False, "timeout": 30}
else:
    _engine_kwargs.update({"pool_size": 5, "max_overflow": 10, "pool_recycle": 1800})

engine = create_engine(settings.db_url, echo=settings.sql_echo,
                       connect_args=_connect_args, **_engine_kwargs)

if settings.db_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _record):  # pragma: no cover - driver level
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA busy_timeout=30000")
        cur.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False,
                            expire_on_commit=False, class_=Session)


class Base(DeclarativeBase):
    """Declarative base for every model."""


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one session per request, always closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    """For workers and scripts: commit on success, roll back on error."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def create_all() -> None:
    """Dev/bootstrap convenience. Production schema comes from Alembic."""
    from app import models  # noqa: F401  (register mappers)
    Base.metadata.create_all(bind=engine)
