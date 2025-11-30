/* =============================================
   JS: Contas a Receber - Modal Comparativo
   Sistema de Dupla Conferência (Sistema × Odoo)
   ============================================= */

// ============================================
// VARIÁVEIS GLOBAIS
// ============================================
let comparativoContaId = null;
let tiposAbatimentoCache = [];

// ============================================
// FUNÇÕES UTILITÁRIAS
// ============================================

function formatarMoedaComp(valor) {
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(valor || 0);
}

function formatarDataComp(dataStr) {
    if (!dataStr) return '-';
    const data = new Date(dataStr);
    return data.toLocaleDateString('pt-BR');
}

// ============================================
// ABRIR MODAL COMPARATIVO
// ============================================

function abrirModalComparativo(contaId) {
    comparativoContaId = contaId;

    // Resetar conteúdo
    document.getElementById('tbody-abatimentos-sistema').innerHTML =
        '<tr><td colspan="6" class="text-center text-muted"><i class="fas fa-spinner fa-spin"></i> Carregando...</td></tr>';
    document.getElementById('tbody-odoo-abatimentos').innerHTML =
        '<tr><td colspan="6" class="text-center text-muted"><i class="fas fa-spinner fa-spin"></i> Carregando...</td></tr>';
    document.getElementById('tbody-odoo-pagamentos').innerHTML =
        '<tr><td colspan="5" class="text-center text-muted"><i class="fas fa-spinner fa-spin"></i> Carregando...</td></tr>';

    // Limpar formulário de novo abatimento
    limparFormularioAbatimento();

    // Abrir modal
    const modal = new bootstrap.Modal(document.getElementById('modalComparativo'));
    modal.show();

    // Carregar dados
    carregarComparativo(contaId);
}

// ============================================
// CARREGAR DADOS DO COMPARATIVO
// ============================================

function carregarComparativo(contaId) {
    fetch(`/financeiro/contas-receber/api/${contaId}/comparativo`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const conta = data.conta;
                const comp = data.comparativo;

                // Header com dados da conta
                document.getElementById('comp-nf').textContent = `${conta.titulo_nf}-${conta.parcela}`;
                document.getElementById('comp-cliente').textContent = conta.raz_social_red || conta.raz_social || '-';
                document.getElementById('comp-cnpj').textContent = conta.cnpj || '-';

                // Valores da conta
                document.getElementById('comp-valor-original').textContent = formatarMoedaComp(conta.valor_original);
                document.getElementById('comp-valor-titulo').textContent = formatarMoedaComp(conta.valor_titulo);
                document.getElementById('comp-desconto').textContent = formatarMoedaComp(conta.desconto);

                // Status badge
                const statusBadge = document.getElementById('comp-status-badge');
                if (comp.status === 'OK') {
                    statusBadge.className = 'badge ms-2 bg-success';
                    statusBadge.textContent = '✅ Conferido';
                } else {
                    statusBadge.className = 'badge ms-2 bg-danger';
                    statusBadge.textContent = '❌ Divergente';
                }

                // Card comparativo - cor do border
                const cardComp = document.getElementById('card-comparativo');
                cardComp.className = comp.status === 'OK' ? 'card mb-3 border-success' : 'card mb-3 border-danger';

                // Ícone
                document.getElementById('comp-icon').textContent = comp.icon;

                // Totais Sistema vs Odoo
                document.getElementById('comp-total-sistema').textContent = formatarMoedaComp(comp.total_sistema);
                document.getElementById('comp-qtd-sistema').textContent = `(${comp.qtd_abatimentos_sistema} itens)`;

                document.getElementById('comp-total-odoo').textContent = formatarMoedaComp(comp.total_odoo_abatimentos);
                document.getElementById('comp-qtd-odoo').textContent = `(${comp.qtd_abatimentos_odoo} itens)`;

                document.getElementById('comp-total-pagamentos').textContent = formatarMoedaComp(comp.total_odoo_pagamentos);
                document.getElementById('comp-qtd-pagamentos').textContent = `(${comp.qtd_pagamentos_odoo} itens)`;

                // Diferença
                const difElement = document.getElementById('comp-diferenca');
                difElement.textContent = formatarMoedaComp(comp.diferenca);
                difElement.className = comp.status === 'OK' ? 'mb-0 text-success' : 'mb-0 text-danger';

                // Badges de vinculação
                document.getElementById('badge-pendentes').textContent = comp.vinculacao.pendentes;
                document.getElementById('badge-vinculados').textContent = comp.vinculacao.vinculados;
                document.getElementById('badge-nao-encontrados').textContent = comp.vinculacao.nao_encontrados;

                // Badges Odoo
                document.getElementById('badge-odoo-abat').textContent = comp.qtd_abatimentos_odoo;
                document.getElementById('badge-odoo-pag').textContent = comp.qtd_pagamentos_odoo;

                // Popular tipos no select de novo abatimento
                popularTiposAbatimento(data.tipos_abatimento || []);

                // Popular tabelas
                popularAbatimentosSistema(data.abatimentos_sistema);
                popularAbatimentosOdoo(data.abatimentos_odoo);
                popularPagamentosOdoo(data.pagamentos_odoo);

            } else {
                Swal.fire('Erro', data.error || 'Erro ao carregar comparativo', 'error');
            }
        })
        .catch(error => {
            console.error('Erro:', error);
            Swal.fire('Erro', 'Erro ao carregar comparativo: ' + error.message, 'error');
        });
}

// ============================================
// POPULAR TIPOS DE ABATIMENTO NO SELECT
// ============================================

function popularTiposAbatimento(tipos) {
    tiposAbatimentoCache = tipos;
    const select = document.getElementById('novo-abat-tipo');
    if (!select) return;

    select.innerHTML = '<option value="">Selecione o tipo...</option>';
    tipos.forEach(t => {
        select.innerHTML += `<option value="${t.id}">${t.tipo}</option>`;
    });
}

// ============================================
// POPULAR TABELA: ABATIMENTOS DO SISTEMA
// ============================================

function popularAbatimentosSistema(abatimentos) {
    const tbody = document.getElementById('tbody-abatimentos-sistema');
    if (!abatimentos || abatimentos.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">Nenhum abatimento registrado</td></tr>';
        return;
    }

    tbody.innerHTML = abatimentos.map(ab => {
        const statusClass = {
            'PENDENTE': 'bg-warning text-dark',
            'VINCULADO': 'bg-success',
            'NAO_ENCONTRADO': 'bg-danger',
            'NAO_APLICAVEL': 'bg-secondary'
        }[ab.status_vinculacao] || 'bg-secondary';

        const statusDisplay = {
            'PENDENTE': '⏳ Pendente',
            'VINCULADO': '✅ Vinculado',
            'NAO_ENCONTRADO': '❌ N/Encontrado',
            'NAO_APLICAVEL': '➖ N/A'
        }[ab.status_vinculacao] || ab.status_vinculacao;

        const vinculoBtn = ab.status_vinculacao === 'VINCULADO'
            ? `<button class="btn btn-outline-danger btn-sm py-0 px-1" onclick="desvincularAbatimento(${ab.id})" title="Desvincular">
                 <i class="fas fa-unlink"></i>
               </button>`
            : `<button class="btn btn-outline-primary btn-sm py-0 px-1" onclick="abrirVinculacaoManual(${ab.id})" title="Vincular manualmente">
                 <i class="fas fa-link"></i>
               </button>`;

        const deleteBtn = `<button class="btn btn-outline-danger btn-sm py-0 px-1 ms-1" onclick="excluirAbatimentoSistema(${ab.id})" title="Excluir">
             <i class="fas fa-trash"></i>
           </button>`;

        return `<tr>
            <td>${ab.tipo || '-'}</td>
            <td title="${ab.motivo || ''}">${(ab.motivo || '-').substring(0, 20)}${ab.motivo && ab.motivo.length > 20 ? '...' : ''}</td>
            <td class="text-end fw-bold">${formatarMoedaComp(ab.valor)}</td>
            <td class="text-center"><span class="badge ${statusClass} small">${statusDisplay}</span></td>
            <td class="text-center" title="${ab.documento_odoo || ''}">${ab.documento_odoo !== '-' ? ab.documento_odoo.substring(0, 15) : '-'}</td>
            <td class="text-center">${vinculoBtn}${deleteBtn}</td>
        </tr>`;
    }).join('');
}

// ============================================
// POPULAR TABELA: ABATIMENTOS DO ODOO
// ============================================

function popularAbatimentosOdoo(abatimentos) {
    const tbody = document.getElementById('tbody-odoo-abatimentos');
    if (!abatimentos || abatimentos.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">Nenhum abatimento no Odoo</td></tr>';
        return;
    }

    tbody.innerHTML = abatimentos.map(ab => {
        const disponivel = ab.disponivel;
        const vinculoStatus = disponivel
            ? '<span class="badge bg-light text-dark border">Disponível</span>'
            : `<span class="badge bg-success">Vinculado #${ab.vinculado_a}</span>`;

        return `<tr class="${disponivel ? '' : 'table-light'}">
            <td>${ab.credit_move_name || '-'}</td>
            <td>${ab.tipo_baixa_display || ab.tipo_baixa || '-'}</td>
            <td title="${ab.credit_move_ref || ''}">${(ab.credit_move_ref || '-').substring(0, 15)}</td>
            <td class="text-end fw-bold">${formatarMoedaComp(ab.amount)}</td>
            <td>${ab.max_date ? formatarDataComp(ab.max_date) : '-'}</td>
            <td class="text-center">${vinculoStatus}</td>
        </tr>`;
    }).join('');
}

// ============================================
// POPULAR TABELA: PAGAMENTOS DO ODOO
// ============================================

function popularPagamentosOdoo(pagamentos) {
    const tbody = document.getElementById('tbody-odoo-pagamentos');
    if (!pagamentos || pagamentos.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">Nenhum pagamento no Odoo</td></tr>';
        return;
    }

    tbody.innerHTML = pagamentos.map(p => `<tr>
        <td>${p.credit_move_name || '-'}</td>
        <td><span class="badge bg-success">💰 ${p.tipo_baixa_display || 'Pagamento'}</span></td>
        <td title="${p.credit_move_ref || ''}">${(p.credit_move_ref || '-').substring(0, 15)}</td>
        <td class="text-end fw-bold text-success">${formatarMoedaComp(p.amount)}</td>
        <td>${p.max_date ? formatarDataComp(p.max_date) : '-'}</td>
    </tr>`).join('');
}

// ============================================
// SINCRONIZAR BAIXAS DO ODOO
// ============================================

function sincronizarBaixasOdoo() {
    if (!comparativoContaId) return;

    const btn = document.getElementById('btn-sync-odoo');
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sincronizando...';

    fetch(`/financeiro/contas-receber/api/${comparativoContaId}/importar-baixas`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    })
        .then(response => response.json())
        .then(data => {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-sync-alt"></i> Sincronizar';

            if (data.success) {
                Swal.fire({
                    icon: 'success',
                    title: 'Sincronização Concluída',
                    text: data.message,
                    timer: 2000,
                    showConfirmButton: false
                });
                carregarComparativo(comparativoContaId);
            } else {
                Swal.fire('Erro', data.error || 'Erro ao sincronizar', 'error');
            }
        })
        .catch(error => {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-sync-alt"></i> Sincronizar';
            Swal.fire('Erro', 'Erro ao sincronizar: ' + error.message, 'error');
        });
}

// ============================================
// VINCULAR PENDENTES AUTOMATICAMENTE
// ============================================

function vincularPendentesAuto() {
    if (!comparativoContaId) return;

    Swal.fire({
        title: 'Vincular Automaticamente',
        text: 'Tentar vincular todos os abatimentos pendentes com as baixas do Odoo?',
        icon: 'question',
        showCancelButton: true,
        confirmButtonText: 'Sim, vincular',
        cancelButtonText: 'Cancelar'
    }).then((result) => {
        if (result.isConfirmed) {
            fetch(`/financeiro/contas-receber/api/${comparativoContaId}/vincular-pendentes`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        Swal.fire({
                            icon: 'success',
                            title: 'Vinculação Concluída',
                            html: `<strong>${data.estatisticas.vinculados}</strong> vinculados<br>
                                   <strong>${data.estatisticas.nao_encontrados}</strong> não encontrados`,
                            timer: 2500,
                            showConfirmButton: false
                        });
                        carregarComparativo(comparativoContaId);
                    } else {
                        Swal.fire('Erro', data.error || 'Erro ao vincular', 'error');
                    }
                })
                .catch(error => {
                    Swal.fire('Erro', 'Erro ao vincular: ' + error.message, 'error');
                });
        }
    });
}

// ============================================
// VINCULAÇÃO MANUAL
// ============================================

function abrirVinculacaoManual(abatimentoId) {
    fetch(`/financeiro/contas-receber/api/${comparativoContaId}/reconciliacoes-disponiveis?abatimento_id=${abatimentoId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success && data.reconciliacoes.length > 0) {
                const opcoes = data.reconciliacoes
                    .filter(r => r.disponivel)
                    .map(r => `<option value="${r.id}">${r.credit_move_name} - ${formatarMoedaComp(r.amount)} (${r.tipo_baixa_display})</option>`)
                    .join('');

                if (!opcoes) {
                    Swal.fire('Aviso', 'Não há reconciliações disponíveis para vincular', 'warning');
                    return;
                }

                Swal.fire({
                    title: 'Vincular Manualmente',
                    html: `
                        <p>Selecione a baixa do Odoo para vincular:</p>
                        <select id="swal-reconciliacao" class="form-select">
                            ${opcoes}
                        </select>
                    `,
                    showCancelButton: true,
                    confirmButtonText: 'Vincular',
                    cancelButtonText: 'Cancelar',
                    preConfirm: () => {
                        return document.getElementById('swal-reconciliacao').value;
                    }
                }).then((result) => {
                    if (result.isConfirmed && result.value) {
                        vincularAbatimento(abatimentoId, result.value);
                    }
                });
            } else {
                Swal.fire('Aviso', 'Não há reconciliações disponíveis para vincular', 'warning');
            }
        })
        .catch(error => {
            Swal.fire('Erro', 'Erro ao buscar reconciliações: ' + error.message, 'error');
        });
}

function vincularAbatimento(abatimentoId, reconciliacaoId) {
    fetch(`/financeiro/contas-receber/api/abatimento/${abatimentoId}/vincular`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reconciliacao_id: parseInt(reconciliacaoId) })
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                Swal.fire({
                    icon: 'success',
                    title: 'Vinculado!',
                    text: data.message,
                    timer: 1500,
                    showConfirmButton: false
                });
                carregarComparativo(comparativoContaId);
            } else {
                Swal.fire('Erro', data.message || 'Erro ao vincular', 'error');
            }
        })
        .catch(error => {
            Swal.fire('Erro', 'Erro ao vincular: ' + error.message, 'error');
        });
}

// ============================================
// DESVINCULAR ABATIMENTO
// ============================================

function desvincularAbatimento(abatimentoId) {
    Swal.fire({
        title: 'Desvincular',
        text: 'Deseja remover a vinculação deste abatimento?',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonText: 'Sim, desvincular',
        cancelButtonText: 'Cancelar'
    }).then((result) => {
        if (result.isConfirmed) {
            fetch(`/financeiro/contas-receber/api/abatimento/${abatimentoId}/desvincular`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        Swal.fire({
                            icon: 'success',
                            title: 'Desvinculado!',
                            text: data.message,
                            timer: 1500,
                            showConfirmButton: false
                        });
                        carregarComparativo(comparativoContaId);
                    } else {
                        Swal.fire('Erro', data.message || 'Erro ao desvincular', 'error');
                    }
                })
                .catch(error => {
                    Swal.fire('Erro', 'Erro ao desvincular: ' + error.message, 'error');
                });
        }
    });
}

// ============================================
// EXCLUIR ABATIMENTO DO SISTEMA
// ============================================

function excluirAbatimentoSistema(abatimentoId) {
    Swal.fire({
        title: 'Excluir Abatimento',
        text: 'Deseja excluir este abatimento do sistema?',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#dc3545',
        confirmButtonText: 'Sim, excluir',
        cancelButtonText: 'Cancelar'
    }).then((result) => {
        if (result.isConfirmed) {
            fetch(`/financeiro/contas-receber/api/abatimentos/${abatimentoId}`, {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' }
            })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        Swal.fire({
                            icon: 'success',
                            title: 'Excluído!',
                            text: data.message,
                            timer: 1500,
                            showConfirmButton: false
                        });
                        carregarComparativo(comparativoContaId);
                        // Atualizar célula na tabela principal
                        atualizarCelulaAbatimentos(comparativoContaId);
                    } else {
                        Swal.fire('Erro', data.error || 'Erro ao excluir', 'error');
                    }
                })
                .catch(error => {
                    Swal.fire('Erro', 'Erro ao excluir: ' + error.message, 'error');
                });
        }
    });
}

// ============================================
// CRIAR NOVO ABATIMENTO
// ============================================

function criarNovoAbatimento(e) {
    if (e) e.preventDefault();
    if (!comparativoContaId) return;

    const tipo = document.getElementById('novo-abat-tipo').value;
    const motivo = document.getElementById('novo-abat-motivo').value.trim();
    const doc = document.getElementById('novo-abat-doc').value.trim();
    const valor = document.getElementById('novo-abat-valor').value;
    const data = document.getElementById('novo-abat-data').value;
    const previsto = document.getElementById('novo-abat-previsto').value;

    if (!tipo) {
        toastr.warning('Selecione o tipo do abatimento');
        return;
    }
    if (!valor || parseFloat(valor) <= 0) {
        toastr.warning('Informe um valor válido');
        return;
    }

    const btn = document.getElementById('btn-criar-abatimento');
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

    fetch(`/financeiro/contas-receber/api/${comparativoContaId}/abatimentos`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            tipo_id: parseInt(tipo),
            motivo: motivo || null,
            doc_motivo: doc || null,
            valor: parseFloat(valor),
            data: data || null,
            previsto: previsto === 'true'
        })
    })
        .then(response => response.json())
        .then(data => {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-plus"></i>';

            if (data.success) {
                toastr.success(data.message);
                limparFormularioAbatimento();
                carregarComparativo(comparativoContaId);
                // Atualizar célula na tabela principal
                atualizarCelulaAbatimentos(comparativoContaId);
            } else {
                toastr.error(data.error || 'Erro ao criar abatimento');
            }
        })
        .catch(error => {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-plus"></i>';
            toastr.error('Erro ao criar abatimento: ' + error.message);
        });
}

function limparFormularioAbatimento() {
    const form = document.getElementById('formNovoAbatimentoComp');
    if (form) form.reset();
}

// ============================================
// TOGGLE PAINEL DE NOVO ABATIMENTO
// ============================================

function toggleNovoAbatimento() {
    const painel = document.getElementById('painel-novo-abatimento');
    const btn = document.getElementById('btn-toggle-novo-abat');

    if (painel.style.display === 'none' || painel.style.display === '') {
        painel.style.display = 'block';
        btn.innerHTML = '<i class="fas fa-minus"></i> Fechar';
        btn.classList.remove('btn-success');
        btn.classList.add('btn-secondary');
    } else {
        painel.style.display = 'none';
        btn.innerHTML = '<i class="fas fa-plus"></i> Novo';
        btn.classList.remove('btn-secondary');
        btn.classList.add('btn-success');
    }
}

// ============================================
// ATUALIZAR CÉLULA NA TABELA PRINCIPAL
// ============================================

function atualizarCelulaAbatimentos(contaId) {
    // Função para atualizar a célula de abatimentos na tabela principal
    // quando um abatimento for criado/excluído no modal
    // Por enquanto, apenas recarrega a página para simplicidade
    // Pode ser otimizado para fazer update via AJAX
    console.log('Abatimento atualizado para conta:', contaId);
}

// ============================================
// INICIALIZAÇÃO
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    // Form de novo abatimento
    const formAbatComp = document.getElementById('formNovoAbatimentoComp');
    if (formAbatComp) {
        formAbatComp.addEventListener('submit', criarNovoAbatimento);
    }
});
