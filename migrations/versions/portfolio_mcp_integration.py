"""Portfolio MCP Integration Migration

Revision ID: portfolio_mcp_integration
Revises: latest
Create Date: 2025-07-28 00:18:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from datetime import datetime

# revision identifiers
revision = 'portfolio_mcp_integration'
down_revision = None  # Will be set to latest migration
branch_labels = None
depends_on = None

def upgrade():
    """Upgrade database for MCP portfolio integration"""
    
    # Create MCP Portfolio Configuration table
    op.create_table('mcp_portfolio_config',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('config_key', sa.String(100), nullable=False),
        sa.Column('config_value', sa.Text(), nullable=True),
        sa.Column('config_type', sa.String(50), nullable=False),  # json, string, number, boolean
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('updated_by', sa.String(100), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('config_key', name='uq_mcp_portfolio_config_key')
    )
    
    # Create MCP Query Log table
    op.create_table('mcp_portfolio_query_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('query_id', sa.String(100), nullable=False),
        sa.Column('user_id', sa.String(100), nullable=True),
        sa.Column('session_id', sa.String(100), nullable=True),
        sa.Column('query_text', sa.Text(), nullable=False),
        sa.Column('query_type', sa.String(50), nullable=False),  # natural_language, api, automated
        sa.Column('intent_detected', sa.String(100), nullable=True),
        sa.Column('entities_extracted', sa.JSON(), nullable=True),
        sa.Column('response_data', sa.JSON(), nullable=True),
        sa.Column('execution_time_ms', sa.Integer(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False, default=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_mcp_query_log_user_date', 'user_id', 'created_at'),
        sa.Index('idx_mcp_query_log_query_type', 'query_type'),
        sa.Index('idx_mcp_query_log_success', 'success')
    )
    
    # Create MCP Portfolio Insights table
    op.create_table('mcp_portfolio_insights',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('insight_id', sa.String(100), nullable=False),
        sa.Column('insight_type', sa.String(50), nullable=False),  # stock, customer, performance, logistics
        sa.Column('severity', sa.String(20), nullable=False),  # low, medium, high, critical
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('data_json', sa.JSON(), nullable=True),
        sa.Column('recommendations', sa.JSON(), nullable=True),
        sa.Column('confidence_score', sa.Numeric(3, 2), nullable=False, default=0.0),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('acknowledged', sa.Boolean(), nullable=False, default=False),
        sa.Column('acknowledged_by', sa.String(100), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('insight_id', name='uq_mcp_portfolio_insights_id'),
        sa.Index('idx_mcp_insights_type_severity', 'insight_type', 'severity'),
        sa.Index('idx_mcp_insights_active', 'is_active', 'acknowledged'),
        sa.Index('idx_mcp_insights_expires', 'expires_at')
    )
    
    # Create MCP Portfolio Predictions table
    op.create_table('mcp_portfolio_predictions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('prediction_id', sa.String(100), nullable=False),
        sa.Column('model_type', sa.String(50), nullable=False),
        sa.Column('prediction_type', sa.String(50), nullable=False),  # demand, stock, performance
        sa.Column('target_entity', sa.String(100), nullable=True),  # product_code, customer_id, etc.
        sa.Column('horizon_days', sa.Integer(), nullable=False),
        sa.Column('predictions_json', sa.JSON(), nullable=False),
        sa.Column('confidence_intervals', sa.JSON(), nullable=True),
        sa.Column('accuracy_metrics', sa.JSON(), nullable=True),
        sa.Column('feature_importance', sa.JSON(), nullable=True),
        sa.Column('model_version', sa.String(20), nullable=False),
        sa.Column('confidence_level', sa.Numeric(3, 2), nullable=False, default=0.95),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('validated_accuracy', sa.Numeric(3, 2), nullable=True),
        sa.Column('validation_date', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('prediction_id', name='uq_mcp_portfolio_predictions_id'),
        sa.Index('idx_mcp_predictions_type_target', 'prediction_type', 'target_entity'),
        sa.Index('idx_mcp_predictions_active', 'is_active'),
        sa.Index('idx_mcp_predictions_expires', 'expires_at')
    )
    
    # Create MCP Portfolio Analytics Cache table
    op.create_table('mcp_portfolio_analytics_cache',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cache_key', sa.String(200), nullable=False),
        sa.Column('cache_type', sa.String(50), nullable=False),  # analysis, query, prediction
        sa.Column('data_json', sa.JSON(), nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('hit_count', sa.Integer(), nullable=False, default=0),
        sa.Column('last_accessed', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('cache_key', name='uq_mcp_portfolio_cache_key'),
        sa.Index('idx_mcp_cache_type', 'cache_type'),
        sa.Index('idx_mcp_cache_expires', 'expires_at'),
        sa.Index('idx_mcp_cache_accessed', 'last_accessed')
    )
    
    # Create MCP Portfolio User Preferences table
    op.create_table('mcp_portfolio_user_preferences',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(100), nullable=False),
        sa.Column('preference_key', sa.String(100), nullable=False),
        sa.Column('preference_value', sa.Text(), nullable=True),
        sa.Column('preference_type', sa.String(50), nullable=False),  # dashboard, alerts, analysis
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'preference_key', name='uq_mcp_user_preferences'),
        sa.Index('idx_mcp_user_prefs_user', 'user_id'),
        sa.Index('idx_mcp_user_prefs_type', 'preference_type')
    )
    
    # Add indexes to existing carteira tables for MCP optimization
    try:
        # Portfolio analysis indexes
        op.create_index('idx_carteira_principal_mcp_analysis', 'carteira_principal', 
                       ['ativo', 'qtd_saldo_produto_pedido', 'expedicao'])
        
        # Customer analytics index
        op.create_index('idx_carteira_principal_customer_analytics', 'carteira_principal',
                       ['cnpj_cpf', 'vendedor', 'ativo', 'data_pedido'])
        
        # Stock projection index  
        op.create_index('idx_carteira_principal_stock_projection', 'carteira_principal',
                       ['cod_produto', 'ativo', 'estoque_d0', 'estoque_d7'])
        
        # Performance metrics index
        op.create_index('idx_carteira_principal_performance', 'carteira_principal',
                       ['data_pedido', 'expedicao', 'ativo'])
        
    except Exception as e:
        # Indexes might already exist, continue
        print(f"Index creation warning: {e}")
    
    # Add MCP-specific columns to existing tables
    try:
        # Add MCP tracking to carteira_principal
        op.add_column('carteira_principal', 
                     sa.Column('mcp_last_analyzed', sa.DateTime(), nullable=True))
        op.add_column('carteira_principal', 
                     sa.Column('mcp_risk_score', sa.Numeric(3, 2), nullable=True))
        op.add_column('carteira_principal', 
                     sa.Column('mcp_insights_json', sa.JSON(), nullable=True))
        
        # Add MCP tracking to pre_separacao_item
        op.add_column('pre_separacao_item', 
                     sa.Column('mcp_optimization_applied', sa.Boolean(), nullable=False, default=False))
        op.add_column('pre_separacao_item', 
                     sa.Column('mcp_recommendations', sa.JSON(), nullable=True))
        
    except Exception as e:
        print(f"Column addition warning: {e}")
    
    # Insert default MCP configuration
    mcp_configs = [
        ('mcp_enabled', 'true', 'boolean', 'Enable MCP portfolio features'),
        ('natural_language_enabled', 'true', 'boolean', 'Enable natural language queries'),
        ('predictions_enabled', 'true', 'boolean', 'Enable demand predictions'),
        ('realtime_monitoring_enabled', 'true', 'boolean', 'Enable real-time monitoring'),
        ('insights_generation_enabled', 'true', 'boolean', 'Enable intelligent insights'),
        ('cache_ttl_default', '300', 'number', 'Default cache TTL in seconds'),
        ('prediction_horizon_default', '30', 'number', 'Default prediction horizon in days'),
        ('alert_thresholds', '{"stock_critical": 3, "stock_warning": 7, "overdue_days": 1}', 'json', 'Alert thresholds configuration'),
        ('analysis_frequency', '{"insights": 600, "predictions": 3600, "metrics": 60}', 'json', 'Analysis frequency in seconds'),
        ('model_versions', '{"demand": "1.0", "stock": "1.0", "performance": "1.0"}', 'json', 'Model versions'),
    ]
    
    config_table = sa.table('mcp_portfolio_config',
        sa.column('config_key', sa.String),
        sa.column('config_value', sa.Text),
        sa.column('config_type', sa.String),
        sa.column('description', sa.Text),
        sa.column('is_active', sa.Boolean),
        sa.column('created_at', sa.DateTime)
    )
    
    for key, value, type_, desc in mcp_configs:
        op.execute(
            config_table.insert().values(
                config_key=key,
                config_value=value,
                config_type=type_,
                description=desc,
                is_active=True,
                created_at=datetime.utcnow()
            )
        )

def downgrade():
    """Downgrade database from MCP portfolio integration"""
    
    # Remove added columns
    try:
        op.drop_column('carteira_principal', 'mcp_insights_json')
        op.drop_column('carteira_principal', 'mcp_risk_score')
        op.drop_column('carteira_principal', 'mcp_last_analyzed')
        
        op.drop_column('pre_separacao_item', 'mcp_recommendations')
        op.drop_column('pre_separacao_item', 'mcp_optimization_applied')
    except Exception as e:
        print(f"Column removal warning: {e}")
    
    # Remove added indexes
    try:
        op.drop_index('idx_carteira_principal_mcp_analysis', 'carteira_principal')
        op.drop_index('idx_carteira_principal_customer_analytics', 'carteira_principal')
        op.drop_index('idx_carteira_principal_stock_projection', 'carteira_principal')
        op.drop_index('idx_carteira_principal_performance', 'carteira_principal')
    except Exception as e:
        print(f"Index removal warning: {e}")
    
    # Drop MCP tables
    op.drop_table('mcp_portfolio_user_preferences')
    op.drop_table('mcp_portfolio_analytics_cache')
    op.drop_table('mcp_portfolio_predictions')
    op.drop_table('mcp_portfolio_insights')
    op.drop_table('mcp_portfolio_query_log')
    op.drop_table('mcp_portfolio_config')