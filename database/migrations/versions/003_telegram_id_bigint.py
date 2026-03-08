# fx/database/migrations/versions/003_telegram_id_bigint.py
"""alter telegram_id to bigint

Revision ID: 003
Revises: 002
Create Date: 2026-03-08 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None

DROP_CONSTRAINT_SQL = """
DO $$ BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'users_telegram_id_key'
    ) THEN
        ALTER TABLE users DROP CONSTRAINT users_telegram_id_key;
    END IF;
END $$;
"""


def upgrade():
    conn = op.get_bind()

    # Drop index and constraint safely — may not exist if DB was built via create_all()
    conn.execute(sa.text('DROP INDEX IF EXISTS idx_user_telegram_id'))
    conn.execute(sa.text(DROP_CONSTRAINT_SQL))

    # Alter column from INTEGER to BIGINT
    op.alter_column(
        'users', 'telegram_id',
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        nullable=False
    )

    # Recreate constraint and index
    op.create_unique_constraint('users_telegram_id_key', 'users', ['telegram_id'])
    op.create_index('idx_user_telegram_id', 'users', ['telegram_id'])


def downgrade():
    conn = op.get_bind()

    conn.execute(sa.text('DROP INDEX IF EXISTS idx_user_telegram_id'))
    conn.execute(sa.text(DROP_CONSTRAINT_SQL))

    op.alter_column(
        'users', 'telegram_id',
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        nullable=False
    )

    op.create_unique_constraint('users_telegram_id_key', 'users', ['telegram_id'])
    op.create_index('idx_user_telegram_id', 'users', ['telegram_id'])