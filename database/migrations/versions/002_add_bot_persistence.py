# fx/database/migrations/versions/002_add_bot_persistence.py
"""add bot_persistence_store table

Revision ID: 002
Revises: 001
Create Date: 2026-03-08 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'bot_persistence_store',
        sa.Column('id',         sa.Integer(),     nullable=False),
        sa.Column('key',        sa.String(100),   nullable=False),
        sa.Column('value',      sa.Text(),         nullable=False),
        sa.Column('updated_at', sa.DateTime(),     server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key'),
    )
    op.create_index('idx_bot_persistence_key', 'bot_persistence_store', ['key'])


def downgrade():
    op.drop_index('idx_bot_persistence_key', table_name='bot_persistence_store')
    op.drop_table('bot_persistence_store')
