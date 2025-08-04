"""
MCP (Model Context Protocol) API endpoints for Flask integration.
Provides natural language query processing, suggestions, feedback, and user preferences.
"""

from flask import Blueprint, request, jsonify, current_app, g
from flask_login import current_user, login_required
from functools import wraps
from datetime import datetime, timedelta
import json
import logging
import traceback
import uuid
from typing import Dict, Any, List, Optional, Tuple
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Import MCP system components
from app.mcp_sistema.main import MCPSystem
from app.mcp_sistema.error_handlers import ErrorHandler
from app.mcp_sistema.monitoring import MonitoringSystem
from app.database import db
from app.models import User

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create Blueprint
mcp_api = Blueprint('mcp_api', __name__, url_prefix='/api/mcp')

# Thread pool for async operations
executor = ThreadPoolExecutor(max_workers=4)

# Initialize systems
mcp_system = None
error_handler = ErrorHandler()
monitoring = MonitoringSystem()


def init_mcp_system(app):
    """Initialize MCP system with Flask app context."""
    global mcp_system
    if not mcp_system:
        mcp_system = MCPSystem(app.config)
        logger.info("MCP system initialized")


# Middleware decorators
def validate_request(f):
    """Validate incoming request data."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Log request
        monitoring.log_request(request)
        
        # Validate content type
        if request.method in ['POST', 'PUT'] and not request.is_json:
            return jsonify({
                'success': False,
                'error': 'Content-Type must be application/json'
            }), 400
        
        # Validate required fields based on endpoint
        if request.endpoint == 'mcp_api.process_query':
            data = request.get_json()
            if not data or 'query' not in data:
                return jsonify({
                    'success': False,
                    'error': 'Missing required field: query'
                }), 400
                
        return f(*args, **kwargs)
    return decorated_function


def extract_user_context(f):
    """Extract and inject user context into request."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Extract user context
        g.user_context = {
            'user_id': current_user.id if current_user.is_authenticated else None,
            'username': current_user.username if current_user.is_authenticated else 'anonymous',
            'session_id': request.headers.get('X-Session-ID', str(uuid.uuid4())),
            'ip_address': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', ''),
            'timestamp': datetime.utcnow().isoformat(),
            'request_id': str(uuid.uuid4())
        }
        
        # Log user context
        logger.info(f"User context: {g.user_context['username']} - Request: {g.user_context['request_id']}")
        
        return f(*args, **kwargs)
    return decorated_function


def format_response(f):
    """Format API responses consistently."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            result = f(*args, **kwargs)
            
            # If result is already a response object, return it
            if hasattr(result, 'get_json'):
                return result
                
            # Format successful response
            response = {
                'success': True,
                'data': result,
                'metadata': {
                    'request_id': g.get('user_context', {}).get('request_id'),
                    'timestamp': datetime.utcnow().isoformat(),
                    'version': '1.0.0'
                }
            }
            
            # Log response
            monitoring.log_response(response, g.get('user_context', {}))
            
            return jsonify(response), 200
            
        except Exception as e:
            # Log error
            logger.error(f"Error in {f.__name__}: {str(e)}\n{traceback.format_exc()}")
            
            # Format error response
            return handle_error(e)
            
    return decorated_function


def handle_error(error: Exception) -> Tuple[Dict[str, Any], int]:
    """Handle errors consistently across all endpoints."""
    error_response = error_handler.handle(error)
    
    response = {
        'success': False,
        'error': error_response['message'],
        'error_code': error_response.get('code', 'INTERNAL_ERROR'),
        'metadata': {
            'request_id': g.get('user_context', {}).get('request_id'),
            'timestamp': datetime.utcnow().isoformat()
        }
    }
    
    # Add debug info in development
    if current_app.config.get('DEBUG'):
        response['debug'] = {
            'type': type(error).__name__,
            'traceback': traceback.format_exc()
        }
    
    # Log error
    monitoring.log_error(error, g.get('user_context', {}))
    
    return jsonify(response), error_response.get('status_code', 500)


# API Endpoints
@mcp_api.route('/query', methods=['POST'])
@validate_request
@extract_user_context
@format_response
def process_query():
    """
    Process natural language queries through MCP system.
    
    Expected JSON payload:
    {
        "query": "string - The natural language query",
        "context": {
            "workspace_id": "optional - Current workspace context",
            "previous_query": "optional - Previous query for context",
            "filters": {} // optional - Any active filters
        },
        "options": {
            "max_results": 10,
            "include_suggestions": true,
            "auto_execute": false
        }
    }
    """
    data = request.get_json()
    query = data.get('query', '').strip()
    context = data.get('context', {})
    options = data.get('options', {})
    
    # Validate query
    if not query:
        raise ValueError("Query cannot be empty")
    
    if len(query) > 1000:
        raise ValueError("Query too long (max 1000 characters)")
    
    # Process query through MCP system
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Run async MCP processing
        result = loop.run_until_complete(
            mcp_system.process_query(
                query=query,
                user_context=g.user_context,
                query_context=context,
                options=options
            )
        )
        
        # Store query in memory for learning
        loop.run_until_complete(
            mcp_system.store_query_result(
                query=query,
                result=result,
                user_context=g.user_context
            )
        )
        
        # Notify coordination system
        logger.info(f"Processed query: {query[:50]}... - Result type: {result.get('type')}")
        
        return {
            'query': query,
            'result': result,
            'suggestions': result.get('suggestions', []),
            'confidence': result.get('confidence', 0.0),
            'execution_time': result.get('execution_time', 0)
        }
        
    finally:
        loop.close()


@mcp_api.route('/suggestions', methods=['GET'])
@extract_user_context
@format_response
def get_suggestions():
    """
    Get query suggestions based on user history and context.
    
    Query parameters:
    - partial_query: Partial query string for autocomplete
    - context: Current context (workspace_id, etc.)
    - limit: Maximum number of suggestions (default: 10)
    """
    partial_query = request.args.get('partial_query', '')
    context = request.args.get('context', '{}')
    limit = min(int(request.args.get('limit', 10)), 50)
    
    try:
        context = json.loads(context) if context else {}
    except json.JSONDecodeError:
        context = {}
    
    # Get suggestions from MCP system
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        suggestions = loop.run_until_complete(
            mcp_system.get_suggestions(
                partial_query=partial_query,
                user_context=g.user_context,
                query_context=context,
                limit=limit
            )
        )
        
        return {
            'suggestions': suggestions,
            'partial_query': partial_query,
            'total_count': len(suggestions)
        }
        
    finally:
        loop.close()


@mcp_api.route('/feedback', methods=['POST'])
@login_required
@validate_request
@extract_user_context
@format_response
def submit_feedback():
    """
    Learn from user feedback on query results.
    
    Expected JSON payload:
    {
        "query_id": "string - ID of the original query",
        "feedback_type": "positive|negative|correction",
        "feedback_data": {
            "rating": 1-5,
            "comment": "optional comment",
            "correct_result": {} // for corrections
        }
    }
    """
    data = request.get_json()
    query_id = data.get('query_id')
    feedback_type = data.get('feedback_type')
    feedback_data = data.get('feedback_data', {})
    
    # Validate feedback
    if not query_id:
        raise ValueError("Query ID is required")
    
    if feedback_type not in ['positive', 'negative', 'correction']:
        raise ValueError("Invalid feedback type")
    
    # Process feedback
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        result = loop.run_until_complete(
            mcp_system.process_feedback(
                query_id=query_id,
                feedback_type=feedback_type,
                feedback_data=feedback_data,
                user_context=g.user_context
            )
        )
        
        # Log feedback for analysis
        logger.info(f"Feedback received: {feedback_type} for query {query_id}")
        
        return {
            'query_id': query_id,
            'feedback_accepted': True,
            'improvement_score': result.get('improvement_score', 0),
            'message': 'Thank you for your feedback!'
        }
        
    finally:
        loop.close()


@mcp_api.route('/preferences/<int:user_id>', methods=['GET'])
@login_required
@extract_user_context
@format_response
def get_user_preferences(user_id):
    """
    Get user preferences for query processing.
    
    Returns user-specific settings like:
    - Preferred query patterns
    - Default contexts
    - UI preferences
    - Learned behaviors
    """
    # Verify user access
    if current_user.id != user_id and not current_user.is_admin:
        raise PermissionError("Access denied to user preferences")
    
    # Get preferences from MCP system
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        preferences = loop.run_until_complete(
            mcp_system.get_user_preferences(user_id)
        )
        
        return {
            'user_id': user_id,
            'preferences': preferences,
            'last_updated': preferences.get('last_updated'),
            'learning_enabled': preferences.get('learning_enabled', True)
        }
        
    finally:
        loop.close()


@mcp_api.route('/confirm-action', methods=['POST'])
@login_required
@validate_request
@extract_user_context
@format_response
def confirm_action():
    """
    Human-in-the-loop confirmation for sensitive actions.
    
    Expected JSON payload:
    {
        "action_id": "string - Unique action identifier",
        "action_type": "delete|update|execute",
        "action_details": {
            "description": "Human-readable description",
            "impact": "Description of impact",
            "reversible": true|false,
            "data": {} // Action-specific data
        },
        "confirmation": true|false,
        "reason": "optional - Reason for rejection"
    }
    """
    data = request.get_json()
    action_id = data.get('action_id')
    action_type = data.get('action_type')
    action_details = data.get('action_details', {})
    confirmation = data.get('confirmation')
    reason = data.get('reason', '')
    
    # Validate request
    if not action_id:
        raise ValueError("Action ID is required")
    
    if action_type not in ['delete', 'update', 'execute']:
        raise ValueError("Invalid action type")
    
    if confirmation is None:
        raise ValueError("Confirmation status is required")
    
    # Process confirmation
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        result = loop.run_until_complete(
            mcp_system.process_confirmation(
                action_id=action_id,
                action_type=action_type,
                action_details=action_details,
                confirmed=confirmation,
                reason=reason,
                user_context=g.user_context
            )
        )
        
        # Log confirmation
        logger.info(f"Action {action_id} {'confirmed' if confirmation else 'rejected'} by {g.user_context['username']}")
        
        return {
            'action_id': action_id,
            'status': 'confirmed' if confirmation else 'rejected',
            'execution_result': result.get('execution_result'),
            'next_steps': result.get('next_steps', [])
        }
        
    finally:
        loop.close()


# Health check endpoint
@mcp_api.route('/health', methods=['GET'])
@format_response
def health_check():
    """Check MCP API health status."""
    health_status = {
        'status': 'healthy',
        'mcp_system': mcp_system is not None,
        'monitoring': monitoring.is_healthy(),
        'timestamp': datetime.utcnow().isoformat()
    }
    
    # Check MCP system health
    if mcp_system:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            mcp_health = loop.run_until_complete(mcp_system.health_check())
            health_status.update(mcp_health)
        finally:
            loop.close()
    
    return health_status


# WebSocket support for real-time updates (if needed)
@mcp_api.route('/ws/subscribe', methods=['GET'])
@login_required
def websocket_subscribe():
    """
    WebSocket endpoint for real-time query updates.
    Useful for long-running queries or live suggestions.
    """
    # This would be implemented with Flask-SocketIO or similar
    # Placeholder for future implementation
    return jsonify({
        'message': 'WebSocket support coming soon',
        'alternative': 'Use polling with /api/mcp/query for now'
    }), 501


# Error handlers
@mcp_api.errorhandler(ValueError)
def handle_value_error(e):
    return handle_error(e)


@mcp_api.errorhandler(PermissionError)
def handle_permission_error(e):
    return handle_error(e)


@mcp_api.errorhandler(Exception)
def handle_generic_error(e):
    return handle_error(e)


# Initialize MCP system when blueprint is registered
@mcp_api.before_app_first_request
def initialize():
    """Initialize MCP system on first request."""
    init_mcp_system(current_app)
    logger.info("MCP API initialized")