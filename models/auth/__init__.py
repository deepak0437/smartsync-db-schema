"""SmartSync Auth & RBAC models — public API.

All models and enums are re-exported here for clean imports
and Alembic metadata discovery.
"""

from .audit import APIKey, AuditLog, AuthEvent, IPWhitelist
from .role import (
    Permission,
    Role,
    RolePermissionTemplate,
    SchoolRolePermission,
    SchoolRoleStats,
    UserRole,
)
from .session import OTPChannel, OTPType, UserOTP, UserSession
from .user import (
    LoginFailureReason,
    User,
    UserCredentials,
    UserLoginHistory,
    UserVerification,
)

__all__ = [
    # audit
    "APIKey",
    "IPWhitelist",
    "AuditLog",
    "AuthEvent",
    # role
    "Role",
    "Permission",
    "RolePermissionTemplate",
    "SchoolRolePermission",
    "UserRole",
    "SchoolRoleStats",
    # session
    "OTPType",
    "OTPChannel",
    "UserSession",
    "UserOTP",
    # user
    "LoginFailureReason",
    "User",
    "UserCredentials",
    "UserVerification",
    "UserLoginHistory",
]
