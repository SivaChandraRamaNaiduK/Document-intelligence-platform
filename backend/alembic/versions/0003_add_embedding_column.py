"""add embedding column to chunks

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-19

"""
import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("chunks", sa.Column("embedding", Vector(1024), nullable=True))
    # HNSW index for fast approximate nearest-neighbor search using cosine distance
    op.execute(
        "CREATE INDEX ix_chunks_embedding_hnsw ON chunks "
        "USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_chunks_embedding_hnsw")
    op.drop_column("chunks", "embedding")