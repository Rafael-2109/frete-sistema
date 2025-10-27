// ==================================================
// MODAL RECURSOS PRODUTIVOS
// ==================================================

// Constantes
const MINUTOS_POR_TURNO = 480; // 8 horas por turno
const MESES_NOME = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                    'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];
const DIAS_SEMANA = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'];

// Variáveis globais do modal
let recursosState = {
    codProduto: null,
    mesAtual: new Date().getMonth() + 1,
    anoAtual: new Date().getFullYear(),
    dadosRecursos: null,
    estoquePorDia: {},  // Estoque do produto selecionado por dia
    estoquePorProduto: {}  // ✅ NOVO - Estoque de TODOS os produtos { cod_produto: { data: {...} } }
};

/**
 * Abre o modal de Recursos Produtivos
 * @param {string} codProduto - Código do produto
 */
function abrirModalRecursosProdutivos(codProduto) {
    console.log(`[RECURSOS] Abrindo modal para produto: ${codProduto}`);

    recursosState.codProduto = codProduto;
    recursosState.mesAtual = new Date().getMonth() + 1;
    recursosState.anoAtual = new Date().getFullYear();

    // Mostrar modal
    const modal = new bootstrap.Modal(document.getElementById('modalRecursosProdutivos'));
    modal.show();

    // Carregar dados
    carregarRecursosProdutivos();
}

/**
 * Carrega dados do backend
 */
async function carregarRecursosProdutivos() {
    try {
        mostrarLoadingRecursos(true);
        esconderConteudoRecursos();

        const params = new URLSearchParams({
            cod_produto: recursosState.codProduto,
            mes: recursosState.mesAtual,
            ano: recursosState.anoAtual
        });

        const response = await fetch(`/manufatura/api/necessidade-producao/recursos-produtivos?${params}`);

        if (!response.ok) {
            throw new Error(`Erro HTTP: ${response.status}`);
        }

        const dados = await response.json();

        if (dados.erro) {
            throw new Error(dados.erro);
        }

        recursosState.dadosRecursos = dados;
        recursosState.estoquePorDia = dados.estoque_por_dia || {};
        recursosState.estoquePorProduto = dados.estoque_por_produto || {};  // ✅ NOVO

        // Renderizar dados
        renderizarRecursosProdutivos(dados);

    } catch (error) {
        console.error('[RECURSOS] Erro ao carregar:', error);
        Swal.fire({
            icon: 'error',
            title: 'Erro ao Carregar Recursos',
            text: error.message || 'Ocorreu um erro desconhecido',
            confirmButtonColor: '#198754'
        });
    } finally {
        mostrarLoadingRecursos(false);
    }
}

/**
 * Renderiza os dados no modal
 */
function renderizarRecursosProdutivos(dados) {
    console.log('[RECURSOS] Renderizando dados:', dados);

    // 1. Renderizar resumo
    renderizarResumo(dados);

    // 2. Renderizar calendários por linha
    renderizarCalendarios(dados);

    // 3. Mostrar conteúdo
    document.getElementById('recursos-resumo').classList.remove('d-none');
    document.getElementById('recursos-calendarios-container').classList.remove('d-none');
}

/**
 * Renderiza o resumo no topo
 */
function renderizarResumo(dados) {
    const { produto, linhas, primeiro_dia_falta, mes, ano } = dados;

    // Produto
    document.getElementById('recursos-produto-nome').textContent = produto.nome_produto;
    document.getElementById('recursos-cod-produto').textContent = produto.cod_produto;
    document.getElementById('recursos-nome-produto-resumo').textContent = produto.nome_produto;

    // Linhas disponíveis
    document.getElementById('recursos-qtd-linhas').textContent = `${linhas.length} linha${linhas.length > 1 ? 's' : ''}`;

    const listaLinhas = linhas.map(l => l.linha_producao).join(', ');
    document.getElementById('recursos-lista-linhas').textContent = listaLinhas;

    // Primeiro dia com falta
    if (primeiro_dia_falta) {
        const dataFormatada = formatarDataBR(primeiro_dia_falta);
        document.getElementById('recursos-primeiro-dia-falta').innerHTML =
            `<i class="fas fa-exclamation-triangle me-1"></i>${dataFormatada}`;
    } else {
        document.getElementById('recursos-primeiro-dia-falta').innerHTML =
            `<span class="text-success"><i class="fas fa-check-circle me-1"></i>Sem ruptura prevista</span>`;
    }

    // Mês atual exibido
    document.getElementById('btn-mes-atual').textContent = `${MESES_NOME[mes - 1]} ${ano}`;
}

/**
 * Renderiza os calendários de cada linha
 */
function renderizarCalendarios(dados) {
    const { linhas, mes, ano } = dados;
    const container = document.getElementById('recursos-calendarios-container');
    container.innerHTML = '';

    if (linhas.length === 0) {
        container.innerHTML = `
            <div class="alert alert-warning text-center">
                <i class="fas fa-exclamation-triangle me-2"></i>
                Produto não possui linhas de produção cadastradas
            </div>
        `;
        return;
    }

    linhas.forEach(linha => {
        const calendarioHTML = gerarCalendarioLinha(linha, mes, ano);
        container.insertAdjacentHTML('beforeend', calendarioHTML);
    });

    // Adicionar event listeners para tooltips
    adicionarTooltipsCalendario();
}

/**
 * Gera HTML de um calendário para uma linha
 */
function gerarCalendarioLinha(linha, mes, ano) {
    const { linha_producao, capacidade_unidade_minuto, qtd_unidade_por_caixa, qtd_lote_ideal,
            eficiencia_media, tempo_setup, programacoes } = linha;

    // Obter dias do mês
    const diasDoMes = obterDiasDoMes(mes, ano);

    // Gerar grid de dias - ✅ PASSANDO qtd_unidade_por_caixa
    const diasHTML = diasDoMes.map(dia =>
        gerarDiaHTML(dia, programacoes, capacidade_unidade_minuto, qtd_unidade_por_caixa)
    ).join('');

    return `
        <div class="recursos-calendario-linha">
            <!-- Header da Linha -->
            <div class="recursos-linha-header">
                <div class="recursos-linha-titulo">
                    <i class="fas fa-industry me-2"></i>${linha_producao}
                </div>
                <div class="recursos-linha-dados">
                    <div>
                        <small>Capacidade</small>
                        <strong>${capacidade_unidade_minuto.toFixed(1)} un/min</strong>
                    </div>
                    <div>
                        <small>Lote Ideal</small>
                        <strong>${qtd_lote_ideal > 0 ? qtd_lote_ideal.toLocaleString('pt-BR') : 'N/A'}</strong>
                    </div>
                    <div>
                        <small>Eficiência</small>
                        <strong>${eficiencia_media}%</strong>
                    </div>
                    <div>
                        <small>Setup</small>
                        <strong>${tempo_setup} min</strong>
                    </div>
                </div>
            </div>

            <!-- Calendário -->
            <div class="recursos-calendario">
                <div class="recursos-calendario-mes">
                    ${MESES_NOME[mes - 1]} ${ano}
                </div>
                <div class="recursos-calendario-grid">
                    ${diasHTML}
                </div>
            </div>
        </div>
    `;
}

/**
 * Gera HTML de um dia do calendário
 */
function gerarDiaHTML(dia, programacoes, capacidadeMinuto, qtdUnidadePorCaixa) {
    const { numero, diaSemana, isWeekend, dataKey } = dia;

    // Verificar se há programações para este dia
    const programacoesDia = programacoes[dataKey] || [];

    // Calcular ocupação total do dia - ✅ PASSANDO qtdUnidadePorCaixa
    const ocupacao = calcularOcupacaoDia(programacoesDia, capacidadeMinuto, qtdUnidadePorCaixa);

    // Buscar dados de estoque do produto selecionado para este dia
    const dadosEstoque = recursosState.estoquePorDia[dataKey] || null;

    // HTML dos dados de estoque (compacto, acima dos produtos)
    let estoqueHTML = '';
    if (dadosEstoque) {
        estoqueHTML = `
            <div class="recursos-estoque-dia">
                <small title="Estoque Inicial">E:${formatarNumeroCompacto(dadosEstoque.estoque_inicial)}</small>
                <small title="Saídas" class="text-danger">S:${formatarNumeroCompacto(dadosEstoque.saidas)}</small>
                <small title="Entradas" class="text-success">Ent:${formatarNumeroCompacto(dadosEstoque.entradas)}</small>
                <small title="Saldo" class="fw-bold">Sld:${formatarNumeroCompacto(dadosEstoque.saldo_final)}</small>
            </div>
        `;
    }

    // Produtos HTML - ✅ ADICIONAR data-dia para tooltip com estoque
    const produtosHTML = programacoesDia.length > 0
        ? programacoesDia.map(prog => `
            <div class="recursos-produto-item"
                 data-produto="${prog.cod_produto}"
                 data-nome="${prog.nome_produto}"
                 data-qtd="${prog.qtd_programada}"
                 data-dia="${dataKey}">
                <span class="recursos-produto-cod">${prog.cod_produto}</span>
                <span class="recursos-produto-qtd">${prog.qtd_programada.toLocaleString('pt-BR')} un</span>
            </div>
          `).join('')
        : '<div class="recursos-dia-vazio">Sem programação</div>';

    return `
        <div class="recursos-dia ${isWeekend ? 'weekend' : ''}" data-data="${dataKey}">
            <!-- Header do dia -->
            <div class="recursos-dia-header">
                <div class="recursos-dia-numero">${numero}</div>
                <div class="recursos-dia-semana">${diaSemana}</div>
            </div>

            <!-- ✅ NOVO: Dados de estoque do produto -->
            ${estoqueHTML}

            <!-- Produtos programados -->
            <div class="recursos-produtos-programados">
                ${produtosHTML}
            </div>

            <!-- ✅ NOVO: 3 Barras Sobrepostas (1 por turno) -->
            <div class="recursos-ocupacao-turno recursos-ocupacao-turno-1" style="height: ${ocupacao.altura_turno_1}%;"></div>
            <div class="recursos-ocupacao-turno recursos-ocupacao-turno-2" style="height: ${ocupacao.altura_turno_2}%;"></div>
            <div class="recursos-ocupacao-turno recursos-ocupacao-turno-3" style="height: ${ocupacao.altura_turno_3}%;"></div>
        </div>
    `;
}

/**
 * Calcula ocupação de um dia - SISTEMA DE 3 BARRAS SOBREPOSTAS
 * Fórmula: ocupacao_minutos = qtd_total / (capacidade_unidade_minuto / qtd_unidade_por_caixa)
 */
function calcularOcupacaoDia(programacoes, capacidadeMinuto, qtdUnidadePorCaixa) {
    if (!programacoes || programacoes.length === 0 || capacidadeMinuto === 0 || !qtdUnidadePorCaixa) {
        return {
            altura_turno_1: 0,
            altura_turno_2: 0,
            altura_turno_3: 0,
            percentual: 0
        };
    }

    // Somar todas as quantidades programadas (em caixas/SKU)
    const qtdTotal = programacoes.reduce((sum, prog) => sum + prog.qtd_programada, 0);

    // ✅ FÓRMULA CORRETA: Converter capacidade para caixas/minuto
    const capacidadeCaixaMinuto = capacidadeMinuto / qtdUnidadePorCaixa;

    // Calcular minutos necessários
    const minutosNecessarios = qtdTotal / capacidadeCaixaMinuto;

    // Calcular quantos turnos estão sendo usados
    const turnosUsados = minutosNecessarios / MINUTOS_POR_TURNO;

    // ✅ NOVO: Calcular altura de cada turno individualmente
    let altura_turno_1 = 0;
    let altura_turno_2 = 0;
    let altura_turno_3 = 0;

    if (turnosUsados > 0) {
        // Turno 1: sempre preenche primeiro (0 a 100% do dia)
        altura_turno_1 = Math.min(turnosUsados * 100, 100);
    }

    if (turnosUsados > 1) {
        // Turno 2: começa após turno 1 completo (0 a 100% do dia)
        altura_turno_2 = Math.min((turnosUsados - 1) * 100, 100);
    }

    if (turnosUsados > 2) {
        // Turno 3: começa após turnos 1 e 2 completos (0 a 100% do dia)
        altura_turno_3 = Math.min((turnosUsados - 2) * 100, 100);
    }

    const percentualTotal = turnosUsados * 100;

    return {
        altura_turno_1,
        altura_turno_2,
        altura_turno_3,
        percentual: percentualTotal
    };
}

/**
 * Obtém dias de um mês
 */
function obterDiasDoMes(mes, ano) {
    const dias = [];
    const ultimoDia = new Date(ano, mes, 0).getDate();

    for (let i = 1; i <= ultimoDia; i++) {
        const data = new Date(ano, mes - 1, i);
        dias.push({
            data: data,
            numero: i,
            diaSemana: DIAS_SEMANA[data.getDay()],
            isWeekend: data.getDay() === 0 || data.getDay() === 6,
            dataKey: `${ano}-${String(mes).padStart(2, '0')}-${String(i).padStart(2, '0')}`
        });
    }

    return dias;
}

/**
 * Adiciona tooltips aos produtos - ✅ ATUALIZADO com dados de estoque
 */
function adicionarTooltipsCalendario() {
    const produtos = document.querySelectorAll('.recursos-produto-item');

    produtos.forEach(item => {
        item.addEventListener('mouseenter', function() {
            const nome = this.dataset.nome;
            const codProduto = this.dataset.produto;
            const qtd = parseFloat(this.dataset.qtd).toLocaleString('pt-BR');
            const dia = this.dataset.dia;

            // ✅ Buscar estoque deste produto específico neste dia
            const estoquesProduto = recursosState.estoquePorProduto[codProduto] || {};
            const estoqueDia = estoquesProduto[dia];

            let tooltipHTML = `<strong>${nome}</strong><br>${qtd} unidades programadas`;

            // ✅ Adicionar dados de estoque se disponíveis
            if (estoqueDia) {
                tooltipHTML += `<br><hr style="margin: 5px 0; border-color: rgba(255,255,255,0.3);">`;
                tooltipHTML += `<small><strong>📊 Estoque:</strong><br>`;
                tooltipHTML += `Est. Inicial: ${estoqueDia.estoque_inicial.toLocaleString('pt-BR')}<br>`;
                tooltipHTML += `Saídas: ${estoqueDia.saidas.toLocaleString('pt-BR')}<br>`;
                tooltipHTML += `Entradas: ${estoqueDia.entradas.toLocaleString('pt-BR')}<br>`;
                tooltipHTML += `<strong>Saldo: ${estoqueDia.saldo_final.toLocaleString('pt-BR')}</strong>`;
                tooltipHTML += `</small>`;
            }

            const tooltip = document.createElement('div');
            tooltip.className = 'recursos-tooltip';
            tooltip.innerHTML = tooltipHTML;
            document.body.appendChild(tooltip);

            const rect = this.getBoundingClientRect();
            tooltip.style.left = `${rect.left + window.scrollX}px`;
            tooltip.style.top = `${rect.bottom + window.scrollY + 5}px`;

            this._tooltip = tooltip;
        });

        item.addEventListener('mouseleave', function() {
            if (this._tooltip) {
                this._tooltip.remove();
                this._tooltip = null;
            }
        });
    });
}

/**
 * Navegar para mês anterior
 */
document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('btn-mes-anterior').addEventListener('click', function() {
        recursosState.mesAtual--;
        if (recursosState.mesAtual < 1) {
            recursosState.mesAtual = 12;
            recursosState.anoAtual--;
        }
        carregarRecursosProdutivos();
    });

    document.getElementById('btn-mes-proximo').addEventListener('click', function() {
        recursosState.mesAtual++;
        if (recursosState.mesAtual > 12) {
            recursosState.mesAtual = 1;
            recursosState.anoAtual++;
        }
        carregarRecursosProdutivos();
    });
});

/**
 * Utilitários
 */
function mostrarLoadingRecursos(mostrar) {
    const loading = document.getElementById('recursos-loading');
    if (mostrar) {
        loading.classList.remove('d-none');
    } else {
        loading.classList.add('d-none');
    }
}

function esconderConteudoRecursos() {
    document.getElementById('recursos-resumo').classList.add('d-none');
    document.getElementById('recursos-calendarios-container').classList.add('d-none');
}

function formatarDataBR(dataISO) {
    if (!dataISO) return '-';
    const partes = dataISO.split('-');
    return `${partes[2]}/${partes[1]}/${partes[0]}`;
}

/**
 * Formata número de forma compacta para exibição nos dias
 */
function formatarNumeroCompacto(valor) {
    if (valor === null || valor === undefined) return '-';

    const num = parseFloat(valor);

    if (num === 0) return '0';
    if (num < 1000) return num.toFixed(0);
    if (num < 1000000) return (num / 1000).toFixed(1) + 'k';
    return (num / 1000000).toFixed(1) + 'M';
}
