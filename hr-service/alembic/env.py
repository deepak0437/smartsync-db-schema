"""
Alembic env.py for hr-service.

Supports:
- Offline mode (generate SQL without DB connection)
- Online mode (apply migrations to live database)
- Auto-detect schema changes from SQLAlchemy models
"""
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool, text

# ---------------------------------------------------------------------------
# Add project root to sys.path so models can be imported
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ---------------------------------------------------------------------------
# Import all models so Alembic can detect schema changes
# ---------------------------------------------------------------------------
from app.db.base import Base, metadata  # noqa: F401 — registers all models

# ---------------------------------------------------------------------------
# Alembic Config
# ---------------------------------------------------------------------------
config = context.config

# Override sqlalchemy.url from environment variable if set
hr_db_url = os.getenv("HR_DATABASE_URL", "").replace("+asyncpg", "")
if hr_db_url:
    config.set_main_option("sqlalchemy.url", hr_db_url)

# Setup logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate
target_metadata = metadata

# Include schemas in autogenerate
def include_object(object, name, type_, reflected, compare_to):
    """Only autogenerate for 'hr' schema objects."""
    if type_ == "table":
        return object.schema == "hr"
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
        version_table_schema="hr",
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
        # Ensure the hr schema exists before running migrations
        connection.execute(text("CREATE SCHEMA IF NOT EXISTS hr"))
        connection.commit()

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            include_object=include_object,
            version_table_schema="hr",
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
