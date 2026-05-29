"""
Academic Service — Database session configuration.
"""
import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

DATABASE_URL: str = os.getenv(
    "ACADEMIC_DATABASE_URL",
    "postgresql+asyncpg://smartsync:smartsync@localhost:5432/smartsync_academic",
)

engine = create_async_engine(
    DATABASE_URL,
    echo=os.getenv("DB_ECHO", "false").lower() == "true",
    pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
    max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),
    pool_pre_ping=True,
    pool_recycle=3600,
    connect_args={
        "server_settings": {
            "search_path": "academic",
            "application_name": "smartsync-academic-service",
        }
    },
)

AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Async session dependency for FastAPI/dependency injection."""
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
    """Create all tables (dev/test only — use Alembic in production)."""
    from .base import Base
    import sqlalchemy
    async with engine.begin() as conn:
        await conn.execute(sqlalchemy.text("CREATE SCHEMA IF NOT EXISTS academic"))
        await conn.run_sync(Base.metadata.create_all)
