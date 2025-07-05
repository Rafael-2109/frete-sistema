"""Adicionar campo status ao EmbarqueItem para exclusao logica

Revision ID: 5c05ac0ba999
Revises: 97ff869fee50
Create Date: 2025-06-12 20:00:47.088283

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5c05ac0ba999'
down_revision = '97ff869fee50'
branch_labels = None
depends_on = None


def upgrade():
    # Adicionar campo status ao EmbarqueItem
    with op.batch_alter_table('embarque_itens', schema=None) as batch_op:
        batch_op.add_column(sa.Column('status', sa.String(20), nullable=False, server_default='ativo'))


def downgrade():
    # Remover campo status do EmbarqueItem
    with op.batch_alter_table('embarque_itens', schema=None) as batch_op:
        batch_op.drop_column('status')
