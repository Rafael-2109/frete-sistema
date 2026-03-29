/**
 * Transportadora Autocomplete — Componente compartilhado
 * =======================================================
 *
 * Autocomplete reutilizavel para busca de transportadoras.
 * Busca por nome, razao social, CNPJ ou prefixo CNPJ (grupo economico).
 *
 * Uso (auto-init via data-transportadora-autocomplete):
 *
 *   <!-- Filtro simples (apenas preenche texto) -->
 *   <input type="text" name="transportadora"
 *          data-transportadora-autocomplete>
 *
 *   <!-- Com campo hidden para ID -->
 *   <input type="text" name="transportadora_nome"
 *          data-transportadora-autocomplete
 *          data-transportadora-id="#transportadora_id"
 *          data-transportadora-cnpj="#transportadora_cnpj">
 *   <input type="hidden" id="transportadora_id" name="transportadora_id">
 *   <input type="hidden" id="transportadora_cnpj" name="transportadora_cnpj">
 *
 * Atributos:
 *   data-transportadora-autocomplete : marca o input (obrigatorio)
 *   data-transportadora-id           : selector do campo hidden para ID
 *   data-transportadora-cnpj         : selector do campo hidden para CNPJ
 *   data-transportadora-uf           : UF destino para filtro de tabelas
 *   data-transportadora-min-chars    : min chars para buscar (default: 2)
 *   data-transportadora-api          : URL da API (default: /carvia/api/opcoes-transportadora)
 *
 * O componente se auto-inicializa via DOMContentLoaded.
 */

(function () {
    'use strict';

    var DEFAULT_API = '/fretes/api/transportadoras/buscar';
    var DEBOUNCE_MS = 300;
    var MIN_CHARS_DEFAULT = 2;

    function init() {
        document.querySelectorAll('[data-transportadora-autocomplete]').forEach(attachAutocomplete);
    }

    function attachAutocomplete(input) {
        var apiUrl = input.getAttribute('data-transportadora-api') || DEFAULT_API;
        var minChars = parseInt(input.getAttribute('data-transportadora-min-chars') || MIN_CHARS_DEFAULT, 10);
        var idSelector = input.getAttribute('data-transportadora-id');
        var cnpjSelector = input.getAttribute('data-transportadora-cnpj');
        var ufAttr = input.getAttribute('data-transportadora-uf');

        // Criar wrapper e dropdown
        var wrapper = document.createElement('div');
        wrapper.className = 'transportadora-ac-wrapper';
        wrapper.style.position = 'relative';
        input.parentNode.insertBefore(wrapper, input);
        wrapper.appendChild(input);

        var dropdown = document.createElement('div');
        dropdown.className = 'transportadora-ac-dropdown';
        dropdown.style.cssText = 'display:none;position:absolute;top:100%;left:0;right:0;z-index:1050;' +
            'max-height:280px;overflow-y:auto;background:var(--bg-card,#fff);border:1px solid var(--border-color,#dee2e6);' +
            'border-top:none;border-radius:0 0 .375rem .375rem;box-shadow:0 4px 8px rgba(0,0,0,.1);';
        wrapper.appendChild(dropdown);

        var debounceTimer = null;
        var selectedIndex = -1;
        var resultados = [];

        // Busca ao digitar
        input.addEventListener('input', function () {
            var q = this.value.trim();
            clearTimeout(debounceTimer);
            selectedIndex = -1;

            if (q.length < minChars) {
                hideDropdown();
                return;
            }

            debounceTimer = setTimeout(function () {
                buscar(q);
            }, DEBOUNCE_MS);
        });

        // Navegacao por teclado
        input.addEventListener('keydown', function (e) {
            if (dropdown.style.display === 'none') return;

            if (e.key === 'ArrowDown') {
                e.preventDefault();
                selectedIndex = Math.min(selectedIndex + 1, resultados.length - 1);
                highlightItem();
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                selectedIndex = Math.max(selectedIndex - 1, 0);
                highlightItem();
            } else if (e.key === 'Enter') {
                e.preventDefault();
                if (selectedIndex >= 0 && resultados[selectedIndex]) {
                    selecionar(resultados[selectedIndex]);
                }
            } else if (e.key === 'Escape') {
                hideDropdown();
            }
        });

        // Fechar ao clicar fora
        document.addEventListener('click', function (e) {
            if (!wrapper.contains(e.target)) {
                hideDropdown();
            }
        });

        // Limpar hidden fields ao editar texto manualmente
        input.addEventListener('input', function () {
            clearHiddenFields();
        });

        function buscar(query) {
            var params = 'busca=' + encodeURIComponent(query);
            if (ufAttr) {
                var ufEl = document.querySelector(ufAttr);
                if (ufEl && ufEl.value) {
                    params += '&uf_destino=' + encodeURIComponent(ufEl.value);
                }
            }

            fetch(apiUrl + '?' + params, {
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            })
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    if (data.sucesso && data.transportadoras) {
                        resultados = data.transportadoras;
                        renderDropdown();
                    } else {
                        resultados = [];
                        hideDropdown();
                    }
                })
                .catch(function () {
                    resultados = [];
                    hideDropdown();
                });
        }

        function renderDropdown() {
            if (resultados.length === 0) {
                dropdown.innerHTML = '<div class="transportadora-ac-empty" style="padding:.5rem .75rem;color:var(--text-muted,#6c757d);font-size:.875rem;">Nenhuma transportadora encontrada</div>';
                dropdown.style.display = 'block';
                return;
            }

            var html = '';
            for (var i = 0; i < resultados.length; i++) {
                var t = resultados[i];
                var cnpjDisplay = t.cnpj ? formatCnpj(t.cnpj) : '';
                var freteiroBadge = t.freteiro ? ' <span class="badge bg-warning text-dark" style="font-size:.65rem;">Freteiro</span>' : '';
                var tabelaBadge = t.tem_tabela ? ' <span class="badge bg-success" style="font-size:.65rem;">Tabela</span>' : '';

                html += '<div class="transportadora-ac-item" data-index="' + i + '" style="padding:.5rem .75rem;cursor:pointer;border-bottom:1px solid var(--border-color,#eee);transition:background .15s;">' +
                    '<div style="font-weight:500;">' + escapeHtml(t.nome) + freteiroBadge + tabelaBadge + '</div>' +
                    (cnpjDisplay ? '<small style="color:var(--text-muted,#6c757d);">' + cnpjDisplay + '</small>' : '') +
                    '</div>';
            }

            dropdown.innerHTML = html;
            dropdown.style.display = 'block';

            // Click handlers
            dropdown.querySelectorAll('.transportadora-ac-item').forEach(function (item) {
                item.addEventListener('click', function () {
                    var idx = parseInt(this.getAttribute('data-index'), 10);
                    if (resultados[idx]) {
                        selecionar(resultados[idx]);
                    }
                });
                item.addEventListener('mouseenter', function () {
                    selectedIndex = parseInt(this.getAttribute('data-index'), 10);
                    highlightItem();
                });
            });
        }

        function highlightItem() {
            var items = dropdown.querySelectorAll('.transportadora-ac-item');
            items.forEach(function (item, i) {
                item.style.background = (i === selectedIndex) ? 'var(--bg-hover,#f0f0f0)' : '';
            });
        }

        function selecionar(t) {
            input.value = t.nome;

            if (idSelector) {
                var idEl = document.querySelector(idSelector);
                if (idEl) { idEl.value = t.id; triggerChange(idEl); }
            }

            if (cnpjSelector) {
                var cnpjEl = document.querySelector(cnpjSelector);
                if (cnpjEl) { cnpjEl.value = t.cnpj || ''; triggerChange(cnpjEl); }
            }

            triggerChange(input);
            hideDropdown();
        }

        function clearHiddenFields() {
            if (idSelector) {
                var idEl = document.querySelector(idSelector);
                if (idEl) idEl.value = '';
            }
            if (cnpjSelector) {
                var cnpjEl = document.querySelector(cnpjSelector);
                if (cnpjEl) cnpjEl.value = '';
            }
        }

        function hideDropdown() {
            dropdown.style.display = 'none';
            selectedIndex = -1;
            resultados = [];
        }
    }

    function formatCnpj(cnpj) {
        if (!cnpj) return '';
        var digits = cnpj.replace(/\D/g, '');
        if (digits.length === 14) {
            return digits.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, '$1.$2.$3/$4-$5');
        }
        return cnpj;
    }

    function escapeHtml(str) {
        var div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    function triggerChange(el) {
        el.dispatchEvent(new Event('change', { bubbles: true }));
        el.dispatchEvent(new Event('input', { bubbles: true }));
    }

    // Auto-init
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Expor para uso programatico
    window.TransportadoraAutocomplete = { init: init };
})();
