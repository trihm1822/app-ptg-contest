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

        _engine = create_async_engine(
            url,
            echo=settings.DATABASE_ECHO,
            future=True,
            pool_pre_ping=True if "sqlite" not in url else False,
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
