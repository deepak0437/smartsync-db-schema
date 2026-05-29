#!/usr/bin/env bash
# Generates boilerplate for all remaining services
set -e

SERVICES=(
  "platform-service:platform"
  "administration-service:administration"
  "management-service:management"
  "finance-service:finance"
  "hr-service:hr"
  "hostel-service:hostel"
  "transport-service:transport"
  "notification-service:notification"
  "library-service:library"
  "security-service:security"
  "communication-service:communication"
  "lms-service:lms"
  "analytics-service:analytics"
  "media-service:media"
)

for entry in "${SERVICES[@]}"; do
  SERVICE="${entry%%:*}"
  SCHEMA="${entry##*:}"
  DB_NAME="smartsync_${SCHEMA}"
  
  echo "==> Setting up $SERVICE ($SCHEMA schema)"

  # __init__.py for models
  cat > "$SERVICE/app/models/__init__.py" << EOF
"""$SERVICE models."""
from .models import Base
__all__ = ["Base"]
EOF

  # db/__init__.py
  touch "$SERVICE/app/db/__init__.py"
  touch "$SERVICE/app/__init__.py"

  # db/base.py
  cat > "$SERVICE/app/db/base.py" << EOF
"""Import all models for Alembic autogenerate."""
from app.models.models import Base  # noqa: F401
metadata = Base.metadata
__all__ = ["Base", "metadata"]
EOF

  # db/session.py
  cat > "$SERVICE/app/db/session.py" << EOF
"""DB session for $SERVICE."""
import os
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
import sqlalchemy

DATABASE_URL = os.getenv("${SCHEMA^^}_DATABASE_URL", "postgresql+asyncpg://smartsync:smartsync@localhost:5432/$DB_NAME")
engine = create_async_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=3600)
AsyncSessionFactory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

async def init_db():
    from .base import Base
    async with engine.begin() as conn:
        await conn.execute(sqlalchemy.text("CREATE SCHEMA IF NOT EXISTS $SCHEMA"))
        await conn.run_sync(Base.metadata.create_all)
EOF

  # alembic.ini
  cat > "$SERVICE/alembic.ini" << EOF
[alembic]
script_location = alembic
file_template = %%(year)d%%(month).2d%%(day).2d_%%(rev)s_%%(slug)s
timezone = UTC
sqlalchemy.url = postgresql://smartsync:smartsync@localhost:5432/$DB_NAME

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %%(levelname)-5.5s [%%(name)s] %%(message)s
datefmt = %%H:%%M:%%S
EOF

  # alembic/env.py
  cat > "$SERVICE/alembic/env.py" << PYEOF
"""Alembic env.py for $SERVICE."""
import os
import sys
from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config, pool, text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.db.base import Base, metadata  # noqa: F401

config = context.config
db_url = os.getenv("${SCHEMA^^}_DATABASE_URL", "").replace("+asyncpg", "")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = metadata

def include_object(object, name, type_, reflected, compare_to):
    if type_ == "table":
        return object.schema == "$SCHEMA"
    return True

def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True,
                      dialect_opts={"paramstyle": "named"}, include_schemas=True,
                      include_object=include_object, version_table_schema="$SCHEMA")
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = engine_from_config(config.get_section(config.config_ini_section, {}),
                                     prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        connection.execute(text("CREATE SCHEMA IF NOT EXISTS $SCHEMA"))
        connection.commit()
        context.configure(connection=connection, target_metadata=target_metadata, include_schemas=True,
                          include_object=include_object, version_table_schema="$SCHEMA")
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
PYEOF

  # alembic/script.py.mako
  cat > "$SERVICE/alembic/script.py.mako" << 'MAKO'
# \${message}
Revision ID: \${up_revision}
Revises: \${down_revision | comma,n}
Create Date: \${create_date}

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
\${imports if imports else ""}

revision: str = \${repr(up_revision)}
down_revision: Union[str, None] = \${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = \${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = \${repr(depends_on)}

def upgrade() -> None:
    \${upgrades if upgrades else "pass"}

def downgrade() -> None:
    \${downgrades if downgrades else "pass"}
MAKO

  # requirements.txt
  cat > "$SERVICE/requirements.txt" << EOF
sqlalchemy==2.0.30
alembic==1.13.1
asyncpg==0.29.0
psycopg2-binary==2.9.9
python-dotenv==1.0.1
EOF

  echo "    ✓ Done"
done

echo ""
echo "✅ All service boilerplate generated!"
