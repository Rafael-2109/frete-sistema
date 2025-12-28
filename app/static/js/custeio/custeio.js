/**
 * ═══════════════════════════════════════════════════════════════════════════
 * CUSTEIO - JavaScript
 * Sistema de Custeio - Nacom Goya
 * ═══════════════════════════════════════════════════════════════════════════
 */

// ==========================================================================
// VARIAVEIS GLOBAIS
// ==========================================================================
let dadosMensal = [];
let dadosConsiderado = [];
let tipoFiltro = '';

// ==========================================================================
// INICIALIZACAO
// ==========================================================================
document.addEventListener('DOMContentLoaded', function() {
    inicializarCusteio();
});

function inicializarCusteio() {
    // Definir mes/ano atual
    const hoje = new Date();
    document.getElementById('filtro-mes').value = hoje.getMonth() + 1;
    document.getElementById('filtro-ano').value = hoje.getFullYear();

    // Carregar estatisticas
    carregarEstatisticas();

    // Event listeners para filtros de tipo
    document.querySelectorAll('.filtro-tipo-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            document.querySelectorAll('.filtro-tipo-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            tipoFiltro = this.dataset.tipo;
            aplicarFiltros();
        });
    });

    // Busca por produto com debounce
    let debounceTimer;
    document.getElementById('filtro-produto').addEventListener('input', function() {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(aplicarFiltros, 300);
    });

    // Tab change
    document.querySelectorAll('#custoTabs button').forEach(tab => {
        tab.addEventListener('shown.bs.tab', function(e) {
            if (e.target.id === 'considerado-tab') {
                buscarCustosConsiderados();
            }
        });
    });
}

// ==========================================================================
// FUNCOES DE BUSCA
// ==========================================================================
function buscarCustos() {
    const mes = document.getElementById('filtro-mes').value;
    const ano = document.getElementById('filtro-ano').value;

    mostrarLoading(true);

    fetch(`/custeio/api/mensal/listar?mes=${mes}&ano=${ano}`)
        .then(r => r.json())
        .then(data => {
            mostrarLoading(false);
            if (data.sucesso) {
                dadosMensal = data.dados;
                renderizarTabelaMensal();
            } else {
                mostrarAlerta('erro', data.erro || 'Erro desconhecido');
            }
        })
        .catch(err => {
            mostrarLoading(false);
            console.error(err);
            mostrarAlerta('erro', 'Erro ao buscar dados');
        });
}

function buscarCustosConsiderados() {
    mostrarLoading(true);

    fetch('/custeio/api/considerado/listar')
        .then(r => r.json())
        .then(data => {
            mostrarLoading(false);
            if (data.sucesso) {
                dadosConsiderado = data.dados;
                renderizarTabelaConsiderado();
            }
        })
        .catch(err => {
            mostrarLoading(false);
            console.error(err);
        });
}

function carregarEstatisticas() {
    fetch('/custeio/api/estatisticas')
        .then(r => r.json())
        .then(data => {
            if (data.sucesso) {
                document.getElementById('stat-comprados').textContent = data.por_tipo.COMPRADO || 0;
                document.getElementById('stat-intermediarios').textContent = data.por_tipo.INTERMEDIARIO || 0;
                document.getElementById('stat-acabados').textContent = data.por_tipo.ACABADO || 0;

                if (data.ultimo_fechamento) {
                    document.getElementById('stat-ultimo-fechamento').textContent =
                        `${data.ultimo_fechamento.mes}/${data.ultimo_fechamento.ano}`;
                }
            }
        })
        .catch(err => console.error('Erro ao carregar estatisticas:', err));
}

// ==========================================================================
// FUNCOES DE RENDERIZACAO
// ==========================================================================
function renderizarTabelaMensal() {
    const tbody = document.getElementById('tbody-mensal');
    const dados = filtrarDados(dadosMensal);

    if (dados.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="10" class="empty-state">
                    <i class="bi bi-inbox"></i>
                    <p>Nenhum dado encontrado</p>
                </td>
            </tr>`;
        return;
    }

    tbody.innerHTML = dados.map(item => `
        <tr>
            <td class="table-sticky"><strong>${item.cod_produto}</strong></td>
            <td>${item.nome_produto || '-'}</td>
            <td><span class="tipo-badge tipo-${item.tipo_produto.toLowerCase()}">${item.tipo_produto}</span></td>
            <td class="text-end valor-custo">${formatarMoeda(item.custo_liquido_medio)}</td>
            <td class="text-end valor-custo">${formatarMoeda(item.ultimo_custo)}</td>
            <td class="text-end valor-custo">${formatarMoeda(item.custo_medio_estoque)}</td>
            <td class="text-end valor-custo ${item.custo_bom ? 'valor-destaque' : ''}">${formatarMoeda(item.custo_bom)}</td>
            <td class="text-end">${formatarNumero(item.qtd_comprada)}</td>
            <td class="text-end">${formatarMoeda(item.valor_compras_liquido)}</td>
            <td class="text-center">
                <span class="badge ${item.status === 'FECHADO' ? 'bg-success' : 'bg-warning'}">${item.status}</span>
            </td>
        </tr>
    `).join('');
}

function renderizarTabelaConsiderado() {
    const tbody = document.getElementById('tbody-considerado');
    const dados = filtrarDados(dadosConsiderado);

    if (dados.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="11" class="empty-state">
                    <i class="bi bi-inbox"></i>
                    <p>Nenhum dado encontrado</p>
                </td>
            </tr>`;
        return;
    }

    tbody.innerHTML = dados.map(item => `
        <tr data-cod="${item.cod_produto}">
            <td class="table-sticky"><strong>${item.cod_produto}</strong></td>
            <td>${item.nome_produto || '-'}</td>
            <td><span class="tipo-badge tipo-${item.tipo_produto.toLowerCase()}">${item.tipo_produto}</span></td>
            <td class="text-end valor-custo">${formatarMoeda(item.custo_medio_mes)}</td>
            <td class="text-end valor-custo">${formatarMoeda(item.ultimo_custo)}</td>
            <td class="text-end valor-custo">${formatarMoeda(item.custo_medio_estoque)}</td>
            <td class="text-end valor-custo">${formatarMoeda(item.custo_bom)}</td>
            <td class="text-center">
                <select class="editable-select" onchange="alterarTipoCusto('${item.cod_produto}', this.value)">
                    <option value="MEDIO_MES" ${item.tipo_custo_selecionado === 'MEDIO_MES' ? 'selected' : ''}>Medio Mes</option>
                    <option value="ULTIMO_CUSTO" ${item.tipo_custo_selecionado === 'ULTIMO_CUSTO' ? 'selected' : ''}>Ultimo Custo</option>
                    <option value="MEDIO_ESTOQUE" ${item.tipo_custo_selecionado === 'MEDIO_ESTOQUE' ? 'selected' : ''}>Medio Estoque</option>
                    <option value="BOM" ${item.tipo_custo_selecionado === 'BOM' ? 'selected' : ''}>BOM</option>
                </select>
                <span class="save-indicator" id="save-${item.cod_produto}"><i class="bi bi-check-lg"></i></span>
            </td>
            <td class="text-end valor-custo valor-destaque">${formatarMoeda(item.custo_considerado)}</td>
            <td class="text-end">${formatarNumero(item.qtd_estoque_inicial)}</td>
            <td class="text-end">${formatarNumero(item.qtd_estoque_final)}</td>
        </tr>
    `).join('');
}

// ==========================================================================
// FUNCOES DE FILTRO
// ==========================================================================
function filtrarDados(dados) {
    const textoBusca = document.getElementById('filtro-produto').value.toLowerCase();

    return dados.filter(item => {
        // Filtro por tipo
        if (tipoFiltro && item.tipo_produto !== tipoFiltro) return false;

        // Filtro por texto
        if (textoBusca) {
            const cod = (item.cod_produto || '').toLowerCase();
            const nome = (item.nome_produto || '').toLowerCase();
            if (!cod.includes(textoBusca) && !nome.includes(textoBusca)) return false;
        }

        return true;
    });
}

function aplicarFiltros() {
    renderizarTabelaMensal();
    renderizarTabelaConsiderado();
}

// ==========================================================================
// FUNCOES DE ACAO
// ==========================================================================
function alterarTipoCusto(codProduto, tipoCusto) {
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';

    fetch('/custeio/api/considerado/alterar-tipo', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({
            cod_produto: codProduto,
            tipo_custo: tipoCusto
        })
    })
    .then(r => r.json())
    .then(data => {
        if (data.sucesso) {
            // Mostrar indicador de salvamento
            const indicator = document.getElementById(`save-${codProduto}`);
            indicator.classList.add('show');
            setTimeout(() => indicator.classList.remove('show'), 2000);

            // Atualizar valor na tabela
            const row = document.querySelector(`tr[data-cod="${codProduto}"]`);
            if (row) {
                row.querySelector('.valor-destaque').textContent = formatarMoeda(data.custo_considerado);
            }
        } else {
            mostrarAlerta('erro', data.erro);
        }
    })
    .catch(err => {
        console.error(err);
        mostrarAlerta('erro', 'Erro ao alterar tipo de custo');
    });
}

function simularFechamento() {
    const mes = document.getElementById('filtro-mes').value;
    const ano = document.getElementById('filtro-ano').value;

    mostrarLoading(true);

    fetch(`/custeio/api/mensal/simular?mes=${mes}&ano=${ano}`)
        .then(r => r.json())
        .then(data => {
            mostrarLoading(false);
            if (data.sucesso) {
                mostrarPreview(data.preview, mes, ano);
            } else {
                mostrarAlerta('erro', data.erro);
            }
        })
        .catch(err => {
            mostrarLoading(false);
            mostrarAlerta('erro', 'Erro ao simular');
        });
}

function mostrarPreview(preview, mes, ano) {
    const content = document.getElementById('preview-content');

    content.innerHTML = `
        <div class="alert alert-info">
            <i class="bi bi-info-circle me-2"></i>
            <strong>Preview do fechamento para ${mes}/${ano}</strong>
        </div>
        <div class="row g-3">
            <div class="col-md-4">
                <div class="card preview-card">
                    <div class="card-header bg-primary text-white">
                        <i class="bi bi-box-seam me-2"></i>Comprados (${preview.resumo.total_comprados})
                    </div>
                    <div class="card-body p-0">
                        <table class="table table-sm mb-0">
                            <thead><tr><th>Codigo</th><th class="text-end">Custo</th></tr></thead>
                            <tbody>
                                ${preview.comprados.slice(0, 20).map(p => `
                                    <tr>
                                        <td>${p.cod_produto}</td>
                                        <td class="text-end">${formatarMoeda(p.custo_liquido_medio)}</td>
                                    </tr>
                                `).join('')}
                                ${preview.comprados.length > 20 ? `<tr><td colspan="2" class="text-muted text-center">... e mais ${preview.comprados.length - 20}</td></tr>` : ''}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card preview-card">
                    <div class="card-header bg-warning">
                        <i class="bi bi-gear me-2"></i>Intermediarios (${preview.resumo.total_intermediarios})
                    </div>
                    <div class="card-body p-0">
                        <table class="table table-sm mb-0">
                            <thead><tr><th>Codigo</th><th class="text-end">Custo BOM</th></tr></thead>
                            <tbody>
                                ${preview.intermediarios.slice(0, 20).map(p => `
                                    <tr>
                                        <td>${p.cod_produto}</td>
                                        <td class="text-end">${p.custo_bom !== null && p.custo_bom !== undefined ? formatarMoeda(p.custo_bom) : '<span class="text-danger">Sem BOM</span>'}</td>
                                    </tr>
                                `).join('')}
                                ${preview.intermediarios.length > 20 ? `<tr><td colspan="2" class="text-muted text-center">... e mais ${preview.intermediarios.length - 20}</td></tr>` : ''}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card preview-card">
                    <div class="card-header bg-success text-white">
                        <i class="bi bi-check-circle me-2"></i>Acabados (${preview.resumo.total_acabados})
                    </div>
                    <div class="card-body p-0">
                        <table class="table table-sm mb-0">
                            <thead><tr><th>Codigo</th><th class="text-end">Custo BOM</th></tr></thead>
                            <tbody>
                                ${preview.acabados.slice(0, 20).map(p => `
                                    <tr>
                                        <td>${p.cod_produto}</td>
                                        <td class="text-end">${p.custo_bom !== null && p.custo_bom !== undefined ? formatarMoeda(p.custo_bom) : '<span class="text-danger">Sem BOM</span>'}</td>
                                    </tr>
                                `).join('')}
                                ${preview.acabados.length > 20 ? `<tr><td colspan="2" class="text-muted text-center">... e mais ${preview.acabados.length - 20}</td></tr>` : ''}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    `;

    new bootstrap.Modal(document.getElementById('modalPreview')).show();
}

function confirmarFechamento() {
    const mes = document.getElementById('filtro-mes').value;
    const ano = document.getElementById('filtro-ano').value;

    document.getElementById('fechamento-periodo').textContent = `${mes}/${ano}`;

    // Fechar modal de preview se estiver aberto
    const previewModal = bootstrap.Modal.getInstance(document.getElementById('modalPreview'));
    if (previewModal) previewModal.hide();

    new bootstrap.Modal(document.getElementById('modalFechamento')).show();
}

function executarFechamento() {
    const mes = document.getElementById('filtro-mes').value;
    const ano = document.getElementById('filtro-ano').value;
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';

    bootstrap.Modal.getInstance(document.getElementById('modalFechamento')).hide();
    mostrarLoading(true);

    fetch('/custeio/api/mensal/fechar', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({ mes: mes, ano: ano })
    })
    .then(r => r.json())
    .then(data => {
        mostrarLoading(false);
        if (data.sucesso) {
            mostrarAlerta('sucesso', data.mensagem);
            buscarCustos();
            carregarEstatisticas();
        } else {
            mostrarAlerta('erro', data.erro);
        }
    })
    .catch(err => {
        mostrarLoading(false);
        mostrarAlerta('erro', 'Erro ao executar fechamento');
    });
}

function exportarExcel(tipo) {
    const mes = document.getElementById('filtro-mes').value;
    const ano = document.getElementById('filtro-ano').value;

    let url = `/custeio/api/exportar-excel?tipo=${tipo}`;
    if (tipo === 'mensal') {
        url += `&mes=${mes}&ano=${ano}`;
    }

    window.location.href = url;
}

// ==========================================================================
// FUNCOES UTILITARIAS
// ==========================================================================
function formatarMoeda(valor) {
    if (valor === null || valor === undefined || valor === 0) return '-';
    return valor.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

function formatarNumero(valor) {
    if (valor === null || valor === undefined || valor === 0) return '-';
    return valor.toLocaleString('pt-BR', { minimumFractionDigits: 0, maximumFractionDigits: 3 });
}

function mostrarLoading(show) {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.classList.toggle('show', show);
    }
}

function mostrarAlerta(tipo, mensagem) {
    // Usar toast ou alert simples
    if (tipo === 'erro') {
        alert('Erro: ' + mensagem);
    } else {
        alert(mensagem);
    }
}

// ==========================================================================
// CUSTO FRETE - CRUD
// ==========================================================================
let dadosFrete = [];

function carregarCustosFrete() {
    mostrarLoading(true);

    fetch('/custeio/api/frete/listar?apenas_vigentes=false')
        .then(r => r.json())
        .then(data => {
            mostrarLoading(false);
            if (data.sucesso) {
                dadosFrete = data.dados;
                renderizarTabelaFrete();
            }
        })
        .catch(err => {
            mostrarLoading(false);
            console.error(err);
        });
}

function renderizarTabelaFrete() {
    const tbody = document.getElementById('tbody-frete');

    if (dadosFrete.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center text-muted py-4">
                    <i class="bi bi-inbox me-2"></i>Nenhum registro cadastrado
                </td>
            </tr>`;
        return;
    }

    tbody.innerHTML = dadosFrete.map(item => `
        <tr>
            <td><span class="badge bg-info">${item.incoterm}</span></td>
            <td><span class="badge bg-secondary">${item.cod_uf}</span></td>
            <td class="text-end"><strong>${item.percentual_frete.toFixed(2)}%</strong></td>
            <td>${item.vigencia_inicio || '-'}</td>
            <td>${item.vigencia_fim || '<span class="text-success">Vigente</span>'}</td>
            <td>${item.criado_por || '-'}</td>
            <td class="text-center">
                <button class="btn btn-outline-primary btn-sm" onclick="editarFrete(${item.id})">
                    <i class="bi bi-pencil"></i>
                </button>
                <button class="btn btn-outline-danger btn-sm" onclick="excluirFrete(${item.id})">
                    <i class="bi bi-trash"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

function abrirModalFrete(id = null) {
    document.getElementById('frete-id').value = '';
    document.getElementById('frete-incoterm').value = '';
    document.getElementById('frete-uf').value = '';
    document.getElementById('frete-percentual').value = '';
    document.getElementById('frete-vigencia-inicio').value = new Date().toISOString().split('T')[0];
    document.getElementById('frete-vigencia-fim').value = '';

    new bootstrap.Modal(document.getElementById('modalFrete')).show();
}

function editarFrete(id) {
    const item = dadosFrete.find(f => f.id === id);
    if (!item) return;

    document.getElementById('frete-id').value = item.id;
    document.getElementById('frete-incoterm').value = item.incoterm;
    document.getElementById('frete-uf').value = item.cod_uf;
    document.getElementById('frete-percentual').value = item.percentual_frete;
    document.getElementById('frete-vigencia-inicio').value = item.vigencia_inicio || '';
    document.getElementById('frete-vigencia-fim').value = item.vigencia_fim || '';

    new bootstrap.Modal(document.getElementById('modalFrete')).show();
}

function salvarFrete() {
    const id = document.getElementById('frete-id').value;
    const incoterm = document.getElementById('frete-incoterm').value;
    const cod_uf = document.getElementById('frete-uf').value;
    const percentual_frete = parseFloat(document.getElementById('frete-percentual').value);
    const vigencia_inicio = document.getElementById('frete-vigencia-inicio').value;
    const vigencia_fim = document.getElementById('frete-vigencia-fim').value;

    if (!incoterm || !cod_uf || isNaN(percentual_frete)) {
        mostrarAlerta('erro', 'Preencha todos os campos obrigatorios');
        return;
    }

    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';

    fetch('/custeio/api/frete/salvar', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({
            id: id || null,
            incoterm,
            cod_uf,
            percentual_frete,
            vigencia_inicio,
            vigencia_fim: vigencia_fim || null
        })
    })
    .then(r => r.json())
    .then(data => {
        if (data.sucesso) {
            bootstrap.Modal.getInstance(document.getElementById('modalFrete')).hide();
            mostrarAlerta('sucesso', data.mensagem);
            carregarCustosFrete();
        } else {
            mostrarAlerta('erro', data.erro);
        }
    })
    .catch(err => {
        console.error(err);
        mostrarAlerta('erro', 'Erro ao salvar');
    });
}

function excluirFrete(id) {
    if (!confirm('Deseja excluir este registro?')) return;

    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';

    fetch(`/custeio/api/frete/excluir/${id}`, {
        method: 'DELETE',
        headers: {
            'X-CSRFToken': csrfToken
        }
    })
    .then(r => r.json())
    .then(data => {
        if (data.sucesso) {
            mostrarAlerta('sucesso', data.mensagem);
            carregarCustosFrete();
        } else {
            mostrarAlerta('erro', data.erro);
        }
    })
    .catch(err => {
        console.error(err);
        mostrarAlerta('erro', 'Erro ao excluir');
    });
}

// ==========================================================================
// PARAMETROS - CRUD
// ==========================================================================
let dadosParametros = [];

function carregarParametros() {
    mostrarLoading(true);

    fetch('/custeio/api/parametros/listar')
        .then(r => r.json())
        .then(data => {
            mostrarLoading(false);
            if (data.sucesso) {
                dadosParametros = data.dados;
                renderizarTabelaParametros();
            }
        })
        .catch(err => {
            mostrarLoading(false);
            console.error(err);
        });
}

function renderizarTabelaParametros() {
    const tbody = document.getElementById('tbody-parametros');

    if (dadosParametros.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center text-muted py-4">
                    <i class="bi bi-inbox me-2"></i>Nenhum parametro cadastrado
                </td>
            </tr>`;
        return;
    }

    tbody.innerHTML = dadosParametros.map(item => `
        <tr>
            <td><code>${item.chave}</code></td>
            <td class="text-end"><strong>${item.valor}</strong></td>
            <td>${item.descricao || '-'}</td>
            <td>${item.atualizado_em || '-'}</td>
            <td>${item.atualizado_por || '-'}</td>
            <td class="text-center">
                <button class="btn btn-outline-primary btn-sm" onclick="editarParametro(${item.id})">
                    <i class="bi bi-pencil"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

function abrirModalParametro() {
    document.getElementById('parametro-id').value = '';
    document.getElementById('parametro-chave').value = '';
    document.getElementById('parametro-chave').disabled = false;
    document.getElementById('parametro-valor').value = '';
    document.getElementById('parametro-descricao').value = '';

    new bootstrap.Modal(document.getElementById('modalParametro')).show();
}

function editarParametro(id) {
    const item = dadosParametros.find(p => p.id === id);
    if (!item) return;

    document.getElementById('parametro-id').value = item.id;
    document.getElementById('parametro-chave').value = item.chave;
    document.getElementById('parametro-chave').disabled = true; // Nao permitir editar chave
    document.getElementById('parametro-valor').value = item.valor;
    document.getElementById('parametro-descricao').value = item.descricao || '';

    new bootstrap.Modal(document.getElementById('modalParametro')).show();
}

function salvarParametro() {
    const id = document.getElementById('parametro-id').value;
    const chave = document.getElementById('parametro-chave').value;
    const valor = parseFloat(document.getElementById('parametro-valor').value);
    const descricao = document.getElementById('parametro-descricao').value;

    if (!chave || isNaN(valor)) {
        mostrarAlerta('erro', 'Preencha chave e valor');
        return;
    }

    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';

    fetch('/custeio/api/parametros/salvar', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({
            id: id || null,
            chave,
            valor,
            descricao
        })
    })
    .then(r => r.json())
    .then(data => {
        if (data.sucesso) {
            bootstrap.Modal.getInstance(document.getElementById('modalParametro')).hide();
            mostrarAlerta('sucesso', data.mensagem);
            carregarParametros();
        } else {
            mostrarAlerta('erro', data.erro);
        }
    })
    .catch(err => {
        console.error(err);
        mostrarAlerta('erro', 'Erro ao salvar');
    });
}

// ==========================================================================
// IMPORTACAO EXCEL
// ==========================================================================

function importarFrete(input) {
    if (!input.files || input.files.length === 0) return;

    const arquivo = input.files[0];
    const formData = new FormData();
    formData.append('arquivo', arquivo);

    mostrarLoading(true);
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';

    fetch('/custeio/api/frete/importar', {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrfToken
        },
        body: formData
    })
    .then(r => r.json())
    .then(data => {
        mostrarLoading(false);
        input.value = ''; // Limpar input

        if (data.sucesso) {
            let msg = data.mensagem;
            if (data.erros && data.erros.length > 0) {
                msg += '\n\nErros:\n' + data.erros.join('\n');
            }
            mostrarAlerta('sucesso', msg);
            carregarCustosFrete();
        } else {
            mostrarAlerta('erro', data.erro);
        }
    })
    .catch(err => {
        mostrarLoading(false);
        input.value = '';
        console.error(err);
        mostrarAlerta('erro', 'Erro ao importar arquivo');
    });
}

function importarParametros(input) {
    if (!input.files || input.files.length === 0) return;

    const arquivo = input.files[0];
    const formData = new FormData();
    formData.append('arquivo', arquivo);

    mostrarLoading(true);
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';

    fetch('/custeio/api/parametros/importar', {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrfToken
        },
        body: formData
    })
    .then(r => r.json())
    .then(data => {
        mostrarLoading(false);
        input.value = '';

        if (data.sucesso) {
            let msg = data.mensagem;
            if (data.erros && data.erros.length > 0) {
                msg += '\n\nErros:\n' + data.erros.join('\n');
            }
            mostrarAlerta('sucesso', msg);
            carregarParametros();
        } else {
            mostrarAlerta('erro', data.erro);
        }
    })
    .catch(err => {
        mostrarLoading(false);
        input.value = '';
        console.error(err);
        mostrarAlerta('erro', 'Erro ao importar arquivo');
    });
}

// ==========================================================================
// CADASTRO MANUAL DE CUSTO CONSIDERADO
// ==========================================================================
let debounceTimerProduto;

function abrirModalCadastro() {
    document.getElementById('cadastro-cod-produto').value = '';
    document.getElementById('cadastro-produto-busca').value = '';
    document.getElementById('cadastro-produto-selecionado').textContent = '';
    document.getElementById('cadastro-custo').value = '';
    document.getElementById('cadastro-producao').value = '';
    document.getElementById('cadastro-tipo').value = 'MEDIO_MES';
    document.getElementById('cadastro-motivo').value = '';

    new bootstrap.Modal(document.getElementById('modalCadastro')).show();

    // Configurar busca de produto com debounce
    const inputBusca = document.getElementById('cadastro-produto-busca');
    inputBusca.removeEventListener('input', buscarProdutosDebounce);
    inputBusca.addEventListener('input', buscarProdutosDebounce);
}

function buscarProdutosDebounce() {
    clearTimeout(debounceTimerProduto);
    debounceTimerProduto = setTimeout(buscarProdutos, 300);
}

function buscarProdutos() {
    const termo = document.getElementById('cadastro-produto-busca').value;
    const lista = document.getElementById('cadastro-produto-lista');

    if (termo.length < 2) {
        lista.style.display = 'none';
        return;
    }

    fetch(`/custeio/api/produtos/buscar?termo=${encodeURIComponent(termo)}`)
        .then(r => r.json())
        .then(data => {
            if (data.dados && data.dados.length > 0) {
                lista.innerHTML = data.dados.map(p => `
                    <a href="#" class="list-group-item list-group-item-action"
                       onclick="selecionarProduto('${p.cod_produto}', '${p.nome_produto.replace(/'/g, "\\'")}', '${p.tipo}'); return false;">
                        <strong>${p.cod_produto}</strong> - ${p.nome_produto}
                        <span class="badge bg-secondary ms-2">${p.tipo}</span>
                    </a>
                `).join('');
                lista.style.display = 'block';
            } else {
                lista.innerHTML = '<div class="list-group-item text-muted">Nenhum produto encontrado</div>';
                lista.style.display = 'block';
            }
        })
        .catch(err => {
            console.error(err);
            lista.style.display = 'none';
        });
}

function selecionarProduto(cod, nome, tipo) {
    document.getElementById('cadastro-cod-produto').value = cod;
    document.getElementById('cadastro-produto-busca').value = cod;
    document.getElementById('cadastro-produto-selecionado').textContent = `${nome} (${tipo})`;
    document.getElementById('cadastro-produto-lista').style.display = 'none';

    // Se for acabado ou intermediario, sugerir tipo BOM
    if (tipo === 'ACABADO' || tipo === 'INTERMEDIARIO') {
        document.getElementById('cadastro-tipo').value = 'BOM';
    } else {
        document.getElementById('cadastro-tipo').value = 'MEDIO_MES';
    }
}

function salvarCadastroManual() {
    const codProduto = document.getElementById('cadastro-cod-produto').value;
    const custo = document.getElementById('cadastro-custo').value;
    const producao = document.getElementById('cadastro-producao').value;
    const tipo = document.getElementById('cadastro-tipo').value;
    const motivo = document.getElementById('cadastro-motivo').value;

    if (!codProduto) {
        mostrarAlerta('erro', 'Selecione um produto');
        return;
    }

    if (!custo || isNaN(parseFloat(custo))) {
        mostrarAlerta('erro', 'Informe o custo considerado');
        return;
    }

    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';

    mostrarLoading(true);

    fetch('/custeio/api/considerado/cadastrar', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({
            cod_produto: codProduto,
            custo_considerado: parseFloat(custo),
            custo_producao: producao ? parseFloat(producao) : null,
            tipo_custo: tipo,
            motivo: motivo
        })
    })
    .then(r => r.json())
    .then(data => {
        mostrarLoading(false);
        if (data.sucesso) {
            bootstrap.Modal.getInstance(document.getElementById('modalCadastro')).hide();
            mostrarAlerta('sucesso', data.mensagem);
            buscarCustosConsiderados();
            carregarEstatisticas();
        } else {
            mostrarAlerta('erro', data.erro);
        }
    })
    .catch(err => {
        mostrarLoading(false);
        console.error(err);
        mostrarAlerta('erro', 'Erro ao salvar custo');
    });
}

// Fechar lista de produtos ao clicar fora
document.addEventListener('click', function(e) {
    const lista = document.getElementById('cadastro-produto-lista');
    const input = document.getElementById('cadastro-produto-busca');
    if (lista && !lista.contains(e.target) && e.target !== input) {
        lista.style.display = 'none';
    }
});
