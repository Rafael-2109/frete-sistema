/**
 * 🔒 MÓDULO CENTRALIZADO DE SEGURANÇA
 * Centraliza funções de segurança como obtenção de CSRF token
 * e outras validações de segurança
 */

(function(window) {
    'use strict';

    const Security = {
        /**
         * Obtém o token CSRF de múltiplas fontes possíveis
         * Tenta na seguinte ordem:
         * 1. Cookie csrftoken
         * 2. Meta tag csrf-token
         * 3. Input hidden csrf_token
         * 4. Variável global window.csrfToken
         * @returns {string} Token CSRF ou string vazia
         */
        getCSRFToken: function() {
            // 1. Tentar obter do cookie
            const cookieValue = document.cookie
                .split('; ')
                .find(row => row.startsWith('csrftoken='))
                ?.split('=')[1];
            
            if (cookieValue) {
                return cookieValue;
            }

            // 2. Tentar obter da meta tag
            const metaToken = document.querySelector('meta[name="csrf-token"]')?.content;
            if (metaToken) {
                return metaToken;
            }

            // 3. Tentar obter de input hidden
            const inputToken = document.querySelector('input[name="csrf_token"]')?.value;
            if (inputToken) {
                return inputToken;
            }

            // 4. Tentar obter de variável global (legado)
            if (window.csrfToken) {
                return window.csrfToken;
            }

            // 5. Log de aviso se não encontrar
            console.warn('⚠️ Token CSRF não encontrado em nenhuma fonte');
            return '';
        },

        /**
         * Prepara headers para requisições AJAX com CSRF
         * @param {Object} headers - Headers existentes (opcional)
         * @returns {Object} Headers com CSRF token incluído
         */
        getSecureHeaders: function(headers = {}) {
            const csrfToken = this.getCSRFToken();
            return {
                ...headers,
                'X-CSRFToken': csrfToken,
                'X-Requested-With': 'XMLHttpRequest'
            };
        },

        /**
         * Prepara configuração completa para fetch com segurança
         * @param {Object} options - Opções do fetch
         * @returns {Object} Opções com headers de segurança
         */
        getSecureFetchOptions: function(options = {}) {
            const defaultOptions = {
                credentials: 'same-origin',
                headers: this.getSecureHeaders(options.headers || {})
            };

            // Se tem body e é objeto, adicionar Content-Type
            if (options.body && typeof options.body === 'object' && !(options.body instanceof FormData)) {
                defaultOptions.headers['Content-Type'] = 'application/json';
                defaultOptions.body = JSON.stringify(options.body);
            } else if (options.body) {
                defaultOptions.body = options.body;
            }

            return {
                ...defaultOptions,
                ...options,
                headers: defaultOptions.headers
            };
        },

        /**
         * Valida se uma URL é segura (mesma origem)
         * @param {string} url - URL a validar
         * @returns {boolean} True se a URL é da mesma origem
         */
        isSameOrigin: function(url) {
            try {
                const urlObj = new URL(url, window.location.origin);
                return urlObj.origin === window.location.origin;
            } catch (e) {
                // Se não conseguir parsear como URL, assumir que é relativa
                return true;
            }
        },

        /**
         * Escapa HTML para prevenir XSS
         * @param {string} text - Texto a escapar
         * @returns {string} Texto escapado
         */
        escapeHtml: function(text) {
            const map = {
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                '"': '&quot;',
                "'": '&#039;'
            };
            return text.replace(/[&<>"']/g, m => map[m]);
        },

        /**
         * Sanitiza input do usuário removendo scripts
         * @param {string} input - Input do usuário
         * @returns {string} Input sanitizado
         */
        sanitizeInput: function(input) {
            if (!input) return '';
            
            // Remove tags script
            let sanitized = input.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '');
            
            // Remove eventos on*
            sanitized = sanitized.replace(/on\w+\s*=\s*["'][^"']*["']/gi, '');
            
            // Remove javascript: protocol
            sanitized = sanitized.replace(/javascript:/gi, '');
            
            return sanitized;
        },

        /**
         * Gera um ID único seguro
         * @param {string} prefix - Prefixo opcional
         * @returns {string} ID único
         */
        generateUniqueId: function(prefix = 'id') {
            const timestamp = Date.now();
            const random = Math.random().toString(36).substr(2, 9);
            return `${prefix}_${timestamp}_${random}`;
        },

        /**
         * Valida formato de CNPJ
         * @param {string} cnpj - CNPJ a validar
         * @returns {boolean} True se CNPJ é válido
         */
        validateCNPJ: function(cnpj) {
            cnpj = cnpj.replace(/[^\d]+/g, '');

            if (cnpj.length !== 14) return false;

            // Elimina CNPJs invalidos conhecidos
            if (/^(\d)\1+$/.test(cnpj)) return false;

            // Valida DVs
            let tamanho = cnpj.length - 2;
            let numeros = cnpj.substring(0, tamanho);
            let digitos = cnpj.substring(tamanho);
            let soma = 0;
            let pos = tamanho - 7;

            for (let i = tamanho; i >= 1; i--) {
                soma += numeros.charAt(tamanho - i) * pos--;
                if (pos < 2) pos = 9;
            }

            let resultado = soma % 11 < 2 ? 0 : 11 - soma % 11;
            if (resultado != digitos.charAt(0)) return false;

            tamanho = tamanho + 1;
            numeros = cnpj.substring(0, tamanho);
            soma = 0;
            pos = tamanho - 7;

            for (let i = tamanho; i >= 1; i--) {
                soma += numeros.charAt(tamanho - i) * pos--;
                if (pos < 2) pos = 9;
            }

            resultado = soma % 11 < 2 ? 0 : 11 - soma % 11;
            if (resultado != digitos.charAt(1)) return false;

            return true;
        }
    };

    // Manter compatibilidade com código legado
    const CompatibilityWrapper = {
        getCSRFToken: function() {
            return Security.getCSRFToken();
        }
    };

    // Exportar para uso global
    window.Security = Security;
    window.SecurityCompat = CompatibilityWrapper;

    // Para debug
    console.log('✅ Módulo de Segurança carregado: window.Security disponível');

})(window);