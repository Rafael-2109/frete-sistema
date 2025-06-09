"""Atualiza status default dos pedidos

Revision ID: update_status_default
Revises: 115f23a90bbd
Create Date: 2025-05-24 13:35:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'update_status_default'
down_revision = '115f23a90bbd'
branch_labels = None
depends_on = None

def upgrade():
    op.execute("UPDATE pedidos SET status = 'ABERTO' WHERE status IS NULL")

def downgrade():
    op.execute("UPDATE pedidos SET status = NULL") 