"""remover constraint unica pre separacao para permitir multiplas

Revision ID: remover_constraint_unica_pre_separacao
Revises: 76bbd63e3bed
Create Date: 2025-07-21 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'remover_constraint_unica_pre_separacao'
down_revision = '76bbd63e3bed'
branch_labels = None
depends_on = None


def upgrade():
    # Remover a constraint única que impedia múltiplas pré-separações
    # Esta constraint estava no modelo PreSeparacaoItem impedindo múltiplas
    # pré-separações do mesmo produto
    
    # Primeiro vamos verificar se a constraint existe e removê-la
    with op.batch_alter_table('pre_separacao_item', schema=None) as batch_op:
        try:
            batch_op.drop_constraint('pre_separacao_itens_pedido_produto_unique', type_='unique')
        except:
            # Constraint pode não existir se foi criada apenas no modelo
            pass


def downgrade():
    # Recriar a constraint única (se necessário, mas não recomendado)
    # pois isso voltaria a impedir múltiplas pré-separações
    with op.batch_alter_table('pre_separacao_item', schema=None) as batch_op:
        batch_op.create_unique_constraint(
            'pre_separacao_itens_pedido_produto_unique',
            ['num_pedido', 'cod_produto', 'cnpj_cliente', 'data_criacao']
        )