import asyncio
import os
import sys
import yaml
from logging.config import fileConfig

from sqlalchemy import pool, text
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# 1. Inject the workspace root into sys.path to allow imports from base and models
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from smartsync_db.base import Base
Base.metadata.schema = "platform"
import smartsync_db.models.platform  # Ensure all platform models are imported and registered on Base.metadata

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 2. Dynamically load connection settings from etc/config/config.yaml
config_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "etc", "config", "config.yaml")
)
try:
    with open(config_path, "r") as f:
        db_cfg = yaml.safe_load(f)["database"]
    
    # Build standard asyncpg URL: postgresql+asyncpg://user:pass@host:port/dbname
    db_url = f"postgresql+asyncpg://{db_cfg['username']}:{db_cfg['password']}@{db_cfg['host']}:{db_cfg['port']}/{db_cfg['name']}"
    config.set_main_option("sqlalchemy.url", db_url)
except Exception as e:
    sys.stderr.write(f"Warning: Failed to load database config from {config_path}: {e}\n")

# 3. Set target metadata default schema to 'platform' to scope all tables
Base.metadata.schema = "platform"
target_metadata = Base.metadata


def include_object(object, name, type_, reflected, compare_to):
    """Filters objects to only include those in the 'platform' schema."""
    if type_ == "table":
        return object.schema == "platform"
    elif type_ == "schema":
        return name == "platform"
    return True


def process_revision_directives(context, revision, directives):
    """Hooks into revision generation to set sequential numeric revision IDs (01, 02, etc.)."""
    # if getattr(context.config.cmd_opts, "autogenerate", False) or getattr(context.config.cmd_opts, "message", None):
    if directives:
        if directives:
            script = directives[0]
            script_directory = context.script
            heads = script_directory.get_heads()
            
            if not heads:
                next_num = 1
            else:
                max_num = 0
                for r in script_directory.walk_revisions():
                    try:
                        val = int(r.revision)
                        if val > max_num:
                            max_num = val
                    except ValueError:
                        pass
                next_num = max_num + 1
            
            # Pad revision ID with 0 to match sequential structure (e.g. 01, 02, ..., 10, ...)
            script.rev_id = f"{next_num:02d}"


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DB API to be available.

    Calls to context.execute() here emit the relation string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
        version_table_schema="platform",
        process_revision_directives=process_revision_directives,
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,
        version_table_schema="platform",
        process_revision_directives=process_revision_directives,
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        # Create platform schema if it doesn't exist
        await connection.execute(text("CREATE SCHEMA IF NOT EXISTS platform"))
        await connection.commit()
        
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    """
    connectable = config.attributes.get("connection", None)

    if connectable is not None:
        do_run_migrations(connectable)
    else:
        asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
