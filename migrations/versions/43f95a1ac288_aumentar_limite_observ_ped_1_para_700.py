"""aumentar_limite_observ_ped_1_para_700

Revision ID: 43f95a1ac288
Revises: initial_consolidated_2025
Create Date: 2025-06-27 12:05:44.683935

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '43f95a1ac288'
down_revision = 'initial_consolidated_2025'
branch_labels = None
depends_on = None


def upgrade():
    # Aumentar o limite do campo observ_ped_1 de 255 para 700 caracteres
    with op.batch_alter_table('separacao', schema=None) as batch_op:
        batch_op.alter_column('observ_ped_1',
               existing_type=sa.String(length=255),
               type_=sa.String(length=700),
               existing_nullable=True)


def downgrade():
    # Reverter para o limite original de 255 caracteres
    with op.batch_alter_table('separacao', schema=None) as batch_op:
        batch_op.alter_column('observ_ped_1',
               existing_type=sa.String(length=700),
               type_=sa.String(length=255),
               existing_nullable=True)
