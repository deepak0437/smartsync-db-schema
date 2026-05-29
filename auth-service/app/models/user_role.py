"""
User-Role and Role-Permission mapping models.
"""
from sqlalchemy import Boolean, Column, Date, DateTime, String, Text, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .base import BaseModel


class UserRole(BaseModel):
    """
    Many-to-many mapping between users and roles.

    Supports:
    - Multiple roles per user (e.g., Teacher + Class Teacher + HOD simultaneously)
    - Temporary role assignments (valid_from / valid_until)
    - Primary role designation for UI defaults
    """
    __tablename__ = "user_roles"
    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", "role_id", name="uq_auth_tenant_user_role"),
        {"schema": "auth", "comment": "User-Role many-to-many mapping with temporal support"},
    )

    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("auth.tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="CASCADE"), nullable=False, index=True)
    role_id = Column(UUID(as_uuid=True), ForeignKey("auth.roles.id", ondelete="CASCADE"), nullable=False, index=True)

    # Assignment context
    assigned_by = Column(UUID(as_uuid=True), ForeignKey("auth.users.id"), nullable=True, comment="Admin who assigned this role")
    assigned_at = Column(DateTime(timezone=True), nullable=True)

    # Temporal validity
    valid_from = Column(Date, nullable=True, comment="Role active from date (null = immediate)")
    valid_until = Column(Date, nullable=True, comment="Role expires on date (null = never)")

    # Primary role flag
    is_primary_role = Column(Boolean, default=False, nullable=False, comment="User's primary display role")

    # Extra Metadata
    extra_metadata = Column(JSONB, default={})
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    user = relationship("User", back_populates="user_roles", foreign_keys=[user_id])
    role = relationship("Role", back_populates="user_roles")

    def __repr__(self):
        return f"<UserRole(user_id={self.user_id}, role_id={self.role_id})>"


class RolePermission(BaseModel):
    """
    Many-to-many mapping between roles and permissions.
    Defines what a role is authorized to do.
    """
    __tablename__ = "role_permissions"
    __table_args__ = (
        UniqueConstraint("tenant_id", "role_id", "permission_id", name="uq_auth_tenant_role_permission"),
        {"schema": "auth", "comment": "Role-Permission many-to-many mapping"},
    )

    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("auth.tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    role_id = Column(UUID(as_uuid=True), ForeignKey("auth.roles.id", ondelete="CASCADE"), nullable=False, index=True)
    permission_id = Column(UUID(as_uuid=True), ForeignKey("auth.permissions.id", ondelete="CASCADE"), nullable=False, index=True)

    # Grant context
    granted_by = Column(UUID(as_uuid=True), ForeignKey("auth.users.id"), nullable=True)
    granted_at = Column(DateTime(timezone=True), nullable=True)

    # Extra Metadata
    extra_metadata = Column(JSONB, default={})
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    role = relationship("Role", back_populates="role_permissions")
    permission = relationship("Permission", back_populates="role_permissions")

    def __repr__(self):
        return f"<RolePermission(role_id={self.role_id}, permission_id={self.permission_id})>"


class UserPermission(BaseModel):
    """
    Direct user-level permissions that OVERRIDE role-based permissions.

    Types:
    - GRANT: Explicitly grant a permission to a user (above their role)
    - DENY:  Explicitly deny a permission (overrides any role that grants it)
    """
    __tablename__ = "user_permissions"
    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", "permission_id", name="uq_auth_tenant_user_permission"),
        {"schema": "auth", "comment": "User-level permission overrides (GRANT or DENY)"},
    )

    # Foreign Keys
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("auth.tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="CASCADE"), nullable=False, index=True)
    permission_id = Column(UUID(as_uuid=True), ForeignKey("auth.permissions.id", ondelete="CASCADE"), nullable=False, index=True)

    # Override type
    permission_type = Column(String(20), nullable=False, comment="GRANT | DENY")

    # Grant context
    granted_by = Column(UUID(as_uuid=True), ForeignKey("auth.users.id"), nullable=True)
    granted_at = Column(DateTime(timezone=True), nullable=True)

    # Temporal validity
    valid_from = Column(Date, nullable=True)
    valid_until = Column(Date, nullable=True)

    # Reason for override
    reason = Column(Text, nullable=True, comment="Admin justification for the override")

    # Extra Metadata
    extra_metadata = Column(JSONB, default={})
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    user = relationship("User", back_populates="user_permissions", foreign_keys=[user_id])
    permission = relationship("Permission", back_populates="user_permissions")

    def __repr__(self):
        return f"<UserPermission(user_id={self.user_id}, permission_id={self.permission_id}, type={self.permission_type})>"
