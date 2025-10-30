// ==================================================
// PROGRAMAÇÃO POR LINHA - SCRIPT PRINCIPAL
// ==================================================

// Constantes (reutilizadas do modal)
const MINUTOS_POR_TURNO = 480;
const MESES_NOME = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                    'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];
const DIAS_SEMANA = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'];

// Estado global
let programacaoState = {
    mesAtual: new Date().getMonth() + 1,
    anoAtual: new Date().getFullYear(),
    linhas: []
};

// ============================================================
// INICIALIZAÇÃO
// ============================================================

$(document).ready(function() {
    const anoAtual = new Date().getFullYear();
    const mesAtual = new Date().getMonth() + 1;

    // Preencher anos
    for (let i = -1; i <= 1; i++) {
        const ano = anoAtual + i;
        $('#filtro-ano').append($('<option></option>').val(ano).text(ano).prop('selected', i === 0));
    }

    // Selecionar mês atual
    $('#filtro-mes').val(mesAtual);

    // Eventos
    $('#btn-carregar').on('click', carregarProgramacaoLinhas);
    $('#btn-expandir-todos').on('click', expandirTodos);
    $('#btn-colapsar-todos').on('click', colapsarTodos);

    // Carregar automaticamente
    carregarProgramacaoLinhas();
});

// ============================================================
// CARREGAMENTO DE DADOS
// ============================================================

async function carregarProgramacaoLinhas() {
    try {
        const mes = $('#filtro-mes').val();
        const ano = $('#filtro-ano').val();

        programacaoState.mesAtual = parseInt(mes);
        programacaoState.anoAtual = parseInt(ano);

        mostrarLoading(true);
        $('#accordion-linhas').html('');

        const params = new URLSearchParams({ mes, ano });
        const response = await fetch(`/manufatura/recursos/api/programacao-linhas/dados?${params}`);

        if (!response.ok) {
            throw new Error(`Erro HTTP: ${response.status}`);
        }

        const dados = await response.json();

        if (dados.erro) {
            throw new Error(dados.erro);
        }

        programacaoState.linhas = dados.linhas || [];

        console.log('[PROGRAMACAO] Dados recebidos:', dados);
        console.log('[PROGRAMACAO] Total de linhas:', dados.linhas.length);
        console.log('[PROGRAMACAO] Primeira linha:', dados.linhas[0]);

        // Renderizar accordions
        renderizarAccordions(dados.linhas);

        $('#total-linhas').text(`${dados.linhas.length} linhas`);

    } catch (error) {
        console.error('[PROGRAMACAO] Erro ao carregar:', error);
        $('#accordion-linhas').html(`
            <div class="text-center text-danger py-5">
                <i class="fas fa-exclamation-triangle me-2"></i>
                Erro ao carregar: ${error.message}
            </div>
        `);
    } finally {
        mostrarLoading(false);
    }
}

// ============================================================
// RENDERIZAÇÃO DOS ACCORDIONS
// ============================================================

function renderizarAccordions(linhas) {
    if (!linhas || linhas.length === 0) {
        $('#accordion-linhas').html(`
            <div class="text-center text-muted py-5">
                <i class="fas fa-inbox me-2"></i>
                Nenhuma linha de produção encontrada
            </div>
        `);
        return;
    }

    let html = '';

    linhas.forEach((linha, index) => {
        const collapseId = `collapse-linha-${index}`;
        const headerId = `heading-linha-${index}`;

        // Gerar calendário da linha
        const calendarioHTML = gerarCalendarioLinha(linha);

        html += `
            <div class="accordion-item">
                <h2 class="accordion-header" id="${headerId}">
                    <button class="accordion-button collapsed" type="button"
                            data-bs-toggle="collapse" data-bs-target="#${collapseId}"
                            aria-expanded="false" aria-controls="${collapseId}">
                        <div class="d-flex align-items-center gap-3">
                            <i class="fas fa-industry text-success"></i>
                            <strong>${linha.linha_producao}</strong>
                        </div>
                    </button>
                </h2>
                <div id="${collapseId}" class="accordion-collapse collapse"
                     aria-labelledby="${headerId}">
                    <div class="accordion-body p-0">
                        ${calendarioHTML}
                    </div>
                </div>
            </div>
        `;
    });

    $('#accordion-linhas').html(html);
}

// ============================================================
// GERAÇÃO DO CALENDÁRIO (REUTILIZADO DO MODAL)
// ============================================================

function gerarCalendarioLinha(linha) {
    const { capacidade_unidade_minuto, qtd_unidade_por_caixa, programacoes } = linha;

    // Obter dias do mês
    const diasDoMes = obterDiasDoMes(programacaoState.mesAtual, programacaoState.anoAtual);

    // Gerar grid de dias
    const diasHTML = diasDoMes.map(dia =>
        gerarDiaHTML(dia, programacoes, capacidade_unidade_minuto, qtd_unidade_por_caixa)
    ).join('');

    return `
        <div class="recursos-calendario-linha">
            <!-- Calendário -->
            <div class="recursos-calendario">
                <div class="recursos-calendario-mes">
                    ${MESES_NOME[programacaoState.mesAtual - 1]} ${programacaoState.anoAtual}
                </div>
                <div class="recursos-calendario-grid">
                    ${diasHTML}
                </div>
            </div>
        </div>
    `;
}

// ============================================================
// FUNÇÕES DE DIA (REUTILIZADAS)
// ============================================================

function gerarDiaHTML(dia, programacoes, capacidadeUnMin, qtdUnPorCaixa) {
    const diaKey = dia.toISOString().split('T')[0];
    const programacoesDia = programacoes[diaKey] || [];

    // DEBUG: Log apenas para o primeiro dia
    if (dia.getDate() === 1) {
        console.log(`[DIA ${diaKey}] Programações:`, programacoesDia);
        console.log(`[DIA ${diaKey}] Total programações do mês:`, Object.keys(programacoes).length);
    }

    const diaMes = dia.getDate();
    const diaSemana = DIAS_SEMANA[dia.getDay()];
    const hoje = new Date();
    const ehHoje = dia.toDateString() === hoje.toDateString();

    // ✅ CALCULAR OCUPAÇÃO POR PRODUTO
    // IMPORTANTE: qtd_programada JÁ ESTÁ EM SKUs (caixas), NÃO em unidades!
    let totalMinutosNecessarios = 0;
    let totalSkusProgramados = 0;

    programacoesDia.forEach(produto => {
        const qtdSkus = produto.qtd_programada;  // JÁ É SKU!
        const capacidade = produto.capacidade_unidade_minuto || capacidadeUnMin;
        const qtdCaixa = produto.qtd_unidade_por_caixa || qtdUnPorCaixa;

        // SKUs deste produto (já está em SKU, apenas somar)
        totalSkusProgramados += qtdSkus;

        // Minutos necessários: converter SKUs para unidades, depois dividir pela capacidade
        // Fórmula: (qtd_skus * qtd_unidades_por_caixa) / capacidade_unidade_minuto
        if (capacidade > 0 && qtdCaixa > 0) {
            const qtdUnidades = qtdSkus * qtdCaixa;
            totalMinutosNecessarios += qtdUnidades / capacidade;
        }
    });

    const minutosNecessarios = Math.round(totalMinutosNecessarios);
    const skusProgramados = Math.round(totalSkusProgramados);

    // ✅ CALCULAR BARRAS DE OCUPAÇÃO (igual ao modal recursos)
    const turnosUsados = totalMinutosNecessarios / MINUTOS_POR_TURNO;
    let altura_turno_1 = 0;
    let altura_turno_2 = 0;
    let altura_turno_3 = 0;

    if (turnosUsados > 0) {
        altura_turno_1 = Math.min(turnosUsados * 100, 100);
    }
    if (turnosUsados > 1) {
        altura_turno_2 = Math.min((turnosUsados - 1) * 100, 100);
    }
    if (turnosUsados > 2) {
        altura_turno_3 = Math.min((turnosUsados - 2) * 100, 100);
    }

    // HTML dos produtos programados (compacto: código + qtd na mesma linha, com tooltip)
    const produtosHTML = programacoesDia.length > 0
        ? programacoesDia.map(p => `
            <div class="dia-produto"
                 title="${p.nome_produto || p.cod_produto}"
                 onclick="abrirModalSeparacoesProduto('${p.cod_produto}', '${diaKey}')">
                <strong>${p.cod_produto}</strong>
                <span>${Math.round(p.qtd_programada)}</span>
            </div>
          `).join('')
        : '<div class="dia-vazio">-</div>';

    return `
        <div class="recursos-dia ${ehHoje ? 'dia-hoje' : ''}">
            <div class="dia-header">
                <div class="dia-numero">${diaMes}</div>
                <div class="dia-semana">${diaSemana}</div>
            </div>

            <div class="dia-produtos">
                ${produtosHTML}
            </div>

            <!-- ✅ BARRAS DE OCUPAÇÃO SOBREPOSTAS -->
            <div class="recursos-ocupacao-turno recursos-ocupacao-turno-1" style="height: ${altura_turno_1}%;"></div>
            <div class="recursos-ocupacao-turno recursos-ocupacao-turno-2" style="height: ${altura_turno_2}%;"></div>
            <div class="recursos-ocupacao-turno recursos-ocupacao-turno-3" style="height: ${altura_turno_3}%;"></div>

            <div class="dia-footer">
                <small>${skusProgramados} | ${minutosNecessarios} min</small>
            </div>
        </div>
    `;
}

function obterDiasDoMes(mes, ano) {
    const primeiroDia = new Date(ano, mes - 1, 1);
    const ultimoDia = new Date(ano, mes, 0);
    const dias = [];

    for (let dia = 1; dia <= ultimoDia.getDate(); dia++) {
        dias.push(new Date(ano, mes - 1, dia));
    }

    return dias;
}

// ============================================================
// UTILITÁRIOS
// ============================================================

function expandirTodos() {
    $('#accordion-linhas .accordion-collapse').collapse('show');
}

function colapsarTodos() {
    $('#accordion-linhas .accordion-collapse').collapse('hide');
}

function mostrarLoading(mostrar) {
    if (mostrar) {
        $('#loading-spinner').removeClass('d-none');
    } else {
        $('#loading-spinner').addClass('d-none');
    }
}

// ============================================================
// MODAL DE SEPARAÇÕES E ESTOQUE
// ============================================================

async function abrirModalSeparacoesProduto(codProduto, diaClicado) {
    try {
        console.log(`[MODAL SEPARACOES] Abrindo para produto: ${codProduto}, dia: ${diaClicado}`);

        // Calcular período: 7 dias antes + dia + 7 dias depois
        const dataClicada = new Date(diaClicado);
        const dataInicio = new Date(dataClicada);
        dataInicio.setDate(dataInicio.getDate() - 7);
        const dataFim = new Date(dataClicada);
        dataFim.setDate(dataFim.getDate() + 7);

        // Buscar dados do backend
        const params = new URLSearchParams({
            cod_produto: codProduto,
            data_inicio: dataInicio.toISOString().split('T')[0],
            data_fim: dataFim.toISOString().split('T')[0],
            data_referencia: diaClicado
        });

        const response = await fetch(`/manufatura/recursos/api/separacoes-estoque?${params}`);
        const dados = await response.json();

        if (dados.erro) {
            throw new Error(dados.erro);
        }

        // Renderizar modal
        renderizarModalSeparacoes(dados, codProduto, diaClicado);

        // Mostrar modal
        const modal = new bootstrap.Modal(document.getElementById('modalSeparacoesProduto'));
        modal.show();

    } catch (error) {
        console.error('[MODAL SEPARACOES] Erro:', error);
        alert(`Erro ao carregar separações: ${error.message}`);
    }
}

function renderizarModalSeparacoes(dados, codProduto, diaReferencia) {
    $('#modal-separacoes-titulo').text(`${dados.nome_produto || codProduto}`);

    // ✅ TABELA HORIZONTAL: Dias nas colunas, movimentações nas linhas
    let html = '<div class="table-responsive"><table class="table table-sm table-bordered table-hover">';

    // HEADER com datas
    html += '<thead><tr><th class="text-start" style="min-width: 120px;">Movimentação</th>';
    dados.dias.forEach(dia => {
        const ehReferencia = dia.data === diaReferencia;
        const data = new Date(dia.data);
        const diaNum = data.getDate().toString().padStart(2, '0');
        const mes = (data.getMonth() + 1).toString().padStart(2, '0');
        const classe = ehReferencia ? 'table-warning fw-bold' : '';

        html += `<th class="text-center ${classe}" style="min-width: 70px;">${diaNum}/${mes}</th>`;
    });
    html += '</tr></thead><tbody>';

    // LINHA 1: Estoque Inicial
    html += '<tr><td class="fw-bold bg-light">Est. Inicial</td>';
    dados.dias.forEach(dia => {
        const ehReferencia = dia.data === diaReferencia;
        const classe = ehReferencia ? 'table-warning' : '';
        html += `<td class="text-center ${classe}">${Math.round(dia.est_inicial).toLocaleString('pt-BR')}</td>`;
    });
    html += '</tr>';

    // LINHA 2: Entradas
    html += '<tr><td class="fw-bold bg-light">Entradas</td>';
    dados.dias.forEach(dia => {
        const ehReferencia = dia.data === diaReferencia;
        const classe = ehReferencia ? 'table-warning' : '';
        const valor = dia.entradas > 0 ? `<span class="text-success fw-bold">+${Math.round(dia.entradas).toLocaleString('pt-BR')}</span>` : '0';
        html += `<td class="text-center ${classe}">${valor}</td>`;
    });
    html += '</tr>';

    // LINHA 3: Saídas
    html += '<tr><td class="fw-bold bg-light">Saídas</td>';
    dados.dias.forEach(dia => {
        const ehReferencia = dia.data === diaReferencia;
        const classe = ehReferencia ? 'table-warning' : '';
        const valor = dia.saidas > 0 ? `<span class="text-danger fw-bold">-${Math.round(dia.saidas).toLocaleString('pt-BR')}</span>` : '0';
        html += `<td class="text-center ${classe}">${valor}</td>`;
    });
    html += '</tr>';

    // LINHA 4: Estoque Final
    html += '<tr class="table-primary"><td class="fw-bold">Est. Final</td>';
    dados.dias.forEach(dia => {
        const ehReferencia = dia.data === diaReferencia;
        const classe = ehReferencia ? 'table-warning fw-bold' : '';
        const valor = Math.round(dia.est_final);
        const cor = valor < 0 ? 'text-danger' : valor === 0 ? 'text-muted' : 'text-dark';
        html += `<td class="text-center fw-bold ${classe} ${cor}">${valor.toLocaleString('pt-BR')}</td>`;
    });
    html += '</tr>';

    html += '</tbody></table></div>';

    // ✅ SEÇÃO DE PEDIDOS
    if (dados.pedidos && dados.pedidos.length > 0) {
        html += '<hr class="my-4">';
        html += '<h6 class="text-success mb-3"><i class="fas fa-clipboard-list me-2"></i>Pedidos Não Sincronizados (sincronizado_nf=False)</h6>';
        html += '<div class="table-responsive"><table class="table table-sm table-bordered table-striped">';
        html += '<thead class="table-light"><tr>';
        html += '<th>Pedido</th>';
        html += '<th>CNPJ</th>';
        html += '<th>Cliente</th>';
        html += '<th class="text-end">Qtd</th>';
        html += '<th>Expedição</th>';
        html += '<th>Agendamento</th>';
        html += '<th class="text-center">Confirmado</th>';
        html += '<th>Dt. Entrega</th>';
        html += '</tr></thead><tbody>';

        dados.pedidos.forEach(ped => {
            html += '<tr>';
            html += `<td><strong>${ped.num_pedido}</strong></td>`;
            html += `<td><small>${ped.cnpj_cpf || '-'}</small></td>`;
            html += `<td>${ped.raz_social_red || '-'}</td>`;
            html += `<td class="text-end">${Math.round(ped.qtd).toLocaleString('pt-BR')}</td>`;
            html += `<td>${ped.expedicao ? new Date(ped.expedicao).toLocaleDateString('pt-BR') : '-'}</td>`;
            html += `<td>${ped.agendamento ? new Date(ped.agendamento).toLocaleDateString('pt-BR') : '-'}</td>`;

            const confirmado = ped.agendamento_confirmado;
            const badgeConfirmado = confirmado
                ? '<span class="badge bg-success">Sim</span>'
                : '<span class="badge bg-secondary">Não</span>';
            html += `<td class="text-center">${badgeConfirmado}</td>`;

            html += `<td>${ped.data_entrega_pedido ? new Date(ped.data_entrega_pedido).toLocaleDateString('pt-BR') : '-'}</td>`;
            html += '</tr>';
        });

        html += '</tbody></table></div>';
    }

    $('#modal-separacoes-conteudo').html(html);
}

