/**
 * sugestao.js - Sugestao de Compras (MRP Simplificado)
 *
 * Fetch API, filtros client-side, ordenacao por coluna.
 */

let dadosSugestoes = [];
let sortCol = 'urgencia';
let sortAsc = true;

// ========================================
// CALCULAR
// ========================================

function calcularSugestoes() {
    const btnCalc = document.getElementById('btn-calcular');
    const loading = document.getElementById('loading');
    const resultado = document.getElementById('resultado-container');
    const resumo = document.getElementById('resumo-cards');

    btnCalc.disabled = true;
    loading.classList.remove('d-none');
    resultado.classList.add('d-none');
    resumo.classList.add('d-none');

    fetch('/manufatura/sugestao-compras/api/calcular')
        .then(res => res.json())
        .then(data => {
            loading.classList.add('d-none');
            btnCalc.disabled = false;

            if (!data.sucesso) {
                toastr.error(data.erro || 'Erro ao calcular sugestoes');
                return;
            }

            dadosSugestoes = data.sugestoes || [];
            preencherFiltros(dadosSugestoes);
            atualizarResumo(data);
            aplicarFiltrosERenderizar();

            resumo.classList.remove('d-none');
            resultado.classList.remove('d-none');
        })
        .catch(err => {
            loading.classList.add('d-none');
            btnCalc.disabled = false;
            toastr.error('Erro de conexao: ' + err.message);
        });
}

// ========================================
// RESUMO
// ========================================

function atualizarResumo(data) {
    document.getElementById('stat-total').textContent = data.total_sugestoes;
    document.getElementById('stat-tempo').textContent = data.tempo_calculo_s + 's';

    const comNecessidade = dadosSugestoes.filter(s => s.necessidade_liquida > 0).length;
    const criticos = dadosSugestoes.filter(s => s.urgencia === 'critico').length;

    document.getElementById('stat-necessidade').textContent = comNecessidade;
    document.getElementById('stat-criticos').textContent = criticos;
}

// ========================================
// FILTROS
// ========================================

function preencherFiltros(dados) {
    const tipos = [...new Set(dados.map(d => d.tipo_materia_prima).filter(Boolean))].sort();
    const cats = [...new Set(dados.map(d => d.categoria_produto).filter(Boolean))].sort();

    const selTipo = document.getElementById('filtro-tipo-mp');
    const selCat = document.getElementById('filtro-categoria');

    // Preservar selecao atual
    const tipoAtual = selTipo.value;
    const catAtual = selCat.value;

    // Limpar opcoes (manter "Todos")
    selTipo.innerHTML = '<option value="">Todos</option>';
    selCat.innerHTML = '<option value="">Todas</option>';

    tipos.forEach(t => {
        const opt = document.createElement('option');
        opt.value = t;
        opt.textContent = t;
        selTipo.appendChild(opt);
    });

    cats.forEach(c => {
        const opt = document.createElement('option');
        opt.value = c;
        opt.textContent = c;
        selCat.appendChild(opt);
    });

    // Restaurar selecao
    selTipo.value = tipoAtual;
    selCat.value = catAtual;
}

function getFiltrados() {
    const tipoMp = document.getElementById('filtro-tipo-mp').value;
    const cat = document.getElementById('filtro-categoria').value;
    const urgencia = document.getElementById('filtro-urgencia').value;
    const busca = document.getElementById('filtro-busca').value.toLowerCase().trim();
    const apenasNecessidade = document.getElementById('filtro-apenas-necessidade').checked;

    return dadosSugestoes.filter(s => {
        if (tipoMp && s.tipo_materia_prima !== tipoMp) return false;
        if (cat && s.categoria_produto !== cat) return false;
        if (urgencia && s.urgencia !== urgencia) return false;
        if (apenasNecessidade && s.necessidade_liquida <= 0) return false;
        if (busca) {
            const cod = (s.cod_produto || '').toLowerCase();
            const nome = (s.nome_produto || '').toLowerCase();
            if (!cod.includes(busca) && !nome.includes(busca)) return false;
        }
        return true;
    });
}

function aplicarFiltrosERenderizar() {
    const filtrados = getFiltrados();
    const ordenados = ordenar(filtrados, sortCol, sortAsc);
    renderizarTabela(ordenados);
    document.getElementById('info-filtro').textContent =
        `Exibindo ${ordenados.length} de ${dadosSugestoes.length} componentes`;
}

// ========================================
// ORDENACAO
// ========================================

const urgenciaOrdem = { 'critico': 0, 'alerta': 1, 'ok': 2 };

function ordenar(dados, col, asc) {
    return [...dados].sort((a, b) => {
        let va = a[col];
        let vb = b[col];

        // Urgencia: ordem customizada
        if (col === 'urgencia') {
            va = urgenciaOrdem[va] !== undefined ? urgenciaOrdem[va] : 99;
            vb = urgenciaOrdem[vb] !== undefined ? urgenciaOrdem[vb] : 99;
        }

        // Null handling
        if (va == null && vb == null) return 0;
        if (va == null) return asc ? 1 : -1;
        if (vb == null) return asc ? -1 : 1;

        // Numeros
        if (typeof va === 'number' && typeof vb === 'number') {
            return asc ? va - vb : vb - va;
        }

        // Strings
        va = String(va);
        vb = String(vb);
        return asc ? va.localeCompare(vb) : vb.localeCompare(va);
    });
}

// ========================================
// RENDERIZAR TABELA
// ========================================

function formatarNumero(val, decimais) {
    if (val == null) return '-';
    return val.toLocaleString('pt-BR', {
        minimumFractionDigits: decimais || 0,
        maximumFractionDigits: decimais || 0
    });
}

function formatarData(isoStr) {
    if (!isoStr) return '-';
    const parts = isoStr.split('-');
    return parts[2] + '/' + parts[1] + '/' + parts[0];
}

function renderizarTabela(dados) {
    const tbody = document.getElementById('tabela-body');

    if (dados.length === 0) {
        tbody.innerHTML = '<tr><td colspan="11" class="text-center text-muted py-4">Nenhuma sugestao encontrada</td></tr>';
        return;
    }

    const hoje = new Date().toISOString().split('T')[0];

    const rows = dados.map(s => {
        const necessidadeCls = s.necessidade_liquida > 0 ? 'sc-valor-positivo' : (s.necessidade_liquida < 0 ? 'sc-valor-negativo' : '');
        const qtdSugeridaCls = s.qtd_sugerida > 0 ? 'sc-qtd-sugerida' : '';
        const dataPedirCls = s.data_pedir && s.data_pedir < hoje ? 'sc-data-atrasada' : '';

        const urgBadge = s.urgencia === 'critico'
            ? '<span class="sc-badge sc-badge-critico">Critico</span>'
            : s.urgencia === 'alerta'
                ? '<span class="sc-badge sc-badge-alerta">Alerta</span>'
                : '<span class="sc-badge sc-badge-ok">OK</span>';

        const emTransitoTitle = `Pedidos: ${formatarNumero(s.em_transito_pedidos, 0)} | Requisicoes: ${formatarNumero(s.em_transito_requisicoes, 0)}`;

        return `<tr>
            <td class="sc-col-sticky">
                <span class="sc-produto-cod">${s.cod_produto}</span>
                <span class="sc-produto-nome" title="${s.nome_produto || ''}">${s.nome_produto || ''}</span>
            </td>
            <td class="text-end">${formatarNumero(s.estoque_atual, 0)}</td>
            <td class="text-end">${formatarNumero(s.demanda_60d, 0)}</td>
            <td class="text-end"><span class="sc-em-transito" title="${emTransitoTitle}">${formatarNumero(s.em_transito, 0)}</span></td>
            <td class="text-end ${necessidadeCls}">${formatarNumero(s.necessidade_liquida, 0)}</td>
            <td class="text-end">${s.lote_minimo > 1 ? formatarNumero(s.lote_minimo, 0) : '-'}</td>
            <td class="text-end ${qtdSugeridaCls}">${s.qtd_sugerida > 0 ? formatarNumero(s.qtd_sugerida, 0) : '-'}</td>
            <td class="text-center">${s.lead_time > 0 ? s.lead_time + 'd' : '-'}</td>
            <td class="text-center ${dataPedirCls}">${formatarData(s.data_pedir)}</td>
            <td class="text-center">${urgBadge}</td>
            <td class="text-center">${s.tipo_materia_prima ? '<span class="sc-badge sc-badge-mp">' + s.tipo_materia_prima + '</span>' : '-'}</td>
        </tr>`;
    });

    tbody.innerHTML = rows.join('');
}

// ========================================
// EVENT LISTENERS
// ========================================

document.addEventListener('DOMContentLoaded', () => {
    // Filtros client-side
    ['filtro-tipo-mp', 'filtro-categoria', 'filtro-urgencia'].forEach(id => {
        document.getElementById(id).addEventListener('change', aplicarFiltrosERenderizar);
    });

    document.getElementById('filtro-busca').addEventListener('input', aplicarFiltrosERenderizar);
    document.getElementById('filtro-apenas-necessidade').addEventListener('change', aplicarFiltrosERenderizar);

    // Ordenacao por coluna
    document.querySelectorAll('.sc-table thead th[data-sort]').forEach(th => {
        th.addEventListener('click', () => {
            const col = th.dataset.sort;
            if (sortCol === col) {
                sortAsc = !sortAsc;
            } else {
                sortCol = col;
                sortAsc = true;
            }
            atualizarIconesSort(th);
            aplicarFiltrosERenderizar();
        });
    });

    // Auto-calcular ao carregar
    calcularSugestoes();
});

function atualizarIconesSort(thAtivo) {
    document.querySelectorAll('.sc-table thead th[data-sort]').forEach(th => {
        const icon = th.querySelector('i');
        th.classList.remove('sort-active');
        if (icon) {
            icon.className = 'fas fa-sort';
        }
    });

    thAtivo.classList.add('sort-active');
    const icon = thAtivo.querySelector('i');
    if (icon) {
        icon.className = sortAsc ? 'fas fa-sort-up' : 'fas fa-sort-down';
    }
}
