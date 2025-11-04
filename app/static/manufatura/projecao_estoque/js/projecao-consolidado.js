/* ============================================================
   PROJEÇÃO DE ESTOQUE - JAVASCRIPT CONSOLIDADO
   ============================================================ */

let dadosComponentes = [];

// ============================================================
// INICIALIZAÇÃO
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
    configurarEventos();
    gerarHeadersProjecao();
    calcular();
});

function configurarEventos() {
    // Botão calcular
    document.getElementById('btn-calcular').addEventListener('click', calcular);

    // Filtro de produto
    document.getElementById('filtro-produto').addEventListener('input', filtrarTabela);

    // Toggles de colunas
    document.querySelectorAll('.col-toggle').forEach(checkbox => {
        checkbox.addEventListener('change', toggleColunas);
    });
}

// ============================================================
// GERAÇÃO DE HEADERS DE PROJEÇÃO D0-D60
// ============================================================

function gerarHeadersProjecao() {
    const thead = document.getElementById('thead-row');
    const hoje = new Date();
    const diasSemana = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'];

    for (let i = 0; i <= 60; i++) {
        const data = new Date(hoje);
        data.setDate(hoje.getDate() + i);

        const diaMes = data.getDate();
        const diaSemana = diasSemana[data.getDay()];
        const texto = `${diaMes}<br>${diaSemana}`;

        const th = document.createElement('th');
        th.className = `col-projecao col-projecao-d${i} text-center`;
        th.innerHTML = texto;
        th.title = data.toLocaleDateString('pt-BR');

        thead.appendChild(th);
    }
}

// ============================================================
// CALCULAR PROJEÇÃO
// ============================================================

async function calcular() {
    mostrarLoading(true);

    try {
        const response = await fetch('/manufatura/projecao-estoque/api/projetar-consolidado');
        const data = await response.json();

        if (data.sucesso) {
            dadosComponentes = data.componentes;
            renderizarTabela(dadosComponentes);
            document.getElementById('total-componentes').textContent = `${data.total_componentes} componentes`;
        } else {
            alert('Erro ao calcular projeção: ' + data.erro);
        }
    } catch (erro) {
        console.error('Erro:', erro);
        alert('Erro ao calcular projeção');
    } finally {
        mostrarLoading(false);
    }
}

// ============================================================
// RENDERIZAR TABELA
// ============================================================

function renderizarTabela(componentes) {
    const tbody = document.getElementById('tbody-projecao');
    tbody.innerHTML = '';

    if (componentes.length === 0) {
        tbody.innerHTML = '<tr><td colspan="100" class="text-center text-muted py-5">Nenhum componente encontrado</td></tr>';
        return;
    }

    componentes.forEach(comp => {
        const tr = document.createElement('tr');

        // Colunas fixas
        tr.innerHTML = `
            <td class="sticky-col-codigo">${comp.cod_produto}</td>
            <td class="sticky-col-produto" title="${comp.nome_produto}">${comp.nome_produto}</td>
            <td class="text-end col-estoque ${classeValor(comp.estoque_atual)}">${formatarNumero(comp.estoque_atual)}</td>
            <td class="text-end col-consumo ${classeValor(comp.consumo_carteira)}">${formatarNumero(comp.consumo_carteira)}</td>
            <td class="text-end col-saldo ${classeValor(comp.saldo_carteira)}">${formatarNumero(comp.saldo_carteira)}</td>
            <td class="text-end col-programacao ${classeValor(comp.consumo_programacao)}">${formatarNumero(comp.consumo_programacao)}</td>
            <td class="text-end col-saldo-prog ${classeValor(comp.saldo_programacao)}">${formatarNumero(comp.saldo_programacao)}</td>
            <td class="text-end col-requisicoes">${formatarNumero(comp.qtd_requisicoes)}</td>
            <td class="text-end col-pedidos">${formatarNumero(comp.qtd_pedidos)}</td>
        `;

        // Colunas de projeção D0-D60
        comp.timeline.forEach((valor, index) => {
            const td = document.createElement('td');
            td.className = `col-projecao col-projecao-d${index} text-end ${classeValor(valor)}`;
            td.textContent = formatarNumero(valor);
            td.title = `D${index}: ${formatarNumero(valor)}`;
            tr.appendChild(td);
        });

        tbody.appendChild(tr);
    });

    // Aplicar visibilidade de colunas
    toggleColunas();
}

// ============================================================
// FILTRAR TABELA
// ============================================================

function filtrarTabela() {
    const filtro = document.getElementById('filtro-produto').value.toUpperCase();

    if (filtro === '') {
        renderizarTabela(dadosComponentes);
        return;
    }

    const filtrados = dadosComponentes.filter(comp => {
        return comp.cod_produto.toUpperCase().includes(filtro) ||
               comp.nome_produto.toUpperCase().includes(filtro);
    });

    renderizarTabela(filtrados);
}

// ============================================================
// TOGGLE DE COLUNAS
// ============================================================

function toggleColunas() {
    // Colunas fixas
    const toggles = {
        'estoque': document.getElementById('col-estoque').checked,
        'consumo': document.getElementById('col-consumo').checked,
        'saldo': document.getElementById('col-saldo').checked,
        'programacao': document.getElementById('col-programacao').checked,
        'saldo-prog': document.getElementById('col-saldo-prog').checked,
        'requisicoes': document.getElementById('col-requisicoes').checked,
        'pedidos': document.getElementById('col-pedidos').checked,
        'projecao': document.getElementById('col-projecao').checked
    };

    // Aplicar visibilidade
    Object.keys(toggles).forEach(tipo => {
        const colunas = document.querySelectorAll(`.col-${tipo}`);
        colunas.forEach(col => {
            col.style.display = toggles[tipo] ? '' : 'none';
        });
    });

    // Timeline D0-D60
    const mostrarProjecao = toggles['projecao'];
    for (let i = 0; i <= 60; i++) {
        document.querySelectorAll(`.col-projecao-d${i}`).forEach(col => {
            col.style.display = mostrarProjecao ? '' : 'none';
        });
    }
}

function selecionarTodasColunas() {
    document.querySelectorAll('.col-toggle').forEach(cb => cb.checked = true);
    toggleColunas();
}

function limparSelecaoColunas() {
    document.querySelectorAll('.col-toggle').forEach(cb => cb.checked = false);
    toggleColunas();
}

// ============================================================
// MUDAR TAMANHO DE FONTE
// ============================================================

function mudarTamanhoFonte(tamanho) {
    // Remover classes anteriores
    document.body.classList.remove('font-very-small', 'font-small', 'font-medium', 'font-large');

    // Adicionar nova classe
    document.body.classList.add(`font-${tamanho}`);

    // Atualizar botões ativos
    document.querySelectorAll('.btn-size-compact').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.size === tamanho) {
            btn.classList.add('active');
        }
    });
}

// ============================================================
// UTILITÁRIOS
// ============================================================

function formatarNumero(valor) {
    if (valor === 0) return '-';
    return parseFloat(valor).toFixed(2).replace('.', ',');
}

function classeValor(valor) {
    if (valor > 0) return 'valor-positivo';
    if (valor < 0) return 'valor-negativo';
    return 'valor-zero';
}

function mostrarLoading(mostrar) {
    const spinner = document.getElementById('loading-spinner');
    if (mostrar) {
        spinner.classList.remove('d-none');
    } else {
        spinner.classList.add('d-none');
    }
}
