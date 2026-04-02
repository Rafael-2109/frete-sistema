(function() {
    // ===== State =====
    let linhasSelecionadas = [];  // [{id, valor, tipo}]
    let docsSelecionados = [];    // [{tipo_documento, documento_id, valor_alocado, saldo}]
    let todasLinhas = [];
    let todosDocs = [];
    let tipoMatchAtual = '';

    const fmtBRL = v => parseFloat(v).toLocaleString('pt-BR', {style:'currency', currency:'BRL'});
    const fmtNum = v => parseFloat(v).toLocaleString('pt-BR', {minimumFractionDigits:2});

    // ===== Carregar linhas extrato =====
    function carregarLinhas() {
        const status = document.getElementById('filtroStatusExtrato').value;
        const busca = document.getElementById('filtroBuscaExtrato').value;

        let url = CARVIA_URLS.extratoBancario + '?formato=json';
        if (status) url += '&status=' + status;
        if (busca) url += '&busca=' + encodeURIComponent(busca);

        // Usar a API de matches para obter linhas (reusa a tela extrato ou API direta)
        // Na verdade, vamos buscar os dados via API simples
        fetch(`/carvia/api/conciliacao/documentos-elegiveis?tipo=receber`)
        .then(r => r.json()).catch(() => ({}));

        // Usar a API de matches para obter linhas (reusa a tela extrato ou API direta)
        // Na verdade, vamos buscar os dados via API simples
        // Na implementacao, o filtro e feito client-side com dados pre-carregados

        document.getElementById('extratoLoading').textContent = 'Use os filtros do Extrato Bancario para uma visao completa.';
    }

    // ===== Renderizar linhas =====
    function renderizarLinhas(linhas) {
        const container = document.getElementById('extratoLista');
        container.innerHTML = '';
        container.classList.remove('d-none');
        document.getElementById('extratoLoading').classList.add('d-none');

        if (linhas.length === 0) {
            container.innerHTML = '<div class="text-center py-3 text-muted">Nenhuma linha encontrada</div>';
            return;
        }

        linhas.forEach(l => {
            const selected = linhasSelecionadas.find(s => s.id === l.id);
            const rowClass = l.tipo === 'CREDITO' ? 'carvia-extrato-row-credito' : 'carvia-extrato-row-debito';
            const selClass = selected ? 'carvia-conciliacao-selected' : '';

            let badgeClass = 'carvia-badge-pendente';
            if (l.status === 'CONCILIADO') badgeClass = 'carvia-badge-conciliado';
            else if (l.status === 'PARCIAL') badgeClass = 'carvia-badge-parcial';

            const div = document.createElement('div');
            div.className = `p-2 border-bottom ${rowClass} ${selClass}`;
            div.style.cursor = 'pointer';
            div.dataset.id = l.id;
            div.dataset.valor = l.valor;
            div.dataset.tipo = l.tipo;
            div.dataset.saldo = l.saldo_a_conciliar;

            div.innerHTML = `
                <div class="carvia-conciliacao-row-primary d-flex justify-content-between align-items-center">
                    <div>
                        <input type="checkbox" class="form-check-input me-1 extrato-check"
                               data-id="${l.id}" ${selected ? 'checked' : ''}>
                        <span>${l.data}</span>
                        <span class="badge ${badgeClass} ms-1" style="font-size:0.65rem">${l.status}</span>
                    </div>
                    <span class="carvia-conciliacao-valor ${l.tipo === 'CREDITO' ? 'text-success' : 'text-danger'}">
                        ${l.tipo === 'CREDITO' ? '+' : ''}${fmtNum(l.valor)}
                        ${l.saldo_a_conciliar < Math.abs(l.valor) - 0.01 ? '<small class="text-muted ms-1">(saldo: ' + fmtNum(l.saldo_a_conciliar) + ')</small>' : ''}
                    </span>
                </div>
                <div class="carvia-conciliacao-row-secondary ps-4">${l.razao_social ? '<strong>' + l.razao_social + '</strong>' : ''}${l.razao_social && l.descricao ? ' — ' : ''}${l.descricao || ''}</div>
            `;
            container.appendChild(div);
        });

        // Event listeners
        container.querySelectorAll('.extrato-check').forEach(cb => {
            cb.addEventListener('change', function(e) {
                e.stopPropagation();
                toggleLinha(parseInt(this.dataset.id));
            });
        });
        container.querySelectorAll('[data-id]').forEach(div => {
            div.addEventListener('click', function(e) {
                if (e.target.classList.contains('form-check-input')) return;
                const cb = this.querySelector('.extrato-check');
                cb.checked = !cb.checked;
                toggleLinha(parseInt(this.dataset.id));
            });
        });
    }

    // ===== Toggle linha =====
    function toggleLinha(id) {
        const idx = linhasSelecionadas.findIndex(s => s.id === id);
        if (idx >= 0) {
            linhasSelecionadas.splice(idx, 1);
        } else {
            const el = document.querySelector(`[data-id="${id}"]`);
            linhasSelecionadas.push({
                id: id,
                valor: parseFloat(el.dataset.valor),
                saldo: parseFloat(el.dataset.saldo),
                tipo: el.dataset.tipo,
            });
        }
        atualizarSelecao();
        carregarDocumentos();
    }

    // ===== Carregar documentos elegiveis =====
    function carregarDocumentos() {
        const docsPlaceholder = document.getElementById('docsPlaceholder');
        const docsLista = document.getElementById('docsLista');

        if (linhasSelecionadas.length === 0) {
            docsPlaceholder.classList.remove('d-none');
            docsLista.classList.add('d-none');
            todosDocs = [];
            docsSelecionados = [];
            atualizarSelecao();
            return;
        }

        // Determinar tipo: se tem CREDITO -> receber, se DEBITO -> pagar
        // Se misto, prioriza o primeiro selecionado
        const tipo = linhasSelecionadas[0].tipo;
        tipoMatchAtual = tipo === 'CREDITO' ? 'receber' : 'pagar';

        docsPlaceholder.innerHTML = '<div class="spinner-border spinner-border-sm"></div> Carregando...';
        docsPlaceholder.classList.remove('d-none');
        docsLista.classList.add('d-none');

        fetch(`/carvia/api/conciliacao/documentos-elegiveis?tipo=${tipoMatchAtual}`)
        .then(r => r.json())
        .then(data => {
            todosDocs = data.documentos || [];
            renderizarDocs(todosDocs);
        })
        .catch(err => {
            docsPlaceholder.textContent = 'Erro ao carregar documentos';
            docsPlaceholder.classList.remove('d-none');
        });
    }

    // ===== Renderizar docs =====
    function renderizarDocs(docs) {
        const docsPlaceholder = document.getElementById('docsPlaceholder');
        const docsLista = document.getElementById('docsLista');
        docsPlaceholder.classList.add('d-none');
        docsLista.classList.remove('d-none');
        docsLista.innerHTML = '';
        docsSelecionados = [];

        if (docs.length === 0) {
            docsLista.innerHTML = '<div class="text-center py-3 text-muted">Nenhum documento elegivel</div>';
            atualizarSelecao();
            return;
        }

        docs.forEach(d => {
            const div = document.createElement('div');
            div.className = 'p-2 border-bottom';
            div.style.cursor = 'pointer';
            div.dataset.tipo = d.tipo_documento;
            div.dataset.docId = d.id;
            div.dataset.saldo = d.saldo;

            const tipoLabel = d.tipo_documento === 'fatura_cliente' ? 'FAT' :
                              d.tipo_documento === 'fatura_transportadora' ? 'FTRANSP' : 'DESP';

            div.innerHTML = `
                <div class="carvia-conciliacao-row-primary d-flex justify-content-between align-items-center">
                    <div>
                        <input type="checkbox" class="form-check-input me-1 doc-check"
                               data-tipo="${d.tipo_documento}" data-id="${d.id}" data-saldo="${d.saldo}">
                        <span class="badge bg-secondary" style="font-size:0.65rem">${tipoLabel}</span>
                        <span>${d.numero}</span>
                    </div>
                    <span class="carvia-conciliacao-valor">${fmtNum(d.saldo)}</span>
                </div>
                <div class="carvia-conciliacao-row-secondary ps-4">
                    ${d.nome} &middot; ${d.data}
                    ${d.vencimento ? ' &middot; Venc: ' + d.vencimento : ''}
                    ${d.condicao_pagamento || d.responsavel_frete_label ? ' &middot; <small class="text-info">' + (d.condicao_pagamento || '') + (d.condicao_pagamento && d.responsavel_frete_label ? ' | ' : '') + (d.responsavel_frete_label || '') + '</small>' : ''}
                </div>
            `;
            docsLista.appendChild(div);
        });

        // Event listeners
        docsLista.querySelectorAll('.doc-check').forEach(cb => {
            cb.addEventListener('change', function(e) {
                e.stopPropagation();
                toggleDoc(this);
            });
        });
        docsLista.querySelectorAll('[data-doc-id]').forEach(div => {
            div.addEventListener('click', function(e) {
                if (e.target.classList.contains('form-check-input')) return;
                const cb = this.querySelector('.doc-check');
                cb.checked = !cb.checked;
                toggleDoc(cb);
            });
        });
    }

    // ===== Toggle doc =====
    function toggleDoc(cb) {
        const tipo = cb.dataset.tipo;
        const id = parseInt(cb.dataset.id);
        const saldo = parseFloat(cb.dataset.saldo);

        if (cb.checked) {
            docsSelecionados.push({
                tipo_documento: tipo,
                documento_id: id,
                valor_alocado: saldo,
                saldo: saldo,
            });
            cb.closest('[data-doc-id]')?.classList.add('carvia-conciliacao-selected');
        } else {
            const idx = docsSelecionados.findIndex(d => d.tipo_documento === tipo && d.documento_id === id);
            if (idx >= 0) docsSelecionados.splice(idx, 1);
            cb.closest('[data-doc-id]')?.classList.remove('carvia-conciliacao-selected');
        }
        atualizarSelecao();
    }

    // ===== Atualizar cards de selecao =====
    function atualizarSelecao() {
        const totalExtrato = linhasSelecionadas.reduce((s, l) => s + l.saldo, 0);
        const totalDocs = docsSelecionados.reduce((s, d) => s + d.valor_alocado, 0);
        const diferenca = totalExtrato - totalDocs;

        document.getElementById('selExtratoValor').textContent =
            linhasSelecionadas.length > 1
                ? `${fmtBRL(totalExtrato)} (${linhasSelecionadas.length} linhas)`
                : fmtBRL(totalExtrato);
        document.getElementById('selDocsValor').textContent = fmtBRL(totalDocs);

        const diffEl = document.getElementById('selDiferenca');
        if (linhasSelecionadas.length > 0 && docsSelecionados.length > 0) {
            if (Math.abs(diferenca) < 0.01) {
                diffEl.textContent = '(OK)';
                diffEl.className = 'ms-2 small text-success fw-bold';
                document.getElementById('cardSelDocs').className = 'card carvia-conciliacao-card-match';
            } else {
                diffEl.textContent = `(Dif: ${fmtBRL(diferenca)})`;
                diffEl.className = 'ms-2 small text-warning';
                document.getElementById('cardSelDocs').className = 'card carvia-conciliacao-card-mismatch';
            }
        } else {
            diffEl.textContent = '';
            document.getElementById('cardSelDocs').className = 'card';
        }

        // Habilitar botao se ha selecao valida
        const btn = document.getElementById('btnConciliarSelecionados');
        btn.disabled = !(linhasSelecionadas.length > 0 && docsSelecionados.length > 0);
    }

    // ===== Conciliar (alocacao greedy N linhas x M docs) =====
    document.getElementById('btnConciliarSelecionados')?.addEventListener('click', async function() {
        if (linhasSelecionadas.length === 0 || docsSelecionados.length === 0) return;

        this.disabled = true;
        this.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Conciliando...';

        // Clone saldos dos docs para alocacao greedy
        const docsRestantes = docsSelecionados.map(d => ({
            ...d,
            saldo_restante: d.valor_alocado,
        }));

        let erro = null;
        let totalConciliados = 0;

        for (const linha of linhasSelecionadas) {
            let restante = linha.saldo;
            const docsParaLinha = [];

            for (const doc of docsRestantes) {
                if (restante <= 0.01) break;
                if (doc.saldo_restante <= 0.01) continue;

                const alocar = Math.min(restante, doc.saldo_restante);
                docsParaLinha.push({
                    tipo_documento: doc.tipo_documento,
                    documento_id: doc.documento_id,
                    valor_alocado: Math.round(alocar * 100) / 100,
                });
                restante -= alocar;
                doc.saldo_restante -= alocar;
            }

            if (docsParaLinha.length === 0) continue;

            try {
                const resp = await fetch(CARVIA_URLS.apiConciliar, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        extrato_linha_id: linha.id,
                        documentos: docsParaLinha,
                    }),
                });
                const data = await resp.json();
                if (!data.sucesso) {
                    erro = data.erro || 'Erro ao conciliar';
                    break;
                }
                totalConciliados++;
            } catch (e) {
                erro = e.message;
                break;
            }
        }

        if (erro) {
            alert(erro);
            if (totalConciliados > 0) location.reload();
            else {
                this.disabled = false;
                this.innerHTML = '<i class="fas fa-check-double"></i> Conciliar Selecionados';
            }
        } else {
            location.reload();
        }
    });

    // ===== Filtro busca docs =====
    document.getElementById('filtroBuscaDocs')?.addEventListener('input', function() {
        const termo = this.value.toLowerCase();
        const filtrados = todosDocs.filter(d =>
            (d.numero || '').toLowerCase().includes(termo) ||
            (d.nome || '').toLowerCase().includes(termo)
        );
        renderizarDocs(filtrados);
    });

    // ===== Init: carregar linhas pendentes via inline data =====
    if (CARVIA_DATA.linhas.length > 0) {
        todasLinhas = CARVIA_DATA.linhas;
        renderizarLinhas(todasLinhas);
    } else {
        document.getElementById('extratoLoading').innerHTML =
            '<div class="text-muted py-3">Importe um arquivo OFX para comecar</div>';
    }

    // Filtros client-side
    function aplicarFiltrosExtrato() {
        const status = document.getElementById('filtroStatusExtrato').value;
        const busca = document.getElementById('filtroBuscaExtrato').value.toLowerCase();
        const filtradas = todasLinhas.filter(l => {
            // Filtro especial: RECEBIMENTO = valor > 0 (credito)
            if (status === 'RECEBIMENTO') {
                if (l.valor <= 0) return false;
            } else if (status) {
                if (l.status !== status) return false;
            }
            if (busca && !(l.descricao || '').toLowerCase().includes(busca)
                      && !(l.razao_social || '').toLowerCase().includes(busca)) return false;
            return true;
        });
        renderizarLinhas(filtradas);
    }

    document.getElementById('filtroStatusExtrato')?.addEventListener('change', aplicarFiltrosExtrato);
    document.getElementById('filtroBuscaExtrato')?.addEventListener('input', aplicarFiltrosExtrato);
})();
