
"""Aumentar campos truncados
Revision ID: aumentar_campos_truncados
Revises: ensure_separacao_lote_id
Create Date: 2025-01-28 02:00:00
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'aumentar_campos_truncados'
down_revision = 'ensure_separacao_lote_id'
branch_labels = None
depends_on = None

def upgrade():
    # Aumentar metodo_entrega_pedido de 50 para 100 caracteres
    op.alter_column('carteira_principal', 'metodo_entrega_pedido',
                    type_=sa.String(100),
                    existing_type=sa.String(50),
                    existing_nullable=True)
    
    # Aumentar telefone_endereco_ent de 20 para 50 caracteres
    op.alter_column('carteira_principal', 'telefone_endereco_ent',
                    type_=sa.String(50),
                    existing_type=sa.String(20),
                    existing_nullable=True)

def downgrade():
    # Reverter para tamanhos originais
    op.alter_column('carteira_principal', 'telefone_endereco_ent',
                    type_=sa.String(20),
                    existing_type=sa.String(50),
                    existing_nullable=True)
    
    op.alter_column('carteira_principal', 'metodo_entrega_pedido',
                    type_=sa.String(50),
                    existing_type=sa.String(100),
                    existing_nullable=True) 