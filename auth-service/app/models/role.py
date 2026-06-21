"""
RBAC Models — Auth Service

Architecture: Platform-Controlled RBAC with School-Level Permission Import

Five-layer design (school-level role enable/disable layer removed — see
note below):
  Layer 1 → roles                     Platform-defined. Top-level role label only.
                                       No business/org hierarchy data — e.g. which
                                       class a TEACHER teaches lives in Academic
                                       Service, never here.
  Layer 2 → permissions               Platform-defined. All permissions for all
                                       roles, across all modules and actions.
  Layer 3 → role_permission_templates  Platform's default Role <-> Permission map.
                                       Many-to-many: one role has many permissions,
                                       one permission belongs to many roles.

School Customization Layer:
  Layer 4 → school_role_permissions   School-level permission IMPORT mechanism.
                                       Lets a school copy another role's granted
                                       permissions into a different role (e.g. give
                                       PRINCIPAL everything TEACHER has, on top of
                                       PRINCIPAL's own permissions) without
                                       duplicating rows in role_permission_templates.

User Assignment:
  Layer 5 → user_roles                Assigns exactly ONE role to a user, scoped
                                       to a school. A user cannot hold multiple
                                       roles — this is now a fixed 1:1 relationship.

Layer 6 → school_role_stats          Real-time per-role user count per school.

REMOVED: school_roles (Layer 4 in the previous version)
---------------------------------------------------------
Every subscribed school is given ALL platform roles by default — there is no
school-level enable/disable decision to make, so a table that only existed to
toggle role availability per school adds no value and is dropped. Permission
customization per school still exists, but it now points directly at `roles`
instead of going through a `school_roles` indirection table.

JWT Effective Permissions are resolved as:
  Permissions a role owns directly (role_permission_templates)
  UNION
  Permissions imported from another role (school_role_permissions, this school only)
"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    SmallInteger,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base, BaseModel


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 1 — ROLES (Platform-Controlled Master Table)
# ═══════════════════════════════════════════════════════════════════════════════

class Role(BaseModel):
    """
    Platform-defined role catalog — the top-level role label only.

    Created and maintained ONLY by the SmartSync platform team. Schools
    cannot create, rename, or delete roles.

    Deliberately thin: this table stores ONLY what Auth Service needs to
    know a role exists and group it for UI display. It does NOT store any
    business/organizational detail — e.g. "which class does this TEACHER
    teach" or "which department does this HOD head" are Academic/HR Service
    concerns, not Auth Service concerns. Auth Service only needs to know
    that "TEACHER" is a valid role and what permissions attach to it.

    Examples:
        STUDENT, PARENT, TEACHER, CLASS_TEACHER, SUBJECT_TEACHER,
        HOD, PRINCIPAL, VICE_PRINCIPAL, ACCOUNTANT, LIBRARIAN,
        WARDEN, DRIVER, RECEPTIONIST, HR, SECURITY_GUARD,
        LAB_ASSISTANT, SPORTS_COACH, COUNSELOR, ...

    Expected: 40–50 roles total. All roles are available to every
    subscribed school by default — there is no per-school enable/disable
    step (see module docstring for why school_roles was removed).
    """

    __tablename__ = "roles"
    __table_args__ = (
        UniqueConstraint("code", name="uq_auth_role_code"),
        Index("ix_auth_role_category", "category"),
        {
            "schema": "auth",
            "comment": "Platform-defined top-level role catalog. Schools cannot create roles.",
        },
    )

    # ── Identity ───────────────────────────────────────────────────────────────
    code = Column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        comment=(
            "Machine-readable role code. UPPER_SNAKE_CASE. "
            "Used in JWT 'role' claim and permission checks. "
            "E.g. 'CLASS_TEACHER', 'HOD', 'PRINCIPAL'"
        ),
    )
    name = Column(
        String(255),
        nullable=False,
        comment="Human-readable display name. E.g. 'Class Teacher'",
    )
    description = Column(
        Text,
        nullable=True,
        comment="Description of what this role represents. No business-domain detail.",
    )

    # ── Classification ─────────────────────────────────────────────────────────
    category = Column(
        String(50),
        nullable=False,
        index=True,
        comment=(
            "Broad category for grouping in UI. "
            "ACADEMIC | ADMINISTRATIVE | OPERATIONAL | SUPPORT | SYSTEM"
        ),
    )

    # ── Status ─────────────────────────────────────────────────────────────────
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="False = retired/deprecated role. Existing assignments are unaffected.",
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    permission_templates = relationship(
        "RolePermissionTemplate",
        back_populates="role",
        cascade="all, delete-orphan",
    )
    user_roles = relationship(
        "UserRole",
        back_populates="role",
    )

    def __repr__(self) -> str:
        return f"<Role code={self.code!r} category={self.category}>"


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 2 — PERMISSIONS (Platform-Controlled Master Table)
# ═══════════════════════════════════════════════════════════════════════════════

class Permission(BaseModel):
    """
    Platform-defined permission catalog.

    Created and maintained ONLY by the SmartSync platform team. Schools
    cannot create permissions.

    This is the single, complete catalog of every permission across every
    role and every module — every action any role could ever need, in one
    place.

    Naming convention: MODULE.SUBMODULE.ACTION
    Examples:
        ACADEMICS.HOMEWORK.CREATE
        ACADEMICS.HOMEWORK.READ
        ACADEMICS.ATTENDANCE.MARK
        ACADEMICS.ATTENDANCE.READ
        ACADEMICS.STUDENT_REVIEW.READ      ← shared across TEACHER, STUDENT,
                                              PRINCIPAL, etc. — see
                                              RolePermissionTemplate below for
                                              how one permission maps to many roles
        FINANCE.FEES.READ
        FINANCE.FEES.COLLECT
        HOSTEL.ROOM.ALLOCATE
        HR.PAYROLL.VIEW
        TRANSPORT.ROUTE.MANAGE
        LIBRARY.BOOK.ISSUE
        SECURITY.VISITOR.APPROVE
        COMMUNICATION.ANNOUNCEMENT.PUBLISH
        LMS.COURSE.CREATE
        ANALYTICS.REPORT.EXPORT

    Expected: 500–1,000 permissions total.
    """

    __tablename__ = "permissions"
    __table_args__ = (
        UniqueConstraint("code", name="uq_auth_permission_code"),
        Index("ix_auth_permission_module", "module"),
        Index("ix_auth_permission_module_submodule", "module", "submodule"),
        {
            "schema": "auth",
            "comment": "Platform-defined permission catalog. Schools cannot create permissions.",
        },
    )

    # ── Identity ───────────────────────────────────────────────────────────────
    code = Column(
        String(150),
        nullable=False,
        unique=True,
        index=True,
        comment=(
            "Full dotted permission code. MODULE.SUBMODULE.ACTION. "
            "Used in JWT 'permissions' claim. "
            "E.g. 'ACADEMICS.HOMEWORK.CREATE'"
        ),
    )
    name = Column(
        String(255),
        nullable=False,
        comment="Human-readable name. E.g. 'Create Homework'",
    )
    description = Column(
        Text,
        nullable=True,
        comment="What this permission allows the user to do",
    )

    # ── Decomposed Parts (for efficient filtering/querying) ───────────────────
    module = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Top-level module. E.g. 'ACADEMICS', 'FINANCE', 'HOSTEL'",
    )
    submodule = Column(
        String(100),
        nullable=False,
        comment="Resource within the module. E.g. 'HOMEWORK', 'FEES', 'ROOM'",
    )
    action = Column(
        String(50),
        nullable=False,
        comment=(
            "Operation being performed. "
            "E.g. 'CREATE', 'READ', 'UPDATE', 'DELETE', 'APPROVE', 'MARK', "
            "'COLLECT', 'EXPORT', 'PUBLISH', 'ALLOCATE', 'ISSUE'"
        ),
    )

    # ── Risk Level ─────────────────────────────────────────────────────────────
    risk_level = Column(
        String(10),
        nullable=False,
        default="LOW",
        comment=(
            "Sensitivity of this permission. "
            "LOW = read-only or routine. "
            "MEDIUM = writes or side effects. "
            "HIGH = financial, admin, or destructive operations."
        ),
    )

    # ── Status ─────────────────────────────────────────────────────────────────
    is_active = Column(Boolean, nullable=False, default=True, index=True)

    # ── Relationships ──────────────────────────────────────────────────────────
    role_templates = relationship(
        "RolePermissionTemplate",
        back_populates="permission",
        cascade="all, delete-orphan",
    )
    school_role_permissions = relationship(
        "SchoolRolePermission",
        back_populates="permission",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Permission code={self.code!r} risk={self.risk_level}>"


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 3 — ROLE PERMISSION TEMPLATES (Platform Defaults — Role <-> Permission Map)
# ═══════════════════════════════════════════════════════════════════════════════

class RolePermissionTemplate(BaseModel):
    """
    Platform's default mapping of Role <-> Permission. Many-to-many.

    A single role can have many permissions, and a single permission can
    belong to many roles. E.g. ACADEMICS.STUDENT_REVIEW.READ is granted to
    TEACHER, STUDENT, and PRINCIPAL simultaneously — each of those three
    roles gets its own row here pointing at the same permission.

    This is the platform-wide baseline every school starts with. Only the
    SmartSync platform team can modify these templates — schools never
    write to this table directly. Schools customize their effective grants
    via SchoolRolePermission (Layer 4) instead, which can import permissions
    from one role into another on top of this baseline.

    Example defaults:
        TEACHER      → ACADEMICS.HOMEWORK.CREATE
        TEACHER      → ACADEMICS.HOMEWORK.READ
        TEACHER      → ACADEMICS.ATTENDANCE.MARK
        TEACHER      → ACADEMICS.STUDENT_REVIEW.READ
        STUDENT      → ACADEMICS.HOMEWORK.READ
        STUDENT      → ACADEMICS.STUDENT_REVIEW.READ
        PRINCIPAL    → ACADEMICS.STUDENT_REVIEW.READ
        PRINCIPAL    → FINANCE.FEES.READ
        ACCOUNTANT   → FINANCE.FEES.COLLECT
        LIBRARIAN    → LIBRARY.BOOK.ISSUE
    """

    __tablename__ = "role_permission_templates"
    __table_args__ = (
        UniqueConstraint(
            "role_id", "permission_id",
            name="uq_auth_role_permission_template",
        ),
        Index("ix_auth_rpt_role_id", "role_id"),
        Index("ix_auth_rpt_permission_id", "permission_id"),
        {
            "schema": "auth",
            "comment": (
                "Platform's default many-to-many role-permission map. "
                "Read-only for schools. Schools layer additional grants via "
                "SchoolRolePermission (permission import between roles)."
            ),
        },
    )

    role_id = Column(
        SmallInteger,
        ForeignKey("auth.roles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    permission_id = Column(
        SmallInteger,
        ForeignKey("auth.permissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    is_active = Column(Boolean, nullable=False, default=True)

    # ── Relationships ──────────────────────────────────────────────────────────
    role = relationship("Role", back_populates="permission_templates")
    permission = relationship("Permission", back_populates="role_templates")

    def __repr__(self) -> str:
        return f"<RolePermissionTemplate role_id={self.role_id} perm_id={self.permission_id}>"


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 4 — SCHOOL ROLE PERMISSIONS (Permission Import Between Roles, Per School)
# ═══════════════════════════════════════════════════════════════════════════════

class SchoolRolePermission(BaseModel):
    """
    School-level permission IMPORT mechanism between two roles.

    This is NOT a copy of RolePermissionTemplate. It exists for one specific
    use case: a school wants role A to also have some or all of role B's
    permissions, without touching the platform-wide template for either role.

    Concrete example (the one you described):
        TEACHER role has 20 platform-default permissions.
        PRINCIPAL role has its own, smaller, default set.
        This particular school wants PRINCIPAL to ALSO have everything
        TEACHER has — so they import TEACHER's permission set into PRINCIPAL.

        Result at this school only:
            PRINCIPAL effective permissions = PRINCIPAL's own template grants
                                               + imported TEACHER grants
            TEACHER effective permissions   = TEACHER's own template grants
                                               (completely unaffected by the import)

    A school can import the FULL permission set of a source role, or a
    specific subset of it — both are represented by individual rows here
    (one row per imported permission), so a partial import is just fewer rows.

    Flow at login (effective permission resolution):
        1. Start with RolePermissionTemplate rows for the user's role_id
           (the role's own platform-default grants).
        2. UNION with SchoolRolePermission rows where
           target_role_id = the user's role_id AND school_id = this school
           AND is_granted = True (permissions imported from another role).
        3. The combined, de-duplicated set is the user's effective permissions.

    Design:
        target_role_id   — the role RECEIVING the imported permission
                            (PRINCIPAL, in the example above)
        source_role_id   — the role the permission is being copied FROM
                            (TEACHER, in the example above) — kept so the
                            import is traceable and revocable as a group
        permission_id    — the specific permission being imported
        is_granted        — True = import is active. False = explicitly
                            revoked without deleting the audit row.
    """

    __tablename__ = "school_role_permissions"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "school_id", "target_role_id", "permission_id",
            name="uq_auth_school_role_permission",
        ),
        Index("ix_auth_srp_lookup", "school_id", "target_role_id", "is_granted"),
        Index("ix_auth_srp_permission", "permission_id"),
        Index("ix_auth_srp_source_role", "source_role_id"),
        {
            "schema": "auth",
            "comment": (
                "Per-school permission import: copies a permission grant from "
                "one role (source_role_id) onto another role (target_role_id) "
                "for this school only. Layered on top of RolePermissionTemplate "
                "at JWT generation time, never replaces it."
            ),
        },
    )

    # ── Scoping ────────────────────────────────────────────────────────────────
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    school_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # ── Import Direction ───────────────────────────────────────────────────────
    target_role_id = Column(
        SmallInteger,
        ForeignKey("auth.roles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="The role RECEIVING this imported permission. E.g. PRINCIPAL.",
    )
    source_role_id = Column(
        SmallInteger,
        ForeignKey("auth.roles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment=(
            "The role this permission is being imported FROM. E.g. TEACHER. "
            "Kept (rather than just storing the permission) so the whole "
            "import can be queried/revoked as 'everything imported from "
            "TEACHER into PRINCIPAL', not just permission-by-permission."
        ),
    )
    permission_id = Column(
        SmallInteger,
        ForeignKey("auth.permissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="The specific permission being imported from source_role_id onto target_role_id.",
    )

    # ── Grant State ────────────────────────────────────────────────────────────
    is_granted = Column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment=(
            "True  = this imported permission is currently active for "
            "target_role_id at this school. "
            "False = import revoked without deleting the row (keeps audit trail)."
        ),
    )

    # ── Change Tracking ────────────────────────────────────────────────────────
    modified_by_user_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        comment="School admin user_id who set up or last modified this import.",
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    target_role = relationship(
        "Role",
        foreign_keys=[target_role_id],
    )
    source_role = relationship(
        "Role",
        foreign_keys=[source_role_id],
    )
    permission = relationship("Permission", back_populates="school_role_permissions")

    def __repr__(self) -> str:
        return (
            f"<SchoolRolePermission school_id={self.school_id} "
            f"{self.source_role_id} -> {self.target_role_id} "
            f"perm_id={self.permission_id} granted={self.is_granted}>"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 5 — USER ROLES (Assigns Exactly One Role to a User)
# ═══════════════════════════════════════════════════════════════════════════════

class UserRole(BaseModel):
    """
    Assigns exactly ONE role to a user within a school.

    Single-role fixed rule:
        A user has one and only one role at a time, scoped to their school.
        A person cannot simultaneously be TEACHER and CLASS_TEACHER as two
        separate role rows — if a school needs a user to act with broader
        permissions, that is handled by importing permissions into their
        single role via SchoolRolePermission (Layer 4), not by stacking
        multiple role assignments on the user.

    Enforced as a hard 1:1 via the unique constraint on
    (tenant_id, school_id, user_id) — no role_id in that constraint,
    because there can only ever be one row per user per school, period.

    Scope:
        Role assignment is scoped to (tenant_id, school_id, user_id).
        A user transferring to another school gets a new UserRole row in
        the new school — their old school's row is untouched.

    At login, effective permissions are computed as:
        WITH user_role AS (
            SELECT role_id FROM user_roles
            WHERE user_id = :user_id AND school_id = :school_id AND is_active = true
        )
        SELECT DISTINCT p.code
        FROM permissions p
        WHERE p.id IN (
            SELECT permission_id FROM role_permission_templates
            WHERE role_id = (SELECT role_id FROM user_role) AND is_active = true
        )
        OR p.id IN (
            SELECT permission_id FROM school_role_permissions
            WHERE target_role_id = (SELECT role_id FROM user_role)
              AND school_id = :school_id
              AND is_granted = true
        )
    """

    __tablename__ = "user_roles"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "school_id", "user_id",
            name="uq_auth_user_role_single",
        ),
        Index("ix_auth_user_role_user", "user_id", "school_id", "is_active"),
        Index("ix_auth_user_role_role", "role_id", "school_id"),
        {
            "schema": "auth",
            "comment": (
                "Exactly one role per user per school. Unique constraint has "
                "no role_id — a user cannot hold a second role row."
            ),
        },
    )

    # ── Scoping ────────────────────────────────────────────────────────────────
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    school_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        unique=True,
        comment="FK -> users.id. Unique: enforces one role row per user, period.",
    )
    role_id = Column(
        SmallInteger,
        ForeignKey("auth.roles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="The single platform role this user holds. RESTRICT prevents accidental role deletion.",
    )

    # ── Assignment Metadata ────────────────────────────────────────────────────
    assigned_by_user_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        comment="School admin who assigned this role",
    )
    assigned_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    user = relationship(
        "User",
        back_populates="user_role",
        foreign_keys=[user_id],
    )
    role = relationship("Role", back_populates="user_roles")

    def __repr__(self) -> str:
        return (
            f"<UserRole user_id={self.user_id} "
            f"role_id={self.role_id} "
            f"school_id={self.school_id}>"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 6 — SCHOOL ROLE STATISTICS (Real-time User Count per Role)
# ═══════════════════════════════════════════════════════════════════════════════

class SchoolRoleStats(BaseModel):
    """
    Real-time aggregate user count per role per school.

    Automatically maintained by PostgreSQL triggers on user_roles table.
    Provides instant visibility into role distribution across the school.

    Purpose:
        - Track how many users have each role in a school
        - Monitor subscription usage per role type
        - Generate role-based analytics and reports
        - Support Platform Service subscription limit checks

    Updated by triggers when:
        - New user assigned a role (INSERT on user_roles)
        - User's role removed (DELETE on user_roles)
        - User status changes (UPDATE on users.is_active)
        - User soft deleted (UPDATE on users.is_deleted)

    Examples:
        School A:
            STUDENT role      → 3890 total, 3850 active
            TEACHER role      →   45 total,   43 active
            PARENT role       → 3500 total, 3450 active
            PRINCIPAL role    →    2 total,    2 active
            LIBRARIAN role    →    1 total,    1 active

    Use cases:
        1. Admin Dashboard: "You have 45 teachers, 3890 students"
        2. Subscription Check: "Students: 3890 / 5000 (78% used)"
        3. Analytics: "Teacher count increased by 5 this month"
        4. Billing: "Calculate per-user pricing based on role breakdown"
    """

    __tablename__ = "school_role_stats"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "school_id", "role_id",
            name="uq_auth_school_role_stats",
        ),
        Index("ix_auth_srs_school", "school_id"),
        Index("ix_auth_srs_role", "role_id"),
        Index("ix_auth_srs_school_role", "school_id", "role_id"),
        {
            "schema": "auth",
            "comment": (
                "Real-time user count per role per school. "
                "Automatically updated by triggers on user_roles and users tables. "
                "Single source of truth for role-based subscription usage."
            ),
        },
    )

    # ── Scoping ────────────────────────────────────────────────────────────────
    tenant_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="Org boundary. Soft FK -> platform.tenants.id",
    )
    school_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="School boundary. Soft FK -> platform.schools.id",
    )
    role_id = Column(
        SmallInteger,
        ForeignKey("auth.roles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Platform role ID. FK -> auth.roles.id",
    )

    # ── Counters ───────────────────────────────────────────────────────────────
    total_users = Column(
        SmallInteger,
        nullable=False,
        default=0,
        comment=(
            "Total users assigned to this role (including inactive/deleted). "
            "Counts all user_roles records regardless of user.is_active or user.is_deleted."
        ),
    )
    active_users = Column(
        SmallInteger,
        nullable=False,
        default=0,
        comment=(
            "Active users with this role. "
            "WHERE user.is_active = true AND user.is_deleted = false AND user_role.is_active = true."
        ),
    )
    inactive_users = Column(
        SmallInteger,
        nullable=False,
        default=0,
        comment=(
            "Inactive users with this role. "
            "WHERE user.is_active = false AND user.is_deleted = false."
        ),
    )
    deleted_users = Column(
        SmallInteger,
        nullable=False,
        default=0,
        comment=(
            "Soft deleted users who had this role. "
            "WHERE user.is_deleted = true."
        ),
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    role = relationship(
        "Role",
        foreign_keys=[role_id],
    )

    def __repr__(self) -> str:
        return (
            f"<SchoolRoleStats school_id={self.school_id} "
            f"role_id={self.role_id} "
            f"total={self.total_users} active={self.active_users}>"
        )
