"""Merge múltiplas heads de migração

Revision ID: merge_heads_20250705_093743
Revises: render_fix_20250704_204702, ai_consolidada_20250704_201224
Create Date: 2025-07-05 09:37:43.486226

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'merge_heads_20250705_093743'
down_revision = ('render_fix_20250704_204702', 'ai_consolidada_20250704_201224')
branch_labels = None
depends_on = None

def upgrade():
    """
    Migração de merge - não faz alterações no banco
    Apenas resolve o conflito de múltiplas heads
    """
    pass

def downgrade():
    """
    Downgrade da migração de merge
    """
    pass
