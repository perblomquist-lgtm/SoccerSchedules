"""Add composite indexes to games table for performance

Revision ID: b3c4d5e6f7g8
Revises: a9fb195b4628
Create Date: 2026-02-12 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3c4d5e6f7g8'
down_revision: Union[str, None] = 'a9fb195b4628'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add index to field_name for location filtering
    op.create_index('ix_games_field_name', 'games', ['field_name'], unique=False)
    
    # Add composite index for division + gotsport_game_id lookups (scraper deduplication)
    op.create_index('ix_games_division_gotsport', 'games', ['division_id', 'gotsport_game_id'], unique=False)
    
    # Add composite index for division + teams + datetime lookups (scraper deduplication fallback)
    op.create_index('ix_games_division_teams_datetime', 'games', 
                    ['division_id', 'home_team_name', 'away_team_name', 'game_date', 'game_time'], 
                    unique=False)
    
    # Add composite index for date + time sorting
    op.create_index('ix_games_datetime', 'games', ['game_date', 'game_time'], unique=False)
    
    # Add composite index for field + date filtering (current matches view)
    op.create_index('ix_games_field_date', 'games', ['field_name', 'game_date'], unique=False)


def downgrade() -> None:
    # Remove all the indexes we created
    op.drop_index('ix_games_field_date', table_name='games')
    op.drop_index('ix_games_datetime', table_name='games')
    op.drop_index('ix_games_division_teams_datetime', table_name='games')
    op.drop_index('ix_games_division_gotsport', table_name='games')
    op.drop_index('ix_games_field_name', table_name='games')
