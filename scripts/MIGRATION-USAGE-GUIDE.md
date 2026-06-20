# SmartSync Migration Manager - Usage Guide

Complete guide for using the unified migration system across all SmartSync microservices.

---

## 📋 Table of Contents

1. [Setup](#setup)
2. [Quick Start](#quick-start)
3. [Interactive Mode](#interactive-mode)
4. [Command Line Mode](#command-line-mode)
5. [Common Operations](#common-operations)
6. [All Commands Reference](#all-commands-reference)
7. [Troubleshooting](#troubleshooting)

---

## 🚀 Setup

### 1. Install Dependencies

```bash
# Navigate to scripts directory
cd scripts

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Configure Database

Edit `etc/config/config.yaml` with your database credentials:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: smartsync-db-schema-config
data:
  app-config.yaml: |
    DB_HOST: your-database-host
    DB_PORT: 5432
    DB_NAME: postgres
    DB_USER: your-username
    DB_PASSWORD: your-password
```

**OR** use environment variables:

```bash
export DB_HOST=your-database-host
export DB_PORT=5432
export DB_NAME=postgres
export DB_USER=your-username
export DB_PASSWORD=your-password
```

### 3. Verify Setup

```bash
# Test configuration loading
python scripts/lib/config_loader.py

# Test service discovery
python scripts/lib/service_registry.py

# Check migration status
python scripts/migrate.py --service all --operation current
```

---

## ⚡ Quick Start

### Interactive Mode (Recommended for Beginners)

```bash
python scripts/migrate.py
```

Follow the on-screen prompts to select operation and services.

### Command Line Mode (For CI/CD and Scripts)

```bash
# Upgrade all services to latest
python scripts/migrate.py --service all --operation upgrade --args head

# Create migration for auth-service
python scripts/migrate.py --service auth --operation revision \
  --args "--autogenerate" "-m" "add_user_fields"

# Check current status
python scripts/migrate.py --service all --operation current
```

---

## 🎮 Interactive Mode

### Starting Interactive Mode

```bash
python scripts/migrate.py
```

### Example Session

```
======================================================================
            SmartSync Database Migration Manager
======================================================================

Select Operation:
  1. Apply pending migrations           (alembic upgrade)
  2. Revert migrations                  (alembic downgrade)
  3. Create new migration               (alembic revision)
  4. Show current revision              (alembic current)
  5. Show migration history             (alembic history)
  6. Show all head revisions            (alembic heads)
  7. Show specific revision             (alembic show)
  8. Mark revision without executing    (alembic stamp)
  9. Exit

Operation [1-9]: 1

======================================================================
Operation: upgrade
======================================================================

Select Service(s):
   0. All services (16)
   1. auth-service                (auth schema)
   2. platform-service            (platform schema)
   3. academic-service            (academic schema)
   ...

Service(s) [0-16, comma-separated]: 1

Upgrade target:
  1. head (latest)
  2. +1 (next revision)
  3. Specific revision ID
Target [1-3]: 1

======================================================================
Confirmation
======================================================================
Operation:  alembic upgrade head
Services:   1 service(s)
            • auth-service (auth schema)
Database:   postgres@localhost:5432/smartsync_dev

Proceed? [y/N]: y

======================================================================
Executing: alembic upgrade head
======================================================================

[1/1] auth-service          ✓ SUCCESS (2.1s)

============================================================
Migration Summary
============================================================
Total services: 1
Succeeded:      1
Failed:         0
Total time:     2.1s
============================================================
```

---

## 💻 Command Line Mode

### Basic Syntax

```bash
python scripts/migrate.py \
  --service <SERVICE_NAME> \
  --operation <OPERATION> \
  --args <ARG1> <ARG2> ...
```

### Service Selection Options

| Option | Description | Example |
|--------|-------------|---------|
| `all` | All 16 services | `--service all` |
| Single service | Specific service | `--service auth` |
| Multiple services | Comma-separated | `--service auth,platform,academic` |

**Note**: You can use short name (`auth`) or full name (`auth-service`).

### Available Operations

| Operation | Description |
|-----------|-------------|
| `upgrade` | Apply pending migrations |
| `downgrade` | Revert migrations |
| `revision` | Create new migration |
| `current` | Show current revision |
| `history` | Show migration history |
| `heads` | Show all head revisions |
| `show` | Show specific revision details |
| `stamp` | Mark revision without executing |

---

## 🎯 Common Operations

### 1. Check Migration Status

**Check all services:**
```bash
python scripts/migrate.py --service all --operation current
```

**Check specific service:**
```bash
python scripts/migrate.py --service auth --operation current
```

**Expected Output:**
```
Executing: alembic current
Services: 1

[1/1] auth-service          ✓ SUCCESS (0.3s)

============================================================
Migration Summary
============================================================
Total services: 1
Succeeded:      1
Failed:         0
Total time:     0.3s
============================================================
```

---

### 2. Apply Pending Migrations

**Upgrade all services to latest:**
```bash
python scripts/migrate.py --service all --operation upgrade --args head
```

**Upgrade specific service:**
```bash
python scripts/migrate.py --service auth --operation upgrade --args head
```

**Upgrade to next revision only (+1):**
```bash
python scripts/migrate.py --service auth --operation upgrade --args "+1"
```

**Upgrade to specific revision:**
```bash
python scripts/migrate.py --service auth --operation upgrade --args "abc123def456"
```

---

### 3. Create New Migration

**Auto-generate from model changes:**
```bash
python scripts/migrate.py --service auth --operation revision \
  --args "--autogenerate" "-m" "add_user_otp_fields"
```

**Create empty migration template:**
```bash
python scripts/migrate.py --service auth --operation revision \
  --args "-m" "custom_data_migration"
```

**Expected Output:**
```
Executing: alembic revision --autogenerate -m add_user_otp_fields
Services: 1

[1/1] auth-service          ✓ SUCCESS (1.2s)
        Output: Generating migration file...
                auth-service/alembic/versions/20240115_abc123_add_user_otp_fields.py

============================================================
Migration Summary
============================================================
Total services: 1
Succeeded:      1
Failed:         0
Total time:     1.2s
============================================================
```

**Next Steps:**
1. Review generated migration file
2. Test migration: `alembic upgrade head` (in service directory)
3. Commit migration to git

---

### 4. Revert Migrations

**Downgrade one step:**
```bash
python scripts/migrate.py --service auth --operation downgrade --args "-1"
```

**Downgrade to specific revision:**
```bash
python scripts/migrate.py --service auth --operation downgrade --args "abc123def456"
```

**⚠️ Downgrade all (DANGEROUS):**
```bash
python scripts/migrate.py --service auth --operation downgrade --args "base"
```

---

### 5. View Migration History

**Show all migrations:**
```bash
python scripts/migrate.py --service auth --operation history
```

**Show verbose history:**
```bash
python scripts/migrate.py --service auth --operation history --args "-v"
```

**Show specific range:**
```bash
python scripts/migrate.py --service auth --operation history --args "abc123:def456"
```

---

### 6. Multi-Service Operations

**Upgrade multiple specific services:**
```bash
python scripts/migrate.py --service auth,platform,academic \
  --operation upgrade --args head
```

**Check status of multiple services:**
```bash
python scripts/migrate.py --service auth,platform,finance \
  --operation current
```

**Continue on error (don't stop if one fails):**
```bash
python scripts/migrate.py --service all --operation upgrade --args head \
  --continue-on-error
```

---

### 7. Generate SQL Without Executing

**Generate SQL for upgrade:**
```bash
python scripts/migrate.py --service auth --operation upgrade \
  --args "--sql" "head"
```

**Generate SQL for downgrade:**
```bash
python scripts/migrate.py --service auth --operation downgrade \
  --args "--sql" "-1"
```

**Output:** SQL statements printed to stdout (useful for review or manual execution)

---

### 8. Stamp Revision (Mark Without Executing)

**Mark current state as specific revision:**
```bash
python scripts/migrate.py --service auth --operation stamp --args "head"
```

**Use cases:**
- Synchronizing migration state after manual database changes
- Initializing existing database with migration history
- Recovery from migration conflicts

---

## 📚 All Commands Reference

### Upgrade Operations

| Command | Description |
|---------|-------------|
| `--operation upgrade --args head` | Upgrade to latest revision |
| `--operation upgrade --args "+1"` | Upgrade one revision forward |
| `--operation upgrade --args "abc123"` | Upgrade to specific revision |
| `--operation upgrade --args "--sql" "head"` | Generate SQL without executing |

---

### Downgrade Operations

| Command | Description |
|---------|-------------|
| `--operation downgrade --args "-1"` | Downgrade one revision |
| `--operation downgrade --args "abc123"` | Downgrade to specific revision |
| `--operation downgrade --args "base"` | Downgrade all (remove all migrations) |
| `--operation downgrade --args "--sql" "-1"` | Generate SQL without executing |

---

### Revision Operations

| Command | Description |
|---------|-------------|
| `--operation revision --args "-m" "message"` | Create empty migration |
| `--operation revision --args "--autogenerate" "-m" "message"` | Auto-generate from models |
| `--operation revision --args "--sql"` | Create SQL-mode migration |
| `--operation revision --args "--head" "branch@base"` | Create branched migration |

---

### Information Operations

| Command | Description |
|---------|-------------|
| `--operation current` | Show current revision |
| `--operation heads` | Show all head revisions |
| `--operation history` | Show migration history |
| `--operation history --args "-v"` | Show verbose history |
| `--operation history --args "-r" "abc:def"` | Show specific range |
| `--operation show --args "abc123"` | Show revision details |

---

### Utility Operations

| Command | Description |
|---------|-------------|
| `--operation stamp --args "head"` | Mark as current revision |
| `--operation stamp --args "abc123"` | Mark as specific revision |
| `--operation merge --args "-m" "message"` | Merge multiple heads |

---

## 🔧 Advanced Usage

### Using Service-Specific Environment Variables

```bash
# Override database URL for specific service
export AUTH_DATABASE_URL="postgresql://user:pass@host:5432/db"

python scripts/migrate.py --service auth --operation current
```

### Using Global Database URL Override

```bash
# Override for all services
export DATABASE_URL="postgresql://user:pass@host:5432/db"

python scripts/migrate.py --service all --operation current
```

### Quiet Mode (Suppress Summary)

```bash
python scripts/migrate.py --service all --operation current --quiet
```

### Verbose Mode (Show Command Output)

```bash
python scripts/migrate.py --service auth --operation upgrade --args head --args "--verbose"
```

---

## 🛠️ Troubleshooting

### Problem: "Config file not found"

**Solution:**
```bash
# Check if config exists
ls -la etc/config/config.yaml

# If not, create from template
cp etc/config/config.yaml.example etc/config/config.yaml

# Edit with your credentials
vim etc/config/config.yaml
```

---

### Problem: "Service not found"

**Solution:**
```bash
# List all available services
python scripts/lib/service_registry.py

# Check service directory exists
ls -la auth-service/alembic/

# Verify service name (use short name)
python scripts/migrate.py --service auth  # ✓ Correct
python scripts/migrate.py --service auth-service  # ✓ Also correct
```

---

### Problem: "ModuleNotFoundError: No module named 'yaml'"

**Solution:**
```bash
# Install dependencies
cd scripts
pip install -r requirements.txt
```

---

### Problem: "Connection refused" or "Could not connect to database"

**Solution:**
```bash
# Test database connection manually
psql "postgresql://user:pass@host:5432/db" -c "\dn"

# Check credentials in config
cat etc/config/config.yaml | grep -A 5 DB_

# Verify environment variables
echo $DATABASE_URL
```

---

### Problem: "Revision not found" or "Can't locate revision"

**Solution:**
```bash
# Check current revision
python scripts/migrate.py --service auth --operation current

# Check available revisions
python scripts/migrate.py --service auth --operation heads

# View migration history
python scripts/migrate.py --service auth --operation history

# If database is out of sync, stamp current state
python scripts/migrate.py --service auth --operation stamp --args "head"
```

---

### Problem: Migration fails with "relation already exists"

**Solution:**
```bash
# Option 1: Stamp current state (if manually created tables)
python scripts/migrate.py --service auth --operation stamp --args "head"

# Option 2: Downgrade and re-apply
python scripts/migrate.py --service auth --operation downgrade --args "-1"
python scripts/migrate.py --service auth --operation upgrade --args "head"

# Option 3: Generate SQL and inspect conflict
python scripts/migrate.py --service auth --operation upgrade --args "--sql" "head"
```

---

### Problem: Multiple heads detected

**Solution:**
```bash
# View all heads
python scripts/migrate.py --service auth --operation heads

# Merge heads into single migration
python scripts/migrate.py --service auth --operation merge \
  --args "-m" "merge_branches"

# Apply merged migration
python scripts/migrate.py --service auth --operation upgrade --args "head"
```

---

## 📝 Best Practices

### 1. Always Review Auto-Generated Migrations

```bash
# Generate migration
python scripts/migrate.py --service auth --operation revision \
  --args "--autogenerate" "-m" "add_fields"

# Review generated file before applying
cat auth-service/alembic/versions/20240115_abc123_add_fields.py

# Test in development first
python scripts/migrate.py --service auth --operation upgrade --args "head"
```

### 2. Use Descriptive Migration Messages

✅ **Good:**
```bash
--args "-m" "add_user_otp_fields_and_indexes"
--args "-m" "create_subscription_upgrade_table"
--args "-m" "remove_deprecated_status_column"
```

❌ **Bad:**
```bash
--args "-m" "update"
--args "-m" "fix"
--args "-m" "changes"
```

### 3. Test Migrations in Development First

```bash
# 1. Generate migration
python scripts/migrate.py --service auth --operation revision \
  --args "--autogenerate" "-m" "add_new_table"

# 2. Apply in dev
python scripts/migrate.py --service auth --operation upgrade --args "head"

# 3. Test rollback
python scripts/migrate.py --service auth --operation downgrade --args "-1"

# 4. Re-apply
python scripts/migrate.py --service auth --operation upgrade --args "head"

# 5. Verify application works

# 6. Commit migration
git add auth-service/alembic/versions/
git commit -m "Add migration: add_new_table"
```

### 4. Use Version Control for Migrations

```bash
# Always commit migrations
git add */alembic/versions/*.py
git commit -m "Add migrations for user OTP fields"

# Never modify existing migrations that are in production
# Create new migration instead
```

### 5. Backup Before Major Changes

```bash
# Before running migrations in production
pg_dump -Fc dbname > backup_$(date +%Y%m%d_%H%M%S).dump

# Run migrations
python scripts/migrate.py --service all --operation upgrade --args "head"

# If something goes wrong, restore
pg_restore -d dbname backup_20240115_143000.dump
```

---

## 🎓 Workflow Examples

### Workflow 1: Adding New Table

```bash
# 1. Modify SQLAlchemy models
vim auth-service/app/models/session.py
# (Add new UserSession table)

# 2. Generate migration
python scripts/migrate.py --service auth --operation revision \
  --args "--autogenerate" "-m" "create_user_sessions_table"

# 3. Review generated migration
cat auth-service/alembic/versions/20240115_abc123_create_user_sessions_table.py

# 4. Apply migration
python scripts/migrate.py --service auth --operation upgrade --args "head"

# 5. Verify table created
psql -c "\d auth.user_sessions"

# 6. Commit
git add auth-service/alembic/versions/
git commit -m "Add user_sessions table"
```

---

### Workflow 2: Adding Column to Existing Table

```bash
# 1. Update model
vim platform-service/app/models/school_subscription.py
# (Add new column: total_upgrades_count)

# 2. Generate migration
python scripts/migrate.py --service platform --operation revision \
  --args "--autogenerate" "-m" "add_subscription_upgrade_tracking"

# 3. Review migration
cat platform-service/alembic/versions/20240115_def456_add_subscription_upgrade_tracking.py

# 4. Test in dev
python scripts/migrate.py --service platform --operation upgrade --args "head"

# 5. Verify column exists
psql -c "\d platform.school_subscriptions"

# 6. Test rollback
python scripts/migrate.py --service platform --operation downgrade --args "-1"

# 7. Re-apply
python scripts/migrate.py --service platform --operation upgrade --args "head"

# 8. Commit
git add platform-service/alembic/versions/
git commit -m "Add subscription upgrade tracking fields"
```

---

### Workflow 3: Deploying to Production

```bash
# 1. Pull latest code
git pull origin main

# 2. Check what migrations will run
python scripts/migrate.py --service all --operation current

# 3. Generate SQL for review (optional)
python scripts/migrate.py --service all --operation upgrade --args "--sql" "head" > migration.sql

# 4. Backup database
pg_dump -Fc postgres > backup_pre_migration_$(date +%Y%m%d_%H%M%S).dump

# 5. Run migrations
python scripts/migrate.py --service all --operation upgrade --args "head"

# 6. Verify success
python scripts/migrate.py --service all --operation current

# 7. Test application
curl http://localhost:8000/health
```

---

## 🔄 CI/CD Integration

### GitHub Actions Example

```yaml
name: Database Migrations

on:
  push:
    branches: [main]
    paths:
      - '*/alembic/versions/**'

jobs:
  migrate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          cd scripts
          pip install -r requirements.txt
      
      - name: Run migrations
        env:
          DB_HOST: ${{ secrets.DB_HOST }}
          DB_PORT: ${{ secrets.DB_PORT }}
          DB_NAME: ${{ secrets.DB_NAME }}
          DB_USER: ${{ secrets.DB_USER }}
          DB_PASSWORD: ${{ secrets.DB_PASSWORD }}
        run: |
          python scripts/migrate.py --service all --operation upgrade --args head
```

---

## 📊 Quick Reference Card

| Task | Command |
|------|---------|
| **Check status** | `python scripts/migrate.py --service all --operation current` |
| **Apply migrations** | `python scripts/migrate.py --service all --operation upgrade --args head` |
| **Create migration** | `python scripts/migrate.py --service auth --operation revision --args "--autogenerate" "-m" "message"` |
| **Rollback one** | `python scripts/migrate.py --service auth --operation downgrade --args "-1"` |
| **View history** | `python scripts/migrate.py --service auth --operation history` |
| **Interactive mode** | `python scripts/migrate.py` |

---

**End of Guide**
