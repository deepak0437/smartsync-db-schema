# Auth Service User Model Architecture

## Overview

The User model has been **refactored from a monolithic 40-column table into a clean, segregated design** with 4 tables handling different concerns.

---

## Architecture: Before vs After

### ❌ BEFORE: Monolithic Design
```
User Table (40+ columns)
├─ Identity (username, email, phone)
├─ Authentication (password_hash, password_salt)
├─ Security (is_locked, failed_attempts, 2FA)
├─ Preferences (language, timezone, metadata)
├─ Account Status (is_active, is_verified, is_password_expired)
└─ Timestamps (last_login_at, last_password_change_at, etc)
```

**Problems:**
- ❌ Single Responsibility Principle violated
- ❌ ~40 columns mixing 5 different concerns
- ❌ Difficult to scale (password policy changes affect whole table)
- ❌ Performance: loading all fields even when only needing username
- ❌ Hard to manage 2FA separately from identity

### ✅ AFTER: Segregated Design
```
User (CORE IDENTITY) — 10 columns
├─ tenant_id, school_id
├─ username, email, phone (contact)
├─ user_type (determines domain service)
├─ display_name, avatar_url
├─ is_active
└─ Relationships to segregated tables

UserAuthCredentials (1-to-1) — 7 columns
├─ password_hash, password_salt
├─ last_password_change_at
├─ password_expires_at
├─ is_password_expired
└─ must_change_password

UserSecuritySettings (1-to-1) — 11 columns
├─ is_locked, account_locked_until
├─ failed_login_attempts
├─ last_login_at, last_login_ip
├─ email_verified_at, phone_verified_at
├─ two_factor_enabled, two_factor_method
└─ two_factor_enrolled_at

UserPreferences (1-to-1) — 3 columns
├─ language_preference
├─ timezone
└─ extra_metadata (JSONB)
```

---

## Table Relationships

```
                    User
                  (CORE IDENTITY)
                       |
         ______________________
         |         |          |
         v         v          v
      UserAuth  UserSecurity UserPrefs
      Credentials Settings
      (1-to-1)   (1-to-1)    (1-to-1)
         |         |          |
      [password]  [locks]   [i18n]
      [salt]      [2FA]     [meta]
      [expiry]    [logins]

User also links to:
├─ UserRole (many-to-many, per school)
├─ UserSession (1-to-many)
├─ UserDevice (1-to-many)
├─ LoginHistory (1-to-many)
├─ PasswordResets (1-to-many)
└─ PasswordHistory (1-to-many)
```

---

## User Type vs User Role: NOT Redundant

### `user_type` (Global, Determines Service Routing)
```python
user_type = Enum(UserType)
# STUDENT, TEACHER, PARENT, ADMIN, SUPER_ADMIN, STAFF

# Purpose: Route to correct domain service for business profile
user_type.domain_service  # Returns "academic-service", "hr-service", etc.

# Immutable after creation
# Set once based on primary role assignment
```

**Examples:**
- TEACHER → profile in hr-service (EmployeeProfile)
- STUDENT → profile in academic-service (StudentProfile)
- PARENT → profile in academic-service (ParentProfile)
- ADMIN → profile in platform-service (AdminProfile)

### `UserRole` (Per-School, Determines Permissions)
```python
# Many-to-many relationship
# Scoped to (tenant_id, school_id, user_id, role_id)

# Purpose: Determine effective permissions in school
# Query: What can this user do?

# Examples:
# - CLASS_TEACHER (hierarchy_level=15)
# - SUBJECT_TEACHER_MATH
# - HOD_SCIENCE
# - PRINCIPAL (hierarchy_level=50)
```

**They Answer Different Questions:**
| Aspect | user_type | UserRole |
|--------|-----------|----------|
| **Question** | "Where is their profile?" | "What can they do?" |
| **Scope** | Platform-global | Per-school |
| **Multiplicity** | One per user | Multiple per user |
| **When set** | At creation | By school admin |
| **Query use** | Service routing | Permission checks |

---

## User Creation Flow

### Step 1: School Admin Initiates User Creation
```
Admin selects:
  - username: "EMP-0042"
  - email: "rahul@school.edu"
  - role: "CLASS_TEACHER"  ← from role.py
```

### Step 2: System Derives user_type from Role
```python
# Lookup role in role.py
selected_role = Role.query(code="CLASS_TEACHER")
# selected_role.category = "ACADEMIC"
# selected_role.hierarchy_level = 15

# From role hierarchy, infer user_type
user_type = UserType.TEACHER  # (not arbitrary string)
```

### Step 3: Generate Credentials
```python
random_password = generate_secure_password()
password_hash = argon2_hash(random_password)
password_salt = extract_salt_from_hash(password_hash)
```

### Step 4: Create User Record
```python
user = User(
    tenant_id=school.tenant_id,
    school_id=school_id,
    username="EMP-0042",
    email="rahul@school.edu",
    phone=None,
    user_type=UserType.TEACHER,  # ← from role
    display_name="Rahul Sharma",
    avatar_url=None,
    is_active=True,
)
db.session.add(user)
db.session.flush()  # get user.id
```

### Step 5: Create Auth Credentials
```python
auth_creds = UserAuthCredentials(
    user_id=user.id,
    password_hash=password_hash,
    password_salt=password_salt,
    must_change_password=True,  # ← Force password change on first login
    is_password_expired=False,
)
db.session.add(auth_creds)
db.session.flush()
```

### Step 6: Create Security Settings
```python
security = UserSecuritySettings(
    user_id=user.id,
    is_locked=False,
    failed_login_attempts=0,
    last_login_at=None,
    two_factor_enabled=False,
    email_verified_at=None,
    phone_verified_at=None,
)
db.session.add(security)
db.session.flush()
```

### Step 7: Create Preferences (with Defaults)
```python
prefs = UserPreferences(
    user_id=user.id,
    language_preference="en",
    timezone="Asia/Kolkata",
    extra_metadata={},
)
db.session.add(prefs)
db.session.flush()
```

### Step 8: Assign Role to User
```python
user_role = UserRole(
    tenant_id=school.tenant_id,
    school_id=school_id,
    user_id=user.id,
    role_id=selected_role_id,
    is_primary=True,  # primary role for UI display
    assigned_by_user_id=admin_user.id,
    assigned_at=datetime.now(),
)
db.session.add(user_role)
db.session.commit()
```

### Step 9: Send Email with Temporary Password
```python
send_email(
    to=user.email,
    subject="SmartSync Account Created",
    body=f"""
    Welcome to SmartSync!
    
    Username: {user.username}
    Temporary Password: {random_password}
    
    On first login, you will be required to change your password.
    
    School: {school.name}
    Role: {selected_role.name}
    """,
)
```

### Step 10: First Login Flow
```
User attempts login with username & temporary password
  ↓
System verifies (password_hash matches)
  ↓
System checks auth_credentials.must_change_password = True
  ↓
BLOCK: "You must change your password before continuing"
  ↓
User sets new password
  ↓
auth_credentials.must_change_password = False
auth_credentials.last_password_change_at = now()
  ↓
Fetch effective permissions from SchoolRolePermission
  ↓
Issue JWT token with:
  - user_id
  - username
  - school_id
  - user_type (for profile service routing)
  - roles[] (from UserRole)
  - permissions[] (from SchoolRolePermission)
  ↓
User logged in!
```

---

## Query Patterns

### Query 1: Login (Fetch User with Credentials)
```python
user = (
    db.query(User)
    .filter(
        User.tenant_id == tenant_id,
        User.school_id == school_id,
        User.username == username,
        User.is_active == True,
    )
    .options(
        selectinload(User.auth_credentials),
        selectinload(User.security_settings),
        selectinload(User.preferences),
    )
    .one_or_none()
)

if not user:
    raise UserNotFoundError()

# Check brute force
if user.security_settings.is_locked:
    if user.security_settings.account_locked_until > datetime.now():
        raise AccountLockedError()

# Verify password
if not verify_password(password, user.auth_credentials.password_hash):
    user.security_settings.failed_login_attempts += 1
    if user.security_settings.failed_login_attempts > 5:
        user.security_settings.is_locked = True
        user.security_settings.account_locked_until = datetime.now() + timedelta(minutes=15)
    db.session.commit()
    raise InvalidPasswordError()

# Success: reset attempts
user.security_settings.failed_login_attempts = 0
user.security_settings.last_login_at = datetime.now()
user.security_settings.last_login_ip = request.remote_addr
db.session.commit()
```

### Query 2: Fetch Profile (Route to Domain Service)
```python
user = db.query(User).filter(User.id == user_id).one()

# Get correct service based on user_type
service = user.user_type.domain_service
# Returns: "academic-service", "hr-service", "platform-service"

# Call domain service
profile = await academic_service.fetch_student_profile(user.id)
```

### Query 3: Fetch Permissions (for JWT)
```python
# Get user's roles in this school
roles = (
    db.query(UserRole)
    .filter(
        UserRole.user_id == user_id,
        UserRole.school_id == school_id,
        UserRole.is_active == True,
    )
    .all()
)

# Get effective permissions for those roles
permissions = (
    db.query(Permission.code)
    .join(SchoolRolePermission.permission)
    .filter(
        SchoolRolePermission.school_id == school_id,
        SchoolRolePermission.school_role_id.in_(
            db.query(SchoolRole.id).filter(
                SchoolRole.role_id.in_([r.role_id for r in roles])
            )
        ),
        SchoolRolePermission.is_granted == True,
    )
    .distinct()
    .all()
)

# Include in JWT
jwt_token = create_jwt(
    user_id=user.id,
    username=user.username,
    user_type=user.user_type.value,
    roles=[r.role.code for r in roles],
    permissions=[p.code for p in permissions],
)
```

### Query 4: Update Preferences
```python
prefs = (
    db.query(UserPreferences)
    .filter(UserPreferences.user_id == user_id)
    .update({
        UserPreferences.language_preference: "hi",
        UserPreferences.timezone: "Asia/Kolkata",
    })
)
db.session.commit()
```

### Query 5: Enable 2FA
```python
security = (
    db.query(UserSecuritySettings)
    .filter(UserSecuritySettings.user_id == user_id)
    .update({
        UserSecuritySettings.two_factor_enabled: True,
        UserSecuritySettings.two_factor_method: "TOTP",
        UserSecuritySettings.two_factor_enrolled_at: datetime.now(),
    })
)
db.session.commit()
```

---

## Benefits of Segregation

✅ **Single Responsibility:** Each table handles one concern
✅ **Performance:** Load only what you need
✅ **Maintainability:** Password policy changes don't affect identity table
✅ **Auditability:** Easy to track security changes
✅ **Scalability:** Can replicate security_settings to different database for audit log
✅ **Clean API:** User.auth_credentials.password_hash vs User.password_hash
✅ **Flexibility:** Add new security settings without touching User table
✅ **Data Integrity:** 1-to-1 relationships guarantee exactly one of each

---

## Files Created

1. **user_type.py** - Enum for user categories + routing helper
2. **user_auth_credentials.py** - Password storage and expiry
3. **user_security_settings.py** - Account locks, 2FA, login history
4. **user_preferences.py** - Language, timezone, extensible metadata
5. **user.py** (refactored) - Core identity only

**Total lines:**
- Old User: ~350 lines (40+ mixed columns)
- New Design: ~400 lines across 5 files (clean separation)

---

## Migration Path (If Upgrading)

```sql
-- Step 1: Create new tables (without FKs initially)
CREATE TABLE auth.user_auth_credentials (...)
CREATE TABLE auth.user_security_settings (...)
CREATE TABLE auth.user_preferences (...)

-- Step 2: Migrate data
INSERT INTO auth.user_auth_credentials
SELECT id, password_hash, password_salt, last_password_change_at, ...
FROM auth.users;

INSERT INTO auth.user_security_settings
SELECT id, is_locked, account_locked_until, failed_login_attempts, ...
FROM auth.users;

INSERT INTO auth.user_preferences
SELECT id, language_preference, timezone, extra_metadata
FROM auth.users;

-- Step 3: Remove old columns from users table
ALTER TABLE auth.users DROP COLUMN password_hash;
ALTER TABLE auth.users DROP COLUMN password_salt;
... (repeat for all moved columns)

-- Step 4: Update user_type to use ENUM
ALTER TABLE auth.users 
  ALTER COLUMN user_type TYPE user_type_enum USING user_type::text;

-- Step 5: Add FKs (after migration complete)
ALTER TABLE auth.user_auth_credentials
  ADD CONSTRAINT fk_user_auth_creds_user
  FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
```

---

## Why This Design is Correct

1. **user_type is NOT redundant with UserRole**
   - user_type: "Where is this person's profile?" → Routes to service
   - UserRole: "What can this person do?" → Determines permissions
   - Different concerns, different queries

2. **Segregation enables better security**
   - Password fields isolated
   - Can implement separate audit logging
   - Password policy independent of user identity

3. **1-to-1 relationships enforce exactly-one**
   - Every user has exactly one auth_credentials
   - Every user has exactly one security_settings
   - Every user has exactly one preferences
   - Database enforces data integrity

4. **Follows microservices best practices**
   - Each table has a clear responsibility
   - Easy to test in isolation
   - Scales independently

---

## Summary

The refactored User model:
- ✅ Splits 40+ columns into 4 focused tables
- ✅ Keeps user_type as required for domain service routing
- ✅ Uses UserRole for permission management (different concern)
- ✅ Enables clean creation flow: create User → add credentials → assign role
- ✅ Enforces 1-to-1 relationships for data integrity
- ✅ Supports security best practices and audit trails
