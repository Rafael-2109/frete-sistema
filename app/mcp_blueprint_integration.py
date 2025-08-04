"""
MCP Blueprint Integration Module
Registers the MCP API blueprint with the Flask application
"""

from flask import Flask
from app.mcp_api import mcp_api, init_mcp_system
import logging

logger = logging.getLogger(__name__)


def register_mcp_blueprints(app: Flask):
    """
    Register MCP API blueprints with the Flask application.
    
    Args:
        app: Flask application instance
    """
    # Register MCP API blueprint
    app.register_blueprint(mcp_api)
    logger.info("MCP API blueprint registered at /api/mcp")
    
    # Initialize MCP system
    with app.app_context():
        init_mcp_system(app)
        logger.info("MCP system initialized with Flask app")
    
    # Add MCP-specific configuration
    if 'MCP_CONFIG' not in app.config:
        app.config['MCP_CONFIG'] = {
            'query_timeout': 30,  # seconds
            'max_query_length': 1000,
            'enable_learning': True,
            'cache_ttl': 3600,  # 1 hour
            'max_suggestions': 10,
            'enable_monitoring': True,
            'log_level': 'INFO'
        }
    
    # Configure MCP-specific error handlers
    @app.errorhandler(TimeoutError)
    def handle_timeout_error(e):
        """Handle MCP query timeouts."""
        return {
            'success': False,
            'error': 'Query processing timed out. Please try a simpler query.',
            'error_code': 'TIMEOUT'
        }, 408
    
    @app.errorhandler(ConnectionError)
    def handle_connection_error(e):
        """Handle MCP system connection errors."""
        return {
            'success': False,
            'error': 'MCP system connection error. Please try again later.',
            'error_code': 'CONNECTION_ERROR'
        }, 503
    
    logger.info("MCP blueprint integration complete")


def get_mcp_api_routes():
    """
    Get a list of all MCP API routes for documentation.
    
    Returns:
        List of tuples (method, route, description)
    """
    return [
        ('POST', '/api/mcp/query', 'Process natural language queries'),
        ('GET', '/api/mcp/suggestions', 'Get query suggestions and autocomplete'),
        ('POST', '/api/mcp/feedback', 'Submit feedback on query results'),
        ('GET', '/api/mcp/preferences/<user_id>', 'Get user-specific preferences'),
        ('POST', '/api/mcp/confirm-action', 'Confirm sensitive actions (HITL)'),
        ('GET', '/api/mcp/health', 'Check MCP API health status'),
        ('GET', '/api/mcp/ws/subscribe', 'WebSocket subscription (future)')
    ]