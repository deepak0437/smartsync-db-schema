"""school_subscription_unique_active_index

Revision ID: 02
Revises: 01
Create Date: 2026-07-17 00:00:00.000000

Fixes uq_subscriptions_school_id_active: it was created as a plain
non-unique index (unique=False) despite its name and the SchoolSubscription
model's own docstring claiming it enforces "at most one active subscription
per school." Replaces it with a real partial unique index on
(school_id) WHERE status = 'ACTIVE'.
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
    op.drop_index('uq_subscriptions_school_id_active', table_name='school_subscriptions', schema='platform')
    op.create_index(
        'uq_subscriptions_school_id_active',
        'school_subscriptions',
        ['school_id'],
        unique=True,
        schema='platform',
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )


def downgrade() -> None:
    op.drop_index('uq_subscriptions_school_id_active', table_name='school_subscriptions', schema='platform')
    op.create_index(
        'uq_subscriptions_school_id_active',
        'school_subscriptions',
        ['school_id'],
        unique=False,
        schema='platform',
    )
