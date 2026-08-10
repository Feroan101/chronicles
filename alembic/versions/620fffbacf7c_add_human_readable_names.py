"""add human-readable names

Revision ID: 620fffbacf7c
Revises: f8e261e677cb
Create Date: 2026-08-10 03:39:37.781818

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "620fffbacf7c"
down_revision: str | Sequence[str] | None = "f8e261e677cb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("memories") as batch_op:
        batch_op.add_column(sa.Column("name", sa.Text(), nullable=True))
        batch_op.create_unique_constraint("uq_memories_project_id_name", ["project_id", "name"])
    with op.batch_alter_table("snapshots") as batch_op:
        batch_op.add_column(sa.Column("name", sa.Text(), nullable=True))
        batch_op.create_unique_constraint("uq_snapshots_project_id_name", ["project_id", "name"])


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("snapshots") as batch_op:
        batch_op.drop_constraint("uq_snapshots_project_id_name", type_="unique")
        batch_op.drop_column("name")
    with op.batch_alter_table("memories") as batch_op:
        batch_op.drop_constraint("uq_memories_project_id_name", type_="unique")
        batch_op.drop_column("name")
