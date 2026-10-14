import os

# Must be set before any app module is imported so pydantic-settings reads them.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import pytest
from fastapi import Request
from httpx import ASGITransport, AsyncClient
from sqlalchemy import Sequence as SASequence, event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.pool import StaticPool

# app.main MUST be imported before app.di.container here: the container's
# own wire() call scans the whole `app` package (including app.main) at
# construction time, and app.main imports the container back — importing
# app.main first means that module is already fully loaded by the time
# wire() reaches it, avoiding a circular-import error at collection time.
from app.main import app, mount_routers  # noqa: I001
from app.auth.dependencies import get_current_user
from app.core.database import Base
from app.di.container import container
from app.middleware.rate_limit import RateLimitMiddleware

# Router mounting happens inside app.main's lifespan at real ASGI startup,
# not at module-import time — but httpx's ASGITransport (used by every
# test client fixture below) never triggers the ASGI lifespan protocol.
# Mount routes once here instead, synchronously, before any test runs.
mount_routers(app)

# ── SQLite compatibility shim ───────────────────────────────────────────────
# JSONB (app/models/organization.py's fhir_data column) has no SQLite
# equivalent — compile it down to plain JSON for the test engine only;
# Postgres keeps its native JSONB untouched.


@compiles(JSONB, "sqlite")
def _jsonb_as_text(element, compiler, **kw):
    return "JSON"


from sqlalchemy import BigInteger


@compiles(BigInteger, "sqlite")
def _bigint_as_integer(element, compiler, **kw):
    return "INTEGER"


# ── Disable rate limiting for tests ───────────────────────────────────────
# The in-process sliding-window limiter accumulates across tests when
# Redis is unavailable, causing 429s. Bypass dispatch entirely in tests.


async def _no_rate_limit(self, request, call_next):
    return await call_next(request)


RateLimitMiddleware.dispatch = _no_rate_limit

# Note: this starter kit's example_cache config (app/core/cache/) has no
# consumer wired into the organization resource. If you wire a
# cache-backed repository/service later, override its cache_backend
# provider with MemoryCacheBackend() here, the same way
# container.core.database is overridden below, so tests never depend on a
# real Redis being reachable.

# ── Sequence simulation ─────────────────────────────────────────────────────
# PostgreSQL sequences (organization_id_seq) aren't supported by SQLite —
# strip the server_default (which would emit nextval() DDL SQLite can't
# run) and assign IDs with an in-process counter in the ORM before_insert
# event instead, mirroring the real sequence's start/increment.

_seq_counters: dict[str, int] = {}
_defaults_stripped = False


def _strip_server_defaults() -> None:
    global _defaults_stripped
    if _defaults_stripped:
        return
    for table in Base.metadata.tables.values():
        for col in table.columns:
            sd = col.server_default
            if sd is None:
                continue
            arg = getattr(sd, "arg", None)
            if arg is not None:
                if type(arg).__name__ == "next_value" or "::jsonb" in str(arg):
                    col.server_default = None
    _defaults_stripped = True


@event.listens_for(Base, "before_insert", propagate=True)
def _simulate_sequence(mapper, connection, target) -> None:
    for col in mapper.local_table.columns:
        if isinstance(col.default, SASequence):
            if getattr(target, col.name, None) is None:
                seq: SASequence = col.default
                key = seq.name
                if key not in _seq_counters:
                    _seq_counters[key] = seq.start or 1
                else:
                    _seq_counters[key] += seq.increment or 1
                setattr(target, col.name, _seq_counters[key])


# ── TestDatabase ────────────────────────────────────────────────────────────


class TestDatabase:
    """Drop-in replacement for app.core.database.Database using a pre-built engine."""

    def __init__(self, engine):
        self.engine = engine
        self.session_maker = async_sessionmaker(
            bind=engine, class_=AsyncSession, expire_on_commit=False
        )

    async def disconnect(self) -> None:
        pass  # lifecycle is managed by the fixture

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        session: AsyncSession = self.session_maker()
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def make_test_user(sub: str = "u-test", org_id: str = "org-test", permissions: list[str] | None = None):
    """Factory that returns a get_current_user override for tests."""
    if permissions is None:
        permissions = [
            "organization:create",
            "organization:read",
            "organization:update",
            "organization:delete",
        ]

    async def _dep(request: Request) -> dict:
        user = {"sub": sub, "org_id": org_id, "permissions": permissions}
        request.state.user = user
        return user

    return _dep


@pytest.fixture
async def _engine():
    """Single in-memory SQLite engine per test (StaticPool -> one connection)."""
    _strip_server_defaults()
    eng = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest.fixture
async def client(_engine):
    """AsyncClient authenticated as u-test / org-test."""
    test_db = TestDatabase(_engine)
    container.core.database.override(test_db)
    app.dependency_overrides[get_current_user] = make_test_user()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.pop(get_current_user, None)
    container.core.database.reset_override()
