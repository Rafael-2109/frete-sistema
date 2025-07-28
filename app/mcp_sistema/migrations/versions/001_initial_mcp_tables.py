"""Initial MCP tables

Revision ID: 001
Revises: 
Create Date: 2025-01-27 19:58:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import json

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create MCP sessions table
    op.create_table('mcp_sessions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('session_id', sa.String(length=255), nullable=False),
        sa.Column('client_id', sa.String(length=255), nullable=False),
        sa.Column('client_name', sa.String(length=255), nullable=True),
        sa.Column('client_version', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('last_activity', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('protocol_version', sa.String(length=20), nullable=True),
        sa.Column('transport', sa.String(length=50), nullable=True),
        sa.Column('capabilities', sa.JSON(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('request_count', sa.Integer(), nullable=True),
        sa.Column('tool_execution_count', sa.Integer(), nullable=True),
        sa.Column('resource_access_count', sa.Integer(), nullable=True),
        sa.Column('total_tokens_used', sa.Integer(), nullable=True),
        sa.Column('avg_response_time', sa.Float(), nullable=True),
        sa.Column('max_response_time', sa.Float(), nullable=True),
        sa.Column('min_response_time', sa.Float(), nullable=True),
        sa.Column('error_count', sa.Integer(), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('last_error_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_mcp_sessions'))
    )
    op.create_index(op.f('ix_mcp_sessions_client_id'), 'mcp_sessions', ['client_id'], unique=False)
    op.create_index(op.f('ix_mcp_sessions_session_id'), 'mcp_sessions', ['session_id'], unique=True)
    op.create_index('idx_session_activity', 'mcp_sessions', ['last_activity'], unique=False)
    op.create_index('idx_session_client', 'mcp_sessions', ['client_id', 'started_at'], unique=False)
    op.create_index('idx_session_status', 'mcp_sessions', ['status', 'last_activity'], unique=False)

    # Create MCP requests table
    op.create_table('mcp_requests',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('request_id', sa.String(length=255), nullable=False),
        sa.Column('session_id', sa.String(length=255), nullable=False),
        sa.Column('method', sa.Enum('INITIALIZE', 'LIST_RESOURCES', 'READ_RESOURCE', 'LIST_TOOLS', 'CALL_TOOL', 'PING', 'CUSTOM', name='requestmethod'), nullable=False),
        sa.Column('endpoint', sa.String(length=255), nullable=True),
        sa.Column('params', sa.JSON(), nullable=True),
        sa.Column('headers', sa.JSON(), nullable=True),
        sa.Column('body', sa.JSON(), nullable=True),
        sa.Column('body_size', sa.Integer(), nullable=True),
        sa.Column('client_ip', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('received_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['mcp_sessions.session_id'], name=op.f('fk_mcp_requests_session_id_mcp_sessions')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_mcp_requests'))
    )
    op.create_index(op.f('ix_mcp_requests_method'), 'mcp_requests', ['method'], unique=False)
    op.create_index(op.f('ix_mcp_requests_request_id'), 'mcp_requests', ['request_id'], unique=True)
    op.create_index(op.f('ix_mcp_requests_session_id'), 'mcp_requests', ['session_id'], unique=False)
    op.create_index('idx_request_method', 'mcp_requests', ['method', 'received_at'], unique=False)
    op.create_index('idx_request_session', 'mcp_requests', ['session_id', 'received_at'], unique=False)

    # Create MCP responses table
    op.create_table('mcp_responses',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('response_id', sa.String(length=255), nullable=False),
        sa.Column('request_id', sa.String(length=255), nullable=False),
        sa.Column('session_id', sa.String(length=255), nullable=False),
        sa.Column('status', sa.Enum('SUCCESS', 'ERROR', 'PARTIAL', 'TIMEOUT', name='responsestatus'), nullable=False),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('headers', sa.JSON(), nullable=True),
        sa.Column('body', sa.JSON(), nullable=True),
        sa.Column('body_size', sa.Integer(), nullable=True),
        sa.Column('error_type', sa.String(length=100), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_details', sa.JSON(), nullable=True),
        sa.Column('processing_time', sa.Float(), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['request_id'], ['mcp_requests.request_id'], name=op.f('fk_mcp_responses_request_id_mcp_requests')),
        sa.ForeignKeyConstraint(['session_id'], ['mcp_sessions.session_id'], name=op.f('fk_mcp_responses_session_id_mcp_sessions')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_mcp_responses'))
    )
    op.create_index(op.f('ix_mcp_responses_request_id'), 'mcp_responses', ['request_id'], unique=True)
    op.create_index(op.f('ix_mcp_responses_response_id'), 'mcp_responses', ['response_id'], unique=True)
    op.create_index(op.f('ix_mcp_responses_session_id'), 'mcp_responses', ['session_id'], unique=False)
    op.create_index(op.f('ix_mcp_responses_status'), 'mcp_responses', ['status'], unique=False)
    op.create_index('idx_response_session', 'mcp_responses', ['session_id', 'sent_at'], unique=False)
    op.create_index('idx_response_status', 'mcp_responses', ['status', 'sent_at'], unique=False)

    # Create MCP tool executions table
    op.create_table('mcp_tool_executions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('execution_id', sa.String(length=255), nullable=False),
        sa.Column('request_id', sa.String(length=255), nullable=False),
        sa.Column('session_id', sa.String(length=255), nullable=False),
        sa.Column('tool_name', sa.String(length=255), nullable=False),
        sa.Column('tool_version', sa.String(length=50), nullable=True),
        sa.Column('tool_category', sa.String(length=100), nullable=True),
        sa.Column('arguments', sa.JSON(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('result', sa.JSON(), nullable=True),
        sa.Column('result_size', sa.Integer(), nullable=True),
        sa.Column('execution_time', sa.Float(), nullable=True),
        sa.Column('memory_used', sa.Integer(), nullable=True),
        sa.Column('cpu_time', sa.Float(), nullable=True),
        sa.Column('error_type', sa.String(length=100), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_stack', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['request_id'], ['mcp_requests.request_id'], name=op.f('fk_mcp_tool_executions_request_id_mcp_requests')),
        sa.ForeignKeyConstraint(['session_id'], ['mcp_sessions.session_id'], name=op.f('fk_mcp_tool_executions_session_id_mcp_sessions')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_mcp_tool_executions'))
    )
    op.create_index(op.f('ix_mcp_tool_executions_execution_id'), 'mcp_tool_executions', ['execution_id'], unique=True)
    op.create_index(op.f('ix_mcp_tool_executions_request_id'), 'mcp_tool_executions', ['request_id'], unique=True)
    op.create_index(op.f('ix_mcp_tool_executions_session_id'), 'mcp_tool_executions', ['session_id'], unique=False)
    op.create_index(op.f('ix_mcp_tool_executions_tool_name'), 'mcp_tool_executions', ['tool_name'], unique=False)
    op.create_index('idx_tool_exec_name', 'mcp_tool_executions', ['tool_name', 'started_at'], unique=False)
    op.create_index('idx_tool_exec_session', 'mcp_tool_executions', ['session_id', 'started_at'], unique=False)
    op.create_index('idx_tool_exec_status', 'mcp_tool_executions', ['status', 'started_at'], unique=False)

    # Create MCP cache table
    op.create_table('mcp_cache',
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cache_key', sa.String(length=500), nullable=False),
        sa.Column('cache_type', sa.String(length=100), nullable=False),
        sa.Column('data', sa.JSON(), nullable=False),
        sa.Column('data_size', sa.Integer(), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('hit_count', sa.Integer(), nullable=True),
        sa.Column('last_accessed', sa.DateTime(timezone=True), nullable=True),
        sa.Column('source_type', sa.String(length=100), nullable=True),
        sa.Column('source_id', sa.String(length=255), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('cache_key', name=op.f('pk_mcp_cache'))
    )
    op.create_index(op.f('ix_mcp_cache_cache_type'), 'mcp_cache', ['cache_type'], unique=False)
    op.create_index(op.f('ix_mcp_cache_expires_at'), 'mcp_cache', ['expires_at'], unique=False)
    op.create_index('idx_cache_accessed', 'mcp_cache', ['last_accessed'], unique=False)
    op.create_index('idx_cache_type_expires', 'mcp_cache', ['cache_type', 'expires_at'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index('idx_cache_type_expires', table_name='mcp_cache')
    op.drop_index('idx_cache_accessed', table_name='mcp_cache')
    op.drop_index(op.f('ix_mcp_cache_expires_at'), table_name='mcp_cache')
    op.drop_index(op.f('ix_mcp_cache_cache_type'), table_name='mcp_cache')
    op.drop_table('mcp_cache')
    
    op.drop_index('idx_tool_exec_status', table_name='mcp_tool_executions')
    op.drop_index('idx_tool_exec_session', table_name='mcp_tool_executions')
    op.drop_index('idx_tool_exec_name', table_name='mcp_tool_executions')
    op.drop_index(op.f('ix_mcp_tool_executions_tool_name'), table_name='mcp_tool_executions')
    op.drop_index(op.f('ix_mcp_tool_executions_session_id'), table_name='mcp_tool_executions')
    op.drop_index(op.f('ix_mcp_tool_executions_request_id'), table_name='mcp_tool_executions')
    op.drop_index(op.f('ix_mcp_tool_executions_execution_id'), table_name='mcp_tool_executions')
    op.drop_table('mcp_tool_executions')
    
    op.drop_index('idx_response_status', table_name='mcp_responses')
    op.drop_index('idx_response_session', table_name='mcp_responses')
    op.drop_index(op.f('ix_mcp_responses_status'), table_name='mcp_responses')
    op.drop_index(op.f('ix_mcp_responses_session_id'), table_name='mcp_responses')
    op.drop_index(op.f('ix_mcp_responses_response_id'), table_name='mcp_responses')
    op.drop_index(op.f('ix_mcp_responses_request_id'), table_name='mcp_responses')
    op.drop_table('mcp_responses')
    
    op.drop_index('idx_request_session', table_name='mcp_requests')
    op.drop_index('idx_request_method', table_name='mcp_requests')
    op.drop_index(op.f('ix_mcp_requests_session_id'), table_name='mcp_requests')
    op.drop_index(op.f('ix_mcp_requests_request_id'), table_name='mcp_requests')
    op.drop_index(op.f('ix_mcp_requests_method'), table_name='mcp_requests')
    op.drop_table('mcp_requests')
    
    op.drop_index('idx_session_status', table_name='mcp_sessions')
    op.drop_index('idx_session_client', table_name='mcp_sessions')
    op.drop_index('idx_session_activity', table_name='mcp_sessions')
    op.drop_index(op.f('ix_mcp_sessions_session_id'), table_name='mcp_sessions')
    op.drop_index(op.f('ix_mcp_sessions_client_id'), table_name='mcp_sessions')
    op.drop_table('mcp_sessions')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS responsestatus')
    op.execute('DROP TYPE IF EXISTS requestmethod')