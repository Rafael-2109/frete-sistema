/**
 * CUSTEIO - Regras de Comissao JavaScript
 * Hierarquia de especificidade: regra mais especifica prevalece
 */

// ==========================================================================
// VARIAVEIS GLOBAIS
// ==========================================================================
let dadosComissao = [];
let gruposDisponiveis = [];
let vendedoresDisponiveis = [];

// Ordem de especificidade
const ORDEM_ESPECIFICIDADE = {
    'CLIENTE_PRODUTO': 1,
    'GRUPO_PRODUTO': 2,
    'VENDEDOR_PRODUTO': 3,
    'CLIENTE': 4,
    'GRUPO': 5,
    'VENDEDOR': 6,
    'PRODUTO': 7
};

const BADGES_TIPO = {
    'CLIENTE_PRODUTO': 'bg-danger',
    'GRUPO_PRODUTO': 'bg-warning text-dark',
    'VENDEDOR_PRODUTO': 'bg-primary',
    'CLIENTE': 'bg-success',
    'GRUPO': 'bg-secondary',
    'VENDEDOR': 'bg-info',
    'PRODUTO': 'bg-dark'
};

// ==========================================================================
// INICIALIZACAO
// ==========================================================================
document.addEventListener('DOMContentLoaded', function() {
    carregarDadosAuxiliares();
    carregarDados();
    configurarAutocomplete();
});

async function carregarDadosAuxiliares() {
    try {
        // Carregar grupos
        const resGrupos = await fetch('/custeio/api/comissao/grupos');
        const dataGrupos = await resGrupos.json();
        if (dataGrupos.sucesso) {
            gruposDisponiveis = dataGrupos.dados;
            popularSelectGrupos();
        }

        // Carregar vendedores
        const resVendedores = await fetch('/custeio/api/comissao/vendedores');
        const dataVendedores = await resVendedores.json();
        if (dataVendedores.sucesso) {
            vendedoresDisponiveis = dataVendedores.dados;
            popularSelectVendedores();
        }

    } catch (err) {
        console.error('Erro ao carregar dados auxiliares:', err);
    }
}

function popularSelectGrupos() {
    const select = document.getElementById('comissao-grupo');
    if (select) {
        select.innerHTML = '<option value="">Selecione</option>';
        gruposDisponiveis.forEach(grupo => {
            const option = document.createElement('option');
            option.value = grupo;
            option.textContent = grupo;
            select.appendChild(option);
        });
    }
}

function popularSelectVendedores() {
    const select = document.getElementById('comissao-vendedor');
    if (select) {
        select.innerHTML = '<option value="">Selecione</option>';
        vendedoresDisponiveis.forEach(vendedor => {
            const option = document.createElement('option');
            option.value = vendedor;
            option.textContent = vendedor;
            select.appendChild(option);
        });
    }
}

// ==========================================================================
// AUTOCOMPLETE
// ==========================================================================
function configurarAutocomplete() {
    // Cliente
    const inputCliente = document.getElementById('comissao-cliente');
    if (inputCliente) {
        inputCliente.addEventListener('input', debounce(function() {
            buscarSugestoes('cliente', this.value, 'sugestoes-cliente');
        }, 300));
    }

    // Produto
    const inputProduto = document.getElementById('comissao-produto');
    if (inputProduto) {
        inputProduto.addEventListener('input', debounce(function() {
            buscarSugestoes('produto', this.value, 'sugestoes-produto');
        }, 300));
    }

    // Fechar sugestoes ao clicar fora
    document.addEventListener('click', function(e) {
        if (!e.target.closest('.sugestoes-autocomplete') && !e.target.closest('input[type="text"]')) {
            document.querySelectorAll('.sugestoes-autocomplete').forEach(el => el.classList.remove('show'));
        }
    });
}

function debounce(func, wait) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}

async function buscarSugestoes(tipo, termo, containerId) {
    const container = document.getElementById(containerId);
    if (!termo || termo.length < 2) {
        container.classList.remove('show');
        return;
    }

    try {
        let url;
        if (tipo === 'cliente') {
            url = `/custeio/api/comissao/clientes?termo=${encodeURIComponent(termo)}`;
        } else {
            url = `/custeio/api/comissao/produtos?termo=${encodeURIComponent(termo)}`;
        }

        const response = await fetch(url);
        const data = await response.json();

        if (data.sucesso && data.dados.length > 0) {
            if (tipo === 'cliente') {
                container.innerHTML = data.dados.map(c =>
                    `<div class="sugestao-item" onclick="selecionarSugestao('${containerId}', '${c.raz_social_red}')">
                        ${c.raz_social_red}
                    </div>`
                ).join('');
            } else {
                container.innerHTML = data.dados.map(p =>
                    `<div class="sugestao-item" onclick="selecionarSugestao('${containerId}', '${p.cod_produto}')">
                        ${p.cod_produto}
                        <small class="text-muted d-block">${p.nome_produto}</small>
                    </div>`
                ).join('');
            }
            container.classList.add('show');
        } else {
            container.classList.remove('show');
        }

    } catch (err) {
        console.error('Erro ao buscar sugestoes:', err);
        container.classList.remove('show');
    }
}

function selecionarSugestao(containerId, valor) {
    const container = document.getElementById(containerId);
    const inputId = containerId.replace('sugestoes-', 'comissao-');
    const input = document.getElementById(inputId);
    if (input) {
        input.value = valor;
    }
    container.classList.remove('show');
}

// ==========================================================================
// CARREGAR DADOS
// ==========================================================================
function carregarDados() {
    const tipoFiltro = document.getElementById('filtro-tipo').value;
    const apenasAtivos = document.getElementById('filtro-ativos').checked;

    let url = `/custeio/api/comissao/listar?apenas_ativos=${apenasAtivos}`;
    if (tipoFiltro) {
        url += `&tipo_regra=${tipoFiltro}`;
    }

    mostrarLoading(true);

    fetch(url)
        .then(r => r.json())
        .then(data => {
            mostrarLoading(false);
            if (data.sucesso) {
                dadosComissao = data.dados;
                atualizarEstatisticas();
                renderizarTabela(dadosComissao);
            }
        })
        .catch(err => {
            mostrarLoading(false);
            console.error(err);
            alert('Erro ao carregar dados');
        });
}

function atualizarEstatisticas() {
    const compostas = dadosComissao.filter(d =>
        ['CLIENTE_PRODUTO', 'GRUPO_PRODUTO', 'VENDEDOR_PRODUTO'].includes(d.tipo_regra)
    ).length;
    const simples = dadosComissao.filter(d =>
        ['CLIENTE', 'GRUPO', 'VENDEDOR', 'PRODUTO'].includes(d.tipo_regra)
    ).length;

    document.getElementById('stat-compostas').textContent = compostas;
    document.getElementById('stat-simples').textContent = simples;
    document.getElementById('stat-total').textContent = dadosComissao.length;
}

// ==========================================================================
// FILTROS E RENDERIZACAO
// ==========================================================================
function filtrarLocal() {
    const termo = document.getElementById('filtro-busca').value.toLowerCase();
    let filtrados = dadosComissao;

    if (termo) {
        filtrados = dadosComissao.filter(d =>
            (d.grupo_empresarial || '').toLowerCase().includes(termo) ||
            (d.raz_social_red || '').toLowerCase().includes(termo) ||
            (d.vendedor || '').toLowerCase().includes(termo) ||
            (d.cod_produto || '').toLowerCase().includes(termo) ||
            (d.descricao || '').toLowerCase().includes(termo)
        );
    }

    renderizarTabela(filtrados);
}

function renderizarTabela(dados) {
    const tbody = document.getElementById('tbody-comissao');
    document.getElementById('total-registros').textContent = `${dados.length} regra(s)`;

    if (dados.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="empty-state">
                    <i class="bi bi-inbox"></i>
                    <p>Nenhuma regra encontrada</p>
                </td>
            </tr>`;
        return;
    }

    // Ordenar por especificidade
    const dadosOrdenados = [...dados].sort((a, b) => {
        const ordemA = ORDEM_ESPECIFICIDADE[a.tipo_regra] || 99;
        const ordemB = ORDEM_ESPECIFICIDADE[b.tipo_regra] || 99;
        return ordemA - ordemB;
    });

    tbody.innerHTML = dadosOrdenados.map(item => {
        const ordem = ORDEM_ESPECIFICIDADE[item.tipo_regra] || '?';
        const badgeClass = BADGES_TIPO[item.tipo_regra] || 'bg-secondary';
        const criterios = montarCriterios(item);

        const vigencia = item.vigencia_fim
            ? `${formatarData(item.vigencia_inicio)} a ${formatarData(item.vigencia_fim)}`
            : `${formatarData(item.vigencia_inicio)}`;

        return `
            <tr>
                <td><span class="badge ${badgeClass}">${ordem}</span></td>
                <td><span class="badge ${badgeClass}">${formatarTipo(item.tipo_regra)}</span></td>
                <td>${criterios}</td>
                <td class="text-end"><strong>${item.comissao_percentual.toFixed(2)}%</strong></td>
                <td><small>${vigencia}</small></td>
                <td><small title="${item.descricao || ''}">${(item.descricao || '-').substring(0, 20)}${item.descricao && item.descricao.length > 20 ? '...' : ''}</small></td>
                <td class="text-center">
                    <button class="btn btn-outline-primary btn-sm" onclick="editarComissao(${item.id})" title="Editar">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-outline-danger btn-sm" onclick="excluirComissao(${item.id})" title="Desativar">
                        <i class="bi bi-trash"></i>
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

function montarCriterios(item) {
    const partes = [];

    if (item.raz_social_red) partes.push(`<strong>Cliente:</strong> ${item.raz_social_red}`);
    if (item.grupo_empresarial) partes.push(`<strong>Grupo:</strong> ${item.grupo_empresarial}`);
    if (item.vendedor) partes.push(`<strong>Vendedor:</strong> ${item.vendedor}`);
    if (item.cod_produto) partes.push(`<strong>Produto:</strong> ${item.cod_produto}`);

    return partes.join(' | ') || '-';
}

function formatarTipo(tipo) {
    const nomes = {
        'CLIENTE_PRODUTO': 'Cliente+Prod',
        'GRUPO_PRODUTO': 'Grupo+Prod',
        'VENDEDOR_PRODUTO': 'Vend+Prod',
        'CLIENTE': 'Cliente',
        'GRUPO': 'Grupo',
        'VENDEDOR': 'Vendedor',
        'PRODUTO': 'Produto'
    };
    return nomes[tipo] || tipo;
}

function formatarData(data) {
    if (!data) return '-';
    const partes = data.split('-');
    return `${partes[2]}/${partes[1]}/${partes[0]}`;
}

// ==========================================================================
// TIPO DE REGRA
// ==========================================================================
function alterarTipoRegra() {
    const tipo = document.getElementById('comissao-tipo').value;
    const container = document.getElementById('campos-dinamicos');

    // Ocultar todos os campos
    document.getElementById('campo-cliente').style.display = 'none';
    document.getElementById('campo-grupo').style.display = 'none';
    document.getElementById('campo-vendedor').style.display = 'none';
    document.getElementById('campo-produto').style.display = 'none';

    if (!tipo) {
        container.style.display = 'none';
        return;
    }

    container.style.display = 'block';

    // Mostrar campos conforme tipo
    if (tipo === 'CLIENTE_PRODUTO') {
        document.getElementById('campo-cliente').style.display = 'block';
        document.getElementById('campo-produto').style.display = 'block';
    } else if (tipo === 'GRUPO_PRODUTO') {
        document.getElementById('campo-grupo').style.display = 'block';
        document.getElementById('campo-produto').style.display = 'block';
    } else if (tipo === 'VENDEDOR_PRODUTO') {
        document.getElementById('campo-vendedor').style.display = 'block';
        document.getElementById('campo-produto').style.display = 'block';
    } else if (tipo === 'CLIENTE') {
        document.getElementById('campo-cliente').style.display = 'block';
    } else if (tipo === 'GRUPO') {
        document.getElementById('campo-grupo').style.display = 'block';
    } else if (tipo === 'VENDEDOR') {
        document.getElementById('campo-vendedor').style.display = 'block';
    } else if (tipo === 'PRODUTO') {
        document.getElementById('campo-produto').style.display = 'block';
    }
}

// ==========================================================================
// CRUD OPERATIONS
// ==========================================================================
function abrirModalComissao() {
    limparFormulario();
    document.getElementById('comissao-vigencia-inicio').value = new Date().toISOString().split('T')[0];
    new bootstrap.Modal(document.getElementById('modalComissao')).show();
}

function limparFormulario() {
    document.getElementById('comissao-id').value = '';
    document.getElementById('comissao-tipo').value = '';
    document.getElementById('campos-dinamicos').style.display = 'none';

    document.getElementById('comissao-cliente').value = '';
    document.getElementById('comissao-grupo').value = '';
    document.getElementById('comissao-vendedor').value = '';
    document.getElementById('comissao-produto').value = '';
    document.getElementById('comissao-percentual').value = '';
    document.getElementById('comissao-vigencia-inicio').value = '';
    document.getElementById('comissao-vigencia-fim').value = '';
    document.getElementById('comissao-descricao').value = '';
}

function editarComissao(id) {
    const item = dadosComissao.find(c => c.id === id);
    if (!item) return;

    limparFormulario();

    document.getElementById('comissao-id').value = item.id;
    document.getElementById('comissao-tipo').value = item.tipo_regra;
    alterarTipoRegra();

    document.getElementById('comissao-cliente').value = item.raz_social_red || '';
    document.getElementById('comissao-grupo').value = item.grupo_empresarial || '';
    document.getElementById('comissao-vendedor').value = item.vendedor || '';
    document.getElementById('comissao-produto').value = item.cod_produto || '';
    document.getElementById('comissao-percentual').value = item.comissao_percentual;
    document.getElementById('comissao-vigencia-inicio').value = item.vigencia_inicio || '';
    document.getElementById('comissao-vigencia-fim').value = item.vigencia_fim || '';
    document.getElementById('comissao-descricao').value = item.descricao || '';

    new bootstrap.Modal(document.getElementById('modalComissao')).show();
}

function salvarComissao() {
    const id = document.getElementById('comissao-id').value;
    const tipoRegra = document.getElementById('comissao-tipo').value;
    const comissaoPercentual = parseFloat(document.getElementById('comissao-percentual').value);

    if (!tipoRegra) {
        alert('Selecione o tipo de regra');
        return;
    }

    if (isNaN(comissaoPercentual)) {
        alert('Informe o percentual de comissao');
        return;
    }

    let dados = {
        id: id || null,
        tipo_regra: tipoRegra,
        comissao_percentual: comissaoPercentual,
        vigencia_inicio: document.getElementById('comissao-vigencia-inicio').value,
        vigencia_fim: document.getElementById('comissao-vigencia-fim').value || null,
        descricao: document.getElementById('comissao-descricao').value
    };

    // Campos conforme tipo
    dados.raz_social_red = document.getElementById('comissao-cliente').value || null;
    dados.grupo_empresarial = document.getElementById('comissao-grupo').value || null;
    dados.vendedor = document.getElementById('comissao-vendedor').value || null;
    dados.cod_produto = document.getElementById('comissao-produto').value || null;

    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';

    mostrarLoading(true);

    fetch('/custeio/api/comissao/salvar', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify(dados)
    })
    .then(r => r.json())
    .then(data => {
        mostrarLoading(false);
        if (data.sucesso) {
            bootstrap.Modal.getInstance(document.getElementById('modalComissao')).hide();
            alert('Regra salva com sucesso!');
            carregarDados();
        } else {
            alert('Erro: ' + (data.erro || 'Erro desconhecido'));
        }
    })
    .catch(err => {
        mostrarLoading(false);
        console.error(err);
        alert('Erro ao salvar');
    });
}

function excluirComissao(id) {
    if (!confirm('Deseja desativar esta regra?')) return;

    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';

    mostrarLoading(true);

    fetch(`/custeio/api/comissao/excluir/${id}`, {
        method: 'DELETE',
        headers: { 'X-CSRFToken': csrfToken }
    })
    .then(r => r.json())
    .then(data => {
        mostrarLoading(false);
        if (data.sucesso) {
            alert('Regra desativada com sucesso!');
            carregarDados();
        } else {
            alert('Erro: ' + (data.erro || 'Erro desconhecido'));
        }
    })
    .catch(err => {
        mostrarLoading(false);
        console.error(err);
        alert('Erro ao desativar');
    });
}

// ==========================================================================
// RECALCULO DE MARGEM
// ==========================================================================
function abrirModalRecalculo() {
    document.getElementById('recalculo-escopo').value = 'pedido';
    document.getElementById('recalculo-num-pedido').value = '';
    document.getElementById('recalculo-cod-produto').value = '';
    document.getElementById('recalculo-resultado').style.display = 'none';
    alterarEscopoRecalculo();
    new bootstrap.Modal(document.getElementById('modalRecalculo')).show();
}

function alterarEscopoRecalculo() {
    const escopo = document.getElementById('recalculo-escopo').value;
    document.getElementById('recalculo-pedido').style.display = escopo === 'pedido' ? 'block' : 'none';
    document.getElementById('recalculo-produto').style.display = escopo === 'produto' ? 'block' : 'none';
}

function executarRecalculo() {
    const escopo = document.getElementById('recalculo-escopo').value;
    const resultadoEl = document.getElementById('recalculo-resultado');

    let dados = {};

    if (escopo === 'pedido') {
        dados.num_pedido = document.getElementById('recalculo-num-pedido').value;
        if (!dados.num_pedido) {
            alert('Informe o numero do pedido');
            return;
        }
    } else if (escopo === 'produto') {
        dados.cod_produto = document.getElementById('recalculo-cod-produto').value;
        if (!dados.cod_produto) {
            alert('Informe o codigo do produto');
            return;
        }
    } else {
        dados.todos = true;
        if (!confirm('Isso ira recalcular TODOS os pedidos com saldo. Confirma?')) {
            return;
        }
    }

    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';

    mostrarLoading(true);

    fetch('/custeio/api/margem/recalcular', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify(dados)
    })
    .then(r => r.json())
    .then(data => {
        mostrarLoading(false);
        if (data.sucesso) {
            resultadoEl.innerHTML = `
                <i class="bi bi-check-circle me-2"></i>
                <strong>${data.mensagem}</strong>
                ${data.erros && data.erros.length > 0 ?
                    '<br><small class="text-danger">Erros: ' + data.erros.slice(0, 3).join(', ') + '</small>' : ''}
            `;
            resultadoEl.classList.remove('alert-info', 'alert-danger');
            resultadoEl.classList.add('alert-success');
            resultadoEl.style.display = 'block';
        } else {
            resultadoEl.innerHTML = `<i class="bi bi-x-circle me-2"></i>${data.erro}`;
            resultadoEl.classList.remove('alert-info', 'alert-success');
            resultadoEl.classList.add('alert-danger');
            resultadoEl.style.display = 'block';
        }
    })
    .catch(err => {
        mostrarLoading(false);
        console.error(err);
        resultadoEl.innerHTML = `<i class="bi bi-x-circle me-2"></i>Erro ao recalcular`;
        resultadoEl.classList.add('alert-danger');
        resultadoEl.style.display = 'block';
    });
}

// ==========================================================================
// IMPORT/EXPORT
// ==========================================================================
function exportarComissao() {
    window.location.href = '/custeio/api/comissao/exportar';
}

function baixarModelo() {
    window.location.href = '/custeio/api/comissao/modelo';
}

function importarComissao(input) {
    if (!input.files || input.files.length === 0) return;

    const arquivo = input.files[0];
    const formData = new FormData();
    formData.append('arquivo', arquivo);

    mostrarLoading(true);
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';

    fetch('/custeio/api/comissao/importar', {
        method: 'POST',
        headers: { 'X-CSRFToken': csrfToken },
        body: formData
    })
    .then(r => r.json())
    .then(data => {
        mostrarLoading(false);
        input.value = '';

        if (data.sucesso) {
            let msg = data.mensagem;
            if (data.erros && data.erros.length > 0) {
                msg += '\n\nErros:\n' + data.erros.slice(0, 5).join('\n');
            }
            alert(msg);
            carregarDados();
        } else {
            alert('Erro: ' + (data.erro || 'Erro desconhecido'));
        }
    })
    .catch(err => {
        mostrarLoading(false);
        input.value = '';
        console.error(err);
        alert('Erro ao importar arquivo');
    });
}

// ==========================================================================
// LOADING
// ==========================================================================
function mostrarLoading(show) {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.classList.toggle('show', show);
    }
}
