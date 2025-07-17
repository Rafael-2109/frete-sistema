"""Merge heads: hora_agendamento e peso_unitario

Revision ID: 2ff2d45b36ff
Revises: 0c6e9779f29c, adicionar_hora_agendamento
Create Date: 2025-07-17 16:27:27.553454

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2ff2d45b36ff'
down_revision = ('0c6e9779f29c', 'adicionar_hora_agendamento')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
