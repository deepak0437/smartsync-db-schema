# SmartSync.ai — Database Architecture Guide
## Multi-Service Alembic Migration Strategy

---

## 1. Why a `schemas/` folder?

The `schemas/` directory contains **raw SQL DDL scripts** — pure PostgreSQL `CREATE TABLE`, `CREATE INDEX`, `CREATE POLICY` statements — for every service.

### Purpose

| Folder | Purpose |
|---|---|
| `schemas/01-auth-service/` | Raw SQL for the `auth` PostgreSQL schema |
| `schemas/02-academic-service/` | Raw SQL for the `academic` PostgreSQL schema |
| `schemas/03-platform-service/` | Raw SQL for the `platform` schema |
| *(and so on)* | |

### When to use `schemas/` SQL files vs Alembic migrations

| Scenario | Use |
|---|---|
| **Production** — apply changes safely with rollback | **Alembic** (always) |
| **CI/CD** — spin up a fresh test database quickly | `schemas/` raw SQL |
| **Dev onboarding** — create all tables from scratch in one shot | `schemas/` raw SQL |
| **DBA review** — share exact DDL for review without running Python | `schemas/` raw SQL |
| **Kubernetes** — init containers that seed a new Postgres instance | `schemas/` raw SQL |

In short: **`schemas/` is the human-readable reference DDL; Alembic is the automated migration engine.**

---

## 2. Database Architecture — One DB, Many Schemas

SmartSync uses a **single PostgreSQL database instance** with **schema-based isolation** for each microservice.

```
PostgreSQL Instance: smartsync_main
│
├── Schema: auth            ← Auth Service owns all tables here
│   ├── tenants
│   ├── users
│   ├── roles
│   ├── permissions
│   ├── user_sessions
│   └── audit_logs
│
├── Schema: academic        ← Academic Service owns all tables here
│   ├── academic_years
│   ├── classes
│   ├── sections
│   ├── subjects
│   ├── academic_profiles
│   ├── attendance_records
│   ├── homework
│   └── student_reviews
│
├── Schema: platform        ← Platform Service
│   ├── tenants (master)
│   └── subscriptions
│
├── Schema: finance         ← Finance Service
├── Schema: hr              ← HR Service
├── Schema: hostel          ← Hostel Service
├── Schema: transport       ← Transport Service
├── Schema: notification    ← Notification Service
├── Schema: library         ← Library Service
├── Schema: security        ← Security Service
├── Schema: communication   ← Communication Service
├── Schema: lms             ← LMS Service
├── Schema: analytics       ← Analytics Service
└── Schema: media           ← Media Service
```

### Why single DB with multiple schemas?

- **Data locality**: Cross-service joins (for reporting) are possible without network overhead.
- **Operational simplicity**: One PostgreSQL instance to backup, monitor, and maintain.
- **Isolation**: Each service has its own schema — services cannot accidentally read each other's tables.
- **Alembic independence**: Each service manages its own Alembic `alembic_version` table **within its own schema**.
- **RLS-ready**: PostgreSQL Row-Level Security policies apply per schema, enforcing tenant isolation.

---

## 3. How Alembic Knows Which Tables to Manage

Each service has its own `alembic/` directory with its own `env.py`.

The key trick is `include_object`:

```python
# In alembic/env.py of auth-service:
def include_object(object, name, type_, reflected, compare_to):
    """Only autogenerate for the 'auth' schema."""
    if type_ == "table":
        return object.schema == "auth"   # ← Only manage tables in 'auth' schema
    return True
```

This means when you run `alembic revision --autogenerate` inside `auth-service/`, Alembic will:
- ✅ Detect changes to `auth.users`, `auth.roles`, etc.
- ❌ Ignore `academic.classes`, `finance.fee_structures`, etc.

Each service's `alembic_version` table is also stored in its own schema:

```python
context.configure(
    ...
    version_table_schema="auth",  # ← alembic_version stored in auth schema
)
```

This means all 17 services can safely coexist in the same database without Alembic conflicts.

---

## 4. Environment Variables

Each service reads its database URL from an environment variable:

| Service | Environment Variable | Default |
|---|---|---|
| auth-service | `AUTH_DATABASE_URL` | `postgresql://smartsync:smartsync@localhost:5432/smartsync_auth` |
| academic-service | `ACADEMIC_DATABASE_URL` | `postgresql://smartsync:smartsync@localhost:5432/smartsync_academic` |
| platform-service | `PLATFORM_DATABASE_URL` | `postgresql://smartsync:smartsync@localhost:5432/smartsync_platform` |

> **Note**: For production, all services can point to the **same database** with different schemas:
> ```
> AUTH_DATABASE_URL=postgresql://smartsync:secret@prod-db:5432/smartsync_main
> ACADEMIC_DATABASE_URL=postgresql://smartsync:secret@prod-db:5432/smartsync_main
> ```

---

## 5. Step-by-Step: Setting Up the Database from Scratch

### Step 1 — Create PostgreSQL Database

```sql
-- Connect as postgres superuser
CREATE USER smartsync WITH PASSWORD 'smartsync';
CREATE DATABASE smartsync_main OWNER smartsync;
GRANT ALL PRIVILEGES ON DATABASE smartsync_main TO smartsync;

-- Connect to smartsync_main
\c smartsync_main

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
```

### Step 2 — Install Dependencies (per service)

```bash
cd auth-service
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Step 3 — Set Environment Variable

```bash
export AUTH_DATABASE_URL="postgresql://smartsync:smartsync@localhost:5432/smartsync_main"
```

---

## 6. Running Migrations — Per Service

### Auth Service

```bash
cd auth-service

# Set DB URL (or via .env)
export AUTH_DATABASE_URL="postgresql://smartsync:smartsync@localhost:5432/smartsync_main"

# Generate first migration (detects all models)
alembic revision --autogenerate -m "initial_auth_schema"

# Review the generated migration in alembic/versions/
cat alembic/versions/*.py

# Apply migration
alembic upgrade head

# Verify
alembic current
alembic history --verbose
```

### Academic Service

```bash
cd academic-service

export ACADEMIC_DATABASE_URL="postgresql://smartsync:smartsync@localhost:5432/smartsync_main"

alembic revision --autogenerate -m "initial_academic_schema"
alembic upgrade head
```

### Finance Service

```bash
cd finance-service

export FINANCE_DATABASE_URL="postgresql://smartsync:smartsync@localhost:5432/smartsync_main"

alembic revision --autogenerate -m "initial_finance_schema"
alembic upgrade head
```

### *(Repeat for each service)*

```bash
# Template for any service:
cd <service-name>
export <SCHEMA>_DATABASE_URL="postgresql://smartsync:smartsync@localhost:5432/smartsync_main"
alembic revision --autogenerate -m "initial_<schema>_schema"
alembic upgrade head
```

---

## 7. Alembic Commands Reference

| Command | What It Does |
|---|---|
| `alembic revision --autogenerate -m "message"` | Auto-detect model changes and generate migration file |
| `alembic upgrade head` | Apply all pending migrations |
| `alembic upgrade +1` | Apply one migration forward |
| `alembic downgrade -1` | Roll back one migration |
| `alembic downgrade base` | Roll back all migrations (drop all tables) |
| `alembic current` | Show current applied migration revision |
| `alembic history` | Show full migration history |
| `alembic show <rev_id>` | Show details of a specific revision |
| `alembic heads` | Show latest (head) revision |
| `alembic check` | Check if there are unapplied migrations |

---

## 8. Making Model Changes After Initial Migration

```bash
# 1. Edit your model file
# e.g., add a new column to auth-service/app/models/user.py

# 2. Generate a new migration
cd auth-service
alembic revision --autogenerate -m "add_profile_picture_url_to_users"

# 3. Review the migration (always review before applying!)
cat alembic/versions/<timestamp>_add_profile_picture_url_to_users.py

# 4. Apply the migration
alembic upgrade head
```

---

## 9. Migration Order (Dependencies)

Some schemas reference others (cross-service foreign keys are avoided — we use UUIDs as soft references). However, for initial setup, this order is recommended:

```
1. platform-service      (tenant master registry — everything else references tenant_id)
2. auth-service          (user accounts, roles — all services use user IDs)
3. academic-service      (academic structure — defines classes, sections, subjects)
4. administration-service
5. management-service
6. finance-service
7. hr-service
8. hostel-service
9. transport-service
10. notification-service
11. library-service
12. security-service
13. communication-service
14. lms-service
15. analytics-service
16. media-service
```

> **Why this order?**
> - `platform` defines tenant UUIDs that all others store as `tenant_id`
> - `auth` defines user UUIDs that all others store as `user_id` (soft references)
> - `academic` defines `class_id`, `section_id`, `subject_id` used by LMS, Finance, etc.
>
> Since there are **no hard foreign keys across schemas**, you can technically run them in any order. This order is for **logical clarity** only.

---

## 10. Using a `.env` File (Recommended)

Create a `.env` file at the root of each service:

```bash
# auth-service/.env
AUTH_DATABASE_URL=postgresql://smartsync:smartsync@localhost:5432/smartsync_main
DB_ECHO=false
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
```

Load it before running Alembic:

```bash
# Option 1: Export manually
set -a && source .env && set +a

# Option 2: Use python-dotenv (already in requirements.txt)
# Alembic will auto-load .env if you add this to env.py:
from dotenv import load_dotenv
load_dotenv()
```

---

## 11. Alembic in Kubernetes (Production)

In production Kubernetes, run migrations as an **init container** before the main service starts:

```yaml
# Example Kubernetes Deployment snippet
initContainers:
  - name: alembic-migrate
    image: smartsync/auth-service:latest
    command: ["alembic", "upgrade", "head"]
    workingDir: /app
    env:
      - name: AUTH_DATABASE_URL
        valueFrom:
          secretKeyRef:
            name: db-credentials
            key: auth-database-url
```

This ensures:
- Migrations run **before** the service starts accepting traffic
- Rollbacks are possible by deploying the previous image version
- Migration failures cause the pod to fail → alerts triggered

---

## 12. Generating Raw SQL DDL (for `schemas/` folder)

You can generate pure SQL DDL from Alembic without applying it:

```bash
cd auth-service

# Generate offline SQL to a file
alembic upgrade head --sql > ../schemas/01-auth-service/001_initial.sql

# Or for a specific revision range
alembic upgrade <base_rev>:<head_rev> --sql > ../schemas/01-auth-service/001_initial.sql
```

This produces the `schemas/` DDL files that can be used for:
- DBA review
- Documentation
- Emergency manual rollback
- CI database seeding

---

## 13. Quick Reference: Service → Schema → DB URL Variable

| Service | Schema | DB URL Env Var |
|---|---|---|
| auth-service | `auth` | `AUTH_DATABASE_URL` |
| academic-service | `academic` | `ACADEMIC_DATABASE_URL` |
| platform-service | `platform` | `PLATFORM_DATABASE_URL` |
| administration-service | `administration` | `ADMINISTRATION_DATABASE_URL` |
| management-service | `management` | `MANAGEMENT_DATABASE_URL` |
| finance-service | `finance` | `FINANCE_DATABASE_URL` |
| hr-service | `hr` | `HR_DATABASE_URL` |
| hostel-service | `hostel` | `HOSTEL_DATABASE_URL` |
| transport-service | `transport` | `TRANSPORT_DATABASE_URL` |
| notification-service | `notification` | `NOTIFICATION_DATABASE_URL` |
| library-service | `library` | `LIBRARY_DATABASE_URL` |
| security-service | `security` | `SECURITY_DATABASE_URL` |
| communication-service | `communication` | `COMMUNICATION_DATABASE_URL` |
| lms-service | `lms` | `LMS_DATABASE_URL` |
| analytics-service | `analytics` | `ANALYTICS_DATABASE_URL` |
| media-service | `media` | `MEDIA_DATABASE_URL` |

> All environment variables accept the same format:
> ```
> postgresql://username:password@host:port/database_name
> ```
> In production, all 16 services can point to the **same** database name with their respective schema isolation handled by Alembic's `include_object` filter.

cd auth-service
export AUTH_DATABASE_URL="postgresql://smartsync:smartsync@localhost:5432/smartsync_main"
alembic revision --autogenerate -m "initial_auth_schema"
alembic upgrade head


cd academic-service
export ACADEMIC_DATABASE_URL="postgresql://smartsync:smartsync@localhost:5432/smartsync_main"
alembic revision --autogenerate -m "initial_academic_schema"
alembic upgrade head
