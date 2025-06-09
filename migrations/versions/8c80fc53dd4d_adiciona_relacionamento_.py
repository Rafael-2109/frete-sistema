"""Adiciona relacionamento PendenciaFinanceiraNF e EntregaMonitorada

Revision ID: 8c80fc53dd4d
Revises: a77c3fbf479e
Create Date: 2025-05-08 20:46:49.817314

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8c80fc53dd4d'
down_revision = 'a77c3fbf479e'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('pendencias_financeiras_nf', schema=None) as batch_op:
        batch_op.add_column(sa.Column('entrega_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_pendencias_entrega_id',  # Nome obrigatório da constraint
            'entregas_monitoradas',
            ['entrega_id'], ['id']
        )

def downgrade():
    with op.batch_alter_table('pendencias_financeiras_nf', schema=None) as batch_op:
        batch_op.drop_constraint('fk_pendencias_entrega_id', type_='foreignkey')
        batch_op.drop_column('entrega_id')

