"""Migração inicial consolidada

Revision ID: initial_consolidated_2025
Revises: 
Create Date: 2025-07-05 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'initial_consolidated_2025'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    """
    Migração inicial que cria todas as tabelas necessárias.
    As tabelas são criadas pelo init_db.py, então esta migração
    apenas marca o banco como atualizado.
    """
    # Esta migração serve apenas para marcar o banco como migrado
    # As tabelas já são criadas pelo init_db.py
    pass

def downgrade():
    """
    Não fazer downgrade da migração inicial
    """
    pass
