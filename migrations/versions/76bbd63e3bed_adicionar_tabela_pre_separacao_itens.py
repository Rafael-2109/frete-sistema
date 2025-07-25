"""adicionar_tabela_pre_separacao_itens

Revision ID: 76bbd63e3bed
Revises: 0ae5f539b83f
Create Date: 2025-07-19 01:09:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision = '76bbd63e3bed'
down_revision = '0ae5f539b83f'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('pre_separacao_itens',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('carteira_principal_id', sa.Integer(), nullable=False),
    sa.Column('cod_produto', sa.String(length=50), nullable=False),
    sa.Column('qtd_original', sa.Float(), nullable=False),
    sa.Column('qtd_selecionada', sa.Float(), nullable=False),
    sa.Column('qtd_restante', sa.Float(), nullable=False),
    sa.Column('expedicao_editavel', sa.Date(), nullable=True),
    sa.Column('agendamento_editavel', sa.Date(), nullable=True),
    sa.Column('protocolo_editavel', sa.String(length=50), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('observacoes', sa.Text(), nullable=True),
    sa.Column('criado_em', sa.DateTime(), nullable=False),
    sa.Column('criado_por', sa.String(length=100), nullable=False),
    sa.Column('atualizado_em', sa.DateTime(), nullable=True),
    sa.Column('atualizado_por', sa.String(length=100), nullable=True),
    sa.ForeignKeyConstraint(['carteira_principal_id'], ['carteira_principal.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('pre_separacao_itens', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_pre_separacao_itens_carteira_principal_id'), ['carteira_principal_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_pre_separacao_itens_cod_produto'), ['cod_produto'], unique=False)
        batch_op.create_index(batch_op.f('ix_pre_separacao_itens_status'), ['status'], unique=False)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('pre_separacao_itens', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_pre_separacao_itens_status'))
        batch_op.drop_index(batch_op.f('ix_pre_separacao_itens_cod_produto'))
        batch_op.drop_index(batch_op.f('ix_pre_separacao_itens_carteira_principal_id'))

    op.drop_table('pre_separacao_itens')
    # ### end Alembic commands ### 