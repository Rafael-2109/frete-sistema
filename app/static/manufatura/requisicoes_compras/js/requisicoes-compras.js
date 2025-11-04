/**
 * JavaScript para Requisições de Compras
 * Módulo: Manufatura
 */

(function() {
    'use strict';

    // ========================================
    // Inicialização
    // ========================================
    document.addEventListener('DOMContentLoaded', function() {
        console.log('[REQUISICOES] Módulo carregado');

        // Inicializar componentes
        inicializarTooltips();
        inicializarFiltros();
        inicializarTabela();
    });

    // ========================================
    // Tooltips Bootstrap
    // ========================================
    function inicializarTooltips() {
        const tooltipTriggerList = [].slice.call(
            document.querySelectorAll('[data-bs-toggle="tooltip"], [title]')
        );

        tooltipTriggerList.forEach(function(tooltipTriggerEl) {
            if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
                new bootstrap.Tooltip(tooltipTriggerEl);
            }
        });
    }

    // ========================================
    // Filtros
    // ========================================
    function inicializarFiltros() {
        const formFiltros = document.querySelector('form[action*="listar_requisicoes"]');

        if (!formFiltros) return;

        // Limpar filtros
        const btnLimpar = formFiltros.querySelector('a[href*="listar_requisicoes"]:not([href*="?"])');
        if (btnLimpar) {
            btnLimpar.addEventListener('click', function(e) {
                e.preventDefault();
                formFiltros.reset();
                window.location.href = btnLimpar.getAttribute('href');
            });
        }

        // Auto-submit ao mudar status (opcional)
        const selectStatus = formFiltros.querySelector('#status');
        if (selectStatus) {
            selectStatus.addEventListener('change', function() {
                // Comentado para não fazer auto-submit
                // formFiltros.submit();
            });
        }
    }

    // ========================================
    // Tabela de Requisições
    // ========================================
    function inicializarTabela() {
        const tabela = document.querySelector('.table-hover');

        if (!tabela) return;

        // Click na linha inteira para ir ao detalhe
        const linhas = tabela.querySelectorAll('tbody tr');

        linhas.forEach(function(linha) {
            linha.style.cursor = 'pointer';

            linha.addEventListener('click', function(e) {
                // Não navegar se clicou em um botão/link
                if (e.target.closest('a, button')) {
                    return;
                }

                const btnDetalhe = linha.querySelector('a[href*="requisicoes-compras"]');
                if (btnDetalhe) {
                    window.location.href = btnDetalhe.getAttribute('href');
                }
            });
        });

        // Highlight da linha ao hover
        linhas.forEach(function(linha) {
            linha.addEventListener('mouseenter', function() {
                linha.style.backgroundColor = 'rgba(0, 123, 255, 0.05)';
            });

            linha.addEventListener('mouseleave', function() {
                linha.style.backgroundColor = '';
            });
        });
    }

    // ========================================
    // Helpers
    // ========================================
    function formatarNumero(numero, casasDecimais = 3) {
        if (typeof numero === 'string') {
            numero = parseFloat(numero);
        }

        if (isNaN(numero)) return '-';

        return numero.toLocaleString('pt-BR', {
            minimumFractionDigits: casasDecimais,
            maximumFractionDigits: casasDecimais
        });
    }

    function formatarData(data) {
        if (!data) return '-';

        const d = new Date(data);

        if (isNaN(d.getTime())) return '-';

        return d.toLocaleDateString('pt-BR');
    }

    function formatarDataHora(data) {
        if (!data) return '-';

        const d = new Date(data);

        if (isNaN(d.getTime())) return '-';

        return d.toLocaleDateString('pt-BR') + ' ' + d.toLocaleTimeString('pt-BR');
    }

    // ========================================
    // Exportar funções globais (se necessário)
    // ========================================
    window.RequisicoesCompras = {
        formatarNumero: formatarNumero,
        formatarData: formatarData,
        formatarDataHora: formatarDataHora
    };

})();
