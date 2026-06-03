Let me walk through a real scenario end-to-end.

---

## Real Scenario

> **Green Valley School, Bangalore** just purchased a subscription.
> The **School Principal** logs into the SmartSync Admin Panel and adds a new teacher: **Rahul Sharma**.

---

## Who is talking to who

```
Principal's Browser
      │
      │  HTTP Request
      ▼
  API Gateway          (routes requests, validates JWT)
      │
      │  forwards to
      ▼
administration-service  ← THE BRAIN — knows the full business workflow
      │
      ├──── calls ────► auth-service      (create login account + assign role)
      │
      └──── calls ────► hr-service        (create employee profile)
```

---

## Step-by-Step Flow

### Step 1 — Principal fills the "Add Teacher" form

The principal fills this form in the browser:

```
Name:         Rahul Sharma
Username:     EMP-0042           ← their login ID
Password:     Temp@1234          ← temporary, must change on first login
Email:        rahul@gvb.com
Phone:        9876543210
Role:         TEACHER
Department:   Mathematics
Employee ID:  EMP-0042
Joining Date: 01-Jun-2024
```

Clicks **Save**.

---

### Step 2 — Browser sends ONE request to administration-service

```
POST https://api.smartsync.ai/admin/schools/school-uuid-bangalore/users

Authorization: Bearer <principal's JWT>

Body:
{
  "username":     "EMP-0042",
  "password":     "Temp@1234",
  "email":        "rahul@gvb.com",
  "phone":        "9876543210",
  "display_name": "Rahul Sharma",
  "role_code":    "TEACHER",
  "profile": {
    "employee_id":   "EMP-0042",
    "department":    "Mathematics",
    "joining_date":  "2024-06-01"
  }
}
```

The principal knows nothing about auth-service or hr-service. They just called ONE endpoint.

---

### Step 3 — administration-service takes over (THE BRAIN)

This is what the code inside `administration-service` does, in order:

```
administration-service receives the request
│
├── 1. Validate: Does this school have an active subscription?
│         → check platform-service or its own cache
│         → subscription is ACTIVE ✅
│
├── 2. Validate: Has the school's user limit been reached?
│         → school purchased 50 teacher slots, currently has 23
│         → 23 < 50 ✅ allowed to add more
│
├── 3. Call auth-service internally (create user identity)
│         POST http://auth-service/internal/users
│         {
│           "tenant_id":     "tenant-uuid",
│           "school_id":     "school-uuid-bangalore",
│           "username":      "EMP-0042",
│           "password":      "Temp@1234",
│           "email":         "rahul@gvb.com",
│           "phone":         "9876543210",
│           "display_name":  "Rahul Sharma"
│         }
│
│         auth-service responds:
│         { "user_id": "usr-uuid-rahul", "status": "created" }
│
├── 4. Call auth-service internally (assign TEACHER role)
│         POST http://auth-service/internal/users/usr-uuid-rahul/roles
│         {
│           "school_id": "school-uuid-bangalore",
│           "role_code":  "TEACHER",
│           "is_primary": true
│         }
│
│         auth-service responds:
│         { "status": "role_assigned" }
│
├── 5. Call hr-service internally (create business profile)
│         POST http://hr-service/internal/employees
│         {
│           "user_id":      "usr-uuid-rahul",   ← links to auth user
│           "school_id":    "school-uuid-bangalore",
│           "employee_id":  "EMP-0042",
│           "department":   "Mathematics",
│           "joining_date": "2024-06-01"
│         }
│
│         hr-service responds:
│         { "employee_profile_id": "emp-uuid-rahul", "status": "created" }
│
└── 6. Publish event to Kafka/RabbitMQ (for other services to react)
          event: USER_CREATED
          {
            "user_id":    "usr-uuid-rahul",
            "school_id":  "school-uuid-bangalore",
            "role":       "TEACHER",
            "event_time": "2024-06-01T10:30:00Z"
          }
          ← other services like notification-service, lms-service
            can pick this up and do their own setup
```

---

### Step 4 — administration-service responds to the browser

```json
HTTP 201 Created

{
  "user_id":            "usr-uuid-rahul",
  "employee_profile_id": "emp-uuid-rahul",
  "username":           "EMP-0042",
  "display_name":       "Rahul Sharma",
  "role":               "TEACHER",
  "status":             "active",
  "message":            "Teacher added successfully. Login credentials sent to rahul@gvb.com"
}
```

The browser shows: **"Rahul Sharma added as TEACHER successfully."**

---

### Step 5 — What happens in each service's database

**auth-service writes to:**
```sql
-- auth.users
INSERT INTO auth.users (id, tenant_id, school_id, username, email, display_name, ...)
VALUES ('usr-uuid-rahul', 'tenant-uuid', 'school-uuid-bangalore', 'EMP-0042', 'rahul@gvb.com', 'Rahul Sharma', ...);

-- auth.user_credentials
INSERT INTO auth.user_credentials (user_id, password_hash, must_change_password)
VALUES ('usr-uuid-rahul', '$argon2id$...', TRUE);

-- auth.user_security
INSERT INTO auth.user_security (user_id, failed_login_attempts, is_locked)
VALUES ('usr-uuid-rahul', 0, FALSE);

-- auth.user_roles
INSERT INTO auth.user_roles (user_id, school_id, role_id, is_primary)
VALUES ('usr-uuid-rahul', 'school-uuid-bangalore', 'role-uuid-teacher', TRUE);
```

**hr-service writes to:**
```sql
-- hr.employee_profiles
INSERT INTO hr.employee_profiles (user_id, school_id, employee_id, department, joining_date)
VALUES ('usr-uuid-rahul', 'school-uuid-bangalore', 'EMP-0042', 'Mathematics', '2024-06-01');
```

---

### Step 6 — Rahul logs in the next day

```
Rahul opens SmartSync → enters EMP-0042 / Temp@1234
→ auth-service validates credentials
→ sees must_change_password = TRUE
→ forces Rahul to set a new password
→ Rahul sets new password
→ auth-service builds JWT:

{
  "user_id":     "usr-uuid-rahul",
  "tenant_id":   "tenant-uuid",
  "school_id":   "school-uuid-bangalore",
  "roles":       ["TEACHER"],
  "permissions": ["ACADEMICS.HOMEWORK.CREATE", "ACADEMICS.ATTENDANCE.MARK", ...]
}
→ Rahul sees the Teacher dashboard
```

---

## Why administration-service and not auth-service directly?

| What happens | auth-service knows? | administration-service knows? |
|---|---|---|
| Is school subscription active? | ❌ Not its job | ✅ Yes |
| Has the teacher quota been reached? | ❌ Not its job | ✅ Yes |
| Where to create the business profile (hr vs academic)? | ❌ Not its job | ✅ Yes |
| How to send welcome email after creation? | ❌ Not its job | ✅ Yes |
| What to do if hr-service fails mid-way? | ❌ Not its job | ✅ Handles rollback |

**auth-service has one job**: identity and security. It does not know whether a school subscription is active, whether a quota is exceeded, or which domain service to call. **administration-service is the workflow coordinator** — it knows the complete business rules for "adding a user to a school."

---

## Summary in one line

> **administration-service** is the school admin's control panel backend. It receives ONE request from the admin, validates business rules, and then coordinates multiple internal service calls to make the complete operation happen.
