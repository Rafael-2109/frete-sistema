"""adicionar_peso_unitario_produto

Revision ID: 0c6e9779f29c
Revises: ca53350e4914
Create Date: 2025-07-14 17:40:56.925481

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0c6e9779f29c'
down_revision = 'ca53350e4914'
branch_labels = None
depends_on = None


def upgrade():
    # ### Adicionar campo peso_unitario_produto na tabela faturamento_produto ###
    op.add_column('faturamento_produto', sa.Column('peso_unitario_produto', sa.Numeric(15, 3), nullable=True, default=0))
    
    # Preencher todos os registros existentes com valor 0
    op.execute('UPDATE faturamento_produto SET peso_unitario_produto = 0 WHERE peso_unitario_produto IS NULL')


def downgrade():
    # ### Remover campo peso_unitario_produto da tabela faturamento_produto ###
    op.drop_column('faturamento_produto', 'peso_unitario_produto')
