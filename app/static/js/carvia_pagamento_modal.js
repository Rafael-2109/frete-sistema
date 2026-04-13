/**
 * CarVia — Modal de Pagamento reusavel
 * =====================================
 *
 * Driver JS para o modal `_modal_pagar_com_conciliacao.html`.
 * Uso:
 *   CarviaPagamentoModal.abrir({
 *     tipoDoc: 'fatura_cliente',
 *     docId: 42,
 *     endpoint: '/carvia/faturas-cliente/42/pagar',
 *     onSuccess: function(resultado) { ... }
 *   });
 *
 * O endpoint deve aceitar POST JSON com payload:
 *   - Modo conciliacao: { data_pagamento, extrato_linha_id }
 *   - Modo manual: { data_pagamento, conta_origem, descricao_pagamento }
 *
 * E retornar: { sucesso, novo_status, pago_em, pago_por, extrato_linha_id, modo }
 *
 * W10 Nivel 2 (Sprint 4).
 */
(function(window, document) {
    'use strict';

    var TIPO_LABELS = {
        'fatura_cliente': 'Fatura Cliente',
        'fatura_transportadora': 'Fatura Transp.',
        'despesa': 'Despesa',
        'custo_entrega': 'Custo Entrega',
        'receita': 'Receita',
    };

    var state = {
        tipoDoc: null,
        docId: null,
        endpoint: null,
        onSuccess: null,
        linhaSelecionadaId: null,
        modalInstance: null,
    };

    function el(id) { return document.getElementById(id); }

    function csrfToken() {
        var meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute('content') : '';
    }

    function resetModal() {
        el('pcDocTipo').textContent = TIPO_LABELS[state.tipoDoc] || state.tipoDoc;
        el('pcDocNumero').textContent = '#' + state.docId;
        el('pcDocValor').textContent = '-';
        el('pcDocNome').textContent = '';
        el('pcDocVenc').textContent = '-';
        el('pcLoading').classList.remove('d-none');
        el('pcLinhasContainer').classList.add('d-none');
        el('pcSemLinhas').classList.add('d-none');
        el('pcDataPagamento').value = new Date().toISOString().slice(0, 10);

        // Reset bloco manual
        el('pcToggleManual').checked = false;
        el('pcBlocoManual').classList.add('d-none');
        el('pcContaOrigem').value = '';
        el('pcDescricaoPagamento').value = '';

        // Reset erro
        el('pcErro').classList.add('d-none');
        el('pcErro').textContent = '';

        // Reset botoes
        el('btnPagarEConciliar').disabled = true;
        el('btnPagarEConciliar').classList.remove('d-none');
        el('btnPagarManual').classList.add('d-none');

        state.linhaSelecionadaId = null;
    }

    function renderLinhas(linhas) {
        var tbody = el('pcLinhasBody');
        tbody.innerHTML = '';

        linhas.forEach(function(ln) {
            var scoreBadge = '';
            if (ln.score_label === 'ALTO') {
                scoreBadge = '<span class="badge carvia-badge-score-alto" style="font-size:0.6rem">&#9733;&#9733;&#9733;</span>';
            } else if (ln.score_label === 'MEDIO') {
                scoreBadge = '<span class="badge carvia-badge-score-medio" style="font-size:0.6rem">&#9733;&#9733;</span>';
            } else {
                scoreBadge = '<span class="badge carvia-badge-score-baixo" style="font-size:0.6rem">&#9733;</span>';
            }

            // Badge origem (OFX/CSV/MANUAL)
            var origem = ln.origem || 'OFX';
            var origemBadge;
            if (origem === 'MANUAL') {
                origemBadge = '<span class="badge bg-info" style="font-size:0.6rem">Manual</span>';
            } else if (origem === 'CSV') {
                origemBadge = '<span class="badge bg-secondary" style="font-size:0.6rem">CSV</span>';
            } else {
                origemBadge = '<span class="badge bg-primary" style="font-size:0.6rem">OFX</span>';
            }

            var contaOrigemTxt = ln.conta_origem ? (' — ' + ln.conta_origem) : '';
            var descricao = (ln.razao_social || ln.descricao || '-') + contaOrigemTxt;

            var tr = document.createElement('tr');
            tr.style.cursor = 'pointer';
            tr.dataset.linhaId = ln.id;
            tr.innerHTML =
                '<td><input type="radio" name="pcLinha" value="' + ln.id + '" class="form-check-input"></td>' +
                '<td>' + ln.data + '</td>' +
                '<td class="text-truncate" style="max-width:180px" title="' + descricao + '">' + descricao + '</td>' +
                '<td>' + origemBadge + '</td>' +
                '<td class="text-end">R$ ' + Math.abs(ln.valor).toLocaleString('pt-BR', {minimumFractionDigits: 2}) + '</td>' +
                '<td class="text-end">R$ ' + parseFloat(ln.saldo_a_conciliar).toLocaleString('pt-BR', {minimumFractionDigits: 2}) + '</td>' +
                '<td>' + scoreBadge + '</td>';
            tbody.appendChild(tr);

            tr.addEventListener('click', function() {
                // Se o modo manual estiver ativo, selecionar linha desativa ele
                el('pcToggleManual').checked = false;
                aplicarModoManual(false);

                var radio = tr.querySelector('input[type=radio]');
                radio.checked = true;
                state.linhaSelecionadaId = ln.id;
                el('btnPagarEConciliar').disabled = false;

                tbody.querySelectorAll('tr').forEach(function(r) {
                    r.classList.remove('table-active');
                });
                tr.classList.add('table-active');
            });
        });

        el('pcLinhasContainer').classList.remove('d-none');
    }

    function aplicarModoManual(ativo) {
        var bloco = el('pcBlocoManual');
        var btnConciliar = el('btnPagarEConciliar');
        var btnManual = el('btnPagarManual');

        if (ativo) {
            bloco.classList.remove('d-none');
            btnConciliar.classList.add('d-none');
            btnManual.classList.remove('d-none');
            // Limpar selecao de linha (exclusivo com manual)
            state.linhaSelecionadaId = null;
            el('pcLinhasBody').querySelectorAll('tr').forEach(function(r) {
                r.classList.remove('table-active');
                var radio = r.querySelector('input[type=radio]');
                if (radio) { radio.checked = false; }
            });
        } else {
            bloco.classList.add('d-none');
            btnConciliar.classList.remove('d-none');
            btnManual.classList.add('d-none');
        }
    }

    function mostrarErro(mensagem) {
        var erroEl = el('pcErro');
        erroEl.textContent = mensagem;
        erroEl.classList.remove('d-none');
    }

    function processarPagamento(modo) {
        el('pcErro').classList.add('d-none');

        var dataPag = el('pcDataPagamento').value;
        if (!dataPag) {
            el('pcDataPagamento').focus();
            mostrarErro('Informe a data do pagamento.');
            return;
        }

        var payload = {
            tipo_doc: state.tipoDoc,
            id: parseInt(state.docId),
            data_pagamento: dataPag,
        };

        if (modo === 'conciliar') {
            if (!state.linhaSelecionadaId) {
                mostrarErro('Selecione uma linha do extrato.');
                return;
            }
            payload.extrato_linha_id = state.linhaSelecionadaId;
        } else if (modo === 'manual') {
            var contaOrigem = el('pcContaOrigem').value.trim();
            var descricao = el('pcDescricaoPagamento').value.trim();

            if (!contaOrigem) {
                el('pcContaOrigem').focus();
                mostrarErro('Informe a conta de origem.');
                return;
            }
            if (!descricao) {
                el('pcDescricaoPagamento').focus();
                mostrarErro('Informe a descricao do pagamento.');
                return;
            }
            payload.conta_origem = contaOrigem;
            payload.descricao_pagamento = descricao;
        }

        // Desabilitar botoes durante requisicao
        var footerBtns = document.querySelectorAll(
            '#modalPagarComConciliacao .modal-footer button'
        );
        footerBtns.forEach(function(b) { b.disabled = true; });

        function reaplicarEstadoBotoesPorModo() {
            // Restaura visibilidade/habilitacao dos botoes conforme o modo atual.
            // Evita que btnPagarEConciliar fique visivel no modo manual apos erro.
            var toggleManual = el('pcToggleManual');
            var btnConc = el('btnPagarEConciliar');
            var btnMan = el('btnPagarManual');
            if (toggleManual && toggleManual.checked) {
                // Modo manual — manter btnPagarEConciliar desabilitado e oculto
                btnConc.disabled = true;
                btnConc.classList.add('d-none');
                btnMan.classList.remove('d-none');
                btnMan.disabled = false;
            } else {
                // Modo conciliacao — btnPagarEConciliar habilitado se ha linha selecionada
                btnConc.disabled = !state.linhaSelecionadaId;
                btnConc.classList.remove('d-none');
                btnMan.classList.add('d-none');
            }
        }

        fetch(state.endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken(),
            },
            body: JSON.stringify(payload),
        })
        .then(function(r) {
            return r.json().then(function(data) {
                return { ok: r.ok, status: r.status, data: data };
            });
        })
        .then(function(resp) {
            footerBtns.forEach(function(b) { b.disabled = false; });
            // Re-aplicar estado dos botoes conforme modo atual
            reaplicarEstadoBotoesPorModo();

            if (!resp.ok || resp.data.erro) {
                mostrarErro(resp.data.erro || 'Erro ao processar pagamento');
                return;
            }

            // Sucesso — fechar modal e chamar callback
            if (state.modalInstance) {
                state.modalInstance.hide();
            }
            if (typeof state.onSuccess === 'function') {
                state.onSuccess(resp.data);
            }
        })
        .catch(function(err) {
            footerBtns.forEach(function(b) { b.disabled = false; });
            reaplicarEstadoBotoesPorModo();
            mostrarErro('Erro de rede: ' + err.message);
        });
    }

    function abrir(opts) {
        state.tipoDoc = opts.tipoDoc;
        state.docId = opts.docId;
        state.endpoint = opts.endpoint;
        state.onSuccess = opts.onSuccess;

        var modalEl = el('modalPagarComConciliacao');
        if (!modalEl) {
            console.error('[CarviaPagamentoModal] Modal nao encontrado no DOM. '
                + 'Inclua _modal_pagar_com_conciliacao.html no template.');
            return;
        }

        if (!state.modalInstance) {
            state.modalInstance = new bootstrap.Modal(modalEl);
        }

        resetModal();
        state.modalInstance.show();

        // Buscar linhas candidatas via matches-por-documento
        var url = '/carvia/api/conciliacao/matches-por-documento?tipo_doc='
            + encodeURIComponent(state.tipoDoc) + '&doc_id=' + state.docId;

        fetch(url)
            .then(function(r) { return r.json(); })
            .then(function(data) {
                el('pcLoading').classList.add('d-none');

                if (data.erro) {
                    el('pcSemLinhas').classList.remove('d-none');
                    el('pcSemLinhas').innerHTML =
                        '<i class="fas fa-exclamation-circle"></i> ' + data.erro;
                    return;
                }

                // Info do documento
                var doc = data.documento;
                if (doc) {
                    el('pcDocNumero').textContent = doc.numero || '#' + state.docId;
                    el('pcDocValor').textContent =
                        'R$ ' + parseFloat(doc.valor).toLocaleString('pt-BR', {minimumFractionDigits: 2});
                    el('pcDocNome').textContent = doc.nome || '';
                    el('pcDocVenc').textContent = doc.vencimento || '-';
                }

                var linhas = data.linhas || [];
                if (linhas.length === 0) {
                    el('pcSemLinhas').classList.remove('d-none');
                    return;
                }

                renderLinhas(linhas);
            })
            .catch(function(err) {
                el('pcLoading').classList.add('d-none');
                el('pcSemLinhas').classList.remove('d-none');
                el('pcSemLinhas').innerHTML =
                    '<i class="fas fa-exclamation-circle"></i> Erro ao buscar: ' + err.message;
            });
    }

    // ==================================================================
    // Event bindings (idempotente — so registra uma vez)
    // ==================================================================

    var bindingsAtivos = false;

    function ativarBindings() {
        if (bindingsAtivos) return;
        if (!el('modalPagarComConciliacao')) return;
        bindingsAtivos = true;

        // Toggle manual
        el('pcToggleManual').addEventListener('change', function() {
            aplicarModoManual(this.checked);
        });

        // Botao pagar e conciliar
        el('btnPagarEConciliar').addEventListener('click', function() {
            processarPagamento('conciliar');
        });

        // Botao pagar manual
        el('btnPagarManual').addEventListener('click', function() {
            processarPagamento('manual');
        });
    }

    // Ativar ao carregar DOM
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', ativarBindings);
    } else {
        ativarBindings();
    }

    // Expor API publica
    window.CarviaPagamentoModal = {
        abrir: abrir,
        _state: state,  // debug
    };

})(window, document);
