"""Reset de migração para corrigir heads

Revision ID: reset_heads_2025
Revises: 
Create Date: 2025-07-04 23:35:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'reset_heads_2025'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    """Reset de migração - não faz nada, apenas marca como aplicada"""
    pass

def downgrade():
    """Downgrade - não faz nada"""
    pass
