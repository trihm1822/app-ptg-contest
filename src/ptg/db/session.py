"""Async database session and engine lifecycle management."""

from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from ptg.config import get_settings

_engine: Optional[AsyncEngine] = None
_sessionmaker: Optional[async_sessionmaker[AsyncSession]] = None


def get_async_engine(database_url: Optional[str] = None) -> AsyncEngine:
    """Initialize or return singleton AsyncEngine."""
    global _engine
    if _engine is None or database_url is not None:
        settings = get_settings()
        url = database_url or settings.DATABASE_URL
        # Ensure SQLite async dialect if sqlite url passed
        if url.startswith("sqlite://") and not url.startswith("sqlite+aiosqlite://"):
            url = url.replace("sqlite://", "sqlite+aiosqlite://")

        # SQLite optimization: use NullPool for file databases to prevent locks, StaticPool for in-memory
        engine_kwargs = {
            "echo": settings.DATABASE_ECHO,
            "future": True,
        }
        if "sqlite" in url:
            if ":memory:" in url:
                from sqlalchemy.pool import StaticPool
                engine_kwargs["poolclass"] = StaticPool
            else:
                from sqlalchemy.pool import NullPool
                engine_kwargs["poolclass"] = NullPool
        else:
            engine_kwargs["pool_pre_ping"] = True

        _engine = create_async_engine(
            url,
            **engine_kwargs,
        )
    return _engine


def get_async_sessionmaker(engine: Optional[AsyncEngine] = None) -> async_sessionmaker[AsyncSession]:
    """Initialize or return singleton async_sessionmaker."""
    global _sessionmaker
    target_engine = engine or get_async_engine()
    if _sessionmaker is None or engine is not None:
        _sessionmaker = async_sessionmaker(
            bind=target_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _sessionmaker


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency generator yielding an AsyncSession."""
    session_factory = get_async_sessionmaker()
    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
