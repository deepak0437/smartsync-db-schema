# SmartSync Multi-Service Database Migration System
**Architecture Design Document**

---

## 📋 Executive Summary

**Problem**: 16 microservices each have separate Alembic configurations, requiring developers to manually navigate to each service directory and run migrations individually. All services share the same database credentials from `etc/config/config.yaml`.

**Solution**: Unified migration orchestration system with a single entry point script that:
- Auto-discovers all services
- Loads shared database credentials
- Provides interactive service selection
- Executes migrations across multiple services
- Handles errors gracefully
- Supports all Alembic operations (upgrade, downgrade, revision, history, etc.)

---

## 🏗️ High-Level Architecture (HLD)

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Developer Workstation                            │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────┐    │
│  │           scripts/migrate.py (Entry Point)                │    │
│  │  • Interactive CLI                                         │    │
│  │  • Service discovery                                       │    │
│  │  • Credential management                                   │    │
│  │  • Operation routing                                       │    │
│  └──────────────────┬────────────────────────────────────────┘    │
│                     │                                              │
│  ┌──────────────────▼───────────────────────────────────────┐    │
│  │      scripts/lib/migration_manager.py                     │    │
│  │  • Service metadata                                        │    │
│  │  • Alembic command wrapper                                │    │
│  │  • Multi-service operations                               │    │
│  │  • Error handling & logging                               │    │
│  └──────────────────┬────────────────────────────────────────┘    │
│                     │                                              │
│  ┌──────────────────▼───────────────────────────────────────┐    │
│  │      scripts/lib/config_loader.py                         │    │
│  │  • Parse etc/config/config.yaml                           │    │
│  │  • Environment variable resolution                        │    │
│  │  • Service-specific URL generation                        │    │
│  └───────────────────────────────────────────────────────────┘    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              │ Reads DB credentials
                              │
            ┌─────────────────▼──────────────────┐
            │   etc/config/config.yaml           │
            │   • DB_HOST                        │
            │   • DB_PORT                        │
            │   • DB_NAME                        │
            │   • DB_USER                        │
            │   • DB_PASSWORD                    │
            └─────────────────┬──────────────────┘
                              │
                              │ Executes migrations
                              │
            ┌─────────────────▼──────────────────────────────────┐
            │          PostgreSQL Database (Supabase)            │
            │                                                     │
            │  ┌────────────┐  ┌────────────┐  ┌──────────────┐ │
            │  │   auth     │  │  platform  │  │   academic   │ │
            │  │   schema   │  │   schema   │  │    schema    │ │
            │  └────────────┘  └────────────┘  └──────────────┘ │
            │                                                     │
            │  ┌────────────┐  ┌────────────┐  ┌──────────────┐ │
            │  │  finance   │  │     hr     │  │  ...13 more  │ │
            │  │   schema   │  │   schema   │  │   schemas    │ │
            │  └────────────┘  └────────────┘  └──────────────┘ │
            │                                                     │
            └─────────────────────────────────────────────────────┘
```

---

## 🔧 Low-Level Design (LLD)

### 1. **Directory Structure**

```
smartsync-db-schema/
├── etc/
│   └── config/
│       └── config.yaml              # Shared DB credentials
│
├── scripts/
│   ├── migrate.py                   # Main entry point (NEW)
│   ├── lib/
│   │   ├── __init__.py
│   │   ├── config_loader.py        # Config parsing (NEW)
│   │   ├── migration_manager.py    # Alembic wrapper (NEW)
│   │   └── service_registry.py     # Service discovery (NEW)
│   ├── bootstrap_services.sh       # Existing bootstrap script
│   └── requirements.txt            # Python dependencies (NEW)
│
├── auth-service/
│   ├── alembic/
│   │   ├── env.py                  # Updated for shared config
│   │   └── versions/
│   └── alembic.ini                 # Updated for env var support
│
├── platform-service/
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   └── alembic.ini
│
└── [14 more services with same structure]
```

---

### 2. **Service Registry**

**File**: `scripts/lib/service_registry.py`

```python
"""
Auto-discovers all services and their Alembic configurations.
"""

SERVICES = [
    {
        "name": "auth-service",
        "schema": "auth",
        "path": "auth-service",
        "env_prefix": "AUTH",
        "description": "Authentication & RBAC Service"
    },
    {
        "name": "platform-service",
        "schema": "platform",
        "path": "platform-service",
        "env_prefix": "PLATFORM",
        "description": "Platform Management Service"
    },
    {
        "name": "academic-service",
        "schema": "academic",
        "path": "academic-service",
        "env_prefix": "ACADEMIC",
        "description": "Academic Management Service"
    },
    # ... 13 more services
]
```

**Discovery Logic**:
- Automatically scans root directory for `*-service/` folders
- Validates each service has `alembic/` and `alembic.ini`
- Extracts schema name from `alembic/env.py`
- Builds service metadata dictionary

---

### 3. **Configuration Loader**

**File**: `scripts/lib/config_loader.py`

**Responsibilities**:
1. Parse `etc/config/config.yaml`
2. Extract database credentials
3. Generate service-specific DATABASE_URL
4. Support environment variable overrides

**Output Format**:
```python
{
    "DB_HOST": "aws-0-ap-south-1.pooler.supabase.com",
    "DB_PORT": "6543",
    "DB_NAME": "postgres",
    "DB_USER": "postgres.xyz",
    "DB_PASSWORD": "secure_password",
    "DATABASE_URL": "postgresql://user:pass@host:port/db"
}
```

**Environment Variable Priority**:
1. Service-specific: `AUTH_DATABASE_URL`
2. Global override: `DATABASE_URL`
3. Config file: `etc/config/config.yaml`
4. Fallback: Hardcoded defaults

---

### 4. **Migration Manager**

**File**: `scripts/lib/migration_manager.py`

**Core Functions**:

#### `run_migration(service, operation, *args)`
Executes Alembic commands for a single service.

**Parameters**:
- `service`: Service metadata dict
- `operation`: `upgrade`, `downgrade`, `revision`, `history`, `current`, `heads`, `show`, `stamp`, `merge`
- `*args`: Additional arguments (e.g., `head`, `-1`, revision ID)

**Process**:
1. Change directory to service folder
2. Set `{SERVICE}_DATABASE_URL` environment variable
3. Execute: `alembic {operation} {args}`
4. Capture stdout/stderr
5. Return status + output

**Example**:
```python
run_migration(
    service={"name": "auth-service", "path": "auth-service"},
    operation="upgrade",
    args=["head"]
)
# Executes: cd auth-service && alembic upgrade head
```

---

#### `run_multi_service_migration(services, operation, *args)`
Executes migration across multiple services sequentially.

**Features**:
- Progress indicator
- Parallel execution support (optional)
- Dependency resolution (if service A requires service B)
- Rollback on failure
- Summary report

**Output**:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: upgrade head
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[1/3] auth-service       ✓ SUCCESS (2.3s)
[2/3] platform-service   ✓ SUCCESS (1.8s)
[3/3] academic-service   ✗ FAILED (0.5s)
      Error: Revision not found

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Summary: 2 succeeded, 1 failed
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

### 5. **Main Entry Point**

**File**: `scripts/migrate.py`

**Usage**:
```bash
# Interactive mode (shows menu)
python scripts/migrate.py

# Direct command
python scripts/migrate.py --service auth-service --operation upgrade --args head

# Multiple services
python scripts/migrate.py --service auth,platform,academic --operation upgrade --args head

# All services
python scripts/migrate.py --service all --operation current

# Create new migration
python scripts/migrate.py --service auth-service --operation revision --args "--autogenerate" "-m" "add_user_otp_fields"
```

**Interactive Menu**:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    SmartSync Database Migration Manager
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Select Operation:
  1. Upgrade migrations (apply pending)
  2. Downgrade migrations (revert)
  3. Create new migration
  4. Show migration history
  5. Show current revision
  6. Show all heads
  7. Generate SQL (offline mode)
  8. Stamp revision (mark without executing)
  9. Exit

Operation [1-9]: 1

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Select Service(s):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  0. All services (16)
  1. auth-service           (auth schema)
  2. platform-service       (platform schema)
  3. academic-service       (academic schema)
  4. finance-service        (finance schema)
  ...
  
Service(s) [0-16, or comma-separated]: 0

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Upgrade Target:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  1. head (latest)
  2. +1 (next revision)
  3. Specific revision ID
  
Target [1-3]: 1

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Confirmation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Operation: upgrade head
Services:  16 services (all)
Database:  postgres@aws-0-ap-south-1.pooler.supabase.com:6543/postgres

Proceed? [y/N]: y

[Starting migrations...]
```

---

### 6. **Alembic Configuration Updates**

#### **auth-service/alembic.ini** (Template for all services)

**Changes**:
```ini
[alembic]
script_location = alembic
file_template = %%(year)d%%(month).2d%%(day).2d_%%(rev)s_%%(slug)s
timezone = UTC

# Default URL (overridden by env var)
sqlalchemy.url = 

# Version table location
version_table = alembic_version
version_table_schema = auth
```

**Key Points**:
- `sqlalchemy.url` left empty (loaded from env var)
- `version_table_schema` set to service schema

---

#### **auth-service/alembic/env.py** (Template for all services)

**Changes**:
```python
import os
from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config, pool, text

# Load shared config
from scripts.lib.config_loader import load_db_config

config = context.config

# Get DATABASE_URL from environment or shared config
db_url = os.getenv("AUTH_DATABASE_URL")
if not db_url:
    shared_config = load_db_config()
    db_url = shared_config["DATABASE_URL"]

# Convert async URL to sync for Alembic
db_url = db_url.replace("+asyncpg", "")
config.set_main_option("sqlalchemy.url", db_url)

# Rest remains the same...
```

---

### 7. **Database URL Generation Logic**

**Service-Specific URL Construction**:
```python
def generate_database_url(service_name: str, config: dict) -> str:
    """
    Generates service-specific DATABASE_URL.
    
    All services connect to the SAME database but use different schemas.
    Schema isolation is handled by Alembic's version_table_schema setting.
    """
    return (
        f"postgresql://{config['DB_USER']}:{config['DB_PASSWORD']}"
        f"@{config['DB_HOST']}:{config['DB_PORT']}/{config['DB_NAME']}"
    )
```

**Key Insight**: 
- All services use the **same DATABASE_URL**
- Schema isolation via `version_table_schema` in Alembic config
- Each service's Alembic tracks versions in its own schema's `alembic_version` table

**Example**:
```sql
-- auth-service migrations tracked in:
auth.alembic_version

-- platform-service migrations tracked in:
platform.alembic_version
```

---

## 🎯 Workflow Examples

### **Example 1: Upgrade All Services**

```bash
$ python scripts/migrate.py

Select Operation: 1 (Upgrade)
Select Service(s): 0 (All)
Target: 1 (head)
Proceed? y

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: upgrade head (16 services)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[1/16] auth-service          ✓ SUCCESS (2.1s)
        Applied: 20240115_abc123_add_user_otp_fields
        
[2/16] platform-service      ✓ SUCCESS (1.8s)
        Applied: 20240115_def456_add_subscription_upgrade
        
[3/16] academic-service      → SKIPPED (0.0s)
        Reason: Already at head
        
...

[16/16] media-service        ✓ SUCCESS (1.5s)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Summary: 14 succeeded, 1 skipped, 1 failed
Total time: 28.3s
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

### **Example 2: Create Migration for Single Service**

```bash
$ python scripts/migrate.py --service auth-service --operation revision --args "--autogenerate" "-m" "add_session_tracking"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Creating Migration: auth-service
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Detected changes:
  + Added column: user_sessions.last_activity_at
  + Added index: ix_auth_session_last_activity

Generated: auth-service/alembic/versions/20240115_abc123_add_session_tracking.py

Review the migration, then run:
  python scripts/migrate.py --service auth-service --operation upgrade --args head
```

---

### **Example 3: Downgrade Multiple Services**

```bash
$ python scripts/migrate.py --service auth,platform --operation downgrade --args "-1"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: downgrade -1 (2 services)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[1/2] auth-service          ✓ SUCCESS (1.2s)
        Reverted: 20240115_abc123_add_user_otp_fields
        
[2/2] platform-service      ✓ SUCCESS (1.0s)
        Reverted: 20240115_def456_add_subscription_upgrade

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Summary: 2 succeeded
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

### **Example 4: Check Migration Status**

```bash
$ python scripts/migrate.py --service all --operation current

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Current Migration Status
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

auth-service
  Current: 20240115_abc123 (head)
  Pending: None

platform-service
  Current: 20240114_def456
  Pending: 20240115_ghi789 (1 revision behind)

academic-service
  Current: 20240115_jkl012 (head)
  Pending: None

...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Summary: 15 up-to-date, 1 pending
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 🔐 Security Considerations

### **1. Credential Storage**
- ✅ Never commit `etc/config/config.yaml` with real credentials
- ✅ Use environment variables in CI/CD
- ✅ Support `.env` file for local development

### **2. Database Connection**
- ✅ Use connection pooling (PgBouncer port 6543)
- ✅ Set short statement timeout
- ✅ Use read-only connection for `current`, `history`, `show` operations

### **3. Migration Safety**
- ✅ Require confirmation for destructive operations
- ✅ Support dry-run mode (generate SQL without applying)
- ✅ Auto-backup before downgrade operations

---

## 🚀 Implementation Plan

### **Phase 1: Core Infrastructure** (Week 1)
- [ ] Create `scripts/lib/` directory structure
- [ ] Implement `config_loader.py`
- [ ] Implement `service_registry.py`
- [ ] Implement `migration_manager.py` (basic operations)
- [ ] Add `scripts/requirements.txt`

### **Phase 2: CLI Interface** (Week 1)
- [ ] Implement `scripts/migrate.py` entry point
- [ ] Add interactive menu system
- [ ] Add command-line argument parsing
- [ ] Implement progress indicators

### **Phase 3: Alembic Integration** (Week 2)
- [ ] Update all `alembic.ini` files
- [ ] Update all `alembic/env.py` files
- [ ] Test single-service migrations
- [ ] Test multi-service migrations

### **Phase 4: Advanced Features** (Week 2)
- [ ] Add migration history viewer
- [ ] Add dependency resolution
- [ ] Add rollback-on-failure
- [ ] Add parallel execution (optional)

### **Phase 5: Documentation & Testing** (Week 3)
- [ ] Write developer guide
- [ ] Create video walkthrough
- [ ] Add integration tests
- [ ] Update CI/CD pipelines

---

## 📚 Developer Guide

### **Setup**
```bash
# Install dependencies
cd scripts
pip install -r requirements.txt

# Configure database
cp etc/config/config.yaml.example etc/config/config.yaml
# Edit with your Supabase credentials

# Verify setup
python migrate.py --service all --operation current
```

### **Creating a New Migration**
```bash
# 1. Modify your SQLAlchemy models
vim auth-service/app/models/session.py

# 2. Generate migration
python scripts/migrate.py --service auth-service --operation revision \
  --args "--autogenerate" "-m" "add_new_fields"

# 3. Review the generated migration
vim auth-service/alembic/versions/20240115_abc123_add_new_fields.py

# 4. Apply migration
python scripts/migrate.py --service auth-service --operation upgrade --args head
```

### **Applying Migrations in Production**
```bash
# 1. Check current status
python scripts/migrate.py --service all --operation current

# 2. Dry run (generate SQL)
python scripts/migrate.py --service all --operation upgrade --args "--sql" "head"

# 3. Apply with confirmation
python scripts/migrate.py --service all --operation upgrade --args head
```

### **Troubleshooting**
```bash
# Check if service is recognized
python scripts/migrate.py --service auth-service --operation heads

# Verify database connection
psql "postgresql://user:pass@host:port/db" -c "\dn"

# Manually stamp a revision (if out of sync)
python scripts/migrate.py --service auth-service --operation stamp --args "head"
```

---

## 🎓 Benefits

### **For Developers**
✅ Single command to run migrations across all services  
✅ No need to remember service-specific paths  
✅ Automatic database credential loading  
✅ Interactive CLI with validation  
✅ Clear error messages and status reports  

### **For DevOps**
✅ CI/CD-friendly command-line interface  
✅ Support for environment variable overrides  
✅ Idempotent operations (safe to re-run)  
✅ Detailed logging for audit trails  

### **For Teams**
✅ Consistent migration workflow across all services  
✅ Reduced onboarding time for new developers  
✅ Self-documenting service registry  
✅ Built-in safeguards against mistakes  

---

## 📊 Success Metrics

After implementation, measure:
- **Time to run migrations**: Target <30s for all services
- **Developer satisfaction**: Survey feedback (target 4.5/5)
- **Error rate**: Track failed migrations (target <5%)
- **Onboarding time**: New developer setup (target <10 min)

---

## 🔮 Future Enhancements

### **Phase 4+**
- **Web UI**: Browser-based migration dashboard
- **Slack Integration**: Post-migration notifications
- **Migration Scheduling**: Automated off-hours upgrades
- **Rollback Automation**: Auto-revert on health check failure
- **Drift Detection**: Compare schemas against models

---

## 📝 Appendix

### **A. Service List**
1. auth-service (auth schema)
2. platform-service (platform schema)
3. academic-service (academic schema)
4. administration-service (administration schema)
5. management-service (management schema)
6. finance-service (finance schema)
7. hr-service (hr schema)
8. hostel-service (hostel schema)
9. transport-service (transport schema)
10. notification-service (notification schema)
11. library-service (library schema)
12. security-service (security schema)
13. communication-service (communication schema)
14. lms-service (lms schema)
15. analytics-service (analytics schema)
16. media-service (media schema)

### **B. Alembic Commands Supported**
- `upgrade [target]` - Apply migrations
- `downgrade [target]` - Revert migrations
- `revision [options]` - Create new migration
- `history` - Show migration history
- `current` - Show current revision
- `heads` - Show all heads
- `show [revision]` - Show migration details
- `stamp [revision]` - Mark revision without executing
- `merge` - Merge multiple heads

---

**End of Document**
