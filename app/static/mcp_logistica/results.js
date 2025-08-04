// MCP Logística Results JavaScript
$(document).ready(function() {
    // Initialize DataTable if results exist
    if ($('#results-table').length > 0) {
        const table = $('#results-table').DataTable({
            pageLength: 25,
            responsive: true,
            order: [],
            language: {
                url: '//cdn.datatables.net/plug-ins/1.11.5/i18n/pt-BR.json'
            },
            dom: 'Bfrtip',
            buttons: [
                {
                    extend: 'copy',
                    text: '<i class="fas fa-copy"></i> Copiar',
                    className: 'btn btn-sm btn-secondary'
                },
                {
                    extend: 'csv',
                    text: '<i class="fas fa-file-csv"></i> CSV',
                    className: 'btn btn-sm btn-secondary'
                },
                {
                    extend: 'excel',
                    text: '<i class="fas fa-file-excel"></i> Excel',
                    className: 'btn btn-sm btn-secondary'
                },
                {
                    extend: 'print',
                    text: '<i class="fas fa-print"></i> Imprimir',
                    className: 'btn btn-sm btn-secondary'
                }
            ]
        });
        
        // Custom export buttons
        $('#export-csv').on('click', function() {
            exportTableToCSV('resultados.csv');
        });
        
        $('#export-excel').on('click', function() {
            exportTableToExcel('resultados.xlsx');
        });
    }
    
    // Action buttons
    $('.action-btn').on('click', function() {
        const $btn = $(this);
        const actionId = $btn.data('action');
        const requiresConfirm = $btn.data('confirm');
        
        if (requiresConfirm) {
            showConfirmationModal(actionId, $btn.text());
        } else {
            executeAction(actionId);
        }
    });
    
    // Confirmation modal
    function showConfirmationModal(actionId, actionName) {
        const $modal = $('#confirmationModal');
        const $confirmBtn = $('#confirm-action-btn');
        
        $('#confirmation-message').text(`Tem certeza que deseja executar a ação: ${actionName}?`);
        
        // Remove previous handlers
        $confirmBtn.off('click');
        
        // Add new handler
        $confirmBtn.on('click', function() {
            $modal.modal('hide');
            executeAction(actionId);
        });
        
        $modal.modal('show');
    }
    
    // Execute action
    function executeAction(actionId) {
        // Show loading
        showLoading();
        
        $.ajax({
            url: '/mcp_logistica/execute_action',
            method: 'POST',
            data: {
                action_id: actionId,
                context: getActionContext()
            },
            success: function(response) {
                hideLoading();
                
                if (response.success) {
                    showSuccessModal(response.message || 'Ação executada com sucesso!');
                    
                    // Reload page if needed
                    if (response.reload) {
                        setTimeout(function() {
                            window.location.reload();
                        }, 2000);
                    }
                } else {
                    showErrorModal(response.message || 'Erro ao executar ação');
                }
            },
            error: function(xhr, status, error) {
                hideLoading();
                showErrorModal('Erro de comunicação: ' + error);
            }
        });
    }
    
    // Get action context (selected items, filters, etc.)
    function getActionContext() {
        const context = {
            query: $('meta[name="query"]').attr('content'),
            selected_rows: []
        };
        
        // Get selected rows if using checkboxes
        $('.row-checkbox:checked').each(function() {
            context.selected_rows.push($(this).val());
        });
        
        return context;
    }
    
    // Export functions
    function exportTableToCSV(filename) {
        const csv = [];
        const rows = $('#results-table').find('tr');
        
        rows.each(function() {
            const row = [];
            $(this).find('td, th').each(function() {
                row.push('"' + $(this).text().replace(/"/g, '""') + '"');
            });
            csv.push(row.join(','));
        });
        
        downloadFile(csv.join('\n'), filename, 'text/csv;charset=utf-8;');
    }
    
    function exportTableToExcel(filename) {
        // For Excel export, we'll use server-side generation
        window.location.href = `/mcp_logistica/export?format=excel&query=${encodeURIComponent($('meta[name="query"]').attr('content'))}`;
    }
    
    function downloadFile(content, filename, mimeType) {
        const blob = new Blob([content], { type: mimeType });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = filename;
        link.click();
        URL.revokeObjectURL(link.href);
    }
    
    // Modal helpers
    function showSuccessModal(message) {
        const $modal = $('#successModal');
        $('#success-message').text(message);
        $modal.modal('show');
    }
    
    function showErrorModal(message, details = null) {
        const $modal = $('#errorModal');
        $('#error-message').text(message);
        
        if (details) {
            $('#error-details').show();
            $('#error-details-content').text(details);
        } else {
            $('#error-details').hide();
        }
        
        $modal.modal('show');
    }
    
    // Report error button
    $('#report-error-btn').on('click', function() {
        const errorDetails = {
            message: $('#error-message').text(),
            details: $('#error-details-content').text(),
            query: $('meta[name="query"]').attr('content'),
            timestamp: new Date().toISOString(),
            userAgent: navigator.userAgent
        };
        
        // Send error report
        $.post('/mcp_logistica/report_error', errorDetails, function(response) {
            alert('Erro reportado com sucesso. Obrigado!');
            $('#errorModal').modal('hide');
        });
    });
    
    // Loading helpers
    function showLoading() {
        $('body').append('<div class="loading-overlay"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Carregando...</span></div></div>');
    }
    
    function hideLoading() {
        $('.loading-overlay').remove();
    }
    
    // Auto-refresh functionality
    const autoRefresh = $('meta[name="auto-refresh"]').attr('content');
    const refreshInterval = parseInt($('meta[name="refresh-interval"]').attr('content') || '30');
    
    if (autoRefresh === 'true') {
        setTimeout(function() {
            window.location.reload();
        }, refreshInterval * 1000);
        
        // Show countdown
        let countdown = refreshInterval;
        const $countdownElement = $('<div class="position-fixed bottom-0 start-0 p-3 text-muted small">Atualização em <span id="countdown">' + countdown + '</span>s</div>');
        $('body').append($countdownElement);
        
        setInterval(function() {
            countdown--;
            $('#countdown').text(countdown);
        }, 1000);
    }
    
    // Highlight search terms in results
    const searchTerms = $('meta[name="search-terms"]').attr('content');
    if (searchTerms) {
        const terms = searchTerms.split(',');
        terms.forEach(function(term) {
            highlightText(term.trim());
        });
    }
    
    function highlightText(term) {
        if (!term) return;
        
        $('#results-table td').each(function() {
            const $cell = $(this);
            const html = $cell.html();
            const regex = new RegExp('(' + escapeRegex(term) + ')', 'gi');
            $cell.html(html.replace(regex, '<mark>$1</mark>'));
        });
    }
    
    function escapeRegex(string) {
        return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }
});

// Add custom styles for loading overlay
$('<style>')
    .text(`
        .loading-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 9999;
        }
        .loading-overlay .spinner-border {
            width: 3rem;
            height: 3rem;
        }
    `)
    .appendTo('head');