"""
Transport Service — Database session configuration.
Uses async SQLAlchemy 2.x with asyncpg driver.
"""
import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# ---------------------------------------------------------------------------
# Database URL
# ---------------------------------------------------------------------------
# Format: postgresql+asyncpg://user:password@host:port/dbname
# Set via environment variable in production.
# Default points to local dev database.
DATABASE_URL: str = os.getenv(
    "TRANSPORT_DATABASE_URL",
    "postgresql+asyncpg://smartsync:smartsync@localhost:5432/smartsync_transport",
)

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
engine = create_async_engine(
    DATABASE_URL,
    echo=os.getenv("DB_ECHO", "false").lower() == "true",   # SQL logging
    pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
    max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),
    pool_pre_ping=True,         # Verify connection health before use
    pool_recycle=3600,          # Recycle connections every 1 hour
    connect_args={
        "server_settings": {
            "search_path": "transport",          # Default schema for transport service
            "application_name": "smartsync-transport-service",
        }
    },
)

# ---------------------------------------------------------------------------
# Session Factory
# ---------------------------------------------------------------------------
AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,     # Avoid lazy-load after commit
    autocommit=False,
    autoflush=False,
)


# ---------------------------------------------------------------------------
# Dependency / Context Manager
# ---------------------------------------------------------------------------
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI / dependency-injection compatible async session generator.

    Usage:
        async with get_db() as session:
            result = await session.execute(...)

    Or as a FastAPI dependency:
        db: AsyncSession = Depends(get_db)
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Create all tables defined in metadata (development/test use only).
    In production, use Alembic migrations.
    """
    from .base_all import metadata  # noqa: F401 — ensure all models are imported
    from .base import Base
    async with engine.begin() as conn:
        # Ensure the 'transport' schema exists
        await conn.execute(__import__("sqlalchemy").text("CREATE SCHEMA IF NOT EXISTS transport"))
        await conn.run_sync(Base.metadata.create_all)
