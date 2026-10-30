"""0002_system_settings

Revision ID: 0002_system_settings
Revises: 163c3b025dd3
Create Date: 2026-10-30 22:19:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0002_system_settings'
down_revision = '163c3b025dd3'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'system_settings',
        sa.Column('key', sa.String(length=64), nullable=False),
        sa.Column('value', sa.String(length=255), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('key')
    )


def downgrade():
    op.drop_table('system_settings')
