"""PostgreSQL engine and request-scoped SQLAlchemy sessions."""

from collections.abc import Generator
from functools import lru_cache
from typing import cast

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from fastapi import Request

from app.core.config import Settings, get_settings


@lru_cache(maxsize=4)
def _engine_for(url: str) -> Engine:
    return create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=10)


def get_engine(settings: Settings | None = None) -> Engine:
    config = settings or get_settings()
    return _engine_for(config.database_url)


def get_session_factory(settings: Settings | None = None) -> sessionmaker[Session]:
    return cast(sessionmaker[Session], sessionmaker(bind=get_engine(settings), autoflush=False, expire_on_commit=False))


def get_db(request: Request) -> Generator[Session, None, None]:
    factory = getattr(request.app.state, "db_session_factory", None) or get_session_factory()
    session = factory()
    try:
        yield session
    finally:
        session.close()
