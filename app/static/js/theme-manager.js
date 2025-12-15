/**
 * ==========================================================================
 * NACOM GOYA - Theme Manager
 * Gerencia dark/light mode com persistência e sync entre abas
 * ==========================================================================
 */

(function() {
    'use strict';

    var STORAGE_KEY = 'nacom-theme';
    var THEMES = {
        DARK: 'dark',
        LIGHT: 'light'
    };

    /**
     * ThemeManager Class
     * Singleton para gerenciamento de tema
     */
    function ThemeManager() {
        this.currentTheme = this.getInitialTheme();
        this.listeners = [];
        this.init();
    }

    /**
     * Inicializa o ThemeManager
     */
    ThemeManager.prototype.init = function() {
        var self = this;

        // Aplica o tema imediatamente (evita flash)
        this.applyTheme(this.currentTheme, false);

        // Quando o DOM estiver pronto, configura os listeners
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', function() {
                self.setupListeners();
            });
        } else {
            this.setupListeners();
        }

        // Sync entre abas
        window.addEventListener('storage', function(e) {
            if (e.key === STORAGE_KEY && e.newValue) {
                self.applyTheme(e.newValue, false);
            }
        });

        // Listener para preferência do sistema
        var mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
        mediaQuery.addEventListener('change', function(e) {
            // Só aplica se não tiver preferência salva
            if (!localStorage.getItem(STORAGE_KEY)) {
                self.applyTheme(e.matches ? THEMES.DARK : THEMES.LIGHT, false);
            }
        });
    };

    /**
     * Configura listeners para botões de toggle
     */
    ThemeManager.prototype.setupListeners = function() {
        var self = this;

        // Botões com classe .nc-theme-toggle ou data-theme-toggle
        document.querySelectorAll('.nc-theme-toggle, [data-theme-toggle]').forEach(function(btn) {
            btn.addEventListener('click', function() {
                self.toggle();
            });
        });

        // Dispara evento customizado
        this.dispatchThemeEvent();
    };

    /**
     * Obtém o tema inicial
     */
    ThemeManager.prototype.getInitialTheme = function() {
        // 1. Verifica localStorage
        var saved = localStorage.getItem(STORAGE_KEY);
        if (saved && (saved === THEMES.DARK || saved === THEMES.LIGHT)) {
            return saved;
        }

        // 2. Verifica preferência do sistema
        if (window.matchMedia('(prefers-color-scheme: light)').matches) {
            return THEMES.LIGHT;
        }

        // 3. Default: dark
        return THEMES.DARK;
    };

    /**
     * Aplica o tema ao documento
     */
    ThemeManager.prototype.applyTheme = function(theme, save) {
        if (save === undefined) save = true;

        var html = document.documentElement;

        // Aplica ambos os atributos para compatibilidade
        html.setAttribute('data-bs-theme', theme);
        html.setAttribute('data-theme', theme);

        // Atualiza color-scheme para inputs nativos
        html.style.colorScheme = theme;

        // Salva preferência
        if (save) {
            localStorage.setItem(STORAGE_KEY, theme);
        }

        // Atualiza estado interno
        this.currentTheme = theme;

        // Atualiza ícones dos botões de toggle
        this.updateToggleIcons(theme);

        // Dispara evento customizado
        this.dispatchThemeEvent();

        // Notifica listeners
        this.listeners.forEach(function(callback) {
            callback(theme);
        });
    };

    /**
     * Atualiza os ícones dos botões de toggle
     */
    ThemeManager.prototype.updateToggleIcons = function(theme) {
        document.querySelectorAll('.nc-theme-toggle, [data-theme-toggle]').forEach(function(btn) {
            var sunIcon = btn.querySelector('.fa-sun');
            var moonIcon = btn.querySelector('.fa-moon');

            if (sunIcon && moonIcon) {
                if (theme === THEMES.LIGHT) {
                    sunIcon.style.opacity = '0';
                    sunIcon.style.transform = 'rotate(90deg)';
                    moonIcon.style.opacity = '1';
                    moonIcon.style.transform = 'rotate(0deg)';
                } else {
                    sunIcon.style.opacity = '1';
                    sunIcon.style.transform = 'rotate(0deg)';
                    moonIcon.style.opacity = '0';
                    moonIcon.style.transform = 'rotate(-90deg)';
                }
            }

            // Atualiza título/tooltip
            btn.title = theme === THEMES.DARK 
                ? 'Mudar para tema claro' 
                : 'Mudar para tema escuro';
        });
    };

    /**
     * Alterna entre dark e light
     */
    ThemeManager.prototype.toggle = function() {
        var newTheme = this.currentTheme === THEMES.DARK ? THEMES.LIGHT : THEMES.DARK;
        this.applyTheme(newTheme);
        return newTheme;
    };

    /**
     * Define um tema específico
     */
    ThemeManager.prototype.setTheme = function(theme) {
        if (theme === THEMES.DARK || theme === THEMES.LIGHT) {
            this.applyTheme(theme);
        }
    };

    /**
     * Retorna o tema atual
     */
    ThemeManager.prototype.getTheme = function() {
        return this.currentTheme;
    };

    /**
     * Verifica se está no modo escuro
     */
    ThemeManager.prototype.isDark = function() {
        return this.currentTheme === THEMES.DARK;
    };

    /**
     * Verifica se está no modo claro
     */
    ThemeManager.prototype.isLight = function() {
        return this.currentTheme === THEMES.LIGHT;
    };

    /**
     * Adiciona um listener para mudanças de tema
     */
    ThemeManager.prototype.onChange = function(callback) {
        if (typeof callback === 'function') {
            this.listeners.push(callback);
        }
    };

    /**
     * Remove um listener
     */
    ThemeManager.prototype.offChange = function(callback) {
        this.listeners = this.listeners.filter(function(cb) {
            return cb !== callback;
        });
    };

    /**
     * Dispara evento customizado para integração com outros sistemas
     */
    ThemeManager.prototype.dispatchThemeEvent = function() {
        var event = new CustomEvent('themechange', {
            detail: {
                theme: this.currentTheme,
                isDark: this.isDark(),
                isLight: this.isLight()
            }
        });
        document.dispatchEvent(event);
    };

    // Cria instância única e expõe globalmente
    var themeManager = new ThemeManager();

    // Expõe no window para uso global
    window.NacomTheme = themeManager;

    // Função helper para compatibilidade com código existente
    window.toggleTheme = function() {
        return themeManager.toggle();
    };

    // Log de inicialização
    console.log('Theme Manager initialized: ' + themeManager.getTheme() + ' mode');

})();
