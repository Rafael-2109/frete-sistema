"""Reset heads migration

Revision ID: reset_heads_2025
Revises: 
Create Date: 2025-07-05 12:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'reset_heads_2025'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Esta migra��o serve apenas para resetar o estado das heads
    # Todas as tabelas j� s�o criadas pelo init_db.py
    pass

def downgrade():
    # N�o fazer downgrade para evitar problemas
    pass
