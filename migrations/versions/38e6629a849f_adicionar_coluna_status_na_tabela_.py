"""Adicionar coluna status na tabela embarque_itens

Revision ID: 38e6629a849f
Revises: 5c05ac0ba999
Create Date: 2025-06-13 11:48:53.050439

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '38e6629a849f'
down_revision = '5c05ac0ba999'
branch_labels = None
depends_on = None


def upgrade():
    # Adicionar coluna status na tabela embarque_itens
    op.add_column('embarque_itens', sa.Column('status', sa.String(20), nullable=False, server_default='ativo'))


def downgrade():
    # Remover coluna status da tabela embarque_itens
    op.drop_column('embarque_itens', 'status')
