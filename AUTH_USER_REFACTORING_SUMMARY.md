# Summary of Auth Service User Model Refactoring

## What Was Changed

### ✅ 1. Created 4 New Model Files

**1. `user_type.py`** - Enum for user categories
- Defines: STUDENT, TEACHER, PARENT, ADMIN, SUPER_ADMIN, STAFF
- Includes helper properties: `domain_service`, `is_staff`, `is_super_user`
- **Purpose:** Route user to correct domain service for business profile

**2. `user_auth_credentials.py`** - Password & authentication
- Columns: password_hash, password_salt, password_expires_at, must_change_password, etc.
- 1-to-1 relationship with User (one-to-one via ForeignKey)
- **Purpose:** Isolate password security management

**3. `user_security_settings.py`** - Account protection & 2FA
- Columns: is_locked, failed_login_attempts, last_login_at, 2FA settings, email/phone verification
- 1-to-1 relationship with User
- **Purpose:** Track security state and brute force protection

**4. `user_preferences.py`** - User customization
- Columns: language_preference, timezone, extra_metadata (JSONB)
- 1-to-1 relationship with User
- **Purpose:** Extensible user settings without touching core identity

### ✅ 2. Updated User Model (user.py)

**Removed Columns (moved to new tables):**
- ❌ password_hash → moved to UserAuthCredentials
- ❌ password_salt → moved to UserAuthCredentials
- ❌ last_password_change_at → moved to UserAuthCredentials
- ❌ password_expires_at → moved to UserAuthCredentials
- ❌ is_password_expired → moved to UserAuthCredentials
- ❌ must_change_password → moved to UserAuthCredentials
- ❌ is_locked → moved to UserSecuritySettings
- ❌ failed_login_attempts → moved to UserSecuritySettings
- ❌ last_login_at → moved to UserSecuritySettings
- ❌ last_login_ip → moved to UserSecuritySettings
- ❌ account_locked_until → moved to UserSecuritySettings
- ❌ email_verified_at → moved to UserSecuritySettings
- ❌ phone_verified_at → moved to UserSecuritySettings
- ❌ two_factor_enabled → moved to UserSecuritySettings
- ❌ two_factor_method → moved to UserSecuritySettings
- ❌ is_verified → moved to UserSecuritySettings (indirectly via email/phone verification)
- ❌ language_preference → moved to UserPreferences
- ❌ timezone → moved to UserPreferences
- ❌ extra_metadata → moved to UserPreferences

**Changed Columns:**
- `user_type`: String(30) → **Enum(UserType)** with import from user_type.py

**Added Relationships:**
- ✅ `auth_credentials` → UserAuthCredentials (1-to-1)
- ✅ `security_settings` → UserSecuritySettings (1-to-1)
- ✅ `preferences` → UserPreferences (1-to-1)

**Kept Columns (Core Identity):**
- ✅ tenant_id, school_id
- ✅ username, email, phone
- ✅ user_type (Enum, determines domain service)
- ✅ display_name, avatar_url
- ✅ is_active
- ✅ user_roles (assignment of permissions)

---

## Architecture Comparison

### Before Refactoring
```
users table (40+ columns)
├─ identity (5 columns)
├─ authentication (2 columns)
├─ security (15 columns)
├─ preferences (3 columns)
├─ account_status (5 columns)
└─ timestamps (10+ columns)

Total: Single table, mixed concerns
Problems: Hard to maintain, performance overhead, security concerns
```

### After Refactoring
```
users (10 columns) - Core identity ONLY
├─ auth_credentials (1-to-1, 7 columns) - Password security
├─ security_settings (1-to-1, 11 columns) - Account locks & 2FA
└─ preferences (1-to-1, 3 columns) - Language, timezone, metadata

Total: 4 focused tables, clean separation of concerns
Benefits: Maintainable, performant, secure, auditable
```

---

## Why This Design is Correct

### Question 1: Is user_type necessary with UserRole?
**Answer:** YES - They serve DIFFERENT purposes

| Aspect | user_type | UserRole |
|--------|-----------|----------|
| **Purpose** | Routes to domain service | Determines permissions |
| **Scope** | Platform-global | Per-school |
| **Set when** | User creation | By school admin |
| **Query** | "Where's profile?" | "What can they do?" |

**Example:**
- RAHUL has user_type=TEACHER (profile in hr-service)
- In Green Valley School: UserRole=CLASS_TEACHER (teach math class)
- In ABC School: UserRole=SUBJECT_TEACHER_SCIENCE (teach science)
- Same user_type, different roles per school!

### Question 2: Should User table be segregated?
**Answer:** YES - Monolithic tables violate Single Responsibility

**Before:** 40+ columns, 5 concerns in one table
**After:** 4 focused tables, each with one responsibility

✅ Easier to modify password policy
✅ Better performance (load only what needed)
✅ Cleaner API (user.auth_credentials.password_hash vs user.password_hash)
✅ Better security (password fields isolated)
✅ Database enforces 1-to-1 relationships

### Question 3: Creation flow with UserRole?
**Answer:** Straightforward

```
Admin selects role (e.g., CLASS_TEACHER)
  ↓
System infers user_type=TEACHER (from role.hierarchy_level)
  ↓
Generate random password
  ↓
Create User record (with user_type=TEACHER)
  ↓
Create UserAuthCredentials (password_hash, must_change_password=True)
  ↓
Create UserSecuritySettings (is_locked=False, 2FA=False)
  ↓
Create UserPreferences (lang=en, timezone=Asia/Kolkata)
  ↓
Create UserRole record (user_id → role_id, school_id)
  ↓
Send email with temporary password
  ↓
On first login: User forced to change password
  ↓
System fetches permissions from SchoolRolePermission
  ↓
Issue JWT with user_id, user_type, roles, permissions
```

---

## Files Created/Modified

| File | Status | Changes |
|------|--------|---------|
| `auth-service/app/models/user.py` | ✅ Modified | Removed 20+ columns, added 3 relationships, changed user_type to Enum |
| `auth-service/app/models/user_type.py` | ✅ Created | UserType enum with 6 values + helper properties |
| `auth-service/app/models/user_auth_credentials.py` | ✅ Created | Password & auth tracking (7 columns) |
| `auth-service/app/models/user_security_settings.py` | ✅ Created | Account locks, 2FA, login history (11 columns) |
| `auth-service/app/models/user_preferences.py` | ✅ Created | Language, timezone, metadata (3 columns) |
| `AUTH_USER_MODEL_ARCHITECTURE.md` | ✅ Created | Comprehensive design documentation |

---

## Database Impact

### Tables Before
```sql
auth.users  (40+ columns)
  - Everything mixed together
  - Hard to query efficiently
  - Wide rows, slow for large tables
```

### Tables After
```sql
auth.users  (10 columns) - core identity
auth.user_auth_credentials  (7 columns) - 1-to-1 ForeignKey to users.id
auth.user_security_settings  (11 columns) - 1-to-1 ForeignKey to users.id
auth.user_preferences  (3 columns) - 1-to-1 ForeignKey to users.id
```

### Benefits
✅ Faster queries (smaller rows, column selection)
✅ Better indexing (focused on relevant columns)
✅ Improved concurrency (less contention on wide table)
✅ Easier to add features (new columns go to relevant table)
✅ Data integrity (1-to-1 relationships enforced by database)

---

## Key Distinctions Clarified

### user_type vs UserRole

| Scenario | user_type | UserRole |
|----------|-----------|----------|
| **Used for** | Domain service routing | Permission checking |
| **Lookup query** | User.user_type | UserRole.filter(user_id=X, school_id=Y) |
| **Change frequency** | Never (immutable) | Often (promotions, role changes) |
| **Example** | TEACHER | CLASS_TEACHER, HOD, SUBJECT_TEACHER |
| **Scope** | Global across all schools | Per school |
| **Set by** | System (based on primary role) | School admin |

**They are NOT redundant.** They answer different questions:
- user_type: "Which service holds this person's business profile?"
- UserRole: "What can this person do in this school?"

---

## Next Steps

1. **Update __init__.py** to export new models:
   ```python
   from .user_type import UserType
   from .user_auth_credentials import UserAuthCredentials
   from .user_security_settings import UserSecuritySettings
   from .user_preferences import UserPreferences
   ```

2. **Update base.py** to include new models in metadata:
   ```python
   from app.models.user_auth_credentials import UserAuthCredentials
   from app.models.user_security_settings import UserSecuritySettings
   from app.models.user_preferences import UserPreferences
   ```

3. **Create Alembic migration** (in `alembic/versions/`):
   - Create the 3 new tables
   - Migrate data from old User table
   - Drop old columns from User
   - Add ForeignKey constraints

4. **Update login service** to use new structure:
   ```python
   # Old: user.password_hash
   # New: user.auth_credentials.password_hash
   
   # Old: user.is_locked
   # New: user.security_settings.is_locked
   ```

5. **Update registration/user creation** to populate all 4 tables

---

## Testing Checklist

- [ ] Create user with all segregated tables
- [ ] Verify 1-to-1 relationships enforce exactly-one
- [ ] Test login with password verification
- [ ] Test brute force protection (failed_login_attempts)
- [ ] Test account lockout
- [ ] Test 2FA enrollment/verification
- [ ] Test preference updates
- [ ] Test user_type routing (TEACHER → hr-service)
- [ ] Test JWT generation with permissions
- [ ] Test Alembic migration (if upgrading)

---

## Architecture Review Complete ✅

The refactored User model is now:
- **Single Responsibility:** Each table handles one concern
- **Maintainable:** Easy to understand and modify
- **Performant:** Load only necessary columns
- **Secure:** Password fields isolated with audit trail potential
- **Correct:** user_type and UserRole serve different purposes
- **Scalable:** 1-to-1 relationships can be extended independently
