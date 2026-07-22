"""seed core RBAC: 4 platform roles + a real CRUD-ish permission matrix

Revision ID: 03
Revises: 02
Create Date: 2026-07-22 00:00:00.000000

Every prior permission/role row in this workspace was hand-inserted via
ad-hoc SQL against prod (PLATFORM.EMAIL.WRITE, PLATFORM.USER.CREATE,
PLATFORM.LOGS.*, ...) with no seed/migration anywhere — a documented,
repeated source of local/prod drift. This migration is the first real,
reproducible source of truth for auth.roles / auth.permissions /
auth.role_permission_templates.

Keeps exactly 4 roles going forward: PLATFORM_ADMIN, MAINTAINER,
DEVELOPER, SCHOOL_ADMIN. Every other existing role row is deactivated
(is_active=false), NOT hard-deleted — auth.user_roles.role_id is
ondelete=RESTRICT and real users may still reference other roles at the
time this runs. Those rows become hard-deletable only after a later,
separate one-off wipe removes every auth.users row (see
smartsync-db-schema/scripts/wipe_platform_data.sql).

Permission design: reuse existing READ/WRITE/CREATE codes as-is (they
already give exactly what's needed for DEVELOPER=read-only and
MAINTAINER=create+read+update); add ONLY the missing DELETE-specific
codes for modules whose delete route currently reuses the combined
WRITE permission (AUTH.ROLE/PERMISSION/USER, PLATFORM.TENANT/SCHOOL) so
MAINTAINER can be granted "everything but delete" for real. LOGS/EMAIL
stay PLATFORM_ADMIN-only (not requested for other roles — least
privilege default). SCHOOL_ADMIN gets read access on ROLE/PERMISSION/
PLAN/ADDON, full USER CRUD (READ/WRITE/DELETE), and PLATFORM.USER.CREATE
(the Teams-tab create gate — still behaves as a team-role-restricted
create per smartsync-auth-service's user_service.py TEAM_ROLE_CODES /
restrict_to_team_roles).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '03'
down_revision: Union[str, None] = '02'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (code, name, description, category)
ROLES = [
    (
        "PLATFORM_ADMIN", "Platform Administrator",
        "Full, unrestricted access to every module. The only role that can "
        "manage roles/permissions themselves.",
        "SYSTEM",
    ),
    (
        "MAINTAINER", "Maintainer",
        "Create, read, and update access across every module. Cannot delete.",
        "SYSTEM",
    ),
    (
        "DEVELOPER", "Developer",
        "Read-only access across every module. Cannot create, update, or delete.",
        "SYSTEM",
    ),
    (
        "SCHOOL_ADMIN", "School Admin",
        "Single permission: create users. No other access.",
        "ADMINISTRATIVE",
    ),
]

# (code, name, description, module, submodule, action)
PERMISSIONS = [
    ("AUTH.ROLE.READ", "Read Roles", "View the role catalog.", "AUTH", "ROLE", "READ"),
    ("AUTH.ROLE.WRITE", "Write Roles", "Create/update roles.", "AUTH", "ROLE", "WRITE"),
    ("AUTH.ROLE.DELETE", "Delete Roles", "Soft-delete a role.", "AUTH", "ROLE", "DELETE"),

    ("AUTH.PERMISSION.READ", "Read Permissions", "View the permission catalog.", "AUTH", "PERMISSION", "READ"),
    ("AUTH.PERMISSION.WRITE", "Write Permissions", "Create/update permissions.", "AUTH", "PERMISSION", "WRITE"),
    ("AUTH.PERMISSION.DELETE", "Delete Permissions", "Soft-delete a permission.", "AUTH", "PERMISSION", "DELETE"),

    ("AUTH.USER.READ", "Read Users", "View users.", "AUTH", "USER", "READ"),
    ("AUTH.USER.WRITE", "Write Users", "Create/update users (full scope).", "AUTH", "USER", "WRITE"),
    ("AUTH.USER.DELETE", "Delete Users", "Soft-delete a user.", "AUTH", "USER", "DELETE"),

    ("PLATFORM.TENANT.READ", "Read Tenants", "View tenants.", "PLATFORM", "TENANT", "READ"),
    ("PLATFORM.TENANT.CREATE", "Create Tenants", "Create a tenant.", "PLATFORM", "TENANT", "CREATE"),
    ("PLATFORM.TENANT.WRITE", "Update Tenants", "Update/archive/restore a tenant.", "PLATFORM", "TENANT", "WRITE"),
    ("PLATFORM.TENANT.DELETE", "Delete Tenants", "Soft-delete a tenant.", "PLATFORM", "TENANT", "DELETE"),

    ("PLATFORM.SCHOOL.READ", "Read Schools", "View schools.", "PLATFORM", "SCHOOL", "READ"),
    ("PLATFORM.SCHOOL.CREATE", "Create Schools", "Create a school.", "PLATFORM", "SCHOOL", "CREATE"),
    ("PLATFORM.SCHOOL.WRITE", "Update Schools", "Update/archive/restore a school.", "PLATFORM", "SCHOOL", "WRITE"),
    ("PLATFORM.SCHOOL.DELETE", "Delete Schools", "Soft-delete a school.", "PLATFORM", "SCHOOL", "DELETE"),

    ("PLATFORM.PLAN.READ", "Read Plans", "View plans.", "PLATFORM", "PLAN", "READ"),
    ("PLATFORM.PLAN.WRITE", "Write Plans", "Create/update plans.", "PLATFORM", "PLAN", "WRITE"),

    ("PLATFORM.ADDON.READ", "Read Addons", "View addons.", "PLATFORM", "ADDON", "READ"),
    ("PLATFORM.ADDON.WRITE", "Write Addons", "Create/update addons.", "PLATFORM", "ADDON", "WRITE"),

    ("PLATFORM.SUBSCRIPTION.READ", "Read Subscriptions", "View subscriptions.", "PLATFORM", "SUBSCRIPTION", "READ"),
    ("PLATFORM.SUBSCRIPTION.WRITE", "Write Subscriptions", "Create subscriptions.", "PLATFORM", "SUBSCRIPTION", "WRITE"),
    ("PLATFORM.SUBSCRIPTION.MANAGE", "Manage Subscriptions", "Upgrade/downgrade/renew/cancel.", "PLATFORM", "SUBSCRIPTION", "MANAGE"),

    ("PLATFORM.ANALYTICS.READ", "Read Analytics", "View dashboard/analytics.", "PLATFORM", "ANALYTICS", "READ"),
    ("PLATFORM.AUDIT.READ", "Read Audit Log", "View the platform audit log.", "PLATFORM", "AUDIT", "READ"),
    ("PLATFORM.EMAIL.WRITE", "Send/Manage Emails", "Compose emails and manage templates.", "PLATFORM", "EMAIL", "WRITE"),

    ("PLATFORM.LOGS.READ", "Read Logs", "View service logs.", "PLATFORM", "LOGS", "READ"),
    ("PLATFORM.LOGS.LIVE", "Live-tail Logs", "Live-tail service logs.", "PLATFORM", "LOGS", "LIVE"),
    ("PLATFORM.LOGS.DOWNLOAD", "Download Logs", "Download log excerpts.", "PLATFORM", "LOGS", "DOWNLOAD"),
    ("PLATFORM.LOGS.EXPORT", "Export Logs", "Export logs.", "PLATFORM", "LOGS", "EXPORT"),
    ("PLATFORM.LOGS.STATS", "Read Log Stats", "View container stats.", "PLATFORM", "LOGS", "STATS"),
    ("PLATFORM.LOGS.ADMIN", "Administer Logs", "Full logs module administration.", "PLATFORM", "LOGS", "ADMIN"),

    ("PLATFORM.USER.CREATE", "Create Team Members", "Create a user restricted to the 4 platform roles (Teams tab).", "PLATFORM", "USER", "CREATE"),
]

ROLE_PERMISSION_MATRIX = {
    "PLATFORM_ADMIN": [code for code, *_ in PERMISSIONS],  # everything
    "MAINTAINER": [
        "AUTH.ROLE.READ", "AUTH.ROLE.WRITE",
        "AUTH.PERMISSION.READ", "AUTH.PERMISSION.WRITE",
        "AUTH.USER.READ", "AUTH.USER.WRITE",
        "PLATFORM.TENANT.READ", "PLATFORM.TENANT.CREATE", "PLATFORM.TENANT.WRITE",
        "PLATFORM.SCHOOL.READ", "PLATFORM.SCHOOL.CREATE", "PLATFORM.SCHOOL.WRITE",
        "PLATFORM.PLAN.READ", "PLATFORM.PLAN.WRITE",
        "PLATFORM.ADDON.READ", "PLATFORM.ADDON.WRITE",
        "PLATFORM.SUBSCRIPTION.READ", "PLATFORM.SUBSCRIPTION.WRITE", "PLATFORM.SUBSCRIPTION.MANAGE",
        "PLATFORM.ANALYTICS.READ",
        "PLATFORM.AUDIT.READ",
        "PLATFORM.USER.CREATE",
    ],
    "DEVELOPER": [
        "AUTH.ROLE.READ",
        "AUTH.PERMISSION.READ",
        "AUTH.USER.READ",
        "PLATFORM.TENANT.READ",
        "PLATFORM.SCHOOL.READ",
        "PLATFORM.PLAN.READ",
        "PLATFORM.ADDON.READ",
        "PLATFORM.SUBSCRIPTION.READ",
        "PLATFORM.ANALYTICS.READ",
        "PLATFORM.AUDIT.READ",
    ],
    "SCHOOL_ADMIN": [
        "AUTH.ROLE.READ",
        "AUTH.PERMISSION.READ",
        "AUTH.USER.READ",
        "AUTH.USER.WRITE",
        "AUTH.USER.DELETE",
        "PLATFORM.PLAN.READ",
        "PLATFORM.ADDON.READ",
        "PLATFORM.USER.CREATE",
    ],
}

_KEEP_ROLE_CODES = tuple(code for code, *_ in ROLES)
_KEEP_PERMISSION_CODES = tuple(code for code, *_ in PERMISSIONS)


def upgrade() -> None:
    conn = op.get_bind()

    # 1) Upsert the 4 target roles (role id 1 = PLATFORM_ADMIN must be
    #    preserved in place, not recreated — referenced everywhere).
    upsert_role = sa.text(
        "INSERT INTO auth.roles (code, name, description, category, is_active) "
        "VALUES (:code, :name, :description, :category, true) "
        "ON CONFLICT (code) DO UPDATE SET "
        "name = EXCLUDED.name, description = EXCLUDED.description, "
        "category = EXCLUDED.category, is_active = true, is_deleted = false, "
        "deleted_at = NULL, deleted_by = NULL"
    )
    for code, name, description, category in ROLES:
        conn.execute(
            upsert_role,
            {"code": code, "name": name, "description": description, "category": category},
        )

    # 2) Deactivate every other existing role (soft — user_roles.role_id is
    #    ondelete=RESTRICT, so a hard delete here would fail while real
    #    users still reference other roles; that cleanup happens later, in
    #    the one-off wipe script, after users are gone).
    conn.execute(
        sa.text("UPDATE auth.roles SET is_active = false WHERE code NOT IN :codes")
        .bindparams(sa.bindparam("codes", expanding=True)),
        {"codes": list(_KEEP_ROLE_CODES)},
    )

    # 3) Wipe all existing role<->permission mappings (safe — nothing else
    #    references this table).
    conn.execute(sa.text("DELETE FROM auth.role_permission_templates"))

    # 4) Upsert the full permission matrix.
    upsert_permission = sa.text(
        "INSERT INTO auth.permissions (code, name, description, module, submodule, action, is_active) "
        "VALUES (:code, :name, :description, :module, :submodule, :action, true) "
        "ON CONFLICT (code) DO UPDATE SET "
        "name = EXCLUDED.name, description = EXCLUDED.description, "
        "module = EXCLUDED.module, submodule = EXCLUDED.submodule, action = EXCLUDED.action, "
        "is_active = true, is_deleted = false, deleted_at = NULL, deleted_by = NULL"
    )
    for code, name, description, module, submodule, action in PERMISSIONS:
        conn.execute(
            upsert_permission,
            {
                "code": code, "name": name, "description": description,
                "module": module, "submodule": submodule, "action": action,
            },
        )

    # 5) Hard-delete any permission not in the new matrix (safe — step 3
    #    already emptied role_permission_templates, and that FK is CASCADE
    #    anyway).
    conn.execute(
        sa.text("DELETE FROM auth.permissions WHERE code NOT IN :codes")
        .bindparams(sa.bindparam("codes", expanding=True)),
        {"codes": list(_KEEP_PERMISSION_CODES)},
    )

    # 6) Insert fresh role<->permission mappings per the matrix.
    insert_mapping = (
        sa.text(
            "INSERT INTO auth.role_permission_templates (role_id, permission_id, is_active) "
            "SELECT r.id, p.id, true "
            "FROM auth.roles r, auth.permissions p "
            "WHERE r.code = :role_code AND p.code IN :permission_codes"
        )
        .bindparams(sa.bindparam("permission_codes", expanding=True))
    )
    for role_code, permission_codes in ROLE_PERMISSION_MATRIX.items():
        if not permission_codes:
            continue
        conn.execute(
            insert_mapping,
            {"role_code": role_code, "permission_codes": list(permission_codes)},
        )


def downgrade() -> None:
    """
    Best-effort reverse — removes the rows this migration inserted. Cannot
    restore the prior ad-hoc, hand-seeded state (it was never captured
    anywhere), so this only guarantees a clean slate, not a true rollback.
    """
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "DELETE FROM auth.role_permission_templates "
            "WHERE role_id IN (SELECT id FROM auth.roles WHERE code IN :codes)"
        ).bindparams(sa.bindparam("codes", expanding=True)),
        {"codes": list(_KEEP_ROLE_CODES)},
    )
    conn.execute(
        sa.text("DELETE FROM auth.permissions WHERE code IN :codes")
        .bindparams(sa.bindparam("codes", expanding=True)),
        {"codes": list(_KEEP_PERMISSION_CODES)},
    )
    conn.execute(
        sa.text("DELETE FROM auth.roles WHERE code IN :codes")
        .bindparams(sa.bindparam("codes", expanding=True)),
        {"codes": [c for c in _KEEP_ROLE_CODES if c != "PLATFORM_ADMIN"]},
    )
