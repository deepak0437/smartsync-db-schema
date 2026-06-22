"""
Alembic env.py for auth-service.

Supports:
- Offline mode (generate SQL without DB connection)
- Online mode (apply migrations to live database)
- Auto-detect schema changes from SQLAlchemy models
- Shared database configuration from etc/config/config.yaml
"""
import os
import sys
from pathlib import Path
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool, text

# ---------------------------------------------------------------------------
# Add project root to sys.path so models can be imported
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Add scripts directory to path for shared config loader
repo_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(repo_root))

# ---------------------------------------------------------------------------
# Import all models so Alembic can detect schema changes
# ---------------------------------------------------------------------------
from app.db.base import Base, metadata  # noqa: F401 — registers all models

# ---------------------------------------------------------------------------
# Alembic Config
# ---------------------------------------------------------------------------
config = context.config

# ---------------------------------------------------------------------------
# Load database URL from environment or shared config
# ---------------------------------------------------------------------------
def get_database_url():
    """
    Get database URL with priority:
    1. Environment variable AUTH_DATABASE_URL
    2. Shared config from etc/config/config.yaml
    3. Fallback to localhost
    """
    # Priority 1: Service-specific env var
    db_url = os.getenv("AUTH_DATABASE_URL")
    if db_url:
        return db_url.replace("+asyncpg", "")
    
    # Priority 2: Load from shared config
    try:
        from scripts.lib.config_loader import load_database_url
        db_url = load_database_url()
        if db_url:
            return db_url.replace("+asyncpg", "")
    except (ImportError, FileNotFoundError):
        pass
    
    # Priority 3: Fallback for local development
    return "postgresql://smartsync:smartsync@localhost:5432/smartsync_dev"

db_url = get_database_url()
config.set_main_option("sqlalchemy.url", db_url)

# Setup logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate
target_metadata = metadata

# Include schemas in autogenerate
def include_object(object, name, type_, reflected, compare_to):
    """Only autogenerate for 'auth' schema objects."""
    if type_ == "table":
        return object.schema == "auth"
    return True


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    Generates SQL script without a live DB connection.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
        include_object=include_object,
        version_table_schema="auth",
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.
    Connects to the database and applies migrations.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # Ensure the auth schema exists before running migrations
        connection.execute(text("CREATE SCHEMA IF NOT EXISTS auth"))
        connection.commit()

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            include_object=include_object,
            version_table_schema="auth",
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
