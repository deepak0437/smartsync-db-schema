"""
user_role.py — DEPRECATED / REMOVED

All RBAC models have been consolidated into role.py.

The following models are now in app/models/role.py:
    - UserRole                  → user_roles table
    - Role                      → roles table
    - Permission                → permissions table
    - RolePermissionTemplate    → role_permission_templates table
    - SchoolRole                → school_roles table
    - SchoolRolePermission      → school_role_permissions table

This file is kept as a redirect placeholder to avoid breaking any imports
during refactor. Import directly from role.py or via app.models.

See role.py for the complete six-layer RBAC implementation.
"""

# Re-export for backward compatibility during refactor
from .role import UserRole, SchoolRole, SchoolRolePermission  # noqa: F401
