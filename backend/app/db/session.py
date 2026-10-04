"""PostgreSQL engine and request-scoped SQLAlchemy sessions."""

from collections.abc import Generator
from functools import lru_cache
from typing import cast

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from fastapi import Request

from app.core.config import Settings, get_settings


_engines: dict[tuple[str, int, int, float, int], Engine] = {}


@lru_cache(maxsize=8)
def _engine_for(
    url: str,
    pool_size: int,
    max_overflow: int,
    pool_timeout: float,
    pool_recycle: int,
) -> Engine:
    engine = create_engine(
        url,
        pool_pre_ping=True,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=pool_timeout,
        pool_recycle=pool_recycle,
    )
    _engines[(url, pool_size, max_overflow, pool_timeout, pool_recycle)] = engine
    return engine


def get_engine(settings: Settings | None = None) -> Engine:
    config = settings or get_settings()
    return _engine_for(
        config.database_url,
        config.db_pool_size,
        config.db_max_overflow,
        config.db_pool_timeout_seconds,
        config.db_pool_recycle_seconds,
    )


def dispose_engines() -> None:
    """Close all cached pools during application shutdown."""
    for engine in tuple(_engines.values()):
        engine.dispose()
    _engines.clear()
    _engine_for.cache_clear()


def get_session_factory(settings: Settings | None = None) -> sessionmaker[Session]:
    return cast(sessionmaker[Session], sessionmaker(bind=get_engine(settings), autoflush=False, expire_on_commit=False))


def get_db(request: Request) -> Generator[Session, None, None]:
    factory = getattr(request.app.state, "db_session_factory", None) or get_session_factory()
    session = factory()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
