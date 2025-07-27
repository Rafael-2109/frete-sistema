"""Fix cascade dependencies for Render deployment

Revision ID: fix_render_cascade_dependencies
Revises: 2b5f3637c189
Create Date: 2025-07-26 23:00:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'fix_render_cascade_dependencies'
down_revision = '2b5f3637c189'
branch_labels = None
depends_on = None


def upgrade():
    """Fix dependent objects before dropping tables"""
    conn = op.get_bind()
    
    # First, check and drop views that depend on tables
    views_to_drop = [
        'ai_session_analytics',
        'ai_pattern_summary',
        'ai_feedback_summary',
        'historico_summary',
        'faturamento_analytics'
    ]
    
    for view_name in views_to_drop:
        try:
            # Check if view exists
            result = conn.execute(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.views 
                    WHERE table_name = '{view_name}'
                )
            """).scalar()
            
            if result:
                conn.execute(f"DROP VIEW IF EXISTS {view_name} CASCADE")
                print(f"✅ Dropped view: {view_name}")
        except Exception as e:
            print(f"⚠️ Could not drop view {view_name}: {e}")
            pass
    
    # Now safely drop tables that might have dependencies
    tables_to_drop = [
        'ai_advanced_sessions',
        'ai_learning_patterns', 
        'ai_feedback_history',
        'historico_faturamento'
    ]
    
    for table_name in tables_to_drop:
        try:
            # Check if table exists
            result = conn.execute(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = '{table_name}'
                )
            """).scalar()
            
            if result:
                conn.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE")
                print(f"✅ Dropped table: {table_name}")
        except Exception as e:
            print(f"⚠️ Could not drop table {table_name}: {e}")
            pass


def downgrade():
    """Cannot recreate dropped objects"""
    pass