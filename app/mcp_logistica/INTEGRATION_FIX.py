"""
MCP Logistics Integration Fix
This file contains the code needed to properly integrate MCP Logistics into the main app
"""

# Add this to app/__init__.py in the blueprint registration section (around line 500)

# Import the MCP Logistics blueprint registration function
from app.mcp_logistica.flask_integration import register_blueprint as register_mcp_logistica

# Then in the blueprint registration section, add:
register_mcp_logistica(app)

# Also ensure the following is in your app config:
# ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')  # Optional - for Claude AI

# Example of complete integration:
"""
# Around line 509 in app/__init__.py, after claude_ai_bp registration:

# MCP Logistics Integration
try:
    from app.mcp_logistica.flask_integration import register_blueprint as register_mcp_logistica
    register_mcp_logistica(app)
    logger.info("MCP Logistics module registered successfully")
except ImportError as e:
    logger.warning(f"MCP Logistics module not available: {e}")
except Exception as e:
    logger.error(f"Error registering MCP Logistics: {e}")
"""

# Create placeholder static files to avoid 404 errors:

STYLE_CSS = """
/* MCP Logistics Styles */
.page-title {
    color: #2c3e50;
    margin-bottom: 1.5rem;
}

.quick-action-card {
    transition: transform 0.2s;
    cursor: pointer;
}

.quick-action-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 5px 15px rgba(0,0,0,0.1);
}

.json-display {
    background-color: #f8f9fa;
    border-radius: 5px;
    padding: 1rem;
    max-height: 500px;
    overflow-y: auto;
}

#recent-queries-container .query-item {
    padding: 0.5rem;
    border-left: 3px solid #007bff;
    margin-bottom: 0.5rem;
    background-color: #f8f9fa;
}

.toast {
    min-width: 300px;
}
"""

MAIN_JS = """
// MCP Logistics Main JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Quick action buttons
    const quickQueryButtons = document.querySelectorAll('.quick-query');
    quickQueryButtons.forEach(button => {
        button.addEventListener('click', function() {
            const query = this.dataset.query;
            document.getElementById('query').value = query;
            document.getElementById('nlq-form').submit();
        });
    });

    // Clear form button
    const clearButton = document.getElementById('clear-form');
    if (clearButton) {
        clearButton.addEventListener('click', function() {
            document.getElementById('nlq-form').reset();
        });
    }

    // Form submission with loading modal
    const nlqForm = document.getElementById('nlq-form');
    if (nlqForm) {
        nlqForm.addEventListener('submit', function() {
            const loadingModal = new bootstrap.Modal(document.getElementById('loadingModal'));
            loadingModal.show();
        });
    }

    // Load recent queries
    loadRecentQueries();
});

function loadRecentQueries() {
    // This would load from localStorage or make an API call
    const recentQueries = JSON.parse(localStorage.getItem('mcp_recent_queries') || '[]');
    const container = document.getElementById('recent-queries-container');
    
    if (recentQueries.length > 0) {
        container.innerHTML = recentQueries.map(q => `
            <div class="query-item">
                <small class="text-muted">${new Date(q.timestamp).toLocaleString()}</small>
                <div>${q.query}</div>
            </div>
        `).join('');
    }
}
"""

RESULTS_JS = """
// MCP Logistics Results JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Initialize DataTable if present
    const resultsTable = document.getElementById('results-table');
    if (resultsTable && typeof $.fn.DataTable !== 'undefined') {
        $(resultsTable).DataTable({
            pageLength: 25,
            responsive: true,
            language: {
                url: '//cdn.datatables.net/plug-ins/1.11.5/i18n/pt-BR.json'
            }
        });
    }

    // Export buttons
    document.getElementById('export-csv')?.addEventListener('click', exportToCSV);
    document.getElementById('export-excel')?.addEventListener('click', exportToExcel);

    // Action buttons
    document.querySelectorAll('.action-btn').forEach(btn => {
        btn.addEventListener('click', handleAction);
    });
});

function exportToCSV() {
    // Implementation for CSV export
    alert('Export to CSV - To be implemented');
}

function exportToExcel() {
    // Implementation for Excel export
    alert('Export to Excel - To be implemented');
}

function handleAction(event) {
    const button = event.currentTarget;
    const actionId = button.dataset.action;
    const requiresConfirm = button.dataset.confirm === 'true';
    
    if (requiresConfirm) {
        // Show confirmation modal
        const confirmModal = new bootstrap.Modal(document.getElementById('confirmationModal'));
        document.getElementById('confirm-action-btn').onclick = () => {
            executeAction(actionId);
            confirmModal.hide();
        };
        confirmModal.show();
    } else {
        executeAction(actionId);
    }
}

function executeAction(actionId) {
    // Implementation for executing actions
    console.log('Executing action:', actionId);
}
"""

PREFERENCES_JS = """
// MCP Logistics Preferences JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Auto-refresh toggle
    const autoRefreshCheckbox = document.getElementById('auto_refresh');
    const refreshIntervalContainer = document.getElementById('refresh_interval_container');
    
    if (autoRefreshCheckbox) {
        autoRefreshCheckbox.addEventListener('change', function() {
            refreshIntervalContainer.style.display = this.checked ? 'block' : 'none';
        });
    }

    // Remove favorite query
    document.querySelectorAll('.remove-favorite').forEach(btn => {
        btn.addEventListener('click', function() {
            const query = this.dataset.query;
            removeFavoriteQuery(query);
        });
    });

    // Reset preferences
    document.getElementById('reset-preferences')?.addEventListener('click', function() {
        if (confirm('Tem certeza que deseja restaurar as configurações padrão?')) {
            resetPreferences();
        }
    });
});

function removeFavoriteQuery(query) {
    // Remove query from favorites
    const btn = document.querySelector(`[data-query="${query}"]`);
    if (btn) {
        btn.closest('.favorite-query-item').remove();
    }
}

function resetPreferences() {
    // Reset form to defaults
    document.getElementById('preferences-form').reset();
    // Trigger change events
    document.getElementById('auto_refresh').dispatchEvent(new Event('change'));
}
"""

# Instructions to create the static files:
print("""
To complete the integration:

1. Add to app/__init__.py (around line 509):
   from app.mcp_logistica.flask_integration import register_blueprint as register_mcp_logistica
   register_mcp_logistica(app)

2. Create static files:
   - app/static/mcp_logistica/style.css (content above)
   - app/static/mcp_logistica/main.js (content above)
   - app/static/mcp_logistica/results.js (content above)
   - app/static/mcp_logistica/preferences.js (content above)

3. Add to config (optional, for Claude AI):
   ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')

4. Run migrations if needed:
   flask db upgrade

5. Test the integration:
   curl http://localhost:5000/api/mcp/logistica/health
""")