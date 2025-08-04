// MCP Logística Main JavaScript
$(document).ready(function() {
    // Cache DOM elements
    const $queryForm = $('#nlq-form');
    const $queryTextarea = $('#query');
    const $submitButton = $('#submit-query');
    const $clearButton = $('#clear-form');
    const $loadingModal = $('#loadingModal');
    const $recentQueriesContainer = $('#recent-queries-container');
    
    // Initialize tooltips
    $('[data-bs-toggle="tooltip"]').tooltip();
    
    // Auto-resize textarea
    $queryTextarea.on('input', function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
    });
    
    // Clear form button
    $clearButton.on('click', function() {
        $queryTextarea.val('').trigger('input');
        $('#output_format').val('table');
        $('#limit').val('100');
    });
    
    // Quick query buttons
    $('.quick-query').on('click', function() {
        const query = $(this).data('query');
        $queryTextarea.val(query).trigger('input');
        $queryForm.submit();
    });
    
    // Form submission
    $queryForm.on('submit', function(e) {
        e.preventDefault();
        
        // Validate form
        if (!$queryTextarea.val().trim()) {
            showToast('Por favor, digite uma consulta', 'warning');
            return;
        }
        
        // Show loading modal
        const loadingModal = new bootstrap.Modal($loadingModal[0]);
        loadingModal.show();
        
        // Save to recent queries
        saveRecentQuery($queryTextarea.val());
        
        // Submit form
        this.submit();
    });
    
    // Load recent queries
    loadRecentQueries();
    
    // Keyboard shortcuts
    $(document).on('keydown', function(e) {
        // Ctrl/Cmd + Enter to submit
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            e.preventDefault();
            $queryForm.submit();
        }
        
        // Ctrl/Cmd + K to focus search
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            $queryTextarea.focus();
        }
        
        // Escape to clear form
        if (e.key === 'Escape' && $queryTextarea.is(':focus')) {
            e.preventDefault();
            $clearButton.click();
        }
    });
    
    // Recent queries functionality
    function loadRecentQueries() {
        const recentQueries = getRecentQueries();
        
        if (recentQueries.length === 0) {
            return;
        }
        
        let html = '<div class="list-group">';
        recentQueries.forEach(function(item) {
            html += `
                <div class="list-group-item list-group-item-action recent-query-item" data-query="${escapeHtml(item.query)}">
                    <div class="d-flex w-100 justify-content-between">
                        <p class="mb-1">${escapeHtml(item.query)}</p>
                        <small class="recent-query-time">${formatTime(item.timestamp)}</small>
                    </div>
                </div>
            `;
        });
        html += '</div>';
        
        $recentQueriesContainer.html(html);
    }
    
    // Click on recent query
    $(document).on('click', '.recent-query-item', function() {
        const query = $(this).data('query');
        $queryTextarea.val(query).trigger('input');
    });
    
    // Save recent query to localStorage
    function saveRecentQuery(query) {
        let recentQueries = getRecentQueries();
        
        // Remove duplicates
        recentQueries = recentQueries.filter(item => item.query !== query);
        
        // Add new query
        recentQueries.unshift({
            query: query,
            timestamp: new Date().getTime()
        });
        
        // Keep only last 10 queries
        recentQueries = recentQueries.slice(0, 10);
        
        localStorage.setItem('mcp_recent_queries', JSON.stringify(recentQueries));
        loadRecentQueries();
    }
    
    // Get recent queries from localStorage
    function getRecentQueries() {
        const stored = localStorage.getItem('mcp_recent_queries');
        return stored ? JSON.parse(stored) : [];
    }
    
    // Format timestamp
    function formatTime(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const diff = now - date;
        
        if (diff < 60000) {
            return 'Agora';
        } else if (diff < 3600000) {
            return Math.floor(diff / 60000) + ' min atrás';
        } else if (diff < 86400000) {
            return Math.floor(diff / 3600000) + 'h atrás';
        } else {
            return date.toLocaleDateString('pt-BR');
        }
    }
    
    // Show toast notification
    function showToast(message, type = 'info') {
        const toastHtml = `
            <div class="toast align-items-center text-white bg-${type} border-0" role="alert" aria-live="assertive" aria-atomic="true">
                <div class="d-flex">
                    <div class="toast-body">
                        ${message}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
            </div>
        `;
        
        const $toastContainer = $('#toast-container');
        if ($toastContainer.length === 0) {
            $('body').append('<div id="toast-container" class="position-fixed bottom-0 end-0 p-3" style="z-index: 11"></div>');
        }
        
        const $toast = $(toastHtml);
        $('#toast-container').append($toast);
        
        const toast = new bootstrap.Toast($toast[0]);
        toast.show();
        
        $toast.on('hidden.bs.toast', function() {
            $(this).remove();
        });
    }
    
    // Escape HTML
    function escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, m => map[m]);
    }
    
    // Auto-save form state
    $queryTextarea.on('input', function() {
        localStorage.setItem('mcp_draft_query', $(this).val());
    });
    
    // Restore draft query
    const draftQuery = localStorage.getItem('mcp_draft_query');
    if (draftQuery) {
        $queryTextarea.val(draftQuery).trigger('input');
    }
    
    // Clear draft on successful submission
    $queryForm.on('submit', function() {
        localStorage.removeItem('mcp_draft_query');
    });
});