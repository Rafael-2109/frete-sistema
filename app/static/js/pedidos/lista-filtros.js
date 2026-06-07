/**
 * lista-filtros.js — Navegacao de filtros unificada via URL params (Fase 1).
 *
 * Funcao central: navegarComFiltros(overrides)
 * Tudo via URL, sem form POST.
 *
 * Depende de: window.PEDIDOS_URLS.listaPedidos (injetado pelo template)
 */
(function () {
    'use strict';

    var BASE_URL = '';
    // Labels para chips
    var PARAM_LABELS = {
        'status': {
            'aberto': 'Aberto',
            'cotado': 'Cotado',
            'faturado': 'Faturado',
            'nf_cd': 'NF no CD'
        },
        'cond_atrasados': 'Atrasados',
        'cond_sem_data': 'Sem Data',
        'cond_pend_embarque': 'Pend. Embarque',
        'cond_agend_pendente': 'Ag. Pendente',
        'cond_ag_pagamento': 'Ag. Pagamento',
        'cond_ag_item': 'Ag. Item',
        'uf': 'UF',
        'rota': 'Rota',
        'sub_rota': 'Sub Rota',
        'numero_pedido': 'Pedido',
        'cnpj_cpf': 'CNPJ',
        'cliente': 'Cliente',
        'expedicao_de': 'De',
        'expedicao_ate': 'Ate'
    };

    // Params que nao geram chips (controle interno)
    // 'pendente' tem chip proprio so quando OFF (estado nao-default)
    var SKIP_CHIP_PARAMS = ['page', 'sort_by', 'sort_order', 'origem', 'pendente'];

    // localStorage: lembra preferencia do toggle "Apenas Pendentes"
    var LS_KEY_PENDENTE = 'pedidos:apenasPendentes';

    // ═══════════════════════════════════════════════════════════════
    // CORE: navegarComFiltros
    // ═══════════════════════════════════════════════════════════════

    // Acumula os params entre navegacoes da MESMA pagina. Sem isso,
    // navegarComFiltros partia sempre de window.location.search (a URL JA
    // carregada). Quando o backend demora, uma 2a mudanca de filtro disparada
    // antes do reload terminar NAO "via" a 1a e a descartava — race classico:
    // ao escolher "De" e logo em seguida "Ate", apenas um sobrevivia.
    // Memorizando os params, a 2a navegacao acumula sobre a 1a (vale para
    // datas E qualquer outro filtro em sequencia rapida).
    var _paramsPendentes = null;

    function _mostrarCarregando() {
        if (document.getElementById('pedidos-loading-overlay')) return;
        var ov = document.createElement('div');
        ov.id = 'pedidos-loading-overlay';
        ov.className = 'pedidos-loading-overlay';
        ov.setAttribute('aria-live', 'polite');
        ov.innerHTML = '<div class="pedidos-loading-box">' +
            '<i class="fas fa-spinner fa-spin"></i> Carregando…</div>';
        document.body.appendChild(ov);
    }

    /**
     * Constroi URL a partir dos params atuais + overrides, e navega.
     * @param {Object} overrides - chave:valor para set/delete (null = delete)
     */
    function navegarComFiltros(overrides) {
        // Parte dos params PENDENTES (navegacao anterior desta pagina ainda
        // nao refletida na URL) ou, na 1a vez, da URL atual.
        var params = _paramsPendentes || new URLSearchParams(window.location.search);
        _paramsPendentes = params;

        Object.keys(overrides).forEach(function (key) {
            var val = overrides[key];
            if (val === null || val === undefined || val === '') {
                params.delete(key);
            } else {
                params.set(key, val);
            }
        });

        // Reset paginacao ao mudar filtros
        params.delete('page');

        _mostrarCarregando();

        var qs = params.toString();
        window.location.href = BASE_URL + (qs ? '?' + qs : '');
    }

    // ═══════════════════════════════════════════════════════════════
    // STATUS TOGGLES (OR)
    // ═══════════════════════════════════════════════════════════════

    function getStatusValue() {
        var checked = [];
        document.querySelectorAll('[data-filter-type="status"] input:checked').forEach(function (cb) {
            checked.push(cb.dataset.value);
        });
        return checked.join(',');
    }

    function onStatusToggle() {
        var val = getStatusValue();
        navegarComFiltros({ status: val || null });
    }

    // ═══════════════════════════════════════════════════════════════
    // CONDITION TOGGLES (AND)
    // ═══════════════════════════════════════════════════════════════

    function onConditionToggle(input) {
        var param = input.dataset.param;
        var overrides = {};
        overrides[param] = input.checked ? '1' : null;
        navegarComFiltros(overrides);
    }

    // ═══════════════════════════════════════════════════════════════
    // SMART DATES
    // ═══════════════════════════════════════════════════════════════

    function onSmartDateClick(btn) {
        var date = btn.dataset.date;
        var params = new URLSearchParams(window.location.search);
        var currentDe = params.get('expedicao_de');
        var currentAte = params.get('expedicao_ate');

        // Toggle: se ja esta ativo, desativa
        if (currentDe === date && currentAte === date) {
            navegarComFiltros({ expedicao_de: null, expedicao_ate: null });
        } else {
            navegarComFiltros({ expedicao_de: date, expedicao_ate: date });
        }
    }

    // ═══════════════════════════════════════════════════════════════
    // SELECTS (navegacao imediata)
    // ═══════════════════════════════════════════════════════════════

    function onSelectChange(select) {
        var param = select.dataset.param;
        var overrides = {};
        overrides[param] = select.value || null;
        navegarComFiltros(overrides);
    }

    // ═══════════════════════════════════════════════════════════════
    // TEXT INPUTS (Enter) + DATE INPUTS (change)
    // ═══════════════════════════════════════════════════════════════

    function onTextEnter(input) {
        var param = input.dataset.param;
        var overrides = {};
        overrides[param] = input.value.trim() || null;
        navegarComFiltros(overrides);
    }

    function onDateChange(input) {
        var param = input.dataset.param;
        var overrides = {};
        overrides[param] = input.value || null;
        navegarComFiltros(overrides);
    }

    // ═══════════════════════════════════════════════════════════════
    // FILTER CHIPS
    // ═══════════════════════════════════════════════════════════════

    function renderChips() {
        var container = document.getElementById('filtros-ativos');
        if (!container) return;

        var params = new URLSearchParams(window.location.search);
        var html = '';
        var hasChips = false;

        // Chip especial: "Universo: Tudo" quando o toggle Apenas Pendentes esta OFF
        if (params.get('pendente') === '0') {
            html += '<span class="pedidos-chip pedidos-chip--info" title="Mostrando todos os pedidos, inclusive faturados/embarcados antigos">' +
                '<i class="fas fa-globe"></i> Universo: Tudo' +
                ' <span class="pedidos-chip__remove" data-action="reset-pendente">&times;</span></span>';
            hasChips = true;
        }

        params.forEach(function (value, key) {
            if (SKIP_CHIP_PARAMS.indexOf(key) >= 0) return;
            if (!value) return;

            if (key === 'status') {
                // Multi-value: um chip por status
                value.split(',').forEach(function (s) {
                    if (!s) return;
                    var label = (PARAM_LABELS.status && PARAM_LABELS.status[s]) || s;
                    html += chipHtml('status', s, label);
                    hasChips = true;
                });
                return;
            }

            var label = PARAM_LABELS[key] || key;
            // Condicoes: nao mostrar valor "1", so o label
            if (key.indexOf('cond_') === 0) {
                html += chipHtml(key, value, label);
            } else {
                html += chipHtml(key, value, label + ': ' + value);
            }
            hasChips = true;
        });

        if (hasChips) {
            html += '<span class="pedidos-chip pedidos-chip--clear" data-action="clear-all">' +
                '<i class="fas fa-times-circle"></i> Limpar todos</span>';
        }

        container.innerHTML = html;
    }

    function chipHtml(param, value, displayText) {
        return '<span class="pedidos-chip">' + escapeHtml(displayText) +
            ' <span class="pedidos-chip__remove" data-param="' + escapeHtml(param) +
            '" data-value="' + escapeHtml(value) + '">&times;</span></span>';
    }

    function onChipRemove(el) {
        var param = el.dataset.param;
        var value = el.dataset.value;

        if (param === 'status') {
            // Remove apenas este status da lista comma-separated
            var params = new URLSearchParams(window.location.search);
            var current = (params.get('status') || '').split(',');
            current = current.filter(function (s) { return s !== value; });
            navegarComFiltros({ status: current.length ? current.join(',') : null });
        } else {
            var overrides = {};
            overrides[param] = null;
            navegarComFiltros(overrides);
        }
    }

    // ═══════════════════════════════════════════════════════════════
    // SORT LINKS
    // ═══════════════════════════════════════════════════════════════

    function updateSortLinks() {
        document.querySelectorAll('.sortable a').forEach(function (link) {
            var campo = link.closest('.sortable').dataset.sort;
            if (!campo) return;

            var params = new URLSearchParams(window.location.search);
            var novaOrdem = 'asc';
            if (params.get('sort_by') === campo && params.get('sort_order') === 'asc') {
                novaOrdem = 'desc';
            }
            params.set('sort_by', campo);
            params.set('sort_order', novaOrdem);
            link.href = BASE_URL + '?' + params.toString();
        });
    }

    // ═══════════════════════════════════════════════════════════════
    // SPACER — alinhar status row abaixo das datas
    // ═══════════════════════════════════════════════════════════════

    function alignDateSpacer() {
        var spacer = document.querySelector('.pedidos-date-spacer');
        if (!spacer) return;

        // Medir largura do grupo Atrasados+SemData (primeiro toggle-group conditions do card filtros)
        var condGroup = document.querySelector('.card .pedidos-toggle-group[data-filter-type="conditions"]');
        if (!condGroup) return;

        // Pegar o separator que vem logo depois
        var sep = condGroup.nextElementSibling;
        var sepWidth = (sep && sep.classList.contains('pedidos-filtros-separator')) ? sep.offsetWidth : 0;
        var gap = 8; // gap: 0.5rem ≈ 8px

        spacer.style.width = (condGroup.offsetWidth + sepWidth + gap) + 'px';
    }

    // ═══════════════════════════════════════════════════════════════
    // UTILS
    // ═══════════════════════════════════════════════════════════════

    function escapeHtml(str) {
        if (!str) return '';
        var div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    // ═══════════════════════════════════════════════════════════════
    // INIT
    // ═══════════════════════════════════════════════════════════════

    function init() {
        BASE_URL = (window.PEDIDOS_URLS && window.PEDIDOS_URLS.listaPedidos)
            || '/pedidos/lista_pedidos';

        // Status toggles
        document.querySelectorAll('[data-filter-type="status"] input').forEach(function (cb) {
            cb.addEventListener('change', onStatusToggle);
        });

        // Condition toggles
        document.querySelectorAll('[data-filter-type="conditions"] input').forEach(function (cb) {
            cb.addEventListener('change', function () { onConditionToggle(this); });
        });

        // Smart date buttons
        document.querySelectorAll('.pedidos-date-btn').forEach(function (btn) {
            btn.addEventListener('click', function () { onSmartDateClick(this); });
        });

        // Selects com navegacao imediata
        document.querySelectorAll('[data-navigate-on-change]').forEach(function (sel) {
            sel.addEventListener('change', function () { onSelectChange(this); });
        });

        // Text inputs com Enter
        document.querySelectorAll('[data-navigate-on-enter]').forEach(function (inp) {
            inp.addEventListener('keydown', function (e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    onTextEnter(this);
                }
            });
        });

        // Date inputs com change
        document.querySelectorAll('#expedicao_de, #expedicao_ate').forEach(function (inp) {
            inp.addEventListener('change', function () { onDateChange(this); });
        });

        // Chips — event delegation
        var chipsContainer = document.getElementById('filtros-ativos');
        if (chipsContainer) {
            chipsContainer.addEventListener('click', function (e) {
                // Reset toggle pendente: voltar ao default ON
                var resetPendBtn = e.target.closest('[data-action="reset-pendente"]');
                if (resetPendBtn) {
                    try { window.localStorage.removeItem(LS_KEY_PENDENTE); } catch (err) {}
                    navegarComFiltros({ pendente: null });
                    return;
                }
                var removeBtn = e.target.closest('.pedidos-chip__remove');
                if (removeBtn) {
                    onChipRemove(removeBtn);
                    return;
                }
                var clearBtn = e.target.closest('[data-action="clear-all"]');
                if (clearBtn) {
                    window.location.href = BASE_URL;
                }
            });
        }

        // Escopo GERAL/NACOM/CARVIA — auto-submit ao trocar
        document.querySelectorAll('input.btn-check[name="origem"]').forEach(function (radio) {
            radio.addEventListener('change', function () {
                navegarComFiltros({ origem: this.value || null });
            });
        });

        // Toggle "Apenas Pendentes" — sincroniza URL <-> localStorage
        var togglePendente = document.getElementById('toggle-apenas-pendentes');
        if (togglePendente) {
            // Registrar change listener PRIMEIRO (antes da hidratacao) para
            // garantir que ele esteja disponivel mesmo se a navegacao de
            // hidratacao falhar/atrasar.
            togglePendente.addEventListener('change', function () {
                // ON = remove o param (default ON); OFF = pendente=0
                var novoValor = this.checked ? null : '0';
                // Persistir preferencia
                try {
                    if (this.checked) {
                        window.localStorage.removeItem(LS_KEY_PENDENTE);
                    } else {
                        window.localStorage.setItem(LS_KEY_PENDENTE, '0');
                    }
                } catch (e) { /* localStorage indisponivel */ }
                navegarComFiltros({ pendente: novoValor });
            });

            // Hidratar estado: se URL nao define `pendente` e localStorage='0',
            // disparar navegacao para refletir preferencia salva.
            // Nao usar `return` aqui — outros listeners abaixo precisam ser
            // registrados ate o navegador efetivamente trocar de pagina.
            var urlParams = new URLSearchParams(window.location.search);
            if (!urlParams.has('pendente')) {
                try {
                    var stored = window.localStorage.getItem(LS_KEY_PENDENTE);
                    if (stored === '0' && togglePendente.checked) {
                        // Dispara navegacao em microtask — deixa init() terminar
                        // de registrar listeners restantes antes do unload.
                        Promise.resolve().then(function () {
                            navegarComFiltros({ pendente: '0' });
                        });
                    }
                } catch (e) { /* localStorage indisponivel — segue default */ }
            }
        }

        // Persistir origem e pendente nos links da pagina (paginacao, sort, etc.)
        var currentOrigem = new URLSearchParams(window.location.search).get('origem');
        var currentPendente = new URLSearchParams(window.location.search).get('pendente');
        if (currentOrigem || currentPendente !== null) {
            document.querySelectorAll('a[href]').forEach(function (link) {
                var hrefAttr = link.getAttribute('href') || '';
                if (!hrefAttr || hrefAttr.startsWith('#') || hrefAttr.startsWith('javascript:')) return;
                try {
                    var linkUrl = new URL(link.href, window.location.origin);
                    if (linkUrl.pathname !== window.location.pathname) return;
                    if (currentOrigem) linkUrl.searchParams.set('origem', currentOrigem);
                    if (currentPendente !== null) linkUrl.searchParams.set('pendente', currentPendente);
                    link.href = linkUrl.toString();
                } catch (e) { /* ignora URLs invalidas */ }
            });
        }

        // Sort links
        updateSortLinks();

        // Chips
        renderChips();

        // Spacer: alinhar status row abaixo das datas
        alignDateSpacer();
    }

    // Expor para uso por sort links no template
    window.navegarComFiltros = navegarComFiltros;

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
