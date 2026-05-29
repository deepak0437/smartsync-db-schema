"""
Auth Service Models — Export all models for Alembic autogenerate and application imports.
"""
from .base import Base, BaseModel, TenantBaseModel
from .tenant import Tenant
from .user import User
from .role import Role, Permission
from .user_role import UserRole, RolePermission, UserPermission
from .session import (
    UserSession,
    UserMFA,
    UserDevice,
    UserLoginHistory,
    PasswordResetToken,
    PasswordHistory,
)
from .audit import APIKey, IPWhitelist, AuditLog, AuthEvent

__all__ = [
    # Base
    "Base",
    "BaseModel",
    "TenantBaseModel",
    # Core
    "Tenant",
    "User",
    # RBAC
    "Role",
    "Permission",
    "UserRole",
    "RolePermission",
    "UserPermission",
    # Sessions & Auth
    "UserSession",
    "UserMFA",
    "UserDevice",
    "UserLoginHistory",
    "PasswordResetToken",
    "PasswordHistory",
    # Security & Events
    "APIKey",
    "IPWhitelist",
    "AuditLog",
    "AuthEvent",
]
