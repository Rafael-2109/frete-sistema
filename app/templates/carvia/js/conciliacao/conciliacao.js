(function() {
    // ===== State =====
    let linhasSelecionadas = [];  // [{id, valor, tipo}]
    let docsSelecionados = [];    // [{tipo_documento, documento_id, valor_alocado, saldo}]
    let todasLinhas = [];
    let todosDocs = [];
    let tipoMatchAtual = '';

    const REGEX_FISCAL = /secretaria|sefaz|gnre/i;

    const fmtBRL = v => parseFloat(v).toLocaleString('pt-BR', {style:'currency', currency:'BRL'});
    const fmtNum = v => parseFloat(v).toLocaleString('pt-BR', {minimumFractionDigits:2});
    // Escapa HTML para prevenir XSS ao interpolar conteudo vindo do banco (OFX externo)
    const escapeHtml = s => {
        if (s == null) return '';
        return String(s)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    };
    const formatCNPJ = c => {
        if (!c || c.length < 14) return c || '';
        const d = c.replace(/\D/g, '');
        if (d.length !== 14) return c;
        return d.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, '$1.$2.$3/$4-$5');
    };

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

            // Detecção fiscal: GNRE/SEFAZ/Secretaria em linhas DEBITO não-conciliadas
            const ehFiscal = l.tipo === 'DEBITO'
                && l.status !== 'CONCILIADO'
                && REGEX_FISCAL.test((l.descricao || '') + ' ' + (l.memo || ''));

            const btnFiscalHTML = ehFiscal
                ? `<button class="btn btn-outline-warning btn-criar-custo-fiscal ms-2"
                       style="font-size:0.7rem; padding:1px 6px;"
                       data-linha-id="${l.id}"
                       data-valor="${l.saldo_a_conciliar}"
                       data-data="${escapeHtml(l.data)}"
                       data-descricao="${escapeHtml(l.descricao || '')}"
                       title="Criar Custo Fiscal (GNRE/SEFAZ)">
                       <i class="fas fa-landmark"></i> Custo Fiscal
                   </button>`
                : '';

            const razaoHtml = l.razao_social ? '<strong>' + escapeHtml(l.razao_social) + '</strong>' : '';
            const sepHtml = l.razao_social && l.descricao ? ' — ' : '';
            const descHtml = escapeHtml(l.descricao || '');
            const obsHtml = l.observacao
                ? '<div class="ps-4 text-muted fst-italic" style="font-size:0.7rem"><i class="fas fa-sticky-note text-warning me-1"></i>' + escapeHtml(l.observacao) + '</div>'
                : '';

            div.innerHTML = `
                <div class="carvia-conciliacao-row-primary d-flex justify-content-between align-items-center">
                    <div>
                        <input type="checkbox" class="form-check-input me-1 extrato-check"
                               data-id="${l.id}" ${selected ? 'checked' : ''}>
                        <span>${l.data}</span>
                        <span class="badge ${badgeClass} ms-1" style="font-size:0.65rem">${l.status}</span>
                        ${btnFiscalHTML}
                    </div>
                    <span class="carvia-conciliacao-valor ${l.tipo === 'CREDITO' ? 'text-success' : 'text-danger'}">
                        ${l.tipo === 'CREDITO' ? '+' : ''}${fmtNum(l.valor)}
                        ${l.saldo_a_conciliar < Math.abs(l.valor) - 0.01 ? '<small class="text-muted ms-1">(saldo: ' + fmtNum(l.saldo_a_conciliar) + ')</small>' : ''}
                    </span>
                </div>
                <div class="carvia-conciliacao-row-secondary ps-4">${razaoHtml}${sepHtml}${descHtml}</div>
                ${obsHtml}
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
                if (e.target.closest('.btn-criar-custo-fiscal')) return;
                const cb = this.querySelector('.extrato-check');
                cb.checked = !cb.checked;
                toggleLinha(parseInt(this.dataset.id));
            });
        });

        // Listeners para botão Custo Fiscal (GNRE/SEFAZ)
        container.querySelectorAll('.btn-criar-custo-fiscal').forEach(btn => {
            btn.addEventListener('click', function(e) {
                e.stopPropagation();
                if (typeof window.abrirModalCriarCustoFiscal === 'function') {
                    window.abrirModalCriarCustoFiscal({
                        linhaId: parseInt(this.dataset.linhaId),
                        valor: parseFloat(this.dataset.valor),
                        data: this.dataset.data,
                        descricao: this.dataset.descricao,
                    });
                }
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

        // Scoring sugestivo: passa linha_id quando 1 unica linha selecionada
        const linhaParam = linhasSelecionadas.length === 1
            ? `&linha_id=${linhasSelecionadas[0].id}` : '';
        fetch(`/carvia/api/conciliacao/documentos-elegiveis?tipo=${tipoMatchAtual}${linhaParam}`)
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

    // ===== Construir secondary HTML enriquecido =====
    function buildSecondaryHTML(d) {
        let html = '';

        if (d.tipo_documento === 'fatura_cliente') {
            // Linha 1: Nome + CNPJ
            html += `<div>${d.nome}`;
            if (d.cnpj_cliente) {
                html += ` <small class="text-muted">(${formatCNPJ(d.cnpj_cliente)})</small>`;
            }
            html += `</div>`;

            // Linha 2: Remetente + Destinatario com enfase no tomador
            const resp = d.responsavel_frete || '';
            if (d.remetente_nome || (d.destinatarios && d.destinatarios.length)) {
                const remEmph = ['100_REMETENTE', '50_50'].includes(resp) ? 'carvia-tomador-emphasis' : '';
                const destEmph = ['100_DESTINATARIO', '50_50'].includes(resp) ? 'carvia-tomador-emphasis' : '';

                html += `<div class="mt-1" style="font-size:0.75rem">`;
                if (d.remetente_nome) {
                    html += `<span class="${remEmph}">Rem: ${d.remetente_nome}</span>`;
                }
                if (d.destinatarios && d.destinatarios.length) {
                    const destLabel = d.destinatarios[0].nome || formatCNPJ(d.destinatarios[0].cnpj);
                    html += `${d.remetente_nome ? ' · ' : ''}<span class="${destEmph}">Dest: ${destLabel}</span>`;
                    if (d.destinatarios.length > 1) {
                        html += ` <small class="text-muted">(+${d.destinatarios.length - 1})</small>`;
                    }
                }
                html += `</div>`;
            }

            // Linha 3: Badges CTe + NF
            let badges = '';
            if (d.cte_numeros && d.cte_numeros.length) {
                d.cte_numeros.forEach(n => {
                    badges += `<span class="badge bg-secondary me-1" style="font-size:0.6rem">${n}</span>`;
                });
            }
            if (d.nf_numeros && d.nf_numeros.length) {
                d.nf_numeros.slice(0, 5).forEach(n => {
                    badges += `<span class="badge bg-info me-1" style="font-size:0.6rem">NF ${n}</span>`;
                });
                if (d.nf_numeros.length > 5) {
                    badges += `<small class="text-muted">+${d.nf_numeros.length - 5} NFs</small>`;
                }
            }
            if (badges) html += `<div class="mt-1">${badges}</div>`;

            // Linha 4: Condicoes comerciais
            if (d.condicao_pagamento || d.responsavel_frete_label) {
                html += `<div><small class="text-info">${d.condicao_pagamento || ''}${d.condicao_pagamento && d.responsavel_frete_label ? ' | ' : ''}${d.responsavel_frete_label || ''}</small></div>`;
            }

            // Linha 5: Data + Vencimento
            html += `<div class="text-muted" style="font-size:0.7rem">${d.data}${d.vencimento ? ' · Venc: ' + d.vencimento : ''}</div>`;

        } else if (d.tipo_documento === 'fatura_transportadora') {
            // Nome + CNPJ transportadora
            html += `<div>${d.nome}`;
            if (d.cnpj_transportadora) {
                html += ` <small class="text-muted">(${formatCNPJ(d.cnpj_transportadora)})</small>`;
            }
            html += `</div>`;
            // Badges CTe subcontratos
            if (d.cte_numeros && d.cte_numeros.length) {
                let badges = '';
                d.cte_numeros.forEach(n => {
                    badges += `<span class="badge bg-secondary me-1" style="font-size:0.6rem">${n}</span>`;
                });
                html += `<div class="mt-1">${badges}</div>`;
            }
            html += `<div class="text-muted" style="font-size:0.7rem">${d.data}${d.vencimento ? ' · Venc: ' + d.vencimento : ''}</div>`;

        } else {
            // Despesa, Custo Entrega, Receita — layout simples
            html += `${d.nome} &middot; ${d.data}${d.vencimento ? ' &middot; Venc: ' + d.vencimento : ''}`;
        }

        return html;
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
                              d.tipo_documento === 'fatura_transportadora' ? 'FTRANSP' :
                              d.tipo_documento === 'custo_entrega' ? 'CE' :
                              d.tipo_documento === 'receita' ? 'REC' : 'DESP';

            // Badge de score sugestivo
            const pct = v => Math.round((v||0)*100) + '%';
            let scoreBadge = '';
            if (d.score_label === 'ALTO') {
                const det = d.score_detalhes || {};
                scoreBadge = `<span class="badge carvia-badge-score-alto ms-1" style="font-size:0.6rem" title="Val:${pct(det.valor)} Dt:${pct(det.data)} Nm:${pct(det.nome)}">&#9733;&#9733;&#9733;</span>`;
            } else if (d.score_label === 'MEDIO') {
                const det = d.score_detalhes || {};
                scoreBadge = `<span class="badge carvia-badge-score-medio ms-1" style="font-size:0.6rem" title="Val:${pct(det.valor)} Dt:${pct(det.data)} Nm:${pct(det.nome)}">&#9733;&#9733;</span>`;
            }

            div.innerHTML = `
                <div class="carvia-conciliacao-row-primary d-flex justify-content-between align-items-center">
                    <div>
                        <input type="checkbox" class="form-check-input me-1 doc-check"
                               data-tipo="${d.tipo_documento}" data-id="${d.id}" data-saldo="${d.saldo}">
                        <span class="badge bg-secondary" style="font-size:0.65rem">${tipoLabel}</span>
                        <span>${d.numero}</span>${scoreBadge}
                    </div>
                    <span class="carvia-conciliacao-valor">${fmtNum(d.saldo)}</span>
                </div>
                <div class="carvia-conciliacao-row-secondary ps-4">
                    ${buildSecondaryHTML(d)}
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

    // ===== Filtros docs (unificado) =====
    function aplicarFiltrosDocs() {
        const termo = (document.getElementById('filtroBuscaDocs')?.value || '').toLowerCase();
        const valMin = parseFloat(document.getElementById('filtroValorMinDocs')?.value) || 0;
        const valMax = parseFloat(document.getElementById('filtroValorMaxDocs')?.value) || Infinity;
        const dataIni = document.getElementById('filtroDataIniDocs')?.value || '';
        const dataFim = document.getElementById('filtroDataFimDocs')?.value || '';

        const filtrados = todosDocs.filter(d => {
            // Faixa de valor (sobre saldo)
            if (d.saldo < valMin || d.saldo > valMax) return false;
            // Data range (DD/MM/YYYY -> YYYY-MM-DD)
            if ((dataIni || dataFim) && d.data) {
                const parts = d.data.split('/');
                if (parts.length === 3) {
                    const dISO = parts[2] + '-' + parts[1] + '-' + parts[0];
                    if (dataIni && dISO < dataIni) return false;
                    if (dataFim && dISO > dataFim) return false;
                }
            }
            // Busca texto: numero, nome, cnpj
            if (termo &&
                !(d.numero || '').toLowerCase().includes(termo) &&
                !(d.nome || '').toLowerCase().includes(termo) &&
                !(d.cnpj_cliente || '').toLowerCase().includes(termo) &&
                !(d.cnpj_transportadora || '').toLowerCase().includes(termo))
                return false;
            return true;
        });
        renderizarDocs(filtrados);
    }

    ['filtroBuscaDocs', 'filtroValorMinDocs', 'filtroValorMaxDocs',
     'filtroDataIniDocs', 'filtroDataFimDocs'].forEach(id => {
        document.getElementById(id)?.addEventListener('input', aplicarFiltrosDocs);
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
        const tipo = document.getElementById('filtroTipoExtrato').value;
        const status = document.getElementById('filtroStatusExtrato').value;
        const busca = document.getElementById('filtroBuscaExtrato').value.toLowerCase();
        const valMin = parseFloat(document.getElementById('filtroValorMinExtrato')?.value) || 0;
        const valMax = parseFloat(document.getElementById('filtroValorMaxExtrato')?.value) || Infinity;

        const filtradas = todasLinhas.filter(l => {
            // Tipo (CREDITO/DEBITO)
            if (tipo && l.tipo !== tipo) return false;
            // Status conciliacao
            if (status && l.status !== status) return false;
            // Faixa de valor (sobre valor absoluto)
            const absVal = Math.abs(l.valor);
            if (absVal < valMin || absVal > valMax) return false;
            // Busca texto
            if (busca && !(l.descricao || '').toLowerCase().includes(busca)
                      && !(l.razao_social || '').toLowerCase().includes(busca)) return false;
            return true;
        });
        renderizarLinhas(filtradas);
    }

    ['filtroTipoExtrato', 'filtroStatusExtrato'].forEach(id => {
        document.getElementById(id)?.addEventListener('change', aplicarFiltrosExtrato);
    });
    ['filtroBuscaExtrato', 'filtroValorMinExtrato', 'filtroValorMaxExtrato'].forEach(id => {
        document.getElementById(id)?.addEventListener('input', aplicarFiltrosExtrato);
    });
})();
