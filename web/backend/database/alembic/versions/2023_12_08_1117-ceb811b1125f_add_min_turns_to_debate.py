"""Add min_turns to Debate

Revision ID: ceb811b1125f
Revises:
Create Date: 2023-12-08 11:17:29.095011

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ceb811b1125f"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("debate", sa.Column("min_turns", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("debate", "min_turns")
