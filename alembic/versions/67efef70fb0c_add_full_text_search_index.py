"""add full text search index over memory version content

Revision ID: 67efef70fb0c
Revises: 4cd6c8553ab4
Create Date: 2026-08-08 08:30:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "67efef70fb0c"
down_revision: str | Sequence[str] | None = "4cd6c8553ab4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the FTS5 search index over Memory Version content.

    Only the ``content`` column is indexed. The Memory and Memory Version
    identifiers are stored UNINDEXED so each indexed row can be associated
    with its owning objects.
    """
    op.execute(
        "CREATE VIRTUAL TABLE search_index USING fts5("
        "memory_id UNINDEXED, "
        "memory_version_id UNINDEXED, "
        "content"
        ")"
    )
    # Backfill the index with existing Memory Versions.
    op.execute(
        "INSERT INTO search_index (memory_id, memory_version_id, content) "
        "SELECT memory_id, id, content FROM memory_versions"
    )
    # Keep the index consistent when a new Version is created.
    op.execute(
        "CREATE TRIGGER trg_search_index_insert "
        "AFTER INSERT ON memory_versions "
        "BEGIN "
        "INSERT INTO search_index (memory_id, memory_version_id, content) "
        "VALUES (NEW.memory_id, NEW.id, NEW.content); "
        "END"
    )


def downgrade() -> None:
    """Drop the search index and its synchronization trigger."""
    op.execute("DROP TRIGGER IF EXISTS trg_search_index_insert")
    op.execute("DROP TABLE IF EXISTS search_index")
