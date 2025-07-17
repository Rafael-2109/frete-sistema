"""Adicionar campo separacao_lote_id na EntregaMonitorada

Revision ID: b3959548cec6
Revises: 818fc9fd1d77
Create Date: 2025-07-17 19:46:25.421063

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b3959548cec6'
down_revision = '818fc9fd1d77'
branch_labels = None
depends_on = None


def upgrade():
    """
    Adicionar campo separacao_lote_id na EntregaMonitorada
    """
    # Adicionar campo separacao_lote_id
    op.add_column('entregas_monitoradas', 
        sa.Column('separacao_lote_id', sa.String(length=50), nullable=True))
    
    # Criar índice para o novo campo
    op.create_index('ix_entregas_monitoradas_separacao_lote_id', 
                    'entregas_monitoradas', ['separacao_lote_id'])


def downgrade():
    """
    Remover campo separacao_lote_id da EntregaMonitorada
    """
    # Remover índice
    op.drop_index('ix_entregas_monitoradas_separacao_lote_id', 
                  table_name='entregas_monitoradas')
    
    # Remover campo
    op.drop_column('entregas_monitoradas', 'separacao_lote_id')
