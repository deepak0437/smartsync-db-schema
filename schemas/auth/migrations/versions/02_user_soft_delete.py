"""user soft delete

Revision ID: 02
Revises: 01
Create Date: 2026-07-17 00:00:00.000000

Adds SoftDeleteMixin columns (deleted_at, is_deleted, deleted_by) to
auth.users — the model's own is_active comment already referenced
"is_deleted from BaseModel" as the intended removal mechanism, but the
column never existed. Needed for Phase 2's admin-triggered user delete.

Also converts the three (tenant_id, school_id, {username,email,mobile_number})
UniqueConstraints into partial unique indexes scoped WHERE deleted_at IS NULL,
matching the convention already used on platform.tenants/schools — so a
soft-deleted user's username/email/mobile frees up for reuse.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '02'
down_revision: Union[str, None] = '01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('deleted_at', sa.BigInteger(), nullable=True), schema='auth')
    op.add_column(
        'users',
        sa.Column('is_deleted', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        schema='auth',
    )
    op.add_column('users', sa.Column('deleted_by', sa.BigInteger(), nullable=True), schema='auth')

    op.drop_constraint('uq_users_tenant_school_username', 'users', schema='auth', type_='unique')
    op.drop_constraint('uq_users_tenant_school_email', 'users', schema='auth', type_='unique')
    op.drop_constraint('uq_users_tenant_school_mobile', 'users', schema='auth', type_='unique')

    op.create_index(
        'uq_users_tenant_school_username',
        'users',
        ['tenant_id', 'school_id', 'username'],
        unique=True,
        schema='auth',
        postgresql_where=sa.text('deleted_at IS NULL'),
    )
    op.create_index(
        'uq_users_tenant_school_email',
        'users',
        ['tenant_id', 'school_id', 'email'],
        unique=True,
        schema='auth',
        postgresql_where=sa.text('deleted_at IS NULL'),
    )
    op.create_index(
        'uq_users_tenant_school_mobile',
        'users',
        ['tenant_id', 'school_id', 'mobile_number'],
        unique=True,
        schema='auth',
        postgresql_where=sa.text('deleted_at IS NULL'),
    )


def downgrade() -> None:
    op.drop_index('uq_users_tenant_school_username', table_name='users', schema='auth')
    op.drop_index('uq_users_tenant_school_email', table_name='users', schema='auth')
    op.drop_index('uq_users_tenant_school_mobile', table_name='users', schema='auth')

    op.create_unique_constraint(
        'uq_users_tenant_school_username', 'users', ['tenant_id', 'school_id', 'username'], schema='auth'
    )
    op.create_unique_constraint(
        'uq_users_tenant_school_email', 'users', ['tenant_id', 'school_id', 'email'], schema='auth'
    )
    op.create_unique_constraint(
        'uq_users_tenant_school_mobile', 'users', ['tenant_id', 'school_id', 'mobile_number'], schema='auth'
    )

    op.drop_column('users', 'deleted_by', schema='auth')
    op.drop_column('users', 'is_deleted', schema='auth')
    op.drop_column('users', 'deleted_at', schema='auth')
