"""
Auth Service — Models Package
Database schema: auth

Tables
------

Identity (3 tables in user.py, all 1-to-1):
    users               Identity anchor: username, email, display_name,
                        is_active, 2FA flags. Low-churn.
    user_credentials    Password hash, salt, policy flags. Changes ~1/year.
    user_security       Brute-force counters + lock state. High-churn.

RBAC — Platform Layer (SmartSync team only):
    roles                      Role catalog (40–50 roles)
    permissions                Permission catalog (500–1,000)
    role_permission_templates  Default role → permission mapping

RBAC — School Layer (customized per school):
    school_roles             School enables/disables/renames roles
    school_role_permissions  School's effective permission set per role

RBAC — User Assignment:
    user_roles   Multi-role assignments per user per school.
                 Primary role drives domain service routing.

Sessions & MFA:
    user_sessions   Active JWT / refresh token sessions
    user_mfa        MFA secret storage (TOTP, backup codes)
    user_devices    Trusted device registry

Audit & History (append-only):
    user_login_history     Every login attempt — success and failure
    password_reset_tokens  Short-lived reset tokens (15-min TTL)
    password_history       Previous N hashes (reuse prevention)

Security Infrastructure:
    api_keys     Service-to-service API keys
    ip_whitelist Tenant-level IP allowlists
    audit_logs   Immutable action audit trail
    auth_events  Transactional outbox for event publishing

Removed / deleted:
    user_type column       → not needed; derive from primary UserRole
    user_type.py           → deleted
    user_preferences.py    → deleted
    user_auth_credentials  → merged into user_credentials
    user_security_settings → merged into user_security
"""

# ── Base ──────────────────────────────────────────────────────────────────────
from .base import Base, BaseModel

# ── Identity (3 tables — one file) ────────────────────────────────────────────
from .user import User, UserCredentials, UserSecurity

# ── RBAC ─────────────────────────────────────────────────────────────────────
from .role import (
    Role,
    Permission,
    RolePermissionTemplate,
    SchoolRole,
    SchoolRolePermission,
    UserRole,
)

# ── Sessions, MFA, Devices, Password Flow ─────────────────────────────────────
from .session import (
    UserSession,
    UserMFA,
    UserDevice,
    UserLoginHistory,
    PasswordResetToken,
    PasswordHistory,
)

# ── Security Infrastructure & Events ──────────────────────────────────────────
from .audit import APIKey, IPWhitelist, AuditLog, AuthEvent

__all__ = [
    # Base
    "Base",
    "BaseModel",
    # Identity
    "User",
    "UserCredentials",
    "UserSecurity",
    # RBAC — Platform
    "Role",
    "Permission",
    "RolePermissionTemplate",
    # RBAC — School
    "SchoolRole",
    "SchoolRolePermission",
    # RBAC — Assignment
    "UserRole",
    # Sessions
    "UserSession",
    "UserMFA",
    "UserDevice",
    # Audit / History
    "UserLoginHistory",
    "PasswordResetToken",
    "PasswordHistory",
    # Security Infrastructure
    "APIKey",
    "IPWhitelist",
    "AuditLog",
    "AuthEvent",
]