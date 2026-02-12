/**
 * modal-cardex.js - Modal de Cardex Projetado
 *
 * Projecao dia-a-dia do estoque com periodos de 30 dias.
 */

let cardexCodProduto = '';
let cardexInicio = 0;
let cardexFim = 30;

function abrirModalCardex(codProduto) {
    cardexCodProduto = codProduto;
    cardexInicio = 0;
    cardexFim = 30;

    const modal = new bootstrap.Modal(document.getElementById('modalCardex'));

    // Buscar nome do produto nos dados ja carregados
    const prod = dadosSugestoes.find(s => s.cod_produto === codProduto);
    const nomeProduto = prod ? prod.nome_produto : '';
    document.getElementById('cx-produto-info').textContent =
        codProduto + (nomeProduto ? ' - ' + nomeProduto : '');

    // Reset btn-group ativo
    _resetBtnGroupCardex(0, 30);

    modal.show();
    carregarCardex();
}

function selecionarPeriodoCardex(inicio, fim) {
    cardexInicio = inicio;
    cardexFim = fim;
    _resetBtnGroupCardex(inicio, fim);
    carregarCardex();
}

function _resetBtnGroupCardex(inicio, fim) {
    const btns = document.querySelectorAll('#modalCardex .btn-group .btn');
    btns.forEach(btn => {
        btn.classList.remove('active');
        const label = btn.textContent.trim();
        if (label === inicio + '-' + fim + 'D') {
            btn.classList.add('active');
        }
    });
}

function carregarCardex() {
    const loading = document.getElementById('cx-loading');
    const conteudo = document.getElementById('cx-conteudo');

    loading.classList.remove('d-none');
    conteudo.classList.add('d-none');

    const url = '/manufatura/sugestao-compras/api/cardex?cod_produto=' +
        encodeURIComponent(cardexCodProduto) +
        '&inicio=' + cardexInicio +
        '&fim=' + cardexFim;

    fetch(url)
        .then(res => res.json())
        .then(data => {
            loading.classList.add('d-none');

            if (!data.sucesso) {
                toastr.error(data.erro || 'Erro ao calcular cardex');
                return;
            }

            renderizarCardex(data);
            conteudo.classList.remove('d-none');
        })
        .catch(err => {
            loading.classList.add('d-none');
            toastr.error('Erro de conexao: ' + err.message);
        });
}

function renderizarCardex(data) {
    // Cards resumo
    document.getElementById('cx-estoque-atual').textContent = formatarNumero(data.estoque_atual, 0);
    document.getElementById('cx-lead-time').textContent = data.lead_time > 0 ? data.lead_time + 'd' : '-';
    document.getElementById('cx-lote-minimo').textContent = data.lote_minimo > 1 ? formatarNumero(data.lote_minimo, 0) : '-';

    const menorSaldoEl = document.getElementById('cx-menor-saldo');
    menorSaldoEl.textContent = formatarNumero(data.menor_saldo, 0);
    menorSaldoEl.className = 'sc-stat-value' + (data.menor_saldo < 0 ? ' sc-text-critico' : '');

    // Tabela dia-a-dia
    const tbody = document.getElementById('cx-tabela-body');

    if (data.projecao.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="sc-alerta-vazio">Sem dados para o periodo selecionado</td></tr>';
        return;
    }

    tbody.innerHTML = data.projecao.map(dia => {
        const rowClass = dia.saldo_final < 0 ? 'sc-row-ruptura' : '';
        const saldoCls = dia.saldo_final < 0 ? 'sc-text-critico fw-bold' : '';

        // Indicador de POs atrasados projetados em D0
        let chegadaHtml = dia.chegada > 0 ? formatarNumero(dia.chegada, 0) : '-';
        if (dia.chegada_atrasada > 0) {
            chegadaHtml = formatarNumero(dia.chegada, 0)
                + ' <span class="sc-badge sc-badge-atrasado">'
                + formatarNumero(dia.chegada_atrasada, 0) + ' atrasado</span>';
        }

        return `<tr class="${rowClass}">
            <td>${formatarData(dia.data)}</td>
            <td class="text-end">${formatarNumero(dia.estoque_inicial, 0)}</td>
            <td class="text-end">${dia.consumo > 0 ? formatarNumero(dia.consumo, 0) : '-'}</td>
            <td class="text-end">${chegadaHtml}</td>
            <td class="text-end ${saldoCls}">${formatarNumero(dia.saldo_final, 0)}</td>
        </tr>`;
    }).join('');
}
