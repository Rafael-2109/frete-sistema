"""
Flask-MCP Integration Bridge
This module integrates the FastAPI MCP system with the Flask application
WITHOUT modifying existing Flask structure or build scripts.
"""

import os
import asyncio
from flask import Blueprint, jsonify, request, current_app
from functools import wraps
import httpx
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Create blueprint for MCP integration
mcp_integration_bp = Blueprint('mcp_integration', __name__, url_prefix='/mcp')


class MCPIntegrationError(Exception):
    """Custom exception for MCP integration errors"""
    pass


class MCPFlaskBridge:
    """
    Bridge between Flask app and FastAPI MCP system.
    Proxies requests to the MCP system running on a separate port.
    """
    
    def __init__(self, mcp_base_url: Optional[str] = None):
        """
        Initialize MCP Flask Bridge
        
        Args:
            mcp_base_url: Base URL of the MCP system (e.g., http://localhost:8000)
        """
        # Get MCP URL from environment or use default
        self.mcp_base_url = mcp_base_url or os.getenv('MCP_BASE_URL', 'http://localhost:8000')
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
        
    async def proxy_request(self, path: str, method: str = 'GET', **kwargs) -> Dict[str, Any]:
        """
        Proxy a request to the MCP system
        
        Args:
            path: API path (e.g., /api/v1/mcp/tools)
            method: HTTP method
            **kwargs: Additional request parameters
            
        Returns:
            Response data from MCP system
        """
        url = f"{self.mcp_base_url}{path}"
        
        try:
            response = await self.client.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"MCP proxy request failed: {e}")
            raise MCPIntegrationError(f"Failed to communicate with MCP system: {str(e)}")
    
    def health_check(self) -> bool:
        """
        Check if MCP system is healthy
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            # Run async health check in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self._async_health_check())
            loop.close()
            return result
        except Exception as e:
            logger.error(f"MCP health check failed: {e}")
            return False
    
    async def _async_health_check(self) -> bool:
        """Async health check implementation"""
        try:
            response = await self.proxy_request('/api/v1/health')
            return response.get('status') == 'healthy'
        except:
            return False


# Global bridge instance
mcp_bridge = None


def init_mcp_integration(app):
    """
    Initialize MCP integration with Flask app
    
    Args:
        app: Flask application instance
    """
    global mcp_bridge
    
    # Get MCP configuration from environment
    mcp_enabled = os.getenv('MCP_ENABLED', 'false').lower() == 'true'
    
    if not mcp_enabled:
        app.logger.info("MCP integration is disabled")
        return
    
    # Check for required MCP environment variables
    missing_vars = check_mcp_requirements()
    
    if missing_vars:
        app.logger.warning(f"MCP integration incomplete - missing variables: {missing_vars}")
        app.logger.warning("MCP endpoints will return error responses")
    
    # Initialize bridge
    mcp_bridge = MCPFlaskBridge()
    
    # Register blueprint
    app.register_blueprint(mcp_integration_bp)
    
    # Test MCP connection
    if mcp_bridge.health_check():
        app.logger.info("✅ MCP integration initialized successfully")
    else:
        app.logger.warning("⚠️ MCP system not responding - integration in degraded mode")


def check_mcp_requirements() -> list:
    """
    Check for missing MCP environment variables
    
    Returns:
        List of missing variable names
    """
    required_vars = [
        'MCP_ENABLED',           # Enable/disable MCP integration
        'MCP_BASE_URL',          # Base URL for MCP system
        'MCP_AUTH_TOKEN',        # Authentication token for MCP
        'MCP_SERVICE_NAME',      # Service identifier
        'MCP_TRANSPORT_TYPE',    # Transport type (stdio, http, etc.)
        'FLASK_MCP_SECRET',      # Shared secret between Flask and MCP
    ]
    
    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    return missing


def async_route(f):
    """Decorator to handle async routes in Flask"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(f(*args, **kwargs))
        finally:
            loop.close()
    return wrapper


# MCP Integration Routes

@mcp_integration_bp.route('/status')
def mcp_status():
    """Get MCP integration status"""
    if not mcp_bridge:
        return jsonify({
            'success': False,
            'error': 'MCP integration not initialized',
            'enabled': False
        }), 503
    
    missing_vars = check_mcp_requirements()
    is_healthy = mcp_bridge.health_check()
    
    return jsonify({
        'success': True,
        'enabled': True,
        'healthy': is_healthy,
        'mcp_url': mcp_bridge.mcp_base_url,
        'missing_config': missing_vars,
        'status': 'operational' if is_healthy and not missing_vars else 'degraded'
    })


@mcp_integration_bp.route('/tools', methods=['GET'])
@async_route
async def list_mcp_tools():
    """List available MCP tools"""
    if not mcp_bridge:
        return jsonify({
            'success': False,
            'error': 'MCP integration not available'
        }), 503
    
    try:
        async with MCPFlaskBridge() as bridge:
            result = await bridge.proxy_request('/api/v1/mcp/tools')
            return jsonify(result)
    except MCPIntegrationError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@mcp_integration_bp.route('/tools/execute', methods=['POST'])
@async_route
async def execute_mcp_tool():
    """Execute an MCP tool"""
    if not mcp_bridge:
        return jsonify({
            'success': False,
            'error': 'MCP integration not available'
        }), 503
    
    try:
        data = request.get_json()
        
        # Get auth token from header or environment
        auth_token = request.headers.get('Authorization') or f"Bearer {os.getenv('MCP_AUTH_TOKEN', '')}"
        
        async with MCPFlaskBridge() as bridge:
            result = await bridge.proxy_request(
                '/api/v1/mcp/tools/execute',
                method='POST',
                json=data,
                headers={'Authorization': auth_token}
            )
            return jsonify(result)
    except MCPIntegrationError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@mcp_integration_bp.route('/resources', methods=['GET'])
@async_route
async def list_mcp_resources():
    """List available MCP resources"""
    if not mcp_bridge:
        return jsonify({
            'success': False,
            'error': 'MCP integration not available'
        }), 503
    
    try:
        async with MCPFlaskBridge() as bridge:
            result = await bridge.proxy_request('/api/v1/mcp/resources')
            return jsonify(result)
    except MCPIntegrationError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Integration Instructions
INTEGRATION_INSTRUCTIONS = """
# Flask-MCP Integration Instructions

## 1. Environment Variables Required for MCP

Add these to your .env file or Render environment:

```bash
# MCP Integration Configuration
MCP_ENABLED=true
MCP_BASE_URL=http://localhost:8000  # URL where MCP system runs
MCP_AUTH_TOKEN=<generate-secure-token>
MCP_SERVICE_NAME=sistema-fretes-mcp
MCP_TRANSPORT_TYPE=http
FLASK_MCP_SECRET=<shared-secret-for-communication>

# MCP System Configuration (for the FastAPI app)
MCP_DATABASE_URL=<separate-database-or-same-as-flask>
MCP_REDIS_URL=redis://localhost:6379/1  # Different DB than Flask
MCP_LOG_LEVEL=INFO
MCP_WORKERS=4
```

## 2. Missing Environment Variables for Production

Based on the provided environment variables, these MCP-specific variables are MISSING:

- MCP_ENABLED: Enable/disable MCP integration (not provided)
- MCP_BASE_URL: Where the MCP FastAPI service will run (not provided)
- MCP_AUTH_TOKEN: Authentication between Flask and MCP (not provided)
- MCP_SERVICE_NAME: Identifier for the MCP service (not provided)
- MCP_TRANSPORT_TYPE: Communication protocol (not provided)
- FLASK_MCP_SECRET: Shared secret for secure communication (not provided)

Note: The following variables ARE available and can be used by MCP:
- DATABASE_URL: Can be shared with MCP system
- REDIS_URL: Redis connection available
- ANTHROPIC_API_KEY: For AI functionality
- AWS credentials: For S3 and other AWS services

## 3. Integration Steps

### Step 1: Add to Flask app initialization (app/__init__.py)

```python
# Near the end of create_app function, after other blueprints
try:
    from app.mcp_flask_integration import init_mcp_integration
    init_mcp_integration(app)
    app.logger.info("✅ MCP integration configured")
except Exception as e:
    app.logger.warning(f"⚠️ MCP integration not available: {e}")
```

### Step 2: Run MCP system separately

```bash
# Development
cd app/mcp_sistema
uvicorn main:app --reload --port 8000

# Production (add to Procfile or separate service)
cd app/mcp_sistema && uvicorn main:app --host 0.0.0.0 --port $MCP_PORT
```

### Step 3: Update Nginx/Reverse Proxy

```nginx
# Route MCP API calls to FastAPI
location /mcp/ {
    proxy_pass http://localhost:8000/api/v1/mcp/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

## 4. Compatibility Warnings

### Dependency Conflicts:
1. **Pydantic**: Flask uses 2.11.7, check FastAPI compatibility
2. **SQLAlchemy**: Different versions may cause issues if sharing DB
3. **JWT Libraries**: PyJWT vs python-jose conflict possible

### Port Conflicts:
- Flask runs on port 5000
- MCP needs separate port (8000 recommended)
- Redis needs configuration to avoid conflicts

### Database Considerations:
- Can share PostgreSQL but use different schemas
- Separate Redis databases recommended (0 for Flask, 1 for MCP)
- Consider separate MCP tables with prefix

## 5. Testing Integration

```python
# Test from Flask app
import requests

# Check MCP status
response = requests.get('http://localhost:5000/mcp/status')
print(response.json())

# List available tools
response = requests.get('http://localhost:5000/mcp/tools')
print(response.json())
```

## 6. Production Deployment (sistema-fretes.onrender.com)

### Option 1: Monorepo with Multiple Services
- Create separate service for MCP
- Share database but different schemas
- Internal networking between services

### Option 2: Single Service with Process Manager
- Use supervisor or similar to run both processes
- Modify start script to launch both Flask and FastAPI
- More complex but single deployment

### Option 3: Embedded Mode (Not Recommended)
- Run FastAPI within Flask process
- Performance and compatibility issues likely
- Only for simple use cases

Note: Current production domain is sistema-fretes.onrender.com
"""


def get_integration_instructions():
    """Return integration instructions as a string"""
    return INTEGRATION_INSTRUCTIONS


# Error handler for MCP routes
@mcp_integration_bp.errorhandler(Exception)
def handle_mcp_error(error):
    """Handle errors in MCP integration"""
    logger.error(f"MCP integration error: {error}")
    return jsonify({
        'success': False,
        'error': 'Internal MCP integration error',
        'details': str(error) if current_app.debug else None
    }), 500