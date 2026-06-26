import os
import yaml
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

def get_db_url_from_config() -> str:
    # Look for config.yaml in the etc directory
    config_path = os.path.join(os.path.dirname(__file__), "etc", "config.yaml")
    
    with open(config_path, "r") as file:
        config = yaml.safe_load(file)
        
    db_config = config.get("database", {})
    user = db_config.get("user", "user")
    password = db_config.get("password", "password")
    host = db_config.get("host", "localhost")
    db_name = db_config.get("name", "smartsync_db")
    
    return f"postgresql+asyncpg://{user}:{password}@{host}/{db_name}"

DATABASE_URL = get_db_url_from_config()

engine = create_async_engine(DATABASE_URL, pool_size=20, max_overflow=10)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session