"""merge_all_heads_20250808

Revision ID: 7e880edbf40a
Revises: 10a83c683c02, 4ae2a285649c, 55f23dc84a3b, 89f8f20d3a04, aa92bac3c410, create_unified_permission_system, add_data_pedido_standby, aumentar_campos_truncados, criar_cache_estoque, fix_render_cascade_dependencies
Create Date: 2025-08-08 01:18:53.442341

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7e880edbf40a'
down_revision = ('10a83c683c02', '4ae2a285649c', '55f23dc84a3b', '89f8f20d3a04', 'aa92bac3c410', 'create_unified_permission_system', 'add_data_pedido_standby', 'aumentar_campos_truncados', 'criar_cache_estoque', 'fix_render_cascade_dependencies')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
