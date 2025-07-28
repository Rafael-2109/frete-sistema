"""Ensure separacao_lote_id field exists

Revision ID: ensure_separacao_lote_id
Revises: 2b5f3637c189
Create Date: 2025-01-28 00:30:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'ensure_separacao_lote_id'
down_revision = '2b5f3637c189'
branch_labels = None
depends_on = None


def upgrade():
    """Garantir que o campo separacao_lote_id existe"""
    # Usar SQL direto que sempre funciona
    conn = op.get_bind()
    
    # Adicionar campo se não existir
    conn.execute("""
        ALTER TABLE pre_separacao_item 
        ADD COLUMN IF NOT EXISTS separacao_lote_id VARCHAR(50)
    """)
    
    # Criar índice se não existir
    conn.execute("""
        CREATE INDEX IF NOT EXISTS ix_pre_separacao_item_separacao_lote_id 
        ON pre_separacao_item(separacao_lote_id)
    """)
    
    print("✅ Campo separacao_lote_id garantido!")


def downgrade():
    """Remover campo se necessário"""
    op.drop_index('ix_pre_separacao_item_separacao_lote_id', table_name='pre_separacao_item')
    op.drop_column('pre_separacao_item', 'separacao_lote_id') 