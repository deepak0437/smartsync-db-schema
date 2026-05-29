"""
Auth Service — Import all models so Alembic autogenerate can detect them.
This file must be imported in alembic/env.py target_metadata.
"""
# Import Base first
from app.models.base import Base  # noqa: F401

# Import all models to register them with Base.metadata
from app.models.tenant import Tenant  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.role import Role, Permission  # noqa: F401
from app.models.user_role import UserRole, RolePermission, UserPermission  # noqa: F401
from app.models.session import (  # noqa: F401
    UserSession,
    UserMFA,
    UserDevice,
    UserLoginHistory,
    PasswordResetToken,
    PasswordHistory,
)
from app.models.audit import APIKey, IPWhitelist, AuditLog, AuthEvent  # noqa: F401

# Expose metadata for Alembic
metadata = Base.metadata

__all__ = ["Base", "metadata"]
