/* ==============================================
   JS: Contas a Receber - Listagem
   ============================================== */

// ============================================
// FUNÇÕES UTILITÁRIAS
// ============================================

function formatarMoeda(valor) {
    return 'R$ ' + (valor || 0).toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2});
}

// URLs base (serão definidas no template)
let URL_BASE = '';
let URL_EXPORT = '';
let URL_SYNC = '';

// Cache de dados para atualização dinâmica
let dadosAbatimentosCache = {};

function initContasReceber(urlBase, urlExport, urlSync) {
    URL_BASE = urlBase;
    URL_EXPORT = urlExport;
    URL_SYNC = urlSync;

    // Carregar lembretes APÓS definir URLs
    carregarLembretes();
}

// ============================================
// EXPORTAR E SINCRONIZAR
// ============================================

function exportarExcel() {
    // Pega os parâmetros de filtro atuais da URL
    const params = new URLSearchParams(window.location.search);
    const url = URL_EXPORT + (params.toString() ? '?' + params.toString() : '');
    const link = document.createElement('a');
    link.href = url;
    link.download = 'contas_receber.xlsx';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    toastr.info('Gerando arquivo Excel com os filtros aplicados...', 'Aguarde');
}

function sincronizarOdoo() {
    const btn = document.getElementById('btnSync');
    if (!btn) return;

    const textoOriginal = btn.innerHTML;

    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sincronizando...';

    fetch(URL_SYNC, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            toastr.success(
                `Novos: ${data.novos} | Atualizados: ${data.atualizados} | Enriquecidos: ${data.enriquecidos}`,
                'Sincronização Concluída!'
            );
            setTimeout(() => location.reload(), 1500);
        } else {
            toastr.error(data.error || 'Erro desconhecido', 'Erro na Sincronização');
        }
    })
    .catch(error => {
        console.error('Erro:', error);
        toastr.error('Erro ao conectar com o servidor', 'Erro');
    })
    .finally(() => {
        btn.disabled = false;
        btn.innerHTML = textoOriginal;
    });
}

// ============================================
// ALERTA TOGGLE
// ============================================

function toggleAlerta(contaId) {
    fetch(URL_BASE.replace('/listar', `/api/${contaId}/alerta`), {
        method: 'POST',
        headers: {'Content-Type': 'application/json'}
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            const el = document.getElementById(`alerta-${contaId}`);
            if (data.alerta) {
                el.classList.remove('alerta-off');
                el.classList.add('alerta-on');
                el.title = 'Alerta ATIVO - Clique para desativar';
            } else {
                el.classList.remove('alerta-on');
                el.classList.add('alerta-off');
                el.title = 'Sem alerta - Clique para ativar';
            }
            toastr.success(data.message);
        } else {
            toastr.error(data.error);
        }
    });
}

// ============================================
// OBSERVAÇÃO COM SWAL
// ============================================

function editarObservacao(contaId, obsAtual) {
    Swal.fire({
        title: 'Observação',
        input: 'textarea',
        inputValue: obsAtual,
        inputPlaceholder: 'Digite a observação...',
        showCancelButton: true,
        confirmButtonText: 'Salvar',
        cancelButtonText: 'Cancelar',
        inputAttributes: {
            'aria-label': 'Observação'
        }
    }).then((result) => {
        if (result.isConfirmed) {
            fetch(URL_BASE.replace('/listar', `/api/${contaId}/observacao`), {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({observacao: result.value})
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    toastr.success('Observação atualizada!');
                    // Atualizar dinamicamente
                    atualizarObservacaoNaTela(contaId, result.value);
                } else {
                    toastr.error(data.error);
                }
            });
        }
    });
}

function atualizarObservacaoNaTela(contaId, observacao) {
    const tr = document.querySelector(`tr[data-conta-id="${contaId}"]`);
    if (!tr) return;

    const obsDiv = tr.querySelector('.obs-clicavel');
    if (!obsDiv) return;

    if (observacao) {
        obsDiv.innerHTML = `<i class="fas fa-sticky-note text-warning"></i> ${observacao.substring(0, 30)}${observacao.length > 30 ? '...' : ''}`;
    } else {
        obsDiv.innerHTML = '<i class="fas fa-plus-circle text-secondary"></i> <small>Add obs</small>';
    }
}

// ============================================
// MODAL ABATIMENTOS REMOVIDO em 2025-11-28
// Agora usa modalComparativo (Sistema × Odoo)
// Funções em: contas_receber_comparativo.js
// ============================================

// ============================================
// MODAL CONFIRMAÇÃO (ATUALIZAÇÃO DINÂMICA)
// ============================================

let modalConfirmacaoInstance = null;

function abrirModalConfirmacao(contaId) {
    document.getElementById('conf-conta-id').value = contaId;

    fetch(URL_BASE.replace('/listar', `/api/${contaId}/confirmacao`))
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            // Popular selects com opção ABERTO
            const selectTipo = document.getElementById('conf-tipo');
            selectTipo.innerHTML = '<option value="">ABERTO</option>'; // Default ABERTO
            data.tipos_confirmacao.forEach(t => {
                const selected = t.id == data.confirmacao.confirmacao_tipo_id ? 'selected' : '';
                selectTipo.innerHTML += `<option value="${t.id}" ${selected}>${t.tipo}</option>`;
            });

            const selectForma = document.getElementById('conf-forma');
            selectForma.innerHTML = '<option value="">Selecione...</option>';
            data.tipos_forma.forEach(t => {
                const selected = t.id == data.confirmacao.forma_confirmacao_tipo_id ? 'selected' : '';
                selectForma.innerHTML += `<option value="${t.id}" ${selected}>${t.tipo}</option>`;
            });

            document.getElementById('conf-obs').value = data.confirmacao.confirmacao_entrega || '';

            // Info de log
            let infoLog = '';
            if (data.confirmacao.data_confirmacao) {
                infoLog = `Confirmado em ${new Date(data.confirmacao.data_confirmacao).toLocaleString('pt-BR')}`;
                if (data.confirmacao.confirmado_por) {
                    infoLog += ` por ${data.confirmacao.confirmado_por}`;
                }
            }
            document.getElementById('conf-info-log').textContent = infoLog;

            const modalEl = document.getElementById('modalConfirmacao');
            modalConfirmacaoInstance = new bootstrap.Modal(modalEl);
            modalConfirmacaoInstance.show();
        }
    });
}

function fecharModalConfirmacao() {
    if (modalConfirmacaoInstance) {
        modalConfirmacaoInstance.hide();
    }
    setTimeout(() => {
        document.querySelectorAll('.modal-backdrop').forEach(el => el.remove());
        document.body.classList.remove('modal-open');
        document.body.style.removeProperty('overflow');
        document.body.style.removeProperty('padding-right');
    }, 300);
}

function salvarConfirmacao() {
    const contaId = document.getElementById('conf-conta-id').value;
    const tipoId = document.getElementById('conf-tipo').value;
    const formaId = document.getElementById('conf-forma').value;
    const obs = document.getElementById('conf-obs').value;

    fetch(URL_BASE.replace('/listar', `/api/${contaId}/confirmacao`), {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            confirmacao_tipo_id: tipoId || null,
            forma_confirmacao_tipo_id: formaId || null,
            confirmacao_entrega: obs
        })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            toastr.success(data.message);
            fecharModalConfirmacao();

            // Atualizar célula dinamicamente
            atualizarCelulaConfirmacao(contaId, tipoId, data.confirmacao_tipo_nome);
        } else {
            toastr.error(data.error);
        }
    });
}

function atualizarCelulaConfirmacao(contaId, tipoId, tipoNome) {
    const cell = document.getElementById(`conf-cell-${contaId}`);
    if (!cell) return;

    if (tipoId) {
        cell.textContent = tipoNome ? tipoNome.substring(0, 12) : 'OK';
        cell.classList.remove('confirmacao-aberto');
        cell.classList.add('confirmacao-ok');
    } else {
        cell.textContent = 'ABERTO';
        cell.classList.remove('confirmacao-ok');
        cell.classList.add('confirmacao-aberto');
    }
}

// ============================================
// MODAL AÇÃO NECESSÁRIA (ATUALIZAÇÃO DINÂMICA)
// ============================================

let modalAcaoInstance = null;

function abrirModalAcao(contaId) {
    document.getElementById('acao-conta-id').value = contaId;

    fetch(URL_BASE.replace('/listar', `/api/${contaId}/acao-necessaria`))
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            // Popular select
            const selectTipo = document.getElementById('acao-tipo');
            selectTipo.innerHTML = '<option value="">Selecione...</option>';
            data.tipos_acao.forEach(t => {
                const selected = t.id == data.acao.acao_necessaria_tipo_id ? 'selected' : '';
                selectTipo.innerHTML += `<option value="${t.id}" ${selected}>${t.tipo}</option>`;
            });

            document.getElementById('acao-obs').value = data.acao.obs_acao_necessaria || '';
            document.getElementById('acao-lembrete').value = data.acao.data_lembrete || '';

            const modalEl = document.getElementById('modalAcao');
            modalAcaoInstance = new bootstrap.Modal(modalEl);
            modalAcaoInstance.show();
        }
    });
}

function fecharModalAcao() {
    if (modalAcaoInstance) {
        modalAcaoInstance.hide();
    }
    setTimeout(() => {
        document.querySelectorAll('.modal-backdrop').forEach(el => el.remove());
        document.body.classList.remove('modal-open');
        document.body.style.removeProperty('overflow');
        document.body.style.removeProperty('padding-right');
    }, 300);
}

function salvarAcao() {
    const contaId = document.getElementById('acao-conta-id').value;
    const tipoId = document.getElementById('acao-tipo').value;
    const tipoSelect = document.getElementById('acao-tipo');
    const tipoNome = tipoSelect.options[tipoSelect.selectedIndex]?.text || '';
    const obs = document.getElementById('acao-obs').value;
    const lembrete = document.getElementById('acao-lembrete').value;

    fetch(URL_BASE.replace('/listar', `/api/${contaId}/acao-necessaria`), {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            acao_necessaria_tipo_id: tipoId || null,
            obs_acao_necessaria: obs,
            data_lembrete: lembrete || null
        })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            toastr.success(data.message);
            fecharModalAcao();

            // Atualizar célula dinamicamente
            atualizarCelulaAcao(contaId, tipoId, tipoNome, lembrete, obs);
        } else {
            toastr.error(data.error);
        }
    });
}

function atualizarCelulaAcao(contaId, tipoId, tipoNome, lembrete, obs) {
    const cell = document.getElementById(`acao-cell-${contaId}`);
    if (!cell) return;

    if (tipoId && tipoNome && tipoNome !== 'Selecione...') {
        let html = tipoNome.substring(0, 10);
        if (tipoNome.length > 10) html += '..';
        if (lembrete) {
            const dataLembrete = new Date(lembrete + 'T00:00:00');
            html += `<small class="d-block text-white">${dataLembrete.toLocaleDateString('pt-BR', {day: '2-digit', month: '2-digit'})}</small>`;
        }
        cell.innerHTML = html;
        cell.classList.remove('acao-vazia');
        cell.classList.add('acao-ativa');
        cell.title = obs || tipoNome;
    } else {
        cell.innerHTML = '<i class="fas fa-plus text-muted"></i>';
        cell.classList.remove('acao-ativa');
        cell.classList.add('acao-vazia');
        cell.title = 'Adicionar ação';
    }

    // Reinicializar tooltip
    const tooltip = bootstrap.Tooltip.getInstance(cell);
    if (tooltip) tooltip.dispose();
    new bootstrap.Tooltip(cell);
}

function limparAcao() {
    document.getElementById('acao-tipo').value = '';
    document.getElementById('acao-obs').value = '';
    document.getElementById('acao-lembrete').value = '';
    salvarAcao();
}

// ============================================
// MODAL SNAPSHOTS (HISTÓRICO DE ALTERAÇÕES)
// ============================================

let modalSnapshotsInstance = null;

function abrirModalSnapshots(contaId) {
    // Mostrar loading
    document.getElementById('snapshots-loading').style.display = 'block';
    document.getElementById('snapshots-empty').style.display = 'none';
    document.getElementById('snapshots-content').style.display = 'none';

    // Abrir modal
    const modalEl = document.getElementById('modalSnapshots');
    modalSnapshotsInstance = new bootstrap.Modal(modalEl);
    modalSnapshotsInstance.show();

    // Buscar dados
    fetch(URL_BASE.replace('/listar', `/api/${contaId}/snapshots`))
    .then(r => r.json())
    .then(data => {
        document.getElementById('snapshots-loading').style.display = 'none';

        if (data.success) {
            document.getElementById('snap-nf').textContent = `${data.titulo_nf}-${data.parcela}`;

            if (data.snapshots.length === 0) {
                document.getElementById('snapshots-empty').style.display = 'block';
            } else {
                document.getElementById('snapshots-content').style.display = 'block';

                const tbody = document.getElementById('snapshots-tbody');
                tbody.innerHTML = '';

                data.snapshots.forEach(s => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td>${s.alterado_em ? new Date(s.alterado_em).toLocaleString('pt-BR') : '-'}</td>
                        <td><code>${formatarNomeCampo(s.campo)}</code></td>
                        <td class="text-danger">${formatarValorSnapshot(s.valor_anterior)}</td>
                        <td class="text-success">${formatarValorSnapshot(s.valor_novo)}</td>
                        <td>${s.alterado_por || '-'}</td>
                    `;
                    tbody.appendChild(tr);
                });
            }
        } else {
            document.getElementById('snapshots-empty').style.display = 'block';
            toastr.error(data.error || 'Erro ao carregar histórico');
        }
    })
    .catch(error => {
        document.getElementById('snapshots-loading').style.display = 'none';
        document.getElementById('snapshots-empty').style.display = 'block';
        console.error('Erro:', error);
    });
}

function formatarNomeCampo(campo) {
    const mapa = {
        'valor_original': 'Valor Original',
        'valor_titulo': 'Valor Título',
        'desconto': 'Desconto',
        'vencimento': 'Vencimento',
        'parcela_paga': 'Pago',
        'cnpj': 'CNPJ',
        'raz_social': 'Razão Social',
        'raz_social_red': 'Nome Fantasia',
        'uf_cliente': 'UF',
        'emissao': 'Emissão',
        'tipo_titulo': 'Tipo Título',
        'status_pagamento_odoo': 'Status Odoo'
    };
    return mapa[campo] || campo;
}

function formatarValorSnapshot(valor) {
    if (valor === null || valor === undefined || valor === 'null') {
        return '<span class="text-muted">-</span>';
    }

    // Tentar parsear JSON
    try {
        const parsed = JSON.parse(valor);
        if (typeof parsed === 'number') {
            return formatarMoeda(parsed);
        }
        if (typeof parsed === 'boolean') {
            return parsed ? 'Sim' : 'Não';
        }
        return parsed;
    } catch (e) {
        // Se for data no formato ISO
        if (/^\d{4}-\d{2}-\d{2}/.test(valor)) {
            const data = new Date(valor);
            return data.toLocaleDateString('pt-BR');
        }
        return valor;
    }
}

// ============================================
// LEMBRETES NO CABEÇALHO
// ============================================

function carregarLembretes() {
    if (!URL_BASE) return;

    fetch(URL_BASE.replace('/listar', '/api/lembretes'))
    .then(r => r.json())
    .then(data => {
        if (data.success && data.total > 0) {
            const lembretesArea = document.getElementById('lembretesArea');
            const container = document.getElementById('lembretesContainer');
            if (!lembretesArea || !container) return;

            lembretesArea.style.display = 'flex';
            container.innerHTML = '';

            // Lembretes com clique para filtrar
            data.lembretes.forEach(l => {
                let classe = '';
                if (l.diff_dias < 0) classe = 'passado';
                else if (l.diff_dias === 0) classe = 'hoje';

                const span = document.createElement('span');
                span.className = `lembrete-item ${classe}`;
                span.title = `${l.count} título(s) - Clique para filtrar`;
                span.textContent = `${l.data_display}: ${l.count}`;
                span.style.cursor = 'pointer';
                span.onclick = () => filtrarPorLembrete(l.data);
                container.appendChild(span);
            });
        }
    })
    .catch(error => console.error('Erro ao carregar lembretes:', error));
}

function filtrarPorLembrete(dataISO) {
    // Redireciona para a listagem filtrada por data_lembrete
    const url = new URL(window.location.href);
    url.searchParams.set('data_lembrete', dataISO);
    url.searchParams.delete('page');
    window.location.href = url.toString();
}

// ============================================
// MODAL PENDÊNCIA FINANCEIRA
// ============================================

let modalPendenciaInstance = null;

function abrirModalPendencia(contaId, tituloNf) {
    document.getElementById('pend-conta-id').value = contaId;
    document.getElementById('pend-nf').textContent = tituloNf;
    document.getElementById('pend-observacao').value = '';

    // Carregar pendências existentes
    carregarPendenciasExistentes(contaId);

    // Abrir modal
    const modalEl = document.getElementById('modalPendencia');
    modalPendenciaInstance = new bootstrap.Modal(modalEl);
    modalPendenciaInstance.show();
}

function carregarPendenciasExistentes(contaId) {
    const container = document.getElementById('pend-lista-container');
    container.innerHTML = '<div class="text-center text-muted"><i class="fas fa-spinner fa-spin"></i> Carregando...</div>';

    fetch(URL_BASE.replace('/listar', `/api/${contaId}/pendencias`))
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            if (data.pendencias.length === 0) {
                container.innerHTML = '<div class="text-muted small">Nenhuma pendência registrada.</div>';
            } else {
                container.innerHTML = '';
                data.pendencias.forEach(p => {
                    const card = document.createElement('div');
                    card.className = `card mb-2 ${p.tem_resposta ? 'border-success' : 'border-warning'}`;
                    card.innerHTML = `
                        <div class="card-body py-2">
                            <div class="d-flex justify-content-between align-items-start">
                                <div>
                                    <strong class="text-danger"><i class="fas fa-arrow-right"></i> Financeiro:</strong>
                                    <p class="mb-1 small">${p.observacao || '-'}</p>
                                    <small class="text-muted">Por ${p.criado_por || '?'} em ${p.criado_em ? new Date(p.criado_em).toLocaleString('pt-BR') : '-'}</small>
                                </div>
                                <span class="badge ${p.tem_resposta ? 'bg-success' : 'bg-warning text-dark'}">${p.tem_resposta ? 'Respondida' : 'Pendente'}</span>
                            </div>
                            ${p.tem_resposta ? `
                                <hr class="my-2">
                                <div>
                                    <strong class="text-success"><i class="fas fa-arrow-left"></i> Logística:</strong>
                                    <p class="mb-1 small">${p.resposta_logistica || '-'}</p>
                                    <small class="text-muted">Por ${p.respondida_por || '?'} em ${p.respondida_em ? new Date(p.respondida_em).toLocaleString('pt-BR') : '-'}</small>
                                </div>
                            ` : ''}
                        </div>
                    `;
                    container.appendChild(card);
                });
            }
        } else {
            container.innerHTML = '<div class="text-danger small">Erro ao carregar pendências.</div>';
        }
    })
    .catch(error => {
        console.error('Erro:', error);
        container.innerHTML = '<div class="text-danger small">Erro ao carregar pendências.</div>';
    });
}

function enviarPendencia() {
    const contaId = document.getElementById('pend-conta-id').value;
    const observacao = document.getElementById('pend-observacao').value.trim();

    if (!observacao) {
        toastr.warning('Digite uma observação para a pendência.');
        return;
    }

    fetch(URL_BASE.replace('/listar', '/api/pendencia-financeira'), {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            conta_id: contaId,
            observacao: observacao
        })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            toastr.success(data.message);
            document.getElementById('pend-observacao').value = '';
            carregarPendenciasExistentes(contaId);

            // Atualizar ícone na tabela
            atualizarIconePendencia(contaId, true);
        } else {
            toastr.error(data.error);
        }
    })
    .catch(error => {
        console.error('Erro:', error);
        toastr.error('Erro ao enviar pendência.');
    });
}

function atualizarIconePendencia(contaId, temPendencia) {
    const tr = document.querySelector(`tr[data-conta-id="${contaId}"]`);
    if (!tr) return;

    const btn = tr.querySelector('.btn-pendencia');
    if (btn) {
        if (temPendencia) {
            btn.classList.remove('btn-outline-secondary');
            btn.classList.add('btn-danger');
            btn.title = 'Pendência aberta';
        } else {
            btn.classList.remove('btn-danger');
            btn.classList.add('btn-outline-secondary');
            btn.title = 'Registrar pendência';
        }
    }
}

// ============================================
// INICIALIZAÇÃO
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    // Tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // NOTA: carregarLembretes() é chamado em initContasReceber() após definir URL_BASE

    // Form de novo abatimento
    const formAbat = document.getElementById('formNovoAbatimento');
    if (formAbat) {
        formAbat.addEventListener('submit', submitNovoAbatimento);
    }

    // Auto submit ao pressionar Enter
    document.querySelectorAll('#formFiltros input[type="text"]').forEach(input => {
        input.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                document.getElementById('formFiltros').submit();
            }
        });
    });

    // Event listener para fechar modais e limpar backdrop
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('hidden.bs.modal', function() {
            document.querySelectorAll('.modal-backdrop').forEach(el => el.remove());
            document.body.classList.remove('modal-open');
            document.body.style.removeProperty('overflow');
            document.body.style.removeProperty('padding-right');
        });
    });
});
