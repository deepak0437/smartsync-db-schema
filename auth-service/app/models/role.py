"""
RBAC Models — Auth Service

Architecture: Platform-Controlled RBAC with School-Level Customization

Three-layer design:
  Layer 1 → roles                    Platform-defined. Read-only for schools.
  Layer 2 → permissions              Platform-defined. Read-only for schools.
  Layer 3 → role_permission_templates  Platform defaults. Schools customize via school_role_permissions.

School Customization Layer:
  Layer 4 → school_roles             School can enable/disable roles for their school.
  Layer 5 → school_role_permissions  School's override of which permissions a role has.

User Assignment:
  Layer 6 → user_roles               Assigns one or more roles to a user, scoped to school.

JWT Effective Permissions are resolved from school_role_permissions, NOT role_permission_templates.
"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from uuid import uuid4

from .base import Base, BaseModel


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 1 — ROLES (Platform-Controlled Master Table)
# ═══════════════════════════════════════════════════════════════════════════════

class Role(Base):
    """
    Platform-defined role catalog.

    Created and maintained ONLY by the SmartSync platform team.
    Schools cannot create or delete roles — they can only enable/disable
    and customize permissions for their school via SchoolRole.

    Examples:
        STUDENT, PARENT, TEACHER, CLASS_TEACHER, SUBJECT_TEACHER,
        HOD, PRINCIPAL, VICE_PRINCIPAL, ACCOUNTANT, LIBRARIAN,
        WARDEN, DRIVER, RECEPTIONIST, HR, SECURITY_GUARD,
        LAB_ASSISTANT, SPORTS_COACH, COUNSELOR, ...

    Expected: 40–50 roles total.
    """

    __tablename__ = "roles"
    __table_args__ = (
        UniqueConstraint("code", name="uq_auth_role_code"),
        Index("ix_auth_role_category", "category"),
        {
            "schema": "auth",
            "comment": "Platform-defined role catalog. Schools cannot create roles.",
        },
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)

    # ── Identity ───────────────────────────────────────────────────────────────
    code = Column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        comment=(
            "Machine-readable role code. UPPER_SNAKE_CASE. "
            "Used in JWT 'roles' claim and permission checks. "
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
        comment="Description of what this role does in the school context",
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
    hierarchy_level = Column(
        Integer,
        nullable=False,
        default=1,
        comment=(
            "Authority level for conflict resolution. "
            "Higher = more authority. "
            "STUDENT=1, TEACHER=10, CLASS_TEACHER=15, HOD=20, "
            "PRINCIPAL=50, SUPER_ADMIN=100"
        ),
    )
    is_multi_assignable = Column(
        Boolean,
        nullable=False,
        default=True,
        comment=(
            "Whether a user can hold this role alongside other roles. "
            "False for mutually exclusive roles (e.g. STUDENT cannot also be TEACHER)."
        ),
    )

    # ── Defaults ───────────────────────────────────────────────────────────────
    is_enabled_by_default = Column(
        Boolean,
        nullable=False,
        default=True,
        comment=(
            "Whether this role is automatically available to all schools. "
            "False = school must explicitly enable it via SchoolRole."
        ),
    )

    # ── Status ─────────────────────────────────────────────────────────────────
    is_active = Column(Boolean, nullable=False, default=True, index=True)

    # ── Timestamps (platform-managed, not using BaseModel) ────────────────────
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    permission_templates = relationship(
        "RolePermissionTemplate",
        back_populates="role",
        cascade="all, delete-orphan",
    )
    school_roles = relationship(
        "SchoolRole",
        back_populates="role",
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

class Permission(Base):
    """
    Platform-defined permission catalog.

    Created and maintained ONLY by the SmartSync platform team.
    Schools cannot create permissions.

    Naming convention: MODULE.SUBMODULE.ACTION
    Examples:
        ACADEMICS.HOMEWORK.CREATE
        ACADEMICS.HOMEWORK.READ
        ACADEMICS.ATTENDANCE.MARK
        ACADEMICS.ATTENDANCE.READ
        ACADEMICS.REVIEW.WRITE
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

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)

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

    # ── Timestamps ─────────────────────────────────────────────────────────────
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

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
# LAYER 3 — ROLE PERMISSION TEMPLATES (Platform Defaults)
# ═══════════════════════════════════════════════════════════════════════════════

class RolePermissionTemplate(Base):
    """
    Platform's default mapping of Role → Permission.

    This is the baseline that every school starts with when they
    enable a role. Schools can then customize their mapping via SchoolRolePermission.

    Only the SmartSync platform team can modify these templates.
    Schools never write to this table.

    Example defaults:
        TEACHER      → ACADEMICS.HOMEWORK.CREATE
        TEACHER      → ACADEMICS.HOMEWORK.READ
        TEACHER      → ACADEMICS.ATTENDANCE.MARK
        STUDENT      → ACADEMICS.HOMEWORK.READ
        STUDENT      → ACADEMICS.ATTENDANCE.READ
        PRINCIPAL    → ACADEMICS.ATTENDANCE.READ
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
                "Platform's default role-permission mapping. "
                "Read-only for schools. Schools customize via SchoolRolePermission."
            ),
        },
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    role_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth.roles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    permission_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth.permissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # ── Relationships ──────────────────────────────────────────────────────────
    role = relationship("Role", back_populates="permission_templates")
    permission = relationship("Permission", back_populates="role_templates")

    def __repr__(self) -> str:
        return f"<RolePermissionTemplate role_id={self.role_id} perm_id={self.permission_id}>"


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 4 — SCHOOL ROLES (School Enables/Disables Platform Roles)
# ═══════════════════════════════════════════════════════════════════════════════

class SchoolRole(BaseModel):
    """
    A school's activation of a platform-defined role.

    Represents the school's decision to use a particular role.
    Automatically seeded from roles.is_enabled_by_default on school creation.

    Schools can:
        ✅ Enable a role   (is_enabled = True)
        ✅ Disable a role  (is_enabled = False)
        ❌ Create new roles
        ❌ Delete platform roles

    Design note:
        This table also stores the school's alias for the role.
        E.g. platform calls it 'CLASS_TEACHER', but school wants to display
        it as 'Form Teacher' — they set display_name = 'Form Teacher'.
    """

    __tablename__ = "school_roles"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "school_id", "role_id",
            name="uq_auth_school_role",
        ),
        Index("ix_auth_school_role_school", "school_id"),
        Index("ix_auth_school_role_enabled", "school_id", "is_enabled"),
        {
            "schema": "auth",
            "comment": "Per-school activation of platform roles. Schools can enable/disable roles.",
        },
    )

    # ── Scoping ────────────────────────────────────────────────────────────────
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    school_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    role_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth.roles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── School Customization ───────────────────────────────────────────────────
    is_enabled = Column(
        Boolean,
        nullable=False,
        default=True,
        comment=(
            "True = role is available in this school. "
            "False = role disabled — cannot be assigned to users."
        ),
    )
    display_name = Column(
        String(255),
        nullable=True,
        comment=(
            "School's custom display name for this role. "
            "Falls back to role.name if null. "
            "E.g. school calls CLASS_TEACHER as 'Form Teacher'"
        ),
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    role = relationship("Role", back_populates="school_roles")
    school_role_permissions = relationship(
        "SchoolRolePermission",
        back_populates="school_role",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<SchoolRole school_id={self.school_id} "
            f"role_id={self.role_id} enabled={self.is_enabled}>"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 5 — SCHOOL ROLE PERMISSIONS (School's Permission Customization)
# ═══════════════════════════════════════════════════════════════════════════════

class SchoolRolePermission(BaseModel):
    """
    School's customized permission mapping for a role.

    This is the EFFECTIVE permission table used during login JWT generation.

    Flow:
        1. On school activation: seeded from RolePermissionTemplate.
        2. School admin can add/remove permissions per role.
        3. At login: fetch rows WHERE school_id = ? AND role_id IN (user's roles)
           AND is_granted = True → these become the user's effective permissions.

    Example:
        School A enables ATTENDANCE.MARK for TEACHER role.
        School B leaves TEACHER with only ATTENDANCE.READ.

        Both schools use the same platform TEACHER role,
        but their effective permissions differ.

    Design:
        Seeded automatically from RolePermissionTemplate on school onboarding.
        School can then GRANT additional permissions or REVOKE defaults.
        is_granted = True  → permission is active
        is_granted = False → permission explicitly revoked (not just absent)
    """

    __tablename__ = "school_role_permissions"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "school_id", "school_role_id", "permission_id",
            name="uq_auth_school_role_permission",
        ),
        Index("ix_auth_srp_lookup", "school_id", "school_role_id", "is_granted"),
        Index("ix_auth_srp_permission", "permission_id"),
        {
            "schema": "auth",
            "comment": (
                "Effective permission set per role per school. "
                "Used during JWT generation. "
                "Seeded from RolePermissionTemplate, customized by school admin."
            ),
        },
    )

    # ── Scoping ────────────────────────────────────────────────────────────────
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    school_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    school_role_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth.school_roles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    permission_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth.permissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Grant State ────────────────────────────────────────────────────────────
    is_granted = Column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment=(
            "True  = permission is active for this role in this school. "
            "False = permission explicitly revoked (overrides template default)."
        ),
    )

    # ── Change Tracking ────────────────────────────────────────────────────────
    source = Column(
        String(20),
        nullable=False,
        default="TEMPLATE",
        comment=(
            "How this row was created. "
            "TEMPLATE = auto-seeded from RolePermissionTemplate. "
            "SCHOOL_OVERRIDE = manually set by school admin."
        ),
    )
    modified_by_user_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        comment=(
            "School admin user_id who last modified this grant. "
            "Null for template-seeded rows."
        ),
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    school_role = relationship("SchoolRole", back_populates="school_role_permissions")
    permission = relationship("Permission", back_populates="school_role_permissions")

    def __repr__(self) -> str:
        return (
            f"<SchoolRolePermission school_id={self.school_id} "
            f"school_role_id={self.school_role_id} "
            f"perm_id={self.permission_id} granted={self.is_granted}>"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 6 — USER ROLES (Assigns Roles to Users)
# ═══════════════════════════════════════════════════════════════════════════════

class UserRole(BaseModel):
    """
    Assigns one or more roles to a user within a school.

    Multi-role support:
        A user can hold multiple roles simultaneously.
        E.g. Rahul is both TEACHER and CLASS_TEACHER.
        E.g. Suresh is both TEACHER and HOSTEL_WARDEN.

    Temporal support:
        Roles can be time-boxed (e.g. acting principal for 2 weeks).

    Scope:
        Role assignments are scoped to (tenant_id, school_id, user_id).
        A user transferring to another school gets a new UserRole
        in the new school.

    At login, effective permissions are computed as:
        SELECT p.code
        FROM school_role_permissions srp
        JOIN permissions p ON p.id = srp.permission_id
        WHERE srp.school_id = :school_id
          AND srp.school_role_id IN (
              SELECT sr.id FROM school_roles sr
              JOIN user_roles ur ON ur.role_id = sr.role_id
              WHERE ur.user_id = :user_id
                AND ur.school_id = :school_id
                AND ur.is_active = true
          )
          AND srp.is_granted = true
    """

    __tablename__ = "user_roles"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "school_id", "user_id", "role_id",
            name="uq_auth_user_role",
        ),
        Index("ix_auth_user_role_user", "user_id", "school_id", "is_active"),
        {
            "schema": "auth",
            "comment": "Role assignments per user per school. Supports multi-role.",
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
    )
    role_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth.roles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Platform role ID. RESTRICT so roles can't be accidentally deleted.",
    )

    # ── Assignment Metadata ────────────────────────────────────────────────────
    is_primary = Column(
        Boolean,
        nullable=False,
        default=False,
        comment=(
            "True = this is the user's primary display role. "
            "Used in UI headers and reports. Only one per user per school."
        ),
    )
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

    # ── Temporal Bounds ────────────────────────────────────────────────────────
    valid_from = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Role becomes effective at this time. Null = immediately.",
    )
    valid_until = Column(
        DateTime(timezone=True),
        nullable=True,
        comment=(
            "Role expires at this time. Null = no expiry. "
            "E.g. acting principal assignment for 2 weeks."
        ),
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    user = relationship(
        "User",
        back_populates="user_roles",
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
# LAYER 7 — SCHOOL ROLE STATISTICS (Real-time User Count per Role)
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
        - New user assigned to role (INSERT on user_roles)
        - User role removed (DELETE on user_roles)
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
        comment="Org boundary. Soft FK → platform.tenants.id",
    )
    school_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="School boundary. Soft FK → platform.schools.id",
    )
    role_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth.roles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Platform role ID. FK → auth.roles.id",
    )

    # ── Counters ───────────────────────────────────────────────────────────────
    total_users = Column(
        Integer,
        nullable=False,
        default=0,
        comment=(
            "Total users assigned to this role (including inactive/deleted). "
            "Counts all user_roles records regardless of user.is_active or user.is_deleted."
        ),
    )
    active_users = Column(
        Integer,
        nullable=False,
        default=0,
        comment=(
            "Active users with this role. "
            "WHERE user.is_active = true AND user.is_deleted = false AND user_role.is_active = true."
        ),
    )
    inactive_users = Column(
        Integer,
        nullable=False,
        default=0,
        comment=(
            "Inactive users with this role. "
            "WHERE user.is_active = false AND user.is_deleted = false."
        ),
    )
    deleted_users = Column(
        Integer,
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
