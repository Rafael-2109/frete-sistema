"""add data_pedido to saldo_standby

Revision ID: add_data_pedido_standby
Revises: 43f95a1ac288
Create Date: 2025-08-04 20:15:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_data_pedido_standby'
down_revision = '43f95a1ac288'
branch_labels = None
depends_on = None


def upgrade():
    # Adicionar campo data_pedido na tabela saldo_standby
    with op.batch_alter_table('saldo_standby', schema=None) as batch_op:
        batch_op.add_column(sa.Column('data_pedido', sa.Date(), nullable=True))


def downgrade():
    # Remover campo data_pedido da tabela saldo_standby
    with op.batch_alter_table('saldo_standby', schema=None) as batch_op:
        batch_op.drop_column('data_pedido')