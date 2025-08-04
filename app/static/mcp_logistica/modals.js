// MCP Logística Modals JavaScript
// This file handles all modal interactions

window.MCPModals = (function() {
    'use strict';
    
    // Modal instances
    let confirmationModal = null;
    let actionResultModal = null;
    let errorModal = null;
    let successModal = null;
    let batchActionModal = null;
    let infoModal = null;
    
    // Initialize modals
    function init() {
        // Get modal elements
        const $confirmationModal = $('#confirmationModal');
        const $actionResultModal = $('#actionResultModal');
        const $errorModal = $('#errorModal');
        const $successModal = $('#successModal');
        const $batchActionModal = $('#batchActionModal');
        const $infoModal = $('#infoModal');
        
        // Create Bootstrap modal instances
        if ($confirmationModal.length) {
            confirmationModal = new bootstrap.Modal($confirmationModal[0]);
        }
        if ($actionResultModal.length) {
            actionResultModal = new bootstrap.Modal($actionResultModal[0]);
        }
        if ($errorModal.length) {
            errorModal = new bootstrap.Modal($errorModal[0]);
        }
        if ($successModal.length) {
            successModal = new bootstrap.Modal($successModal[0]);
        }
        if ($batchActionModal.length) {
            batchActionModal = new bootstrap.Modal($batchActionModal[0]);
        }
        if ($infoModal.length) {
            infoModal = new bootstrap.Modal($infoModal[0]);
        }
        
        // Setup batch action modal handlers
        setupBatchActionHandlers();
    }
    
    // Show confirmation modal
    function showConfirmation(options) {
        const defaults = {
            title: 'Confirmar Ação',
            message: 'Tem certeza que deseja executar esta ação?',
            details: null,
            confirmText: 'Confirmar',
            cancelText: 'Cancelar',
            confirmClass: 'btn-primary',
            onConfirm: function() {},
            onCancel: function() {}
        };
        
        const settings = $.extend({}, defaults, options);
        
        // Update modal content
        $('#confirmationModalLabel').text(settings.title);
        $('#confirmation-message').text(settings.message);
        
        if (settings.details) {
            $('#confirmation-details').html(settings.details).show();
        } else {
            $('#confirmation-details').hide();
        }
        
        const $confirmBtn = $('#confirm-action-btn');
        $confirmBtn.text(settings.confirmText)
            .removeClass('btn-primary btn-danger btn-warning')
            .addClass(settings.confirmClass);
        
        // Setup handlers
        $confirmBtn.off('click').on('click', function() {
            confirmationModal.hide();
            settings.onConfirm();
        });
        
        // Show modal
        confirmationModal.show();
    }
    
    // Show action result modal
    function showActionResult(options) {
        const defaults = {
            title: 'Resultado da Ação',
            content: '',
            size: 'modal-lg'
        };
        
        const settings = $.extend({}, defaults, options);
        
        // Update modal
        $('#actionResultModalLabel').text(settings.title);
        $('#action-result-content').html(settings.content);
        
        // Update size
        const $dialog = $('#actionResultModal .modal-dialog');
        $dialog.removeClass('modal-sm modal-lg modal-xl').addClass(settings.size);
        
        // Show modal
        actionResultModal.show();
    }
    
    // Show error modal
    function showError(message, details = null) {
        $('#error-message').text(message);
        
        if (details) {
            $('#error-details').show();
            $('#error-details-content').text(details);
        } else {
            $('#error-details').hide();
        }
        
        errorModal.show();
    }
    
    // Show success modal
    function showSuccess(message) {
        $('#success-message').text(message);
        successModal.show();
    }
    
    // Show batch action modal
    function showBatchAction(selectedItems) {
        // Clear previous state
        $('#batch-action-select').val('');
        $('#batch-action-options').empty();
        $('#execute-batch-action-btn').prop('disabled', true);
        
        // Display selected items
        let itemsHtml = '<ul class="mb-0">';
        selectedItems.forEach(function(item) {
            itemsHtml += `<li>${item}</li>`;
        });
        itemsHtml += '</ul>';
        
        $('#batch-items-list').html(itemsHtml);
        
        // Store selected items
        $('#batchActionModal').data('selectedItems', selectedItems);
        
        // Show modal
        batchActionModal.show();
    }
    
    // Show info modal
    function showInfo(title, content) {
        $('#infoModalLabel').text(title);
        $('#info-content').html(content);
        infoModal.show();
    }
    
    // Setup batch action handlers
    function setupBatchActionHandlers() {
        // Action selection change
        $('#batch-action-select').on('change', function() {
            const action = $(this).val();
            const $optionsContainer = $('#batch-action-options');
            const $executeBtn = $('#execute-batch-action-btn');
            
            $optionsContainer.empty();
            
            if (!action) {
                $executeBtn.prop('disabled', true);
                return;
            }
            
            $executeBtn.prop('disabled', false);
            
            // Show action-specific options
            switch (action) {
                case 'update-status':
                    $optionsContainer.html(`
                        <div class="mb-3">
                            <label for="new-status" class="form-label">Novo Status:</label>
                            <select class="form-select" id="new-status">
                                <option value="pending">Pendente</option>
                                <option value="processing">Processando</option>
                                <option value="completed">Concluído</option>
                                <option value="cancelled">Cancelado</option>
                            </select>
                        </div>
                    `);
                    break;
                    
                case 'assign-batch':
                    $optionsContainer.html(`
                        <div class="mb-3">
                            <label for="batch-number" class="form-label">Número do Lote:</label>
                            <input type="text" class="form-control" id="batch-number" placeholder="Ex: LOTE-2024-001">
                        </div>
                    `);
                    break;
                    
                case 'generate-report':
                    $optionsContainer.html(`
                        <div class="mb-3">
                            <label for="report-type" class="form-label">Tipo de Relatório:</label>
                            <select class="form-select" id="report-type">
                                <option value="summary">Resumo</option>
                                <option value="detailed">Detalhado</option>
                                <option value="analytics">Analítico</option>
                            </select>
                        </div>
                        <div class="mb-3">
                            <label for="report-format" class="form-label">Formato:</label>
                            <select class="form-select" id="report-format">
                                <option value="pdf">PDF</option>
                                <option value="excel">Excel</option>
                                <option value="csv">CSV</option>
                            </select>
                        </div>
                    `);
                    break;
                    
                case 'export-data':
                    $optionsContainer.html(`
                        <div class="mb-3">
                            <label for="export-format" class="form-label">Formato de Exportação:</label>
                            <select class="form-select" id="export-format">
                                <option value="csv">CSV</option>
                                <option value="excel">Excel</option>
                                <option value="json">JSON</option>
                                <option value="xml">XML</option>
                            </select>
                        </div>
                        <div class="form-check mb-3">
                            <input class="form-check-input" type="checkbox" id="include-related" checked>
                            <label class="form-check-label" for="include-related">
                                Incluir dados relacionados
                            </label>
                        </div>
                    `);
                    break;
            }
        });
        
        // Execute batch action
        $('#execute-batch-action-btn').on('click', function() {
            const action = $('#batch-action-select').val();
            const selectedItems = $('#batchActionModal').data('selectedItems');
            
            if (!action || !selectedItems) {
                showError('Nenhuma ação ou itens selecionados');
                return;
            }
            
            // Collect options
            const options = {};
            $('#batch-action-options').find('input, select').each(function() {
                const $el = $(this);
                if ($el.is(':checkbox')) {
                    options[$el.attr('id')] = $el.is(':checked');
                } else {
                    options[$el.attr('id')] = $el.val();
                }
            });
            
            // Hide modal
            batchActionModal.hide();
            
            // Execute action
            executeBatchAction(action, selectedItems, options);
        });
    }
    
    // Execute batch action
    function executeBatchAction(action, items, options) {
        // Show loading
        const $loading = $('<div class="loading-overlay"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Processando...</span></div></div>');
        $('body').append($loading);
        
        $.ajax({
            url: '/mcp_logistica/batch_action',
            method: 'POST',
            data: {
                action: action,
                items: items,
                options: options
            },
            success: function(response) {
                $loading.remove();
                
                if (response.success) {
                    showSuccess(response.message || 'Ação em lote executada com sucesso!');
                    
                    // Reload if needed
                    if (response.reload) {
                        setTimeout(function() {
                            window.location.reload();
                        }, 2000);
                    }
                } else {
                    showError(response.message || 'Erro ao executar ação em lote', response.details);
                }
            },
            error: function(xhr, status, error) {
                $loading.remove();
                showError('Erro de comunicação: ' + error);
            }
        });
    }
    
    // Public API
    return {
        init: init,
        showConfirmation: showConfirmation,
        showActionResult: showActionResult,
        showError: showError,
        showSuccess: showSuccess,
        showBatchAction: showBatchAction,
        showInfo: showInfo
    };
})();

// Initialize when DOM is ready
$(document).ready(function() {
    MCPModals.init();
});