# SmartSync DB Schema — Architecture Guide

> This document explains the complete database schema architecture for the SmartSync microservices platform using **FastAPI + SQLAlchemy + Alembic + PostgreSQL**.

---

## 1. Why This Approach?

In a microservices architecture:
- Each service owns its **own business logic**
- But all services share a **single PostgreSQL DB** with **separate schemas** (like namespaces)
- ORM models and migrations live in **one central repo** (`smartsync-db-schema`)
- Each service **installs this repo as a Python package** and imports only what it needs

---

## 2. Repository Structure




```
smartsync-db-schema/
│
├── models/                          ← SQLAlchemy ORM model classes
│   ├── __init__.py
│   ├── platform/
│   │   ├── __init__.py
│   │   └── tenant.py                ← Tenant, Subscription models
│   ├── academic/
│   │   ├── __init__.py
│   │   ├── student.py               ← Student model
│   │   └── course.py                ← Course model
│   ├── auth/
│   │   ├── __init__.py
│   │   └── user.py                  ← User, Role models
│   └── admin/
│       ├── __init__.py
│       └── audit_log.py             ← AuditLog model
│
├── schemas/                         ← Alembic migration configs (one per PG schema)
│   ├── platform/
│   │   ├── alembic.ini              ← Alembic config for platform schema
│   │   └── migrations/
│   │       ├── env.py               ← Tells Alembic which models to watch
│   │       └── versions/            ← Auto-generated migration files
│   ├── academic/
│   │   ├── alembic.ini
│   │   └── migrations/
│   │       ├── env.py
│   │       └── versions/
│   ├── auth/
│   │   ├── alembic.ini
│   │   └── migrations/
│   │       ├── env.py
│   │       └── versions/
│   └── admin/
│       ├── alembic.ini
│       └── migrations/
│           ├── env.py
│           └── versions/
│
├── base.py                          ← Shared SQLAlchemy DeclarativeBase
├── db.py                            ← Shared DB engine/session factory
├── pyproject.toml                   ← Package definition (how services install this)
└── README.md
```

> **Key Rule:** `models/` contains only ORM class definitions. `schemas/` contains only Alembic migration config. No mixing.

---

## 3. What Each File Contains

### `base.py` — Shared Base Class
```python
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
```
All models inherit from this single `Base`. Alembic uses `Base.metadata` to detect changes.

---

### `db.py` — Shared DB Engine
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL")  # each service sets this env var

engine = create_async_engine(DATABASE_URL, pool_size=20, max_overflow=10)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
```

---

### `models/platform/tenant.py` — Example Model
```python
import uuid
from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from smartsync_db_schema.base import Base

class Tenant(Base):
    __tablename__ = "tenants"
    __table_args__ = {"schema": "platform"}   # ← maps to platform schema in PostgreSQL

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(nullable=False)  # for multi-tenancy RLS
```

---

### `models/auth/user.py` — Example Model
```python
import uuid
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from smartsync_db_schema.base import Base

class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "auth"}   # ← maps to auth schema in PostgreSQL

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
```

---

### `models/academic/student.py` — Example Model
```python
import uuid
from sqlalchemy import String, Date
from sqlalchemy.orm import Mapped, mapped_column
from smartsync_db_schema.base import Base

class Student(Base):
    __tablename__ = "students"
    __table_args__ = {"schema": "academic"}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    enrollment_date: Mapped[Date] = mapped_column(nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
```

---

## 4. Alembic Setup — How Migrations Know What to Watch

Each schema folder has its own independent Alembic setup.

### `schemas/platform/migrations/env.py`
```python
from alembic import context
from sqlalchemy import engine_from_config, pool

# Import ONLY platform models — Alembic watches only these
from smartsync_db_schema.models.platform.tenant import Tenant
from smartsync_db_schema.base import Base

target_metadata = Base.metadata   # Alembic diffs this against actual DB

def run_migrations_online():
    connectable = engine_from_config(
        context.config.get_section(context.config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,           # ← required for multi-schema support
            version_table_schema="platform" # ← stores alembic_version in platform schema
        )
        with context.begin_transaction():
            context.run_migrations()
```

> **This is how Alembic knows what to migrate** — it only imports `platform` models in the platform `env.py`. So it only generates migrations for platform tables. Academic env.py imports academic models only, and so on.

---

### `schemas/platform/alembic.ini`
```ini
[alembic]
script_location = migrations
sqlalchemy.url = postgresql+asyncpg://user:password@localhost/smartsync_db
```

---

## 5. Running Migrations

Each schema is migrated **independently**:

```bash
# Migrate only platform schema
cd schemas/platform
alembic upgrade head

# Migrate only academic schema
cd schemas/academic
alembic upgrade head

# Migrate only auth schema
cd schemas/auth
alembic upgrade head
```

To generate a new migration after model changes:
```bash
cd schemas/platform
alembic revision --autogenerate -m "add_slug_to_tenants"
alembic upgrade head
```

Alembic compares `Base.metadata` (your model definition) against the actual DB and generates the diff automatically.

---

## 6. Publishing as a Python Package

### `pyproject.toml`
```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "smartsync-db-schema"
version = "1.0.0"
description = "Shared SQLAlchemy models for SmartSync microservices"
requires-python = ">=3.11"
dependencies = [
    "sqlalchemy>=2.0",
    "asyncpg>=0.29",
]

[tool.setuptools.packages.find]
where = ["."]
include = ["models*", "base*", "db*"]
```

Push this repo to your internal Git (GitHub/GitLab). Services install it directly from Git.

---

## 7. Installing in Each Microservice

```bash
# Install from internal Git repo
pip install git+https://github.com/your-org/smartsync-db-schema.git@v1.0.0
```

Or pin it in each service's `requirements.txt`:
```
smartsync-db-schema @ git+https://github.com/your-org/smartsync-db-schema.git@v1.0.0
```

---

## 8. How Each Service Uses the Package

### Platform Service — ORM for simple ops
```python
from smartsync_db_schema.models.platform.tenant import Tenant
from smartsync_db_schema.db import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
import uuid

# Simple CRUD using ORM
async def get_tenant(tenant_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await db.get(Tenant, tenant_id)

async def create_tenant(name: str, slug: str, db: AsyncSession = Depends(get_db)):
    tenant = Tenant(name=name, slug=slug, tenant_id=uuid.uuid4())
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    return tenant
```

### Platform Service — Raw SQL for complex ops
```python
from sqlalchemy import text

async def get_tenant_usage_report(db: AsyncSession):
    result = await db.execute(text("""
        SELECT
            t.id,
            t.name,
            COUNT(DISTINCT s.id) as student_count,
            COUNT(DISTINCT c.id) as course_count
        FROM platform.tenants t
        LEFT JOIN academic.students s ON s.tenant_id = t.id
        LEFT JOIN academic.courses c ON c.tenant_id = t.id
        GROUP BY t.id, t.name
        ORDER BY student_count DESC
    """))
    return result.fetchall()
```

---

## 9. Service Boundaries — Who Can Use What

```
platform-service    → imports: models/platform/
academic-service    → imports: models/academic/
auth-service        → imports: models/auth/
admin-service       → imports: models/admin/, models/platform/  (read-only audit)
```

> **Rule: A service must NEVER import models from another service's domain to write data.
> It must call that service's API instead.**

### Wrong ❌
```python
# Inside platform-service
from smartsync_db_schema.models.auth.user import User

# Platform directly creating a user in auth schema — NEVER do this
user = User(email="john@example.com", ...)
db.add(user)
```

### Correct ✅
```python
# Inside platform-service
import httpx

async def create_user_in_auth_service(user_data: dict):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://auth-service/api/v1/users",
            json=user_data,
            headers={"Authorization": f"Bearer {internal_token}"}
        )
    return response.json()
```

---

## 10. What To Do When You Update a Table

### Scenario: Adding a new column `phone_number` to `platform.tenants`

**Step 1 — Update the model in `smartsync-db-schema` repo**
```python
# models/platform/tenant.py
class Tenant(Base):
    ...
    phone_number: Mapped[str] = mapped_column(String(20), nullable=True)  # ← added
```

**Step 2 — Generate and run migration**
```bash
cd schemas/platform
alembic revision --autogenerate -m "add_phone_number_to_tenants"
alembic upgrade head
```

**Step 3 — Bump version in `pyproject.toml`**
```toml
version = "1.1.0"   # was 1.0.0
```

**Step 4 — Push and tag the release**
```bash
git commit -am "feat: add phone_number to tenants"
git tag v1.1.0
git push origin main --tags
```

**Step 5 — Upgrade only affected services**
```bash
# Only in platform-service and admin-service (if they use Tenant)
pip install git+https://github.com/your-org/smartsync-db-schema.git@v1.1.0
```

> Academic service and auth service do **not** need to upgrade — they don't use `Tenant`.

---

## 11. Safe vs Risky Column Changes

| Change Type | Risk | Safe Strategy |
|---|---|---|
| Add nullable column | ✅ Safe | Direct migration |
| Add non-null column | ⚠️ Breaking | Add as nullable first → backfill → add constraint |
| Rename column | ❌ Breaking | Add new col → backfill data → remove old col (3 steps) |
| Drop column | ❌ Breaking | Remove from model first → deploy → then drop from DB |
| Change column type | ❌ Breaking | Add new col with new type → migrate data → drop old |

---

## 12. Multi-Tenancy with Row Level Security (RLS)

Every table has a `tenant_id` column. Enforce isolation at DB level:

```sql
-- Run once per table in PostgreSQL
ALTER TABLE academic.students ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON academic.students
    USING (tenant_id = current_setting('app.tenant_id')::uuid);
```

Set tenant context per request in FastAPI middleware:
```python
@app.middleware("http")
async def set_tenant_context(request: Request, call_next):
    tenant_id = request.headers.get("X-Tenant-ID")
    async with AsyncSessionLocal() as db:
        await db.execute(text(f"SET app.tenant_id = '{tenant_id}'"))
    return await call_next(request)
```

---

## 13. CI/CD Flow

```
Developer updates model in smartsync-db-schema
            │
            ▼
PR merged → CI pipeline runs:
    alembic upgrade head  (against staging DB)
            │
            ▼
Version bumped → Git tag pushed
            │
            ▼
Affected services update package version in their own PR
            │
            ▼
Service deployed AFTER migration runs
(DB always updated before new code goes live)
```

---

## 14. Full Architecture Summary

```
smartsync-db-schema (single repo)
├── models/         ← ORM classes — imported by all services
└── schemas/        ← Alembic configs — migrations run here only
        │
        ▼
  PostgreSQL (single DB)
  ├── platform schema   (tenants, subscriptions)
  ├── academic schema   (students, courses, grades)
  ├── auth schema       (users, roles, permissions)
  └── admin schema      (audit logs, configs)
        ▲
        │ each service installs smartsync-db-schema package
        │
  ┌─────────────────────────────────┐
  │  platform-service  (FastAPI)    │  imports models/platform/
  │  academic-service  (FastAPI)    │  imports models/academic/
  │  auth-service      (FastAPI)    │  imports models/auth/
  │  admin-service     (FastAPI)    │  imports models/admin/
  └─────────────────────────────────┘
        │
        │ services talk to each other via HTTP API only
        │ never via direct DB cross-schema writes
```

---

## 15. Quick Reference

| Question | Answer |
|---|---|
| Where do ORM models live? | `smartsync-db-schema/models/` only |
| Where do migrations run? | `smartsync-db-schema/schemas/<name>/migrations/` |
| Do services define their own models? | No — they import from shared package |
| Who runs migrations? | `smartsync-db-schema` CI/CD pipeline |
| When do services upgrade package? | After migration is run and version is bumped |
| Can service A write to service B's schema via ORM? | Never — call service B's API |
| ORM or SQL? | ORM for CRUD, Raw SQL for complex joins/reports |
| How is tenant data isolated? | `tenant_id` on every table + PostgreSQL RLS |


#  etc/config -> config.yaml - db creds 

# 1 - created_at, updated_at, id
# 2 - deleted_at, is_deleted, 
# 3 - created_by, updated_by, deleted_by

