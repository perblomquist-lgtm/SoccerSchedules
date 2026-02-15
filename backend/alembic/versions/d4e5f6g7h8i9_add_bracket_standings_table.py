"""add bracket standings table

Revision ID: d4e5f6g7h8i9
Revises: c8d9e0f1g2h3
Create Date: 2026-02-14 02:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd4e5f6g7h8i9'
down_revision = 'c8d9e0f1g2h3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create bracket_standings table
    op.create_table('bracket_standings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('division_id', sa.Integer(), nullable=False),
        sa.Column('bracket_name', sa.String(length=100), nullable=False),
        sa.Column('team_name', sa.String(length=255), nullable=False),
        sa.Column('played', sa.Integer(), nullable=False),
        sa.Column('wins', sa.Integer(), nullable=False),
        sa.Column('draws', sa.Integer(), nullable=False),
        sa.Column('losses', sa.Integer(), nullable=False),
        sa.Column('goals_for', sa.Integer(), nullable=False),
        sa.Column('goals_against', sa.Integer(), nullable=False),
        sa.Column('goal_difference', sa.Integer(), nullable=False),
        sa.Column('points', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['division_id'], ['divisions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_bracket_standings_bracket_name'), 'bracket_standings', ['bracket_name'], unique=False)
    op.create_index(op.f('ix_bracket_standings_division_id'), 'bracket_standings', ['division_id'], unique=False)
    op.create_index('ix_bracket_division_bracket_team', 'bracket_standings', ['division_id', 'bracket_name', 'team_name'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_bracket_division_bracket_team', table_name='bracket_standings')
    op.drop_index(op.f('ix_bracket_standings_division_id'), table_name='bracket_standings')
    op.drop_index(op.f('ix_bracket_standings_bracket_name'), table_name='bracket_standings')
    op.drop_table('bracket_standings')
