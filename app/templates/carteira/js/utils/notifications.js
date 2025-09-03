/**
 * 📢 MÓDULO CENTRALIZADO DE NOTIFICAÇÕES
 * Sistema unificado de notificações e feedback ao usuário
 * Suporta toast notifications, alerts e integração com SweetAlert2
 */

(function(window) {
    'use strict';

    const Notifications = {
        /**
         * Configurações padrão
         */
        config: {
            duration: 3000,
            position: 'top-right',
            zIndex: 10000,
            animationDuration: 300
        },

        /**
         * Cores por tipo de notificação
         */
        colors: {
            success: '#28a745',
            error: '#dc3545',
            warning: '#ffc107',
            info: '#17a2b8',
            primary: '#007bff',
            secondary: '#6c757d'
        },

        /**
         * Exibe uma notificação toast
         * @param {string} mensagem - Mensagem a exibir
         * @param {string} tipo - Tipo: success, error, warning, info
         * @param {number} duracao - Duração em ms (opcional)
         */
        toast: function(mensagem, tipo = 'info', duracao = null) {
            const duration = duracao || this.config.duration;
            const color = this.colors[tipo] || this.colors.info;
            
            // Criar elemento toast
            const toast = document.createElement('div');
            toast.className = `toast-notification toast-${tipo}`;
            
            // Determinar posição baseada na configuração
            const position = this.config.position;
            let positionStyles = '';
            
            if (position.includes('top')) {
                positionStyles += 'top: 20px;';
            } else {
                positionStyles += 'bottom: 20px;';
            }
            
            if (position.includes('right')) {
                positionStyles += 'right: 20px;';
            } else if (position.includes('left')) {
                positionStyles += 'left: 20px;';
            } else {
                positionStyles += 'left: 50%; transform: translateX(-50%);';
            }
            
            toast.style.cssText = `
                position: fixed;
                ${positionStyles}
                background: ${color};
                color: white;
                padding: 12px 24px;
                border-radius: 4px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.2);
                z-index: ${this.config.zIndex};
                max-width: 350px;
                word-wrap: break-word;
                animation: slideIn ${this.config.animationDuration}ms ease;
            `;
            
            // Adicionar ícone baseado no tipo
            const icon = this.getIcon(tipo);
            toast.innerHTML = `
                <div style="display: flex; align-items: center;">
                    ${icon ? `<span style="margin-right: 10px; font-size: 20px;">${icon}</span>` : ''}
                    <span>${mensagem}</span>
                </div>
            `;
            
            // Adicionar ao DOM
            document.body.appendChild(toast);
            
            // Auto remover após duração
            if (duration > 0) {
                setTimeout(() => {
                    toast.style.animation = `slideOut ${this.config.animationDuration}ms ease`;
                    setTimeout(() => {
                        if (toast.parentNode) {
                            toast.remove();
                        }
                    }, this.config.animationDuration);
                }, duration);
            }
            
            return toast;
        },

        /**
         * Atalhos para tipos específicos
         */
        success: function(mensagem, duracao) {
            return this.toast(mensagem, 'success', duracao);
        },

        error: function(mensagem, duracao) {
            return this.toast(mensagem, 'error', duracao);
        },

        warning: function(mensagem, duracao) {
            return this.toast(mensagem, 'warning', duracao);
        },

        info: function(mensagem, duracao) {
            return this.toast(mensagem, 'info', duracao);
        },

        /**
         * Exibe alerta usando SweetAlert2 se disponível
         * Fallback para alert nativo
         * @param {string} titulo - Título do alerta
         * @param {string} mensagem - Mensagem
         * @param {string} tipo - Tipo do alerta
         */
        alert: function(titulo, mensagem, tipo = 'info') {
            if (typeof Swal !== 'undefined') {
                return Swal.fire({
                    title: titulo,
                    text: mensagem,
                    icon: tipo,
                    confirmButtonText: 'OK'
                });
            } else {
                // Fallback para alert nativo
                alert(`${titulo}\n\n${mensagem}`);
            }
        },

        /**
         * Exibe confirmação usando SweetAlert2 se disponível
         * @param {string} titulo - Título
         * @param {string} mensagem - Mensagem
         * @returns {Promise} Promise com resultado da confirmação
         */
        confirm: function(titulo, mensagem) {
            if (typeof Swal !== 'undefined') {
                return Swal.fire({
                    title: titulo,
                    text: mensagem,
                    icon: 'question',
                    showCancelButton: true,
                    confirmButtonText: 'Sim',
                    cancelButtonText: 'Cancelar'
                }).then(result => result.isConfirmed);
            } else {
                // Fallback para confirm nativo
                return Promise.resolve(confirm(`${titulo}\n\n${mensagem}`));
            }
        },

        /**
         * Exibe loading/spinner
         * @param {string} mensagem - Mensagem de loading
         * @returns {Function} Função para fechar o loading
         */
        loading: function(mensagem = 'Carregando...') {
            let loadingElement;
            
            if (typeof Swal !== 'undefined') {
                Swal.fire({
                    title: mensagem,
                    allowOutsideClick: false,
                    allowEscapeKey: false,
                    didOpen: () => {
                        Swal.showLoading();
                    }
                });
                
                return () => Swal.close();
            } else {
                // Criar loading manual
                loadingElement = document.createElement('div');
                loadingElement.style.cssText = `
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: rgba(0, 0, 0, 0.5);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    z-index: ${this.config.zIndex + 1};
                `;
                
                loadingElement.innerHTML = `
                    <div style="background: white; padding: 20px; border-radius: 8px;">
                        <div class="spinner-border text-primary" role="status">
                            <span class="sr-only">${mensagem}</span>
                        </div>
                        <p style="margin-top: 10px; margin-bottom: 0;">${mensagem}</p>
                    </div>
                `;
                
                document.body.appendChild(loadingElement);
                
                return () => {
                    if (loadingElement.parentNode) {
                        loadingElement.remove();
                    }
                };
            }
        },

        /**
         * Retorna ícone HTML baseado no tipo
         * @param {string} tipo - Tipo da notificação
         * @returns {string} HTML do ícone
         */
        getIcon: function(tipo) {
            const icons = {
                success: '✓',
                error: '✕',
                warning: '⚠',
                info: 'ℹ',
                primary: '★',
                secondary: '○'
            };
            
            return icons[tipo] || '';
        },

        /**
         * Limpa todas as notificações ativas
         */
        clearAll: function() {
            const toasts = document.querySelectorAll('.toast-notification');
            toasts.forEach(toast => {
                if (toast.parentNode) {
                    toast.remove();
                }
            });
            
            if (typeof Swal !== 'undefined' && Swal.isVisible()) {
                Swal.close();
            }
        },

        /**
         * Configura opções globais
         * @param {Object} options - Opções de configuração
         */
        configure: function(options) {
            this.config = {
                ...this.config,
                ...options
            };
        }
    };

    // Adicionar estilos CSS necessários
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateX(100%);
            }
            to {
                opacity: 1;
                transform: translateX(0);
            }
        }
        
        @keyframes slideOut {
            from {
                opacity: 1;
                transform: translateX(0);
            }
            to {
                opacity: 0;
                transform: translateX(100%);
            }
        }
        
        .toast-notification {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            font-size: 14px;
            line-height: 1.5;
        }
    `;
    document.head.appendChild(style);

    // Manter compatibilidade com implementações antigas
    const CompatibilityWrapper = {
        mostrarFeedback: function(mensagem, tipo) {
            return Notifications.toast(mensagem, tipo);
        },
        mostrarToast: function(mensagem, tipo) {
            if (tipo === 'top-end') {
                // Compatibilidade com SweetAlert2 toast
                if (typeof Swal !== 'undefined') {
                    return Swal.fire({
                        toast: true,
                        position: 'top-end',
                        icon: 'success',
                        title: mensagem,
                        showConfirmButton: false,
                        timer: 3000
                    });
                }
            }
            return Notifications.toast(mensagem, tipo);
        },
        mostrarAlerta: function(mensagem) {
            return Notifications.warning(mensagem);
        }
    };

    // Exportar para uso global
    window.Notifications = Notifications;
    window.NotificationsCompat = CompatibilityWrapper;

    // Atalhos globais opcionais
    window.notify = {
        success: (msg, duration) => Notifications.success(msg, duration),
        error: (msg, duration) => Notifications.error(msg, duration),
        warning: (msg, duration) => Notifications.warning(msg, duration),
        info: (msg, duration) => Notifications.info(msg, duration),
        loading: (msg) => Notifications.loading(msg),
        confirm: (title, msg) => Notifications.confirm(title, msg),
        clear: () => Notifications.clearAll()
    };

    // Para debug
    console.log('✅ Módulo de Notificações carregado: window.Notifications e window.notify disponíveis');

})(window);