/**
 * Validacoes NF x PO - JavaScript
 *
 * Funcoes compartilhadas (formatacao, modais, download) estao em divergencias_shared.js
 *
 * Contem:
 * - Modal Detalhes da Validacao
 * - Validar NF, Consolidar, Reverter
 * - Executar Validacao Manual (com periodo)
 * - Accordion de Divergencias inline (lazy load via API)
 */

// =============================================================================
// VARIAVEIS GLOBAIS
// =============================================================================

let modalDetalhes;
const divergenciasCache = {};  // Cache: validacaoId -> divergencias data

// =============================================================================
// MODAL DETALHES DA VALIDACAO
// =============================================================================

function verDetalhes(id) {
    document.getElementById('modalDetalhesBody').innerHTML = `
        <div class="text-center py-5">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Carregando...</span>
            </div>
        </div>
    `;
    modalDetalhes.show();

    fetch(`/api/recebimento/validacoes-nf-po/${id}`)
        .then(r => r.json())
        .then(data => {
            if (data.sucesso) {
                renderizarDetalhes(data);
            } else {
                document.getElementById('modalDetalhesBody').innerHTML = `
                    <div class="alert alert-danger">Erro: ${data.erro}</div>
                `;
            }
        })
        .catch(err => {
            document.getElementById('modalDetalhesBody').innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    Erro ao carregar detalhes: ${err.message}
                </div>
            `;
        });
}

function renderizarDetalhes(data) {
    const v = data.validacao;
    const matches = data.matches;
    const divergencias = data.divergencias;

    const statusMap = {
        'aprovado': '<span class="badge bg-success">Aprovado</span>',
        'bloqueado': '<span class="badge bg-danger">Bloqueado</span>',
        'consolidado': '<span class="badge bg-primary">Consolidado</span>',
        'finalizado_odoo': '<span class="badge bg-success">Finalizado</span>',
        'pendente': '<span class="badge bg-secondary">Pendente</span>',
        'erro': '<span class="badge bg-danger">Erro</span>'
    };
    const statusBadge = statusMap[v.status] || `<span class="badge bg-secondary">${v.status}</span>`;

    let html = `
        <div class="row mb-4">
            <div class="col-md-6">
                <h6>Dados da NF ${statusBadge}</h6>
                <table class="table table-sm">
                    <tr><td>Numero:</td><td><strong>${v.numero_nf || v.odoo_dfe_id}</strong></td></tr>
                    <tr><td>Data:</td><td>${v.data_nf || 'N/A'}</td></tr>
                    <tr><td>Valor:</td><td>R$ ${parseFloat(v.valor_total_nf)?.toFixed(2) || 'N/A'}</td></tr>
                    <tr><td>Itens:</td><td>${v.total_itens || 'N/A'}</td></tr>
                </table>
            </div>
            <div class="col-md-6">
                <h6>Fornecedor</h6>
                <table class="table table-sm">
                    <tr><td>Razao:</td><td><strong>${v.razao_fornecedor || 'N/A'}</strong></td></tr>
                    <tr><td>CNPJ:</td><td>${v.cnpj_fornecedor}</td></tr>
                </table>
            </div>
        </div>
    `;

    if (v.status === 'finalizado_odoo') {
        html += `
            <div class="alert alert-success mb-4">
                <h6 class="mb-2"><i class="fas fa-check-circle me-2"></i>DFE Finalizado no Odoo</h6>
                <p class="mb-1">Este DFE ja possui PO vinculado diretamente no Odoo e nao requer validacao manual.</p>
                <table class="table table-sm table-borderless mt-2 mb-0">
                    ${v.odoo_po_vinculado_name ? `<tr><td><strong>PO Vinculado:</strong></td><td>${v.odoo_po_vinculado_name}</td></tr>` : ''}
                    ${v.odoo_po_fiscal_name ? `<tr><td><strong>PO Fiscal:</strong></td><td>${v.odoo_po_fiscal_name}</td></tr>` : ''}
                    ${v.pos_vinculados_importados_em ? `<tr><td><strong>Importado em:</strong></td><td>${v.pos_vinculados_importados_em}</td></tr>` : ''}
                    <tr><td><strong>Total Itens:</strong></td><td>${v.total_itens || 'N/A'}</td></tr>
                </table>
            </div>
        `;
        if (matches.length === 0) {
            document.getElementById('modalDetalhesBody').innerHTML = html;
            return;
        }
    }

    if (v.status === 'consolidado' && v.po_consolidado_name) {
        html += `
            <div class="alert alert-primary mb-4">
                <h6 class="mb-2"><i class="fas fa-object-group me-2"></i>PO Consolidado</h6>
                <p class="mb-0">PO Conciliador: <strong>${v.po_consolidado_name}</strong></p>
                ${v.consolidado_em ? `<small class="text-muted">Consolidado em: ${v.consolidado_em}</small>` : ''}
            </div>
        `;
    }

    // Secao de Recebimento Fisico
    if (data.recebimento) {
        const r = data.recebimento;
        let recebBadge = '';
        let recebIcon = 'fas fa-boxes';

        if (r.odoo_status === 'done' || r.status === 'processado') {
            recebBadge = '<span class="badge bg-success ms-2">Recebido</span>';
            recebIcon = 'fas fa-check-double text-success';
        } else if (r.status === 'processando') {
            recebBadge = '<span class="badge bg-info ms-2">Processando</span>';
            recebIcon = 'fas fa-spinner fa-spin text-info';
        } else if (r.status === 'erro') {
            recebBadge = '<span class="badge bg-danger ms-2">Erro</span>';
            recebIcon = 'fas fa-exclamation-circle text-danger';
        } else if (r.status === 'pendente') {
            recebBadge = '<span class="badge bg-warning ms-2">Pendente</span>';
            recebIcon = 'fas fa-clock text-warning';
        } else if (r.odoo_status === 'assigned') {
            recebBadge = '<span class="badge bg-primary ms-2">Pronto Receber</span>';
            recebIcon = 'fas fa-box-open text-primary';
        } else if (r.odoo_status) {
            recebBadge = `<span class="badge bg-secondary ms-2">${r.odoo_status}</span>`;
        }

        html += `
            <div class="row mb-4">
                <div class="col-12">
                    <div class="card border-info">
                        <div class="card-header bg-info bg-opacity-10">
                            <h6 class="mb-0">
                                <i class="${recebIcon} me-2"></i>Recebimento Fisico ${recebBadge}
                            </h6>
                        </div>
                        <div class="card-body py-2">
                            <div class="row">
                                <div class="col-md-4">
                                    <small class="text-muted">Picking</small>
                                    <div><strong>${r.picking_name || 'N/A'}</strong></div>
                                </div>
                                <div class="col-md-4">
                                    <small class="text-muted">Status Odoo</small>
                                    <div>${r.odoo_status || 'N/A'}</div>
                                </div>
                                <div class="col-md-4">
                                    <small class="text-muted">Processado em</small>
                                    <div>${r.processado_em || '-'}</div>
                                </div>
                            </div>
                            ${r.erro_mensagem ? `
                                <div class="alert alert-danger mt-2 mb-0 py-1 small">
                                    <i class="fas fa-exclamation-triangle me-1"></i>${r.erro_mensagem}
                                </div>
                            ` : ''}
                            ${r.picking_id ? `
                                <a href="https://odoo.nacomgoya.com.br/web#id=${r.picking_id}&model=stock.picking&view_type=form"
                                   class="btn btn-sm btn-outline-info mt-2" target="_blank">
                                    <i class="fas fa-external-link-alt me-1"></i>Abrir no Odoo
                                </a>
                            ` : ''}
                        </div>
                    </div>
                </div>
            </div>
        `;
    } else if (v.status === 'consolidado' || v.status === 'finalizado_odoo') {
        html += `
            <div class="row mb-4">
                <div class="col-12">
                    <div class="alert alert-secondary mb-0">
                        <i class="fas fa-boxes me-2"></i>
                        <strong>Recebimento Fisico:</strong> Aguardando picking no Odoo ou recebimento nao iniciado.
                    </div>
                </div>
            </div>
        `;
    }

    html += `<h6>Resultado do Match (${matches.length} itens)</h6>
        <table class="table table-sm table-bordered">
            <thead class="table-light">
                <tr>
                    <th>Produto</th>
                    <th class="text-end">Qtd NF</th>
                    <th class="text-end">Preco NF</th>
                    <th>PO</th>
                    <th class="text-end">Qtd PO</th>
                    <th>Data PO</th>
                    <th class="text-center">Status</th>
                </tr>
            </thead>
            <tbody>
    `;

    for (const m of matches) {
        let matchBadge = '';
        if (m.status_match === 'match') {
            matchBadge = '<span class="badge bg-success">Match</span>';
        } else if (m.status_match === 'sem_depara') {
            matchBadge = '<span class="badge bg-secondary">Sem De-Para</span>';
        } else if (m.status_match === 'sem_po') {
            matchBadge = '<span class="badge bg-warning">Sem PO</span>';
        } else {
            matchBadge = `<span class="badge bg-danger">${m.status_match}</span>`;
        }

        html += `
            <tr>
                <td>
                    <code>${m.cod_produto_fornecedor || 'N/A'}</code>
                    ${m.cod_produto_interno ? `<i class="fas fa-arrow-right mx-1"></i><code class="text-success">${m.cod_produto_interno}</code>` : ''}
                    <br>
                    <small class="${m.nome_produto_interno ? 'text-success' : ''}">
                        ${m.nome_produto_interno || m.nome_produto || ''}
                    </small>
                </td>
                <td class="text-end">${m.qtd_nf != null ? parseFloat(m.qtd_nf).toFixed(2) : 'N/A'}</td>
                <td class="text-end">${m.preco_nf != null ? parseFloat(m.preco_nf).toFixed(4) : 'N/A'}</td>
                <td>${m.odoo_po_name || '-'}</td>
                <td class="text-end">${m.qtd_po != null ? parseFloat(m.qtd_po).toFixed(2) : '-'}</td>
                <td>${m.data_po || '-'}</td>
                <td class="text-center">${matchBadge}</td>
            </tr>
        `;
    }

    html += '</tbody></table>';

    if (divergencias.length > 0) {
        html += `
            <h6 class="mt-4">Divergencias (${divergencias.length})</h6>
            <table class="table table-sm table-bordered">
                <thead class="table-light">
                    <tr>
                        <th>Tipo</th>
                        <th>Produto</th>
                        <th>NF</th>
                        <th>PO</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
        `;

        for (const d of divergencias) {
            html += `
                <tr>
                    <td><span class="badge bg-warning">${d.tipo_divergencia}</span></td>
                    <td>${d.nome_produto || d.cod_produto_fornecedor}</td>
                    <td>${d.valor_nf || 'N/A'}</td>
                    <td>${d.valor_po || 'N/A'}</td>
                    <td>${d.status}</td>
                </tr>
            `;
        }

        html += '</tbody></table>';
    }

    document.getElementById('modalDetalhesBody').innerHTML = html;
}

// =============================================================================
// ACOES: VALIDAR, CONSOLIDAR, REVERTER
// =============================================================================

function validarNf(dfeId) {
    if (!confirm('Validar esta NF contra os POs do fornecedor?')) return;

    fetch(`/api/recebimento/validar-nf-po/${dfeId}`, {method: 'POST'})
        .then(r => r.json())
        .then(data => {
            if (data.status === 'aprovado') {
                alert('NF aprovada! Todos os itens com match.');
            } else if (data.status === 'bloqueado') {
                alert('NF bloqueada: ' + data.mensagem);
            } else {
                alert('Erro: ' + data.mensagem);
            }
            location.reload();
        });
}

function consolidarPos(validacaoId) {
    if (!confirm('Consolidar os POs desta NF?\n\nEsta acao ira:\n- Unificar POs em 1 principal\n- Criar POs de saldo se necessario\n- Cancelar POs vazios')) return;

    fetch(`/api/recebimento/consolidar-pos/${validacaoId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || ''
        },
        body: JSON.stringify({})
    })
        .then(r => r.json())
        .then(data => {
            if (data.sucesso) {
                alert(`Consolidacao concluida!\n\nPO principal: ${data.po_consolidado_name}\nSaldos criados: ${data.pos_saldo_criados?.length || 0}`);
                location.reload();
            } else {
                alert('Erro: ' + data.erro);
            }
        });
}

function reverterConsolidacao(validacaoId) {
    if (!confirm('ATENCAO: Reverter consolidacao?\n\nEsta acao pode nao ser 100% reversivel.')) return;

    fetch(`/api/recebimento/reverter-consolidacao/${validacaoId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || ''
        },
        body: JSON.stringify({})
    })
        .then(r => r.json())
        .then(data => {
            if (data.sucesso) {
                alert('Consolidacao revertida!');
                location.reload();
            } else {
                alert('Erro: ' + data.erro);
            }
        });
}

// =============================================================================
// EXECUTAR VALIDACAO (com periodo selecionavel)
// =============================================================================

function confirmarValidacao() {
    const dataDe = document.getElementById('validacaoDataDe').value;
    const dataAte = document.getElementById('validacaoDataAte').value;

    if (!dataDe || !dataAte) {
        alert('Selecione o período (De e Até)');
        return;
    }

    const de = new Date(dataDe);
    const ate = new Date(dataAte);
    const diffDias = (ate - de) / (1000 * 60 * 60 * 24);
    if (diffDias < 0) {
        alert('Data "De" deve ser anterior à data "Até"');
        return;
    }
    if (diffDias > 90) {
        alert('Período máximo: 90 dias');
        return;
    }

    const btn = document.getElementById('btnConfirmarValidacao');
    const originalHtml = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Executando...';
    btn.disabled = true;

    fetch('/api/recebimento/executar-validacao', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ data_de: dataDe, data_ate: dataAte })
    })
    .then(r => r.json())
    .then(data => {
        if (data.sucesso) {
            const res = data.resultado || {};
            const syncPo = res.sync_pos_vinculados || {};
            const msg = [
                'Validação executada com sucesso!',
                '',
                `POs vinculados (sync): ${syncPo.dfes_atualizados || 0} atualizados`,
                `DFEs processados: ${res.dfes_processados || 0}`,
                `Fase 1 - Aprovados: ${res.fase1_fiscal?.dfes_aprovados || 0}`,
                `Fase 1 - Bloqueados: ${res.fase1_fiscal?.dfes_bloqueados || 0}`,
                `Fase 2 - Aprovados: ${res.fase2_nf_po?.dfes_aprovados || 0}`,
                `Fase 2 - Bloqueados: ${res.fase2_nf_po?.dfes_bloqueados || 0}`
            ].join('\n');
            alert(msg);
            location.reload();
        } else {
            alert('Erro: ' + (data.erro || 'Erro desconhecido'));
            btn.innerHTML = originalHtml;
            btn.disabled = false;
        }
    })
    .catch(err => {
        alert('Erro de conexão: ' + err.message);
        btn.innerHTML = originalHtml;
        btn.disabled = false;
    });
}

function initValidacaoDatas() {
    const hoje = new Date();
    const seteDiasAtras = new Date();
    seteDiasAtras.setDate(hoje.getDate() - 7);

    const inputDe = document.getElementById('validacaoDataDe');
    const inputAte = document.getElementById('validacaoDataAte');

    if (inputDe && inputAte) {
        inputAte.value = hoje.toISOString().split('T')[0];
        inputDe.value = seteDiasAtras.toISOString().split('T')[0];
    }
}

// =============================================================================
// ACCORDION DE DIVERGENCIAS INLINE
// =============================================================================

/**
 * Toggle accordion de divergencias para uma validacao.
 * Faz lazy load via API na primeira expansao, usa cache depois.
 */
function toggleDivergencias(validacaoId) {
    const row = document.querySelector(`tr[data-id="${validacaoId}"]`);
    const divRow = document.getElementById(`divRow-${validacaoId}`);
    const divBody = document.getElementById(`divBody-${validacaoId}`);

    if (!divRow || !divBody) return;

    const isExpanded = row.classList.contains('rec-row-expanded');

    if (isExpanded) {
        // Colapsar
        row.classList.remove('rec-row-expanded');
        divRow.classList.add('d-none');
        return;
    }

    // Expandir
    row.classList.add('rec-row-expanded');
    divRow.classList.remove('d-none');

    // Se ja tem cache, renderizar direto
    if (divergenciasCache[validacaoId]) {
        renderDivergenciasInline(divBody, divergenciasCache[validacaoId]);
        return;
    }

    // Loading
    divBody.innerHTML = `
        <div class="text-center py-3">
            <i class="fas fa-spinner fa-spin me-2"></i>Carregando divergencias...
        </div>
    `;

    // Fetch via API
    fetch(`/api/recebimento/validacoes-nf-po/${validacaoId}`)
        .then(r => r.json())
        .then(data => {
            if (!data.sucesso) {
                divBody.innerHTML = `
                    <div class="alert alert-danger m-2 mb-0">Erro: ${data.erro}</div>
                `;
                return;
            }

            // Guardar dados da validacao para contexto dos modais
            const validacaoData = {
                divergencias: data.divergencias,
                validacao: data.validacao
            };
            divergenciasCache[validacaoId] = validacaoData;
            renderDivergenciasInline(divBody, validacaoData);
        })
        .catch(err => {
            divBody.innerHTML = `
                <div class="alert alert-danger m-2 mb-0">
                    <i class="fas fa-exclamation-triangle me-1"></i>Erro: ${err.message}
                </div>
            `;
        });
}

/**
 * Renderiza tabela de divergencias dentro do container do accordion.
 * @param {HTMLElement} container - Elemento onde renderizar
 * @param {object} data - {divergencias: [...], validacao: {...}}
 */
function renderDivergenciasInline(container, data) {
    const divergencias = data.divergencias || [];
    const validacao = data.validacao || {};

    if (divergencias.length === 0) {
        container.innerHTML = `
            <div class="text-center text-muted py-3">
                <i class="fas fa-check-circle text-success me-2"></i>Nenhuma divergencia
            </div>
        `;
        return;
    }

    // Badge helpers — tipoBadge recebe objeto divergencia para exibir campo_label
    const tipoBadge = (d) => {
        const badgeMap = {
            'sem_depara': '<span class="badge bg-secondary">Sem De-Para</span>',
            'sem_po': '<span class="badge bg-secondary">Sem PO</span>',
            'preco': '<span class="badge bg-danger">Preco</span>',
            'quantidade': '<span class="badge bg-warning text-dark">Qtd</span>',
            'quantidade_tolerancia': '<span class="badge bg-info">Qtd Tol.</span>',
            'data_entrega': '<span class="badge bg-warning text-dark">Data</span>'
        };
        const badge = badgeMap[d.tipo_divergencia] || `<span class="badge bg-secondary">${d.tipo_divergencia}</span>`;
        const label = d.campo_label ? `<br><small class="text-muted">${d.campo_label}</small>` : '';
        return badge + label;
    };

    const statusBadge = (status) => {
        const map = {
            'pendente': '<span class="badge bg-warning text-dark">Pendente</span>',
            'aprovada': '<span class="badge bg-success">Aprovada</span>',
            'rejeitada': '<span class="badge bg-danger">Rejeitada</span>'
        };
        return map[status] || `<span class="badge bg-secondary">${status}</span>`;
    };

    // Toolbar com links Odoo / XML / PDF
    const dfeId = validacao.odoo_dfe_id;
    const numeroNf = validacao.numero_nf || dfeId;
    const odooUrl = dfeId
        ? `https://odoo.nacomgoya.com.br/web#id=${dfeId}&model=l10n_br_ciel_it_account.dfe&view_type=form`
        : '';

    let html = `
        <div class="rec-div-toolbar d-flex align-items-center gap-2 px-3 py-2 border-bottom">
            <span class="text-muted small me-auto">
                <i class="fas fa-file-invoice me-1"></i>NF ${numeroNf} — ${divergencias.length} divergencia(s)
            </span>
            <div class="btn-group btn-group-sm">
                ${odooUrl ? `<a href="${odooUrl}" target="_blank" class="btn btn-outline-secondary" title="Abrir DFe no Odoo">
                    <i class="fas fa-external-link-alt"></i> Odoo
                </a>` : ''}
                ${dfeId ? `<button onclick="downloadXml(${dfeId})" class="btn btn-outline-secondary" title="Download XML">
                    <i class="fas fa-file-code"></i> XML
                </button>
                <button onclick="downloadPdf(${dfeId})" class="btn btn-outline-secondary" title="Download DANFE">
                    <i class="fas fa-file-pdf"></i> PDF
                </button>` : ''}
            </div>
        </div>
        <div class="p-2">
            <table class="table table-sm table-bordered rec-div-table mb-0">
                <thead>
                    <tr>
                        <th>Produto</th>
                        <th class="text-center">Tipo</th>
                        <th>NF vs PO</th>
                        <th class="text-center">Dif%</th>
                        <th class="text-center">Status</th>
                        <th class="text-center rec-div-actions">Acoes</th>
                    </tr>
                </thead>
                <tbody>
    `;

    for (const d of divergencias) {
        const isResolvida = d.status !== 'pendente';
        const rowClass = isResolvida ? 'text-muted' : '';

        // Produto display
        const prodHtml = d.cod_produto_fornecedor
            ? `<code>${d.cod_produto_fornecedor}</code>` +
              (d.cod_produto_interno ? ` <i class="fas fa-arrow-right text-muted mx-1"></i> <code class="text-success">${d.cod_produto_interno}</code>` : '') +
              `<br><small class="${d.nome_produto_interno ? 'text-success' : 'text-muted'}">${d.nome_produto_interno || d.nome_produto || ''}</small>`
            : `<small class="text-muted">${d.nome_produto || 'N/A'}</small>`;

        // NF vs PO — descricao contextual por tipo de divergencia
        let nfVsPo = '';
        if (d.tipo_divergencia === 'sem_depara') {
            nfVsPo = '<small class="text-muted">Codigo fornecedor nao cadastrado no De-Para</small>';
        } else if (d.tipo_divergencia === 'sem_po') {
            nfVsPo = '<small class="text-muted">Nenhum PO encontrado para o produto</small>';
        } else if (d.valor_nf || d.valor_po) {
            nfVsPo = `<small class="text-muted">NF:</small> <strong>${d.valor_nf || 'N/A'}</strong>`;
            nfVsPo += `<br><small class="text-muted">PO:</small> <strong>${d.valor_po || 'N/A'}</strong>`;
            if (d.odoo_po_name) {
                nfVsPo += `<br><small class="text-muted">${d.odoo_po_name}</small>`;
            }
        } else {
            nfVsPo = '<span class="text-muted">-</span>';
        }

        // Dif%
        const difHtml = d.diferenca_percentual != null
            ? `<span class="${Math.abs(d.diferenca_percentual) > 5 ? 'text-danger fw-bold' : ''}">${d.diferenca_percentual}%</span>`
            : '-';

        // Status com justificativa quando resolvida
        let statusHtml = statusBadge(d.status);
        if (isResolvida) {
            if (d.resolucao) {
                statusHtml += `<br><small class="text-muted">${d.resolucao}</small>`;
            }
            if (d.justificativa) {
                statusHtml += `<br><small class="text-muted fst-italic">"${d.justificativa}"</small>`;
            }
            if (d.resolvido_por) {
                statusHtml += `<br><small class="text-muted">por ${d.resolvido_por}</small>`;
            }
        }

        // Acoes - apenas para pendentes
        let acoesHtml = '';
        if (!isResolvida) {
            acoesHtml = buildAcoesHtml(d, validacao);
        }

        html += `
            <tr class="${rowClass}">
                <td>${prodHtml}</td>
                <td class="text-center">${tipoBadge(d)}</td>
                <td>${nfVsPo}</td>
                <td class="text-center">${difHtml}</td>
                <td class="text-center">${statusHtml}</td>
                <td class="text-center rec-div-actions">${acoesHtml}</td>
            </tr>
        `;
    }

    html += '</tbody></table></div>';
    container.innerHTML = html;
}

/**
 * Monta botoes de acao contextuais para uma divergencia no accordion.
 * Passa dados como parametro para as funcoes de modal (nao depende de data-* do DOM).
 */
function buildAcoesHtml(d, validacao) {
    const podeAprovar = ['quantidade_tolerancia', 'data_entrega'].includes(d.tipo_divergencia);

    // Dados para passar aos modais (JSON-safe, escapado)
    const dadosDepara = JSON.stringify({
        qtdNf: d.qtd_nf || 0,
        precoNf: d.preco_nf || 0,
        umNf: d.um_nf || '',
        codProdutoFornecedor: d.cod_produto_fornecedor || '',
        nomeProduto: d.nome_produto || ''
    }).replace(/'/g, "\\'").replace(/"/g, '&quot;');

    const dadosAprovar = JSON.stringify({
        numeroNf: validacao.numero_nf || '-',
        razaoFornecedor: d.razao_fornecedor || validacao.razao_fornecedor || '',
        cnpjFornecedor: d.cnpj_fornecedor || validacao.cnpj_fornecedor || '',
        codProdutoFornecedor: d.cod_produto_fornecedor || '-',
        codProdutoInterno: d.cod_produto_interno || '-',
        nomeProduto: d.nome_produto_interno || d.nome_produto || '-',
        tipoDivergencia: d.tipo_divergencia || '',
        valorNf: d.valor_nf || '-',
        valorPo: d.valor_po || '-',
        odooPoName: d.odoo_po_name || ''
    }).replace(/'/g, "\\'").replace(/"/g, '&quot;');

    let btns = '<div class="btn-group btn-group-sm">';

    if (d.tipo_divergencia === 'sem_depara') {
        btns += `<button class="btn btn-primary" onclick='criarDepara(${d.id}, JSON.parse(this.dataset.dados))' data-dados="${dadosDepara}" title="Criar De-Para">
            <i class="fas fa-exchange-alt"></i> De-Para
        </button>`;
    } else if (d.tipo_divergencia === 'sem_po') {
        btns += `<button class="btn btn-info" onclick="verPosCandidatos(${d.odoo_dfe_id})" title="Ver POs candidatos">
            <i class="fas fa-search"></i> Ver POs
        </button>`;
    } else if (d.tipo_divergencia === 'preco' || d.tipo_divergencia === 'quantidade') {
        btns += `<button class="btn btn-info" onclick="verPosCandidatos(${d.odoo_dfe_id})" title="Ver POs candidatos">
            <i class="fas fa-search"></i>
        </button>`;
        if (d.odoo_po_id) {
            btns += `<a href="https://odoo.nacomgoya.com.br/web#id=${d.odoo_po_id}&model=purchase.order&view_type=form" target="_blank" class="btn btn-outline-secondary" title="Editar PO no Odoo">
                <i class="fas fa-edit"></i>
            </a>`;
        }
    } else if (podeAprovar) {
        btns += `<button class="btn btn-success" onclick='abrirModalAprovar(${d.id}, JSON.parse(this.dataset.dados))' data-dados="${dadosAprovar}" title="Aprovar">
            <i class="fas fa-check"></i>
        </button>`;
        btns += `<button class="btn btn-danger" onclick="rejeitarDivergencia(${d.id})" title="Rejeitar">
            <i class="fas fa-times"></i>
        </button>`;
    }

    btns += '</div>';
    return btns;
}

// =============================================================================
// INICIALIZACAO
// =============================================================================

document.addEventListener('DOMContentLoaded', function() {
    modalDetalhes = new bootstrap.Modal(document.getElementById('modalDetalhes'));
    initModaisCompartilhados();
    initValidacaoDatas();
});
