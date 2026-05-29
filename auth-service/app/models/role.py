"""
Role and Permission models for RBAC.
"""
from sqlalchemy import Boolean, Column, Integer, String, Text, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .base import BaseModel, Base


class Permission(Base):
    """
    Global permission definitions for fine-grained access control.
    Permissions are global (not per-tenant) and defined by the platform.

    Format: SERVICE.RESOURCE.ACTION
    Examples:
        ACADEMICS.REVIEW.CREATE
        ACADEMICS.ATTENDANCE.MARK
        FINANCE.FEE.READ
        HR.PAYROLL.APPROVE
    """
    __tablename__ = "permissions"
    __table_args__ = (
        UniqueConstraint("permission_code", name="uq_auth_permission_code"),
        {"schema": "auth", "comment": "Platform-wide permission definitions (global, not per-tenant)"},
    )

    from uuid import uuid4
    from sqlalchemy import func
    from datetime import timezone

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)

    # Permission Information
    permission_code = Column(String(150), unique=True, nullable=False, index=True, comment="Dotted permission code e.g. ACADEMICS.REVIEW.CREATE")
    permission_name = Column(String(255), nullable=False)
    permission_description = Column(Text, nullable=True)

    # Resource & Action
    service = Column(String(50), nullable=False, index=True, comment="Service that owns this permission: ACADEMICS | FINANCE | HR ...")
    resource = Column(String(100), nullable=False, index=True, comment="Resource being acted on: REVIEW | FEE | ATTENDANCE ...")
    action = Column(String(50), nullable=False, comment="Action: CREATE | READ | UPDATE | DELETE | APPROVE | EXPORT ...")

    # Category
    permission_category = Column(String(50), nullable=True, comment="ACADEMIC | ADMINISTRATIVE | OPERATIONAL | SYSTEM")

    # System Permission flag
    is_system_permission = Column(Boolean, default=True, nullable=False)

    # Metadata
    extra_metadata = Column(JSONB, default={})

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps (no BaseModel since global)
    from sqlalchemy import DateTime
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    role_permissions = relationship("RolePermission", back_populates="permission", cascade="all, delete-orphan")
    user_permissions = relationship("UserPermission", back_populates="permission", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Permission(code={self.permission_code})>"


class Role(BaseModel):
    """
    Role definitions for role-based access control (RBAC).

    Examples: STUDENT | TEACHER | CLASS_TEACHER | SUBJECT_TEACHER | HOD | PRINCIPAL | ADMIN
    """
    __tablename__ = "roles"
    __table_args__ = (
        UniqueConstraint("tenant_id", "role_code", name="uq_auth_tenant_role_code"),
        {"schema": "auth", "comment": "RBAC roles per tenant"},
    )

    # Foreign Keys
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth.tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Role Information
    role_code = Column(String(100), nullable=False, index=True, comment="STUDENT | TEACHER | CLASS_TEACHER | HOD | PRINCIPAL ...")
    role_name = Column(String(255), nullable=False)
    role_description = Column(Text, nullable=True)
    role_type = Column(String(50), nullable=False, comment="SYSTEM | CUSTOM")
    role_category = Column(String(50), nullable=True, comment="ACADEMIC | ADMINISTRATIVE | OPERATIONAL")

    # System Role
    is_system_role = Column(Boolean, default=False, nullable=False, comment="System roles cannot be deleted")

    # Hierarchy level for priority resolution
    hierarchy_level = Column(Integer, default=0, comment="0=lowest priority, 100=highest (SUPER_ADMIN)")

    # Cached permissions for fast authorization checks
    permissions_cache = Column(JSONB, default=[], comment="Cached permission code list — refresh on role_permission change")

    # Extra Metadata
    extra_metadata = Column(JSONB, default={})

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    tenant = relationship("Tenant", back_populates="roles")
    user_roles = relationship("UserRole", back_populates="role", cascade="all, delete-orphan")
    role_permissions = relationship("RolePermission", back_populates="role", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Role(code={self.role_code}, name={self.role_name})>"
