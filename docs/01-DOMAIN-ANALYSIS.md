# Domain Analysis - SmartSync.ai

## 1. DOMAIN ANALYSIS

### 1.1 Core Domains

#### Identity & Access Domain (Auth Service)
**Purpose**: Manage authentication, authorization, and user identity across the platform

**Core Concepts**:
- **User**: Central identity entity (username-based, no email signup)
- **Role**: Job function or position (Student, Teacher, Parent, Admin, HOD, Principal)
- **Permission**: Granular action authorization (e.g., ACADEMICS.REVIEW.CREATE)
- **Tenant**: School organization (multi-tenant isolation)
- **Session**: User authentication state

**Key Rules**:
- Users created by School Admin only (no self-signup)
- Username varies by role: Admission# (Student), Employee# (Teacher), Phone (Parent), Email (Admin)
- Multi-tenant isolation at row level
- Support for MFA and IP whitelisting

#### Academic Domain (Academic Service)
**Purpose**: Manage academic operations, student lifecycle, and educational activities

**Core Concepts**:
- **Academic Profile**: Student's academic identity and enrollment
- **Class**: Grade level (e.g., Grade 1, Grade 2)
- **Section**: Division within a class (e.g., Section A, B)
- **Subject**: Course/subject taught
- **Timetable**: Schedule of classes
- **Attendance**: Daily presence tracking
- **Homework**: Assignments given to students
- **Review**: Teacher assessment of student
- **Remark**: Teacher comments on student
- **Behavior**: Positive/negative behavioral incidents
- **Discipline**: Disciplinary actions
- **Achievement**: Awards and recognitions
- **Leave**: Absence requests

**Key Rules**:
- Students belong to one class-section at a time
- Teachers can teach multiple subjects across multiple classes
- Class Teacher has holistic view of assigned class
- Subject Teacher has subject-specific view
- HOD has department-wide view
- Ownership-based data access (students see only their data)

### 1.2 Supporting Domains

#### Platform Domain
- Tenant (School) Management
- Subscription & Licensing
- Feature Flags
- System Configuration

#### Administration Domain
- Student Admission
- Employee Onboarding
- Document Management
- ID Card Generation

#### Management Domain
- Organizational Structure
- Department Management
- Designation Management
- Reporting Hierarchy

#### Finance Domain
- Fee Structure
- Fee Collection
- Invoicing
- Payment Gateway

#### HR Domain
- Employee Management
- Payroll
- Leave Management (Staff)
- Performance Reviews

#### Hostel Domain
- Room Allocation
- Hostel Attendance
- Mess Management

#### Transport Domain
- Route Management
- Vehicle Tracking
- Transport Fee

#### Notification Domain
- Push Notifications
- Email Notifications
- SMS Notifications
- In-App Notifications

#### Library Domain
- Book Catalog
- Issue/Return
- Fine Management

#### Security Domain
- Visitor Management
- Gate Pass
- CCTV Integration

#### Communication Domain
- Announcements
- Circulars
- Parent-Teacher Communication
- Notice Board

#### LMS Domain
- Course Content
- Video Lectures
- Assignments
- Quizzes

#### Analytics Domain
- Academic Analytics
- Financial Analytics
- Operational Dashboards

#### Media Domain
- File Upload
- Image Storage
- Document Storage
- CDN Integration

---

## 2. AGGREGATE BOUNDARIES

### Auth Service Aggregates

#### User Aggregate
**Root**: User
**Entities**: User, UserRole, UserSession, UserMFA, UserDevice
**Value Objects**: Username, PasswordHash, Email, Phone
**Invariants**:
- Username must be unique per tenant
- User must have at least one role
- Active sessions must be valid

#### Role Aggregate
**Root**: Role
**Entities**: Role, RolePermission
**Value Objects**: RoleName, PermissionCode
**Invariants**:
- Role name unique per tenant
- Permissions must exist before assignment

#### Tenant Aggregate
**Root**: Tenant
**Entities**: Tenant, TenantSettings, TenantSubscription
**Value Objects**: TenantCode, Domain, SubscriptionPlan
**Invariants**:
- Tenant code globally unique
- Active subscription required for access

### Academic Service Aggregates

#### Student Aggregate
**Root**: AcademicProfile (Student)
**Entities**: AcademicProfile, StudentParentMapping, StudentAttendance, StudentLeave
**Value Objects**: AdmissionNumber, RollNumber, BloodGroup
**Invariants**:
- Admission number unique per tenant
- Must be enrolled in one class-section
- Cannot have overlapping enrollments

#### Class Aggregate
**Root**: Class
**Entities**: Class, Section, ClassSubject, ClassTimetable
**Value Objects**: ClassName, SectionName, AcademicYear
**Invariants**:
- Class-Section combination unique per academic year
- Timetable slots cannot overlap

#### Homework Aggregate
**Root**: Homework
**Entities**: Homework, HomeworkSubmission, HomeworkAttachment
**Value Objects**: Title, Description, DueDate
**Invariants**:
- Due date must be future
- Only assigned students can submit
- Cannot modify after closure

#### Review Aggregate
**Root**: StudentReview
**Entities**: StudentReview, ReviewAcknowledgment
**Value Objects**: ReviewText, Rating, ReviewType
**Invariants**:
- Only authorized teachers can create
- Parents must acknowledge
- Cannot delete after acknowledgment

#### Behavior Aggregate
**Root**: BehaviorRecord
**Entities**: BehaviorRecord, BehaviorAction
**Value Objects**: IncidentType, Severity, ActionTaken
**Invariants**:
- Must have valid incident type
- Severe incidents require HOD approval

#### Achievement Aggregate
**Root**: Achievement
**Entities**: Achievement, AchievementEvidence
**Value Objects**: AchievementType, AwardDate, Description
**Invariants**:
- Must have valid achievement type
- Award date cannot be future

---

## 3. BOUNDED CONTEXT DESIGN

### Context Map

```
┌─────────────────────────────────────────────────────────────┐
│                      API GATEWAY                             │
│                   (Routing + Auth)                           │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────┐      ┌──────────────┐     ┌──────────────┐
│ Auth Service │◄────►│   Platform   │     │  Academic    │
│   (Core)     │      │   Service    │     │   Service    │
└──────────────┘      └──────────────┘     └──────────────┘
        │                     │                     │
        │                     │                     │
        └─────────────────────┴─────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
            ┌──────────────┐    ┌──────────────┐
            │ Notification │    │   Analytics  │
            │   Service    │    │   Service    │
            └──────────────┘    └──────────────┘
```

### Context Relationships

#### Auth Service (Core Context)
**Type**: Core Domain
**Relationships**:
- **Upstream** to all services (provides identity)
- **Published Events**: UserCreated, UserUpdated, RoleAssigned, UserLoggedIn
- **Consumed Events**: None (independent)

#### Academic Service
**Type**: Core Domain
**Relationships**:
- **Downstream** from Auth (consumes user_id)
- **Downstream** from Platform (consumes tenant_id)
- **Published Events**: StudentEnrolled, AttendanceMarked, HomeworkCreated, ReviewCreated
- **Consumed Events**: UserCreated, UserDeactivated

#### Platform Service
**Type**: Supporting Domain
**Relationships**:
- **Upstream** to all services (provides tenant context)
- **Published Events**: TenantCreated, TenantActivated, SubscriptionExpired
- **Consumed Events**: None

### Anti-Corruption Layers

Each service maintains its own view of shared entities:

**Auth Service owns**:
- users (full entity)
- roles
- permissions

**Academic Service references**:
- user_id (foreign key only, no user details)
- Fetches user details via API/Event when needed
- Maintains own academic_profiles with user_id reference

**No direct database joins across services**

---

## 4. ENTITY RELATIONSHIP DESIGN

### Auth Service Entities

#### Core Entities
1. **tenants** - School organizations
2. **users** - System users (all roles)
3. **roles** - Job functions
4. **permissions** - Granular actions
5. **user_roles** - User-Role mapping
6. **role_permissions** - Role-Permission mapping
7. **user_sessions** - Active sessions
8. **user_mfa** - Multi-factor auth
9. **user_devices** - Trusted devices
10. **user_login_history** - Audit trail
11. **password_reset_tokens** - Password recovery
12. **api_keys** - Service-to-service auth
13. **ip_whitelist** - IP restrictions

#### Relationships
- Tenant 1:N Users
- User N:M Roles (via user_roles)
- Role N:M Permissions (via role_permissions)
- User 1:N Sessions
- User 1:N MFA
- User 1:N Devices

### Academic Service Entities

#### Profile Entities
1. **academic_profiles** - Student academic identity
2. **student_parent_mapping** - Parent-child relationship
3. **employee_profiles** - Staff/Teacher profiles
4. **teacher_profiles** - Teacher-specific data

#### Academic Structure
5. **academic_years** - School years
6. **classes** - Grade levels
7. **sections** - Class divisions
8. **subjects** - Courses
9. **departments** - Academic departments
10. **class_sections** - Class-Section combinations
11. **class_subjects** - Subjects per class

#### Ownership Mapping
12. **teacher_class_mapping** - Class Teacher assignments
13. **teacher_subject_mapping** - Subject Teacher assignments
14. **teacher_section_mapping** - Section assignments
15. **hod_department_mapping** - HOD assignments

#### Timetable
16. **timetable_slots** - Time periods
17. **timetables** - Class schedules
18. **timetable_entries** - Individual schedule entries

#### Attendance
19. **attendance_records** - Daily attendance
20. **attendance_summary** - Monthly aggregates
21. **leave_requests** - Absence requests
22. **leave_approvals** - Approval workflow

#### Homework
23. **homework** - Assignments
24. **homework_submissions** - Student submissions
25. **homework_attachments** - File attachments

#### Reviews & Remarks
26. **student_reviews** - Teacher assessments
27. **student_remarks** - Teacher comments
28. **review_acknowledgments** - Parent acknowledgments

#### Behavior & Discipline
29. **behavior_records** - Behavioral incidents
30. **discipline_records** - Disciplinary actions
31. **behavior_types** - Incident categories
32. **discipline_types** - Action categories

#### Achievements
33. **achievements** - Awards and recognitions
34. **achievement_types** - Award categories

#### Tasks
35. **student_tasks** - Personal student tasks
36. **academic_tasks** - Teacher-assigned tasks

#### Events (Outbox Pattern)
37. **academic_events** - Event sourcing

---

## 5. KEY DESIGN DECISIONS

### Multi-Tenancy Strategy
**Decision**: Row-Level Security (RLS) with tenant_id in every table
**Rationale**: 
- Simpler than schema-per-tenant
- Better resource utilization
- Easier maintenance
- PostgreSQL RLS provides strong isolation

### Primary Key Strategy
**Decision**: UUID v4
**Rationale**:
- Globally unique (distributed system safe)
- No sequence contention
- Prevents enumeration attacks
- Easier data migration

### Soft Delete Strategy
**Decision**: deleted_at timestamp + is_deleted boolean
**Rationale**:
- Audit compliance
- Data recovery
- Historical reporting
- Cascade soft delete support

### Audit Strategy
**Decision**: created_at, updated_at, created_by, updated_by in every table
**Rationale**:
- Full audit trail
- Compliance requirements
- Debugging support
- Change tracking

### Authorization Strategy
**Decision**: RBAC + Ownership-Based
**Rationale**:
- RBAC for permission checks (can user perform action?)
- Ownership for data access (can user access this specific record?)
- Flexible and scalable
- Supports complex scenarios (teacher teaching multiple classes)

### Event Strategy
**Decision**: Transactional Outbox Pattern
**Rationale**:
- Guaranteed event delivery
- Atomic with database transaction
- No dual-write problem
- Event replay capability

---

## 6. DOMAIN RULES & INVARIANTS

### Auth Service Rules

1. **User Creation**
   - Only School Admin can create users
   - Username format varies by role
   - Email/Phone must be unique per tenant
   - Default password must be changed on first login

2. **Role Assignment**
   - User must have at least one role
   - Multiple roles allowed (Teacher + Class Teacher + HOD)
   - Role changes must be audited

3. **Session Management**
   - Max 5 concurrent sessions per user
   - Session timeout: 8 hours
   - Refresh token valid for 30 days

4. **Password Policy**
   - Min 8 characters
   - Must contain uppercase, lowercase, number, special char
   - Cannot reuse last 5 passwords
   - Expires every 90 days

### Academic Service Rules

1. **Student Enrollment**
   - Student must be enrolled in exactly one class-section per academic year
   - Admission number unique per tenant
   - Cannot have overlapping enrollments

2. **Teacher Assignment**
   - Teacher can teach multiple subjects
   - Teacher can be assigned to multiple classes
   - Class Teacher assigned to one class per academic year
   - HOD assigned to one department

3. **Attendance**
   - Marked once per day per student
   - Cannot mark future attendance
   - Cannot modify attendance after 7 days (configurable)
   - Minimum 75% attendance required (business rule)

4. **Homework**
   - Due date must be future
   - Can assign to class, section, or individual students
   - Cannot modify after due date
   - Late submissions marked automatically

5. **Reviews & Remarks**
   - Only assigned teachers can create
   - Parents must acknowledge within 7 days
   - Cannot delete after parent acknowledgment
   - Negative reviews require HOD approval

6. **Behavior & Discipline**
   - Severe incidents require immediate HOD notification
   - Disciplinary actions must have approval
   - Parents must be notified within 24 hours
   - Incident reports cannot be deleted (only soft delete)

7. **Leave Requests**
   - Must be submitted before leave date
   - Requires parent approval (for students)
   - Requires class teacher approval
   - Medical leave requires certificate for >3 days

8. **Data Access (Ownership)**
   - Students: Own data only
   - Parents: Mapped children only
   - Teachers: Assigned students only
   - Class Teachers: Assigned class students only
   - Subject Teachers: Students in assigned subject only
   - HOD: Department students only
   - Principal/VP: All students (read-only)

---

## 7. SCALABILITY CONSIDERATIONS

### Data Volume Projections (500 Schools)

| Entity | Per School | Total (500 Schools) |
|--------|-----------|---------------------|
| Students | 2,000 | 1,000,000 |
| Teachers | 100 | 50,000 |
| Parents | 3,000 | 1,500,000 |
| Classes | 50 | 25,000 |
| Subjects | 30 | 15,000 |
| Attendance Records/Year | 400,000 | 200,000,000 |
| Homework/Year | 10,000 | 5,000,000 |
| Reviews/Year | 8,000 | 4,000,000 |

### Partitioning Strategy

**Attendance Records**: Partition by month
```sql
-- Range partition by created_at
CREATE TABLE attendance_records_2024_01 PARTITION OF attendance_records
FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
```

**Academic Events**: Partition by week
```sql
-- Range partition by created_at
CREATE TABLE academic_events_2024_w01 PARTITION OF academic_events
FOR VALUES FROM ('2024-01-01') TO ('2024-01-08');
```

### Indexing Strategy

**Composite Indexes** for common queries:
- (tenant_id, user_id, is_deleted)
- (tenant_id, class_id, section_id, is_deleted)
- (tenant_id, academic_year_id, is_deleted)

**Partial Indexes** for active records:
```sql
CREATE INDEX idx_active_students ON academic_profiles(tenant_id, class_id) 
WHERE is_deleted = false;
```

### Caching Strategy

**Redis Cache**:
- User sessions (TTL: 8 hours)
- User permissions (TTL: 1 hour)
- Class-student mappings (TTL: 24 hours)
- Timetables (TTL: 24 hours)

**Cache Invalidation**:
- Event-driven (on entity updates)
- TTL-based expiration
- Manual purge via admin API

### Read Replicas

**Primary**: Write operations
**Replicas**: Read operations (reports, analytics)
**Lag Tolerance**: 5 seconds

---

**Document Version**: 1.0  
**Last Updated**: 2024  
**Author**: Principal Software Architect
