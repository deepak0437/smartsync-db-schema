"""refactor: address review comments and apply DRY base model

Revision ID: 1ccbfb593bcd
Revises: 
Create Date: 2026-06-24 14:28:37.404260+00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1ccbfb593bcd'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass