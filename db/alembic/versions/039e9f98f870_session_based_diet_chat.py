"""session based diet chat

Revision ID: 039e9f98f870
Revises: ad0291fbd3b8
Create Date: 2026-10-12 01:04:15.814835

Session-based diet-chat storage: `chat_sessions` mein `session_id` column (unique) — har chat
session ka apna row. Purana per-prediction unique constraint (agar mojood ho) hata diya taake
ek prediction ke multiple sessions ho saken.
"""
from alembic import op
import sqlalchemy as sa


revision = '039e9f98f870'
down_revision = 'ad0291fbd3b8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('chat_sessions', sa.Column('session_id', sa.String(length=64), nullable=True))
    # Purana unique constraint hata do (idempotent — real DB mein shayad pehle se na ho).
    op.execute("ALTER TABLE chat_sessions DROP CONSTRAINT IF EXISTS chat_sessions_prediction_id_key")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_chat_sessions_session_id ON chat_sessions (session_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_chat_sessions_session_id")
    op.drop_column('chat_sessions', 'session_id')
    op.execute("ALTER TABLE chat_sessions ADD CONSTRAINT chat_sessions_prediction_id_key UNIQUE (prediction_id)")
