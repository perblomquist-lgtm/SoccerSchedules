"""add gotsport_game_id index

Revision ID: c8d9e0f1g2h3
Revises: b3c4d5e6f7g8
Create Date: 2026-02-12 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c8d9e0f1g2h3'
down_revision = 'b3c4d5e6f7g8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add index on gotsport_game_id for faster lookups
    op.create_index('ix_games_gotsport_id', 'games', ['gotsport_game_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_games_gotsport_id', table_name='games')
