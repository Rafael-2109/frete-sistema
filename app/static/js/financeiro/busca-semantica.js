/**
 * Busca Semantica de Entidades Financeiras
 * ==========================================
 *
 * Componente reutilizavel que adiciona autocomplete semantico a campos
 * de fornecedor/cliente. Usa FinancialEntityEmbedding via API.
 *
 * Uso:
 *   <input type="text" name="fornecedor" data-semantic-search="supplier">
 *   <input type="text" name="cliente" data-semantic-search="customer">
 *
 * Atributos:
 *   data-semantic-search: tipo de entidade ('supplier', 'customer', 'all')
 *   data-semantic-cnpj: selector do campo CNPJ para auto-preencher (opcional)
 *   data-semantic-min-chars: minimo de chars para buscar (default: 3)
 *
 * O componente se auto-inicializa via DOMContentLoaded.
 */

(function () {
    'use strict';

    const API_URL = '/financeiro/api/busca-semantica';
    const DEBOUNCE_MS = 400;
    const MIN_CHARS_DEFAULT = 3;

    /**
     * Inicializa busca semantica em todos os inputs com data-semantic-search.
     */
    function init() {
        const inputs = document.querySelectorAll('[data-semantic-search]');
        inputs.forEach(attachSemanticSearch);
    }

    /**
     * Anexa comportamento de busca semantica a um input.
     */
    function attachSemanticSearch(input) {
        const tipo = input.getAttribute('data-semantic-search') || 'all';
        const cnpjSelector = input.getAttribute('data-semantic-cnpj') || null;
        const minChars = parseInt(input.getAttribute('data-semantic-min-chars') || MIN_CHARS_DEFAULT, 10);

        // Criar wrapper relativo para posicionar dropdown
        const wrapper = document.createElement('div');
        wrapper.className = 'semantic-search-wrapper';
        input.parentNode.insertBefore(wrapper, input);
        wrapper.appendChild(input);

        // Criar dropdown
        const dropdown = document.createElement('div');
        dropdown.className = 'semantic-search-dropdown';
        dropdown.style.display = 'none';
        wrapper.appendChild(dropdown);

        // Criar indicador de busca
        const indicator = document.createElement('span');
        indicator.className = 'semantic-search-indicator';
        indicator.innerHTML = '<i class="fas fa-brain" title="Busca inteligente ativa"></i>';
        indicator.style.display = 'none';
        wrapper.appendChild(indicator);

        let debounceTimer = null;
        let currentQuery = '';
        let selectedIndex = -1;

        // Debounced search on input
        input.addEventListener('input', function () {
            const q = this.value.trim();
            clearTimeout(debounceTimer);

            if (q.length < minChars) {
                hideDropdown(dropdown, indicator);
                return;
            }

            currentQuery = q;
            indicator.style.display = 'flex';
            indicator.classList.add('semantic-search-indicator--loading');

            debounceTimer = setTimeout(function () {
                fetchResults(q, tipo, dropdown, indicator, input, cnpjSelector);
            }, DEBOUNCE_MS);
        });

        // Keyboard navigation
        input.addEventListener('keydown', function (e) {
            if (dropdown.style.display === 'none') return;

            const items = dropdown.querySelectorAll('.semantic-search-item');
            if (!items.length) return;

            if (e.key === 'ArrowDown') {
                e.preventDefault();
                selectedIndex = Math.min(selectedIndex + 1, items.length - 1);
                updateSelection(items, selectedIndex);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                selectedIndex = Math.max(selectedIndex - 1, 0);
                updateSelection(items, selectedIndex);
            } else if (e.key === 'Enter' && selectedIndex >= 0) {
                e.preventDefault();
                items[selectedIndex].click();
            } else if (e.key === 'Escape') {
                hideDropdown(dropdown, indicator);
                selectedIndex = -1;
            }
        });

        // Close on outside click
        document.addEventListener('click', function (e) {
            if (!wrapper.contains(e.target)) {
                hideDropdown(dropdown, indicator);
                selectedIndex = -1;
            }
        });

        // Re-show on focus if has results
        input.addEventListener('focus', function () {
            if (dropdown.children.length > 0 && this.value.trim().length >= minChars) {
                dropdown.style.display = 'block';
            }
        });
    }

    /**
     * Busca resultados na API.
     */
    function fetchResults(q, tipo, dropdown, indicator, input, cnpjSelector) {
        const url = `${API_URL}?q=${encodeURIComponent(q)}&tipo=${tipo}&limit=8`;

        fetch(url)
            .then(function (res) { return res.json(); })
            .then(function (data) {
                indicator.classList.remove('semantic-search-indicator--loading');

                if (!data.success || !data.resultados || !data.resultados.length) {
                    hideDropdown(dropdown, indicator);
                    return;
                }

                renderResults(data.resultados, dropdown, indicator, input, cnpjSelector);
            })
            .catch(function () {
                indicator.classList.remove('semantic-search-indicator--loading');
                hideDropdown(dropdown, indicator);
            });
    }

    /**
     * Renderiza resultados no dropdown.
     */
    function renderResults(resultados, dropdown, indicator, input, cnpjSelector) {
        dropdown.innerHTML = '';

        // Header
        const header = document.createElement('div');
        header.className = 'semantic-search-header';
        header.innerHTML = '<i class="fas fa-brain"></i> Sugestoes inteligentes';
        dropdown.appendChild(header);

        resultados.forEach(function (r, i) {
            const item = document.createElement('div');
            item.className = 'semantic-search-item';
            item.setAttribute('data-index', i);

            const tipoLabel = r.entity_type === 'supplier' ? 'Fornecedor' : 'Cliente';
            const tipoClass = r.entity_type === 'supplier' ? 'semantic-tag--supplier' : 'semantic-tag--customer';
            const similarityPct = Math.round(r.similarity * 100);
            const cnpjDisplay = r.cnpj_completo
                ? formatCnpj(r.cnpj_completo)
                : (r.cnpj_raiz || '');

            item.innerHTML =
                '<div class="semantic-search-item__main">' +
                    '<span class="semantic-search-item__name">' + escapeHtml(r.nome) + '</span>' +
                    '<span class="semantic-search-item__cnpj">' + cnpjDisplay + '</span>' +
                '</div>' +
                '<div class="semantic-search-item__meta">' +
                    '<span class="semantic-tag ' + tipoClass + '">' + tipoLabel + '</span>' +
                    '<span class="semantic-search-item__score" title="Similaridade: ' + similarityPct + '%">' +
                        similarityPct + '%' +
                    '</span>' +
                '</div>';

            item.addEventListener('click', function () {
                selectResult(r, input, cnpjSelector, dropdown, indicator);
            });

            dropdown.appendChild(item);
        });

        dropdown.style.display = 'block';
        indicator.style.display = 'flex';
    }

    /**
     * Seleciona um resultado e preenche os campos.
     */
    function selectResult(r, input, cnpjSelector, dropdown, indicator) {
        // Preencher nome
        input.value = r.nome;

        // Preencher CNPJ se selector fornecido
        if (cnpjSelector) {
            const cnpjInput = document.querySelector(cnpjSelector);
            if (cnpjInput && r.cnpj_completo) {
                cnpjInput.value = r.cnpj_completo;
            }
        }

        hideDropdown(dropdown, indicator);

        // Disparar evento de change para triggers existentes
        input.dispatchEvent(new Event('change', { bubbles: true }));

        // Auto-submit do form se existir
        const form = input.closest('form');
        if (form) {
            form.submit();
        }
    }

    /**
     * Esconde dropdown.
     */
    function hideDropdown(dropdown, indicator) {
        dropdown.style.display = 'none';
        if (indicator) {
            indicator.classList.remove('semantic-search-indicator--loading');
        }
    }

    /**
     * Atualiza selecao visual no dropdown (keyboard nav).
     */
    function updateSelection(items, index) {
        items.forEach(function (item, i) {
            item.classList.toggle('semantic-search-item--selected', i === index);
        });
    }

    /**
     * Formata CNPJ: 12345678000190 -> 12.345.678/0001-90
     */
    function formatCnpj(cnpj) {
        var digits = cnpj.replace(/\D/g, '');
        if (digits.length === 14) {
            return digits.replace(
                /^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/,
                '$1.$2.$3/$4-$5'
            );
        }
        return cnpj;
    }

    /**
     * Escapa HTML para prevenir XSS.
     */
    function escapeHtml(str) {
        var div = document.createElement('div');
        div.appendChild(document.createTextNode(str));
        return div.innerHTML;
    }

    // Auto-inicializar
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
