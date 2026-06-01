"""
Auth Service — Models Package

All SQLAlchemy model classes for the Auth Service.

Tables by layer:

  Identity (auth schema):
    users                    → User identity + credentials + security state
    user_sessions            → Active JWT/refresh token sessions
    user_mfa                 → TOTP/SMS/Email 2FA configuration per user
    user_devices             → Trusted device registry
    user_login_history       → Login attempt audit trail
    password_reset_tokens    → Password reset flow tokens
    password_history         → Prevents password reuse

  RBAC Layer 1 & 2 (Platform-Controlled):
    roles                    → Platform role catalog (TEACHER, HOD, PRINCIPAL...)
    permissions              → Platform permission catalog (ACADEMICS.HOMEWORK.CREATE...)
    role_permission_templates → Platform's default role → permission mapping

  RBAC Layer 4 & 5 (School-Controlled):
    school_roles             → School enables/disables platform roles
    school_role_permissions  → School's effective permission set per role (customized)

  RBAC Layer 6 (User Assignment):
    user_roles               → Assigns roles to users (multi-role supported)

  Security & Audit:
    api_keys                 → API key auth for service-to-service calls
    ip_whitelists            → IP allowlist per tenant
    audit_logs               → Auth event audit trail
    auth_events              → Transactional outbox for event publishing

Usage:
    from app.models import User, UserSession, Role, Permission
    from app.models import SchoolRole, SchoolRolePermission, UserRole
    from app.models import Base  # for Alembic autogenerate
"""

# ── Base ──────────────────────────────────────────────────────────────────────
from .base import Base, BaseModel

# ── Identity ──────────────────────────────────────────────────────────────────
from .user import User

# ── RBAC ─────────────────────────────────────────────────────────────────────
from .role import (
    Role,
    Permission,
    RolePermissionTemplate,
    SchoolRole,
    SchoolRolePermission,
    UserRole,
)

# ── Sessions & Security ───────────────────────────────────────────────────────
from .session import (
    UserSession,
    UserMFA,
    UserDevice,
    UserLoginHistory,
    PasswordResetToken,
    PasswordHistory,
)

# ── Audit & Events ────────────────────────────────────────────────────────────
from .audit import APIKey, IPWhitelist, AuditLog, AuthEvent

__all__ = [
    # Base
    "Base",
    "BaseModel",
    # Identity
    "User",
    # RBAC — Platform Layer
    "Role",
    "Permission",
    "RolePermissionTemplate",
    # RBAC — School Layer
    "SchoolRole",
    "SchoolRolePermission",
    # RBAC — User Assignment
    "UserRole",
    # Sessions
    "UserSession",
    "UserMFA",
    "UserDevice",
    "UserLoginHistory",
    "PasswordResetToken",
    "PasswordHistory",
    # Security & Audit
    "APIKey",
    "IPWhitelist",
    "AuditLog",
    "AuthEvent",
]