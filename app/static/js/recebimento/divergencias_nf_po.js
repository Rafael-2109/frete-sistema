/**
 * Divergencias NF x PO - JavaScript
 *
 * Funcionalidades:
 * - Modal POs Candidatos (comparacao NF vs PO)
 * - Modal Criar De-Para
 * - Modal Aprovar Divergencia
 * - Executar Validacao Manual
 * - Download XML/PDF
 */

// =============================================================================
// VARIAVEIS GLOBAIS
// =============================================================================

let modalCriarDepara, modalAprovar, modalPosCandidatos;
let itemAtual = {};

// Inicializar modais quando DOM estiver pronto
document.addEventListener('DOMContentLoaded', function() {
    modalCriarDepara = new bootstrap.Modal(document.getElementById('modalCriarDepara'));
    modalAprovar = new bootstrap.Modal(document.getElementById('modalAprovar'));
    modalPosCandidatos = new bootstrap.Modal(document.getElementById('modalPosCandidatos'));

    // Event listener para atualizar simulacao de conversao
    const fatorInput = document.getElementById('fatorConversaoModal');
    if (fatorInput) {
        fatorInput.addEventListener('input', atualizarSimulacaoConversao);
    }
});

// =============================================================================
// FUNCOES DE FORMATACAO
// =============================================================================

function formatarMoeda(valor) {
    if (valor == null || isNaN(valor)) return '-';
    return 'R$ ' + parseFloat(valor).toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2});
}

function formatarMoeda4(valor) {
    if (valor == null || isNaN(valor)) return '-';
    return 'R$ ' + parseFloat(valor).toLocaleString('pt-BR', {minimumFractionDigits: 4, maximumFractionDigits: 4});
}

function formatarCnpj(cnpj) {
    if (!cnpj) return '-';
    cnpj = cnpj.replace(/\D/g, '');
    if (cnpj.length === 14) {
        return cnpj.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, '$1.$2.$3/$4-$5');
    }
    return cnpj;
}

function formatarNumero(valor, decimais = 2) {
    if (valor == null || isNaN(valor)) return '-';
    return parseFloat(valor).toLocaleString('pt-BR', {minimumFractionDigits: decimais, maximumFractionDigits: decimais});
}

// =============================================================================
// POS CANDIDATOS - MODAL PRINCIPAL
// =============================================================================

function verPosCandidatos(dfeId) {
    // Mostrar modal com loading
    document.getElementById('tabelaItensNf').innerHTML =
        '<tr><td colspan="9" class="text-center py-3"><i class="fas fa-spinner fa-spin me-2"></i>Carregando...</td></tr>';
    document.getElementById('listaPosCandidatos').innerHTML =
        '<div class="text-center py-3"><i class="fas fa-spinner fa-spin me-2"></i>Buscando POs do fornecedor...</div>';

    modalPosCandidatos.show();

    // Buscar dados do endpoint
    fetch(`/api/recebimento/dfe/${dfeId}/pos-candidatos`)
        .then(r => r.json())
        .then(data => {
            if (!data.sucesso) {
                document.getElementById('listaPosCandidatos').innerHTML =
                    `<div class="alert alert-danger m-3">Erro: ${data.erro}</div>`;
                return;
            }

            // Preencher dados da NF
            document.getElementById('posNfNumero').textContent = `NF ${data.dfe.numero_nf || '-'}`;
            document.getElementById('posFornecedor').textContent = data.dfe.razao_fornecedor || '-';
            document.getElementById('posCnpj').textContent = formatarCnpj(data.dfe.cnpj_fornecedor || '');
            document.getElementById('posDataEmissao').textContent = data.dfe.data_emissao || '-';
            document.getElementById('posValorTotal').textContent = formatarMoeda(data.dfe.valor_total);
            document.getElementById('posQtdItens').textContent = data.itens_nf.length;

            // Resumo
            document.getElementById('resumoItensNf').textContent = data.resumo.itens_nf;
            document.getElementById('resumoItensDepara').textContent = data.resumo.itens_com_depara;
            document.getElementById('resumoItensComPo').textContent = data.resumo.itens_com_po;
            document.getElementById('resumoPosCandidatos').textContent = data.resumo.pos_candidatos;

            // Tabela de itens da NF
            renderizarTabelaItensNf(data.itens_nf, data.pos_candidatos);

            // Lista de POs candidatos
            renderizarPosCandidatos(data.pos_candidatos, data.itens_nf);
        })
        .catch(err => {
            document.getElementById('listaPosCandidatos').innerHTML =
                `<div class="alert alert-danger m-3">Erro de conexao: ${err.message}</div>`;
        });
}

function renderizarTabelaItensNf(itensNf, posCandidatos) {
    if (!itensNf || itensNf.length === 0) {
        document.getElementById('tabelaItensNf').innerHTML =
            '<tr><td colspan="9" class="text-center text-muted py-3">Nenhum item encontrado</td></tr>';
        return;
    }

    let html = '';
    itensNf.forEach((item, idx) => {
        // Verificar se tem match em algum PO
        let poMatch = '-';
        for (const po of posCandidatos) {
            const linhaMatch = po.linhas.find(l => l.match_item_nf === item.cod_produto_fornecedor);
            if (linhaMatch) {
                poMatch = `<span class="badge bg-success">${po.po_name}</span>`;
                break;
            }
        }

        const temConversao = item.fator_conversao && item.fator_conversao !== 1;
        const rowClass = item.tem_depara ? '' : 'table-warning';

        html += `
            <tr class="${rowClass}">
                <td>${item.nitem || (idx + 1)}</td>
                <td><code class="text-primary">${item.cod_produto_fornecedor || '-'}</code></td>
                <td class="text-truncate" style="max-width: 180px;" title="${item.nome_produto}">${item.nome_produto || '-'}</td>
                <td class="text-end">${formatarNumero(item.qtd_nf, 3)}</td>
                <td class="text-end">${formatarMoeda4(item.preco_nf)}</td>
                <td class="text-end ${temConversao ? 'text-info fw-bold' : ''}">${formatarNumero(item.qtd_convertida, 3)}</td>
                <td class="text-end ${temConversao ? 'text-info fw-bold' : ''}">${formatarMoeda4(item.preco_convertido)}</td>
                <td>
                    ${item.tem_depara
                        ? `<span class="badge bg-success"><i class="fas fa-check"></i> ${item.cod_produto_interno}</span>
                           ${temConversao ? `<br><small class="text-muted">Fator: ${item.fator_conversao}</small>` : ''}`
                        : '<span class="badge bg-danger"><i class="fas fa-times"></i></span>'
                    }
                </td>
                <td class="text-center">${poMatch}</td>
            </tr>
        `;
    });

    document.getElementById('tabelaItensNf').innerHTML = html;
}

function renderizarPosCandidatos(posCandidatos, itensNf) {
    if (!posCandidatos || posCandidatos.length === 0) {
        document.getElementById('listaPosCandidatos').innerHTML = `
            <div class="alert alert-warning m-3">
                <i class="fas fa-exclamation-triangle me-2"></i>
                Nenhum PO encontrado para este fornecedor com saldo disponivel.
                <br><small>Verifique se existe um Pedido de Compra no Odoo para este fornecedor.</small>
            </div>
        `;
        return;
    }

    let html = '<div class="accordion" id="accordionPos">';

    posCandidatos.forEach((po, idx) => {
        const hasMatch = po.qtd_linhas_match > 0;
        const headerClass = hasMatch ? 'bg-success text-white' : 'bg-light';
        const matchBadge = hasMatch
            ? `<span class="badge bg-light text-success">${po.qtd_linhas_match} match(es)</span>`
            : '<span class="badge bg-secondary">Sem match</span>';

        html += `
            <div class="accordion-item">
                <h2 class="accordion-header">
                    <button class="accordion-button ${idx > 0 ? 'collapsed' : ''} ${headerClass}"
                            type="button"
                            data-bs-toggle="collapse"
                            data-bs-target="#collapsePo${idx}">
                        <div class="d-flex justify-content-between w-100 me-3">
                            <div>
                                <strong>${po.po_name}</strong>
                                ${matchBadge}
                            </div>
                            <div>
                                <span class="me-3"><small>Pedido:</small> ${po.data_pedido || '-'}</span>
                                <span class="me-3"><small>Previsto:</small> ${po.data_prevista || '-'}</span>
                                <span><small>Total:</small> <strong>${formatarMoeda(po.valor_total)}</strong></span>
                            </div>
                        </div>
                    </button>
                </h2>
                <div id="collapsePo${idx}" class="accordion-collapse collapse ${idx === 0 ? 'show' : ''}">
                    <div class="accordion-body p-0">
                        <table class="table table-sm table-bordered mb-0 table-hover">
                            <thead class="table-dark">
                                <tr>
                                    <th rowspan="2" style="vertical-align: middle;">Produto PO</th>
                                    <th colspan="3" class="text-center bg-secondary">PO (Pedido)</th>
                                    <th colspan="3" class="text-center bg-primary">NF (Convertido)</th>
                                    <th colspan="2" class="text-center bg-warning text-dark">Divergencia</th>
                                    <th rowspan="2" class="text-center" style="vertical-align: middle;">Status</th>
                                </tr>
                                <tr>
                                    <th class="text-end bg-secondary">Saldo</th>
                                    <th class="text-end bg-secondary">Preco</th>
                                    <th class="text-center bg-secondary">Entrega</th>
                                    <th class="text-end bg-primary">Qtd</th>
                                    <th class="text-end bg-primary">Preco</th>
                                    <th class="text-center bg-primary">-</th>
                                    <th class="text-end bg-warning text-dark">Qtd %</th>
                                    <th class="text-end bg-warning text-dark">Preco %</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${renderizarLinhasPo(po.linhas)}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        `;
    });

    html += '</div>';
    document.getElementById('listaPosCandidatos').innerHTML = html;
}

function renderizarLinhasPo(linhas) {
    if (!linhas || linhas.length === 0) {
        return '<tr><td colspan="10" class="text-center text-muted py-2">Nenhuma linha</td></tr>';
    }

    return linhas.map(linha => {
        const hasMatch = linha.match_item_nf && linha.divergencias;
        const saldoClass = linha.saldo > 0 ? 'text-success' : 'text-danger';

        // Dados do PO
        const saldoPo = formatarNumero(linha.saldo, 2);
        const precoPo = formatarMoeda4(linha.preco);
        const dataPrevista = linha.data_prevista || '-';

        // Dados da NF (se houver match)
        let qtdNf = '-', precoNf = '-';
        let divQtd = '-', divPreco = '-';
        let statusIcon = '<span class="badge bg-secondary">-</span>';

        if (hasMatch) {
            const div = linha.divergencias;
            qtdNf = formatarNumero(div.qtd_nf_convertida, 2);
            precoNf = formatarMoeda4(div.preco_nf_convertido);

            // Divergencias com cores
            const qtdOk = div.qtd_ok;
            const precoOk = div.preco_ok;
            const qtdClass = qtdOk ? 'text-success' : 'text-danger fw-bold';
            const precoClass = precoOk ? 'text-success' : 'text-danger fw-bold';

            const sinal = (val) => val > 0 ? '+' : '';
            divQtd = `<span class="${qtdClass}">${sinal(div.dif_qtd_pct)}${div.dif_qtd_pct?.toFixed(1)}%</span>`;
            divPreco = `<span class="${precoClass}">${sinal(div.dif_preco_pct)}${div.dif_preco_pct?.toFixed(1)}%</span>`;

            // Status geral
            if (qtdOk && precoOk) {
                statusIcon = '<span class="badge bg-success"><i class="fas fa-check-circle"></i> OK</span>';
            } else if (!qtdOk && !precoOk) {
                statusIcon = '<span class="badge bg-danger"><i class="fas fa-times-circle"></i> Qtd+Preco</span>';
            } else if (!qtdOk) {
                statusIcon = '<span class="badge bg-warning text-dark"><i class="fas fa-exclamation-circle"></i> Qtd</span>';
            } else {
                statusIcon = '<span class="badge bg-warning text-dark"><i class="fas fa-exclamation-circle"></i> Preco</span>';
            }
        }

        const rowClass = hasMatch ? (linha.divergencias.qtd_ok && linha.divergencias.preco_ok ? 'table-success' : 'table-warning') : '';

        return `
            <tr class="${rowClass}">
                <td>
                    <code class="text-primary">${linha.cod_interno || '-'}</code>
                    <br><small class="text-muted text-truncate d-block" style="max-width: 150px;" title="${linha.nome}">${linha.nome || '-'}</small>
                </td>
                <td class="text-end ${saldoClass}"><strong>${saldoPo}</strong></td>
                <td class="text-end">${precoPo}</td>
                <td class="text-center"><small>${dataPrevista}</small></td>
                <td class="text-end">${qtdNf}</td>
                <td class="text-end">${precoNf}</td>
                <td class="text-center">${hasMatch ? `<small class="text-muted">${linha.match_item_nf}</small>` : '-'}</td>
                <td class="text-end">${divQtd}</td>
                <td class="text-end">${divPreco}</td>
                <td class="text-center">${statusIcon}</td>
            </tr>
        `;
    }).join('');
}

// =============================================================================
// DOWNLOAD XML/PDF
// =============================================================================

function downloadXml(dfeId) {
    window.open(`/api/recebimento/dfe/${dfeId}/xml`, '_blank');
}

function downloadPdf(dfeId) {
    window.open(`/api/recebimento/dfe/${dfeId}/pdf`, '_blank');
}

// =============================================================================
// MODAL APROVAR DIVERGENCIA
// =============================================================================

function abrirModalAprovar(id) {
    const row = document.querySelector(`tr[data-id="${id}"]`);
    if (!row) {
        alert('Item nao encontrado');
        return;
    }

    // Preencher dados do modal
    document.getElementById('aprovarDivergenciaId').value = id;
    document.getElementById('aprovarNumeroNf').textContent = row.dataset.numeroNf || '-';
    document.getElementById('aprovarFornecedor').textContent =
        `${row.dataset.razaoFornecedor} (${row.dataset.cnpjFornecedor})`;
    document.getElementById('aprovarCodFornecedor').textContent = row.dataset.codProdutoFornecedor || '-';
    document.getElementById('aprovarCodInterno').textContent =
        row.querySelector('code.text-success')?.textContent || '-';
    document.getElementById('aprovarNomeProduto').textContent = row.dataset.nomeProduto || '-';
    document.getElementById('aprovarValorNf').textContent = row.dataset.valorNf || '-';
    document.getElementById('aprovarValorPo').textContent = row.dataset.valorPo || '-';

    // Tipo divergencia com badge
    const tipo = row.dataset.tipoDivergencia;
    const tipoConfig = {
        'sem_depara': { class: 'bg-secondary', label: 'Sem De-Para' },
        'sem_po': { class: 'bg-secondary', label: 'Sem PO' },
        'preco': { class: 'bg-danger', label: 'Preco Divergente' },
        'quantidade': { class: 'bg-warning text-dark', label: 'Quantidade Divergente' },
        'quantidade_tolerancia': { class: 'bg-info', label: 'Qtd Tolerancia' },
        'data_entrega': { class: 'bg-warning text-dark', label: 'Data Fora do Prazo' }
    };
    const config = tipoConfig[tipo] || { class: 'bg-secondary', label: tipo };
    document.getElementById('aprovarTipoDivergencia').innerHTML =
        `<span class="badge ${config.class}">${config.label}</span>`;

    // PO Name
    const poName = row.dataset.odooPoName;
    if (poName) {
        document.getElementById('aprovarPoName').textContent = poName;
        document.getElementById('aprovarPoNameRow').style.display = 'block';
    } else {
        document.getElementById('aprovarPoNameRow').style.display = 'none';
    }

    // Limpar justificativa
    document.getElementById('aprovarJustificativa').value = '';

    modalAprovar.show();
}

function confirmarAprovar() {
    const id = document.getElementById('aprovarDivergenciaId').value;
    const justificativa = document.getElementById('aprovarJustificativa').value.trim();

    if (!justificativa) {
        alert('Justificativa obrigatoria para aprovacao');
        document.getElementById('aprovarJustificativa').focus();
        return;
    }

    fetch(`/api/recebimento/divergencias-nf-po/${id}/aprovar`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({justificativa: justificativa})
    })
    .then(r => r.json())
    .then(data => {
        if (data.sucesso) {
            modalAprovar.hide();
            location.reload();
        } else {
            alert('Erro: ' + data.erro);
        }
    });
}

// =============================================================================
// REJEITAR DIVERGENCIA
// =============================================================================

function rejeitarDivergencia(id) {
    const justificativa = prompt('Justificativa da rejeicao:');
    if (!justificativa) {
        alert('Justificativa obrigatoria para rejeitar');
        return;
    }

    fetch(`/api/recebimento/divergencias-nf-po/${id}/rejeitar`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({justificativa: justificativa})
    })
    .then(r => r.json())
    .then(data => {
        if (data.sucesso) {
            location.reload();
        } else {
            alert('Erro: ' + data.erro);
        }
    });
}

// =============================================================================
// MODAL CRIAR DE-PARA
// =============================================================================

function criarDepara(id) {
    const row = document.querySelector(`tr[data-id="${id}"]`);
    if (!row) {
        alert('Item nao encontrado');
        return;
    }

    // Guardar dados do item
    itemAtual = {
        qtdNf: parseFloat(row.dataset.qtdNf) || 0,
        precoNf: parseFloat(row.dataset.precoNf) || 0,
        umNf: row.dataset.umNf || '',
        codProdutoFornecedor: row.dataset.codProdutoFornecedor || '',
        nomeProduto: row.dataset.nomeProduto || ''
    };

    // Preencher dados da NF no modal
    document.getElementById('nfCodProdutoFornecedor').textContent = itemAtual.codProdutoFornecedor || '-';
    document.getElementById('nfNomeProduto').textContent = itemAtual.nomeProduto || '-';
    document.getElementById('nfQuantidade').textContent = itemAtual.qtdNf ? itemAtual.qtdNf.toFixed(3) : '-';
    document.getElementById('nfPreco').textContent = itemAtual.precoNf ? `R$ ${itemAtual.precoNf.toFixed(4)}` : '-';
    document.getElementById('nfUmFornecedor').textContent = itemAtual.umNf || '-';

    // Preencher campos do formulario
    document.getElementById('divergenciaId').value = id;
    document.getElementById('codProdutoInternoModal').value = '';
    document.getElementById('nomeProdutoInternoModal').value = '';
    document.getElementById('odooProductIdModal').value = '';
    document.getElementById('umFornecedorModal').value = itemAtual.umNf || '';
    document.getElementById('fatorConversaoModal').value = '1';
    document.getElementById('justificativaModal').value = '';

    // Esconder simulacao
    document.getElementById('simulacaoConversao').style.display = 'none';

    modalCriarDepara.show();
}

function buscarProdutoOdooModal() {
    const cod = document.getElementById('codProdutoInternoModal').value.trim();
    if (!cod) {
        alert('Digite o codigo do produto');
        return;
    }

    const btn = event.target.closest('button');
    const originalHtml = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Buscando...';
    btn.disabled = true;

    fetch(`/api/recebimento/buscar-produto-odoo?cod_produto=${encodeURIComponent(cod)}`)
        .then(r => r.json())
        .then(data => {
            if (data.sucesso) {
                document.getElementById('nomeProdutoInternoModal').value = data.produto.name;
                document.getElementById('odooProductIdModal').value = data.produto.id;
                atualizarSimulacaoConversao();
            } else {
                alert(data.erro);
                document.getElementById('nomeProdutoInternoModal').value = '';
                document.getElementById('odooProductIdModal').value = '';
            }
        })
        .finally(() => {
            btn.innerHTML = originalHtml;
            btn.disabled = false;
        });
}

function atualizarSimulacaoConversao() {
    const fator = parseFloat(document.getElementById('fatorConversaoModal').value) || 1;

    if (itemAtual.qtdNf || itemAtual.precoNf) {
        const qtdConvertida = itemAtual.qtdNf * fator;
        const precoConvertido = itemAtual.precoNf / fator;

        document.getElementById('simQtdOriginal').textContent =
            `${itemAtual.qtdNf.toFixed(3)} ${itemAtual.umNf}`;
        document.getElementById('simQtdConvertida').textContent =
            `${qtdConvertida.toFixed(3)} UN`;
        document.getElementById('simPrecoOriginal').textContent =
            `R$ ${itemAtual.precoNf.toFixed(4)} / ${itemAtual.umNf}`;
        document.getElementById('simPrecoConvertido').textContent =
            `R$ ${precoConvertido.toFixed(4)} / UN`;

        document.getElementById('simulacaoConversao').style.display = 'block';
    }
}

function confirmarCriarDepara() {
    const id = document.getElementById('divergenciaId').value;
    const codProduto = document.getElementById('codProdutoInternoModal').value.trim();

    if (!codProduto) {
        alert('Codigo do produto interno obrigatorio');
        document.getElementById('codProdutoInternoModal').focus();
        return;
    }

    const odooProductId = document.getElementById('odooProductIdModal').value;
    if (!odooProductId) {
        alert('Produto nao validado. Clique em Buscar para validar o codigo.');
        return;
    }

    const dados = {
        cod_produto_interno: codProduto,
        nome_produto_interno: document.getElementById('nomeProdutoInternoModal').value,
        odoo_product_id: parseInt(odooProductId) || null,
        um_fornecedor: document.getElementById('umFornecedorModal').value,
        fator_conversao: parseFloat(document.getElementById('fatorConversaoModal').value) || 1,
        justificativa: document.getElementById('justificativaModal').value
    };

    const btn = event.target;
    const originalHtml = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Criando...';
    btn.disabled = true;

    fetch(`/api/recebimento/divergencias-nf-po/${id}/criar-depara`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(dados)
    })
    .then(r => r.json())
    .then(data => {
        if (data.sucesso) {
            modalCriarDepara.hide();
            alert('De-Para criado com sucesso! A NF sera revalidada automaticamente.');
            location.reload();
        } else {
            alert('Erro: ' + data.erro);
            btn.innerHTML = originalHtml;
            btn.disabled = false;
        }
    })
    .catch((err) => {
        alert('Erro de conexao. Tente novamente.');
        btn.innerHTML = originalHtml;
        btn.disabled = false;
    });
}

// =============================================================================
// EXECUTAR VALIDACAO MANUAL
// =============================================================================

function executarValidacao() {
    const btn = document.getElementById('btnExecutarValidacao');
    const originalHtml = btn.innerHTML;

    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Executando...';
    btn.disabled = true;

    fetch('/api/recebimento/executar-validacao', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'}
    })
    .then(r => r.json())
    .then(data => {
        if (data.sucesso) {
            const res = data.resultado || {};
            const msg = [
                'Validacao executada com sucesso!',
                '',
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
        alert('Erro de conexao: ' + err.message);
        btn.innerHTML = originalHtml;
        btn.disabled = false;
    });
}
