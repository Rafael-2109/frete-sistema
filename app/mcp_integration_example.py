"""
Example integration of MCP API with existing Flask application
Shows how to add MCP capabilities to your app
"""

from flask import Flask, render_template
from flask_login import login_required, current_user
from app.mcp_blueprint_integration import register_mcp_blueprints
from app.database import db
import logging

# Example of updating your main Flask app initialization
def create_app_with_mcp(config_name='production'):
    """
    Create Flask app with MCP integration.
    
    This is an example of how to integrate MCP into your existing app.
    """
    app = Flask(__name__)
    app.config.from_object(f'config.{config_name}')
    
    # Initialize extensions
    db.init_app(app)
    # ... other extensions ...
    
    # Register MCP blueprints
    register_mcp_blueprints(app)
    
    # Add MCP-enabled routes to existing views
    @app.route('/workspace/<int:workspace_id>/mcp')
    @login_required
    def workspace_with_mcp(workspace_id):
        """Example: Workspace view with MCP integration."""
        return render_template(
            'workspace_mcp.html',
            workspace_id=workspace_id,
            mcp_enabled=True,
            user_preferences_url=f'/api/mcp/preferences/{current_user.id}'
        )
    
    return app


# Example JavaScript integration for frontend
MCP_FRONTEND_INTEGRATION = """
// Example JavaScript code for integrating MCP API in frontend

class MCPClient {
    constructor(baseUrl = '/api/mcp') {
        this.baseUrl = baseUrl;
        this.sessionId = this.generateSessionId();
    }
    
    generateSessionId() {
        return 'session-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
    }
    
    async processQuery(query, context = {}) {
        const response = await fetch(`${this.baseUrl}/query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Session-ID': this.sessionId
            },
            body: JSON.stringify({
                query: query,
                context: context,
                options: {
                    max_results: 10,
                    include_suggestions: true,
                    auto_execute: false
                }
            })
        });
        
        return await response.json();
    }
    
    async getSuggestions(partialQuery, context = {}) {
        const params = new URLSearchParams({
            partial_query: partialQuery,
            context: JSON.stringify(context),
            limit: 10
        });
        
        const response = await fetch(`${this.baseUrl}/suggestions?${params}`);
        return await response.json();
    }
    
    async submitFeedback(queryId, feedbackType, feedbackData) {
        const response = await fetch(`${this.baseUrl}/feedback`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Session-ID': this.sessionId
            },
            body: JSON.stringify({
                query_id: queryId,
                feedback_type: feedbackType,
                feedback_data: feedbackData
            })
        });
        
        return await response.json();
    }
    
    async confirmAction(actionId, actionType, actionDetails, confirmed, reason = '') {
        const response = await fetch(`${this.baseUrl}/confirm-action`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Session-ID': this.sessionId
            },
            body: JSON.stringify({
                action_id: actionId,
                action_type: actionType,
                action_details: actionDetails,
                confirmation: confirmed,
                reason: reason
            })
        });
        
        return await response.json();
    }
    
    async getUserPreferences(userId) {
        const response = await fetch(`${this.baseUrl}/preferences/${userId}`, {
            headers: {
                'X-Session-ID': this.sessionId
            }
        });
        
        return await response.json();
    }
}

// Example usage in your application
const mcpClient = new MCPClient();

// Process a natural language query
async function handleUserQuery(query) {
    const result = await mcpClient.processQuery(query, {
        workspace_id: currentWorkspaceId,
        filters: getActiveFilters()
    });
    
    if (result.success) {
        displayQueryResult(result.data);
        
        // Show confirmation dialog for sensitive actions
        if (result.data.result.requires_confirmation) {
            const confirmed = await showConfirmationDialog(result.data.result);
            if (confirmed) {
                await mcpClient.confirmAction(
                    result.data.result.action_id,
                    result.data.result.action_type,
                    result.data.result.action_details,
                    true
                );
            }
        }
    }
}

// Autocomplete suggestions
async function setupAutocomplete(inputElement) {
    let debounceTimer;
    
    inputElement.addEventListener('input', (e) => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(async () => {
            const suggestions = await mcpClient.getSuggestions(e.target.value);
            if (suggestions.success) {
                displaySuggestions(suggestions.data.suggestions);
            }
        }, 300);
    });
}
"""


# Example cURL commands for testing
EXAMPLE_CURL_COMMANDS = """
# Test MCP API endpoints with cURL

# 1. Process a natural language query
curl -X POST http://localhost:5000/api/mcp/query \\
  -H "Content-Type: application/json" \\
  -H "X-Session-ID: test-session-123" \\
  -d '{
    "query": "Show me all pending orders for workspace 123",
    "context": {
      "workspace_id": 123
    },
    "options": {
      "max_results": 10,
      "include_suggestions": true
    }
  }'

# 2. Get query suggestions
curl -X GET "http://localhost:5000/api/mcp/suggestions?partial_query=show%20me&limit=5"

# 3. Submit feedback (requires authentication)
curl -X POST http://localhost:5000/api/mcp/feedback \\
  -H "Content-Type: application/json" \\
  -H "Cookie: session=your-session-cookie" \\
  -d '{
    "query_id": "query-123",
    "feedback_type": "positive",
    "feedback_data": {
      "rating": 5,
      "comment": "Perfect results!"
    }
  }'

# 4. Get user preferences (requires authentication)
curl -X GET http://localhost:5000/api/mcp/preferences/1 \\
  -H "Cookie: session=your-session-cookie"

# 5. Confirm an action (requires authentication)
curl -X POST http://localhost:5000/api/mcp/confirm-action \\
  -H "Content-Type: application/json" \\
  -H "Cookie: session=your-session-cookie" \\
  -d '{
    "action_id": "action-456",
    "action_type": "delete",
    "action_details": {
      "description": "Delete 5 old records",
      "impact": "This will permanently remove records",
      "reversible": false
    },
    "confirmation": true
  }'

# 6. Health check
curl -X GET http://localhost:5000/api/mcp/health
"""


def save_examples():
    """Save example code to files for easy reference."""
    # Save JavaScript client example
    with open('static/js/mcp-client.js', 'w') as f:
        f.write(MCP_FRONTEND_INTEGRATION)
    
    # Save cURL examples
    with open('docs/mcp-api-examples.sh', 'w') as f:
        f.write(EXAMPLE_CURL_COMMANDS)
    
    logging.info("MCP integration examples saved")


if __name__ == '__main__':
    # This is just an example - integrate into your actual app initialization
    print("MCP Integration Example")
    print("See mcp_api.py for the full API implementation")
    print("See mcp_blueprint_integration.py for Flask integration")