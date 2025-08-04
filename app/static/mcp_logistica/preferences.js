// MCP Logística Preferences JavaScript
$(document).ready(function() {
    // Cache DOM elements
    const $preferencesForm = $('#preferences-form');
    const $autoRefreshCheckbox = $('#auto_refresh');
    const $refreshIntervalContainer = $('#refresh_interval_container');
    const $saveButton = $('#save-preferences');
    const $resetButton = $('#reset-preferences');
    
    // Toggle refresh interval visibility
    $autoRefreshCheckbox.on('change', function() {
        if ($(this).is(':checked')) {
            $refreshIntervalContainer.slideDown();
        } else {
            $refreshIntervalContainer.slideUp();
        }
    });
    
    // Remove favorite query
    $(document).on('click', '.remove-favorite', function(e) {
        e.preventDefault();
        const $btn = $(this);
        const query = $btn.data('query');
        
        if (confirm('Remover esta consulta dos favoritos?')) {
            $btn.closest('.favorite-query-item').fadeOut(function() {
                $(this).remove();
                
                // Update empty state if needed
                if ($('#favorite-queries-list .favorite-query-item').length === 0) {
                    $('#favorite-queries-list').html('<p class="text-muted mb-0">Nenhuma consulta favorita salva.</p>');
                }
            });
            
            // Add to form data for backend processing
            $('<input>').attr({
                type: 'hidden',
                name: 'removed_favorites[]',
                value: query
            }).appendTo($preferencesForm);
        }
    });
    
    // Form validation
    $preferencesForm.on('submit', function(e) {
        e.preventDefault();
        
        // Validate numeric fields
        const defaultLimit = parseInt($('#default_limit').val());
        const refreshInterval = parseInt($('#refresh_interval').val());
        
        if (defaultLimit < 1 || defaultLimit > 1000) {
            showAlert('O limite de resultados deve estar entre 1 e 1000', 'danger');
            return false;
        }
        
        if ($autoRefreshCheckbox.is(':checked') && (refreshInterval < 5 || refreshInterval > 300)) {
            showAlert('O intervalo de atualização deve estar entre 5 e 300 segundos', 'danger');
            return false;
        }
        
        // Show saving state
        $saveButton.prop('disabled', true).html('<i class="fas fa-spinner fa-spin"></i> Salvando...');
        
        // Submit form via AJAX
        $.ajax({
            url: $(this).attr('action'),
            method: 'POST',
            data: $(this).serialize(),
            success: function(response) {
                if (response.success) {
                    showAlert('Preferências salvas com sucesso!', 'success');
                    
                    // Update localStorage with new preferences
                    localStorage.setItem('mcp_preferences', JSON.stringify(response.preferences));
                    
                    // Redirect after a short delay
                    setTimeout(function() {
                        window.location.href = response.redirect || '/mcp_logistica';
                    }, 1500);
                } else {
                    showAlert(response.message || 'Erro ao salvar preferências', 'danger');
                    $saveButton.prop('disabled', false).html('<i class="fas fa-save"></i> Salvar Preferências');
                }
            },
            error: function(xhr, status, error) {
                showAlert('Erro de comunicação: ' + error, 'danger');
                $saveButton.prop('disabled', false).html('<i class="fas fa-save"></i> Salvar Preferências');
            }
        });
    });
    
    // Reset preferences
    $resetButton.on('click', function() {
        if (confirm('Tem certeza que deseja restaurar as configurações padrão?')) {
            // Reset form to defaults
            $('#default_output_format').val('table');
            $('#default_limit').val('100');
            $('#items_per_page').val('25');
            $('#show_sql_query').prop('checked', false);
            $('#auto_refresh').prop('checked', false).trigger('change');
            $('#refresh_interval').val('30');
            $('#language').val('pt-br');
            $('#save_query_history').prop('checked', true);
            $('#suggest_queries').prop('checked', true);
            $('#enable_shortcuts').prop('checked', true);
            $('#notify_query_complete').prop('checked', true);
            $('#notify_errors').prop('checked', true);
            $('#notify_alerts').prop('checked', true);
            $('#notification_sound').val('bell');
            $('#default_export_format').val('csv');
            $('#include_headers').prop('checked', true);
            $('#include_metadata').prop('checked', false);
            $('#csv_delimiter').val(',');
            
            // Clear localStorage
            localStorage.removeItem('mcp_preferences');
            localStorage.removeItem('mcp_recent_queries');
            
            showAlert('Configurações restauradas para o padrão', 'info');
        }
    });
    
    // Keyboard shortcuts info
    if ($('#enable_shortcuts').is(':checked')) {
        addKeyboardShortcutsInfo();
    }
    
    $('#enable_shortcuts').on('change', function() {
        if ($(this).is(':checked')) {
            addKeyboardShortcutsInfo();
        } else {
            $('#keyboard-shortcuts-info').remove();
        }
    });
    
    function addKeyboardShortcutsInfo() {
        if ($('#keyboard-shortcuts-info').length === 0) {
            const shortcutsHtml = `
                <div id="keyboard-shortcuts-info" class="alert alert-info mt-3">
                    <h6>Atalhos de Teclado:</h6>
                    <ul class="mb-0">
                        <li><span class="keyboard-shortcut">Ctrl+Enter</span> - Executar consulta</li>
                        <li><span class="keyboard-shortcut">Ctrl+K</span> - Focar no campo de consulta</li>
                        <li><span class="keyboard-shortcut">Esc</span> - Limpar formulário</li>
                        <li><span class="keyboard-shortcut">Ctrl+S</span> - Salvar preferências</li>
                    </ul>
                </div>
            `;
            $('#enable_shortcuts').closest('.mb-3').after(shortcutsHtml);
        }
    }
    
    // Test notification sound
    $(document).on('click', '.test-sound', function() {
        const sound = $('#notification_sound').val();
        if (sound !== 'none') {
            playNotificationSound(sound);
        }
    });
    
    // Add test button for notification sound
    $('#notification_sound').after('<button type="button" class="btn btn-sm btn-outline-secondary mt-2 test-sound"><i class="fas fa-volume-up"></i> Testar Som</button>');
    
    function playNotificationSound(type) {
        const audio = new Audio(`/static/mcp_logistica/sounds/${type}.mp3`);
        audio.play().catch(function(error) {
            console.log('Error playing sound:', error);
        });
    }
    
    // Show alert helper
    function showAlert(message, type) {
        const alertHtml = `
            <div class="alert alert-${type} alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-3" style="z-index: 1050;" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;
        
        const $alert = $(alertHtml);
        $('body').append($alert);
        
        // Auto-dismiss after 5 seconds
        setTimeout(function() {
            $alert.alert('close');
        }, 5000);
    }
    
    // Keyboard shortcuts for preferences page
    $(document).on('keydown', function(e) {
        // Ctrl/Cmd + S to save
        if ((e.ctrlKey || e.metaKey) && e.key === 's') {
            e.preventDefault();
            $preferencesForm.submit();
        }
    });
    
    // Import/Export preferences
    $('#export-preferences').on('click', function() {
        const preferences = $preferencesForm.serializeArray();
        const data = {};
        
        preferences.forEach(function(item) {
            data[item.name] = item.value;
        });
        
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = 'mcp_preferences.json';
        link.click();
        URL.revokeObjectURL(url);
    });
    
    $('#import-preferences').on('click', function() {
        $('#import-file').click();
    });
    
    $('#import-file').on('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function(e) {
                try {
                    const data = JSON.parse(e.target.result);
                    
                    // Apply imported preferences
                    Object.keys(data).forEach(function(key) {
                        const $element = $(`[name="${key}"]`);
                        if ($element.length) {
                            if ($element.is(':checkbox')) {
                                $element.prop('checked', data[key] === 'on');
                            } else {
                                $element.val(data[key]);
                            }
                        }
                    });
                    
                    // Trigger change events
                    $autoRefreshCheckbox.trigger('change');
                    
                    showAlert('Preferências importadas com sucesso!', 'success');
                } catch (error) {
                    showAlert('Erro ao importar arquivo: ' + error.message, 'danger');
                }
            };
            reader.readAsText(file);
        }
    });
    
    // Add import/export buttons
    $('.card-body.text-center').prepend(`
        <button type="button" class="btn btn-info me-2" id="import-preferences">
            <i class="fas fa-upload"></i> Importar
        </button>
        <button type="button" class="btn btn-info me-2" id="export-preferences">
            <i class="fas fa-download"></i> Exportar
        </button>
        <input type="file" id="import-file" accept=".json" style="display: none;">
    `);
});