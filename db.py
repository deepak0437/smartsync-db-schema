from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "fake_url")  # each service sets this env var

engine = create_async_engine(DATABASE_URL, pool_size=20, max_overflow=10)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session