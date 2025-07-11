"""Implementar sistema completo de Carteira de Pedidos com 9 modelos e funcionalidades críticas

Revision ID: 32a9fa957ff1
Revises: dcbaf7c4720d
Create Date: 2025-06-30 21:42:07.486524

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '32a9fa957ff1'
down_revision = 'dcbaf7c4720d'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('movimentacao_estoque', schema=None) as batch_op:
        batch_op.add_column(sa.Column('criado_em', sa.DateTime(), nullable=False))
        batch_op.add_column(sa.Column('atualizado_em', sa.DateTime(), nullable=False))
        batch_op.add_column(sa.Column('criado_por', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('atualizado_por', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('ativo', sa.Boolean(), nullable=True))
        batch_op.create_index(batch_op.f('ix_movimentacao_estoque_ativo'), ['ativo'], unique=False)
        batch_op.drop_column('created_by')
        batch_op.drop_column('created_at')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('movimentacao_estoque', schema=None) as batch_op:
        batch_op.add_column(sa.Column('created_at', sa.DATETIME(), nullable=False))
        batch_op.add_column(sa.Column('created_by', sa.VARCHAR(length=100), nullable=True))
        batch_op.drop_index(batch_op.f('ix_movimentacao_estoque_ativo'))
        batch_op.drop_column('ativo')
        batch_op.drop_column('atualizado_por')
        batch_op.drop_column('criado_por')
        batch_op.drop_column('atualizado_em')
        batch_op.drop_column('criado_em')

    # ### end Alembic commands ###
