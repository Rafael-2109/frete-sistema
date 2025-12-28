/**
 * Analise de Margem - JavaScript
 * Controle de agrupamentos, filtros e visualizacao de dados
 */

// Estado global
let dadosAtuais = [];
let filtrosDisponiveis = {};
let paginaAtual = 1;
let totalPaginas = 1;
const ITENS_POR_PAGINA = 50;

// Inicializacao
document.addEventListener('DOMContentLoaded', function() {
    carregarFiltros();
    definirDatasDefault();
});

/**
 * Define datas padrao (ultimos 30 dias)
 */
function definirDatasDefault() {
    const hoje = new Date();
    const inicio = new Date();
    inicio.setDate(hoje.getDate() - 30);

    document.getElementById('filtro-data-inicio').value = formatarDataInput(inicio);
    document.getElementById('filtro-data-fim').value = formatarDataInput(hoje);
}

/**
 * Formata data para input date
 */
function formatarDataInput(data) {
    return data.toISOString().split('T')[0];
}

/**
 * Carrega filtros disponiveis da API
 */
async function carregarFiltros() {
    try {
        const response = await fetch('/comercial/api/margem/filtros');
        const data = await response.json();

        if (data.sucesso) {
            filtrosDisponiveis = data.filtros;
            preencherSelectFiltros();
        }
    } catch (error) {
        console.error('Erro ao carregar filtros:', error);
    }
}

/**
 * Preenche os selects de filtros
 */
function preencherSelectFiltros() {
    // Equipes
    const selectEquipe = document.getElementById('filtro-equipe');
    selectEquipe.innerHTML = '<option value="">Todas</option>';
    filtrosDisponiveis.equipes?.forEach(e => {
        selectEquipe.innerHTML += `<option value="${e}">${e}</option>`;
    });

    // Vendedores
    const selectVendedor = document.getElementById('filtro-vendedor');
    selectVendedor.innerHTML = '<option value="">Todos</option>';
    filtrosDisponiveis.vendedores?.forEach(v => {
        selectVendedor.innerHTML += `<option value="${v}">${v}</option>`;
    });

    // Tipos de produto (default: embalagem)
    carregarTiposProduto();
}

/**
 * Carrega tipos de produto baseado no campo selecionado
 */
function carregarTiposProduto() {
    const campo = document.getElementById('filtro-tipo-campo').value;
    const selectTipo = document.getElementById('filtro-tipo-produto');

    selectTipo.innerHTML = '<option value="">Todos</option>';

    const tipos = filtrosDisponiveis.tipos_produto?.[campo] || [];
    tipos.forEach(t => {
        selectTipo.innerHTML += `<option value="${t}">${t}</option>`;
    });
}

/**
 * Carrega dados da API
 */
async function carregarDados() {
    mostrarLoading(true);
    paginaAtual = 1;

    try {
        const params = construirParametros();
        const response = await fetch(`/comercial/api/margem/dados?${params}`);
        const data = await response.json();

        if (data.sucesso) {
            dadosAtuais = data.dados;
            atualizarTotais(data.totais);
            atualizarPaginacao(data.paginacao);
            renderizarTabela();
        } else {
            mostrarErro(data.erro || 'Erro ao carregar dados');
        }
    } catch (error) {
        console.error('Erro ao carregar dados:', error);
        mostrarErro('Erro de conexao');
    } finally {
        mostrarLoading(false);
    }
}

/**
 * Constroi parametros da query
 */
function construirParametros() {
    const params = new URLSearchParams();

    params.append('agrupamento', document.getElementById('filtro-agrupamento').value);
    params.append('page', paginaAtual);
    params.append('per_page', ITENS_POR_PAGINA);

    const dataInicio = document.getElementById('filtro-data-inicio').value;
    const dataFim = document.getElementById('filtro-data-fim').value;
    const equipe = document.getElementById('filtro-equipe').value;
    const vendedor = document.getElementById('filtro-vendedor').value;
    const tipoProduto = document.getElementById('filtro-tipo-produto').value;
    const tipoCampo = document.getElementById('filtro-tipo-campo').value;

    if (dataInicio) params.append('data_inicio', dataInicio);
    if (dataFim) params.append('data_fim', dataFim);
    if (equipe) params.append('equipe', equipe);
    if (vendedor) params.append('vendedor', vendedor);
    if (tipoProduto) {
        params.append('tipo_produto', tipoProduto);
        params.append('tipo_produto_campo', tipoCampo);
    }

    return params.toString();
}

/**
 * Atualiza cards de totais
 */
function atualizarTotais(totais) {
    document.getElementById('stat-valor').textContent = formatarMoeda(totais.valor_total || 0);
    document.getElementById('stat-margem').textContent = formatarMoeda(totais.margem_liquida_total || 0);
    document.getElementById('stat-margem-pct').textContent = formatarPercentual(totais.margem_media_percentual || 0);

    // Cores baseadas na margem
    const statMargem = document.getElementById('stat-margem');
    statMargem.classList.remove('text-success', 'text-danger');
    statMargem.classList.add(totais.margem_liquida_total >= 0 ? 'text-success' : 'text-danger');
}

/**
 * Atualiza paginacao
 */
function atualizarPaginacao(pag) {
    totalPaginas = pag.total_pages || 1;

    document.getElementById('paginacao-info').textContent = `${paginaAtual}/${totalPaginas}`;
    document.getElementById('btn-pagina-anterior').disabled = paginaAtual <= 1;
    document.getElementById('btn-proxima-pagina').disabled = paginaAtual >= totalPaginas;
    document.getElementById('total-registros').textContent = `${pag.total || 0} registros`;
}

/**
 * Renderiza tabela baseado no agrupamento
 */
function renderizarTabela() {
    const agrupamento = document.getElementById('filtro-agrupamento').value;
    const thead = document.getElementById('thead-margem');
    const tbody = document.getElementById('tbody-margem');

    // Cabecalho dinamico
    thead.innerHTML = getCabecalho(agrupamento);

    // Corpo da tabela
    if (!dadosAtuais || dadosAtuais.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="10" class="empty-state">
                    <i class="bi bi-inbox"></i>
                    <p>Nenhum dado encontrado</p>
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = dadosAtuais.map(row => getLinha(row, agrupamento)).join('');
}

/**
 * Retorna cabecalho baseado no agrupamento
 */
function getCabecalho(agrupamento) {
    const cabecalhos = {
        'produto_pedido': `
            <tr>
                <th>Pedido</th>
                <th>Produto</th>
                <th>Cliente</th>
                <th>UF</th>
                <th>Cidade</th>
                <th>Frete</th>
                <th class="text-end">Valor</th>
                <th class="text-end">Margem R$</th>
                <th class="text-end">Margem %</th>
                <th class="text-center">Contrato</th>
            </tr>
        `,
        'pedido': `
            <tr>
                <th>Pedido</th>
                <th>Cliente</th>
                <th>UF</th>
                <th>Cidade</th>
                <th>Frete</th>
                <th>Vendedor</th>
                <th class="text-center">Itens</th>
                <th class="text-end">Valor</th>
                <th class="text-end">Margem R$</th>
                <th class="text-end">Margem %</th>
                <th class="text-center">Contrato</th>
            </tr>
        `,
        'data': `
            <tr>
                <th>Data</th>
                <th class="text-center">Pedidos</th>
                <th class="text-center">Itens</th>
                <th class="text-end">Valor Total</th>
                <th class="text-end">Margem R$</th>
                <th class="text-end">Margem %</th>
            </tr>
        `,
        'tipo_produto': `
            <tr>
                <th>Tipo Produto</th>
                <th class="text-center">Pedidos</th>
                <th class="text-center">Itens</th>
                <th class="text-end">Valor Total</th>
                <th class="text-end">Margem R$</th>
                <th class="text-end">Margem %</th>
            </tr>
        `,
        'equipe': `
            <tr>
                <th>Equipe</th>
                <th class="text-center">Vendedores</th>
                <th class="text-center">Clientes</th>
                <th class="text-center">Pedidos</th>
                <th class="text-end">Valor Total</th>
                <th class="text-end">Margem R$</th>
                <th class="text-end">Margem %</th>
            </tr>
        `,
        'vendedor': `
            <tr>
                <th>Vendedor</th>
                <th>Equipe</th>
                <th class="text-center">Clientes</th>
                <th class="text-center">Pedidos</th>
                <th class="text-end">Valor Total</th>
                <th class="text-end">Margem R$</th>
                <th class="text-end">Margem %</th>
            </tr>
        `
    };

    return cabecalhos[agrupamento] || cabecalhos['produto_pedido'];
}

/**
 * Retorna linha da tabela baseado no agrupamento
 */
function getLinha(row, agrupamento) {
    const margemClass = (row.margem_liquida || 0) >= 0 ? 'margem-positiva' : 'margem-negativa';
    const margemPctClass = (row.margem_liquida_percentual || 0) >= 0 ? 'text-success' : 'text-danger';

    switch (agrupamento) {
        case 'produto_pedido':
            return `
                <tr>
                    <td><span class="badge bg-secondary">${row.num_pedido || '-'}</span></td>
                    <td>
                        <small class="text-muted">${row.cod_produto || ''}</small><br>
                        ${truncar(row.nome_produto, 30)}
                    </td>
                    <td class="cliente-link" onclick="mostrarHistorico('${row.cnpj_cpf || ''}')" title="Clique para ver historico">
                        ${truncar(row.raz_social_red, 25)}
                    </td>
                    <td>${row.cod_uf || '-'}</td>
                    <td>${truncar(row.nome_cidade, 15)}</td>
                    <td><span class="badge bg-info">${row.incoterm || '-'}</span></td>
                    <td class="text-end">${formatarMoeda(row.valor_total)}</td>
                    <td class="text-end ${margemClass}">${formatarMoeda(row.margem_liquida)}</td>
                    <td class="text-end ${margemPctClass}">${formatarPercentual(row.margem_liquida_percentual)}</td>
                    <td class="text-center">${getContratoTag(row.contrato)}</td>
                </tr>
            `;

        case 'pedido':
            return `
                <tr>
                    <td><span class="badge bg-secondary">${row.num_pedido || '-'}</span></td>
                    <td class="cliente-link" onclick="mostrarHistorico('${row.cnpj_cpf || ''}')" title="Clique para ver historico">
                        ${truncar(row.raz_social_red, 25)}
                    </td>
                    <td>${row.cod_uf || '-'}</td>
                    <td>${truncar(row.nome_cidade, 15)}</td>
                    <td><span class="badge bg-info">${row.incoterm || '-'}</span></td>
                    <td>${truncar(row.vendedor, 20)}</td>
                    <td class="text-center">${row.qtd_itens || 0}</td>
                    <td class="text-end">${formatarMoeda(row.valor_total)}</td>
                    <td class="text-end ${margemClass}">${formatarMoeda(row.margem_liquida)}</td>
                    <td class="text-end ${margemPctClass}">${formatarPercentual(row.margem_liquida_percentual)}</td>
                    <td class="text-center">${getContratoTag(row.contrato)}</td>
                </tr>
            `;

        case 'data':
            return `
                <tr>
                    <td>${formatarData(row.data_pedido)}</td>
                    <td class="text-center">${row.qtd_pedidos || 0}</td>
                    <td class="text-center">${row.qtd_itens || 0}</td>
                    <td class="text-end">${formatarMoeda(row.valor_total)}</td>
                    <td class="text-end ${margemClass}">${formatarMoeda(row.margem_liquida)}</td>
                    <td class="text-end ${margemPctClass}">${formatarPercentual(row.margem_liquida_percentual)}</td>
                </tr>
            `;

        case 'tipo_produto':
            return `
                <tr>
                    <td><span class="badge bg-primary">${row.tipo_produto || '-'}</span></td>
                    <td class="text-center">${row.qtd_pedidos || 0}</td>
                    <td class="text-center">${row.qtd_itens || 0}</td>
                    <td class="text-end">${formatarMoeda(row.valor_total)}</td>
                    <td class="text-end ${margemClass}">${formatarMoeda(row.margem_liquida)}</td>
                    <td class="text-end ${margemPctClass}">${formatarPercentual(row.margem_liquida_percentual)}</td>
                </tr>
            `;

        case 'equipe':
            return `
                <tr>
                    <td><span class="badge bg-primary">${row.equipe_vendas || '-'}</span></td>
                    <td class="text-center">${row.qtd_vendedores || 0}</td>
                    <td class="text-center">${row.qtd_clientes || 0}</td>
                    <td class="text-center">${row.qtd_pedidos || 0}</td>
                    <td class="text-end">${formatarMoeda(row.valor_total)}</td>
                    <td class="text-end ${margemClass}">${formatarMoeda(row.margem_liquida)}</td>
                    <td class="text-end ${margemPctClass}">${formatarPercentual(row.margem_liquida_percentual)}</td>
                </tr>
            `;

        case 'vendedor':
            return `
                <tr>
                    <td>${row.vendedor || '-'}</td>
                    <td><span class="badge bg-secondary">${row.equipe_vendas || '-'}</span></td>
                    <td class="text-center">${row.qtd_clientes || 0}</td>
                    <td class="text-center">${row.qtd_pedidos || 0}</td>
                    <td class="text-end">${formatarMoeda(row.valor_total)}</td>
                    <td class="text-end ${margemClass}">${formatarMoeda(row.margem_liquida)}</td>
                    <td class="text-end ${margemPctClass}">${formatarPercentual(row.margem_liquida_percentual)}</td>
                </tr>
            `;

        default:
            return '';
    }
}

/**
 * Tag de contrato
 */
function getContratoTag(contrato) {
    if (!contrato) return '-';
    if (contrato.tem_desconto) {
        const pct = contrato.percentual ? ` ${formatarPercentual(contrato.percentual)}` : '';
        return `<span class="badge bg-warning text-dark" title="Desconto contratual${pct}">Sim${pct}</span>`;
    }
    return '-';
}

/**
 * Mostra historico do cliente
 */
async function mostrarHistorico(cnpj) {
    if (!cnpj) return;

    const modal = new bootstrap.Modal(document.getElementById('modalHistoricoCliente'));
    document.getElementById('modal-cliente-nome').textContent = 'Carregando...';
    document.getElementById('modal-cliente-cnpj').textContent = cnpj;
    document.getElementById('tbody-historico').innerHTML = '<tr><td colspan="5" class="text-center">Carregando...</td></tr>';

    modal.show();

    try {
        const response = await fetch(`/comercial/api/margem/cliente/${encodeURIComponent(cnpj)}/historico`);
        const data = await response.json();

        if (data.sucesso) {
            document.getElementById('modal-cliente-nome').textContent = data.cliente.raz_social_red || 'Cliente';

            if (data.pedidos.length === 0) {
                document.getElementById('tbody-historico').innerHTML = '<tr><td colspan="5" class="text-center text-muted">Nenhum pedido encontrado</td></tr>';
            } else {
                document.getElementById('tbody-historico').innerHTML = data.pedidos.map(p => {
                    const margemClass = (p.margem_liquida || 0) >= 0 ? 'text-success' : 'text-danger';
                    return `
                        <tr>
                            <td><span class="badge bg-secondary">${p.num_pedido}</span></td>
                            <td>${formatarData(p.data_pedido)}</td>
                            <td class="text-end">${formatarMoeda(p.valor_total)}</td>
                            <td class="text-end ${margemClass}">${formatarMoeda(p.margem_liquida)}</td>
                            <td class="text-end ${margemClass}">${formatarPercentual(p.margem_liquida_percentual)}</td>
                        </tr>
                    `;
                }).join('');
            }
        } else {
            document.getElementById('tbody-historico').innerHTML = `<tr><td colspan="5" class="text-center text-danger">${data.erro || 'Erro'}</td></tr>`;
        }
    } catch (error) {
        console.error('Erro:', error);
        document.getElementById('tbody-historico').innerHTML = '<tr><td colspan="5" class="text-center text-danger">Erro de conexao</td></tr>';
    }
}

/**
 * Paginacao
 */
function paginaAnterior() {
    if (paginaAtual > 1) {
        paginaAtual--;
        carregarPagina();
    }
}

function proximaPagina() {
    if (paginaAtual < totalPaginas) {
        paginaAtual++;
        carregarPagina();
    }
}

async function carregarPagina() {
    mostrarLoading(true);

    try {
        const params = construirParametros();
        const response = await fetch(`/comercial/api/margem/dados?${params}`);
        const data = await response.json();

        if (data.sucesso) {
            dadosAtuais = data.dados;
            atualizarPaginacao(data.paginacao);
            renderizarTabela();
        }
    } catch (error) {
        console.error('Erro:', error);
    } finally {
        mostrarLoading(false);
    }
}

/**
 * Filtro local (busca na tabela atual)
 */
function filtrarLocal() {
    const busca = document.getElementById('filtro-busca').value.toLowerCase().trim();
    const linhas = document.querySelectorAll('#tbody-margem tr');

    linhas.forEach(linha => {
        if (linha.querySelector('.empty-state')) return;

        const texto = linha.textContent.toLowerCase();
        linha.style.display = texto.includes(busca) ? '' : 'none';
    });
}

/**
 * Exportar dados
 */
function exportarDados() {
    alert('Funcionalidade de exportacao em desenvolvimento');
}

// Formatadores
function formatarMoeda(valor) {
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(valor || 0);
}

function formatarPercentual(valor) {
    return `${(valor || 0).toFixed(2)}%`;
}

function formatarData(data) {
    if (!data) return '-';
    return new Date(data).toLocaleDateString('pt-BR');
}

function truncar(texto, max) {
    if (!texto) return '-';
    return texto.length > max ? texto.substring(0, max) + '...' : texto;
}

// UI Helpers
function mostrarLoading(show) {
    document.getElementById('loading-overlay').style.display = show ? 'flex' : 'none';
}

function mostrarErro(msg) {
    document.getElementById('tbody-margem').innerHTML = `
        <tr>
            <td colspan="10" class="empty-state">
                <i class="bi bi-exclamation-triangle text-danger"></i>
                <p class="text-danger">${msg}</p>
            </td>
        </tr>
    `;
}
