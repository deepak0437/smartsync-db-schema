"""school_approval_workflow

Revision ID: 04
Revises: 03
Create Date: 2026-07-21 00:00:00.000000

Adds REJECTED to the school_status enum and approval-audit columns to
platform.schools, backing the Pending School Approval workflow (Platform
Admin approve/reject actions on a newly-created, still-PENDING school).

Postgres allows ALTER TYPE ... ADD VALUE inside a transaction as of PG12+,
as long as the new value isn't used by a DML statement in the same
transaction — it isn't here, so this is safe to run as a normal migration.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '04'
down_revision: Union[str, None] = '03'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE platform.school_status ADD VALUE IF NOT EXISTS 'REJECTED'")

    op.add_column('schools', sa.Column('approved_by', sa.BigInteger(), nullable=True), schema='platform')
    op.add_column('schools', sa.Column('approved_at', sa.BigInteger(), nullable=True), schema='platform')
    op.add_column('schools', sa.Column('rejected_by', sa.BigInteger(), nullable=True), schema='platform')
    op.add_column('schools', sa.Column('rejected_at', sa.BigInteger(), nullable=True), schema='platform')
    op.add_column(
        'schools',
        sa.Column(
            'approval_remarks',
            sa.Text(),
            nullable=True,
            comment='Free-text remarks from the Platform Admin, required on reject.',
        ),
        schema='platform',
    )


def downgrade() -> None:
    op.drop_column('schools', 'approval_remarks', schema='platform')
    op.drop_column('schools', 'rejected_at', schema='platform')
    op.drop_column('schools', 'rejected_by', schema='platform')
    op.drop_column('schools', 'approved_at', schema='platform')
    op.drop_column('schools', 'approved_by', schema='platform')

    # Postgres has no native "DROP VALUE" for enum types — removing REJECTED
    # would require rebuilding the type (rename, create new, migrate column,
    # drop old), which risks data loss if any row was ever set to REJECTED.
    # Not attempted here; a schema still needing to downgrade past this
    # revision must not have any school in REJECTED status first.
    pass
