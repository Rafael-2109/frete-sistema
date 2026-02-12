/**
 * modal-sugestao-inteligente.js - Modal de Sugestao Inteligente
 *
 * Projecao dia-a-dia com sugestoes automaticas de compra.
 */

let siCodProduto = '';
let siInicio = 0;
let siFim = 30;

function abrirModalSugestaoInteligente(codProduto) {
    siCodProduto = codProduto;
    siInicio = 0;
    siFim = 30;

    const modal = new bootstrap.Modal(document.getElementById('modalSugestaoInteligente'));

    // Buscar nome do produto nos dados ja carregados
    const prod = dadosSugestoes.find(s => s.cod_produto === codProduto);
    const nomeProduto = prod ? prod.nome_produto : '';
    document.getElementById('si-produto-info').textContent =
        codProduto + (nomeProduto ? ' - ' + nomeProduto : '');

    // Reset btn-group ativo
    _resetBtnGroupSI(0, 30);

    modal.show();
    carregarSugestaoInteligente();
}

function selecionarPeriodoSI(inicio, fim) {
    siInicio = inicio;
    siFim = fim;
    _resetBtnGroupSI(inicio, fim);
    carregarSugestaoInteligente();
}

function _resetBtnGroupSI(inicio, fim) {
    const btns = document.querySelectorAll('#modalSugestaoInteligente .btn-group .btn');
    btns.forEach(btn => {
        btn.classList.remove('active');
        const label = btn.textContent.trim();
        if (label === inicio + '-' + fim + 'D') {
            btn.classList.add('active');
        }
    });
}

function carregarSugestaoInteligente() {
    const loading = document.getElementById('si-loading');
    const conteudo = document.getElementById('si-conteudo');

    loading.classList.remove('d-none');
    conteudo.classList.add('d-none');

    const url = '/manufatura/sugestao-compras/api/sugestao-inteligente?cod_produto=' +
        encodeURIComponent(siCodProduto) +
        '&inicio=' + siInicio +
        '&fim=' + siFim;

    fetch(url)
        .then(res => res.json())
        .then(data => {
            loading.classList.add('d-none');

            if (!data.sucesso) {
                toastr.error(data.erro || 'Erro ao calcular sugestao inteligente');
                return;
            }

            renderizarSugestaoInteligente(data);
            conteudo.classList.remove('d-none');
        })
        .catch(err => {
            loading.classList.add('d-none');
            toastr.error('Erro de conexao: ' + err.message);
        });
}

function renderizarSugestaoInteligente(data) {
    // Cards resumo
    document.getElementById('si-estoque-atual').textContent = formatarNumero(data.estoque_atual, 0);
    document.getElementById('si-lead-time').textContent = data.lead_time > 0 ? data.lead_time + 'd' : '-';
    document.getElementById('si-lote-minimo').textContent = data.lote_minimo > 1 ? formatarNumero(data.lote_minimo, 0) : '-';
    document.getElementById('si-total-sugestoes').textContent = data.total_sugestoes;

    // Card de sugestoes
    const sugestoesCard = document.getElementById('si-sugestoes-card');
    const sugestoesLista = document.getElementById('si-sugestoes-lista');

    if (data.sugestoes.length > 0) {
        sugestoesCard.classList.remove('d-none');

        sugestoesLista.innerHTML = data.sugestoes.map((sug, idx) => {
            const atrasadoBadge = sug.atrasado
                ? '<span class="sc-badge sc-badge-atrasado ms-2">ATRASADO</span>'
                : '';
            const diasTexto = sug.dias_ate_pedir < 0
                ? Math.abs(sug.dias_ate_pedir) + 'd atras'
                : sug.dias_ate_pedir === 0
                    ? 'Hoje'
                    : 'em ' + sug.dias_ate_pedir + 'd';

            return `<div class="sc-sugestao-item d-flex justify-content-between align-items-center">
                <div>
                    <span class="sc-badge sc-badge-sugestao me-2">#${idx + 1}</span>
                    <strong>Pedir ${formatarData(sug.data_pedir)}</strong> (${diasTexto})
                    ${atrasadoBadge}
                    <span class="text-muted mx-2">|</span>
                    Chegada: ${formatarData(sug.data_chegada)}
                </div>
                <div class="text-end">
                    <strong>${formatarNumero(sug.qtd_comprar, 0)}</strong> un
                    <span class="text-muted ms-1">(nec: ${formatarNumero(sug.necessidade, 0)})</span>
                </div>
            </div>`;
        }).join('');
    } else {
        sugestoesCard.classList.add('d-none');
    }

    // Tabela dia-a-dia
    const tbody = document.getElementById('si-tabela-body');

    if (data.projecao.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="sc-alerta-vazio">Sem dados para o periodo selecionado</td></tr>';
        return;
    }

    tbody.innerHTML = data.projecao.map(dia => {
        let rowClass = '';
        if (dia.tem_sugestao) {
            rowClass = 'sc-row-sugestao';
        } else if (dia.saldo_final < 0) {
            rowClass = 'sc-row-ruptura';
        }

        const saldoCls = dia.saldo_final < 0 ? 'sc-text-critico fw-bold' : '';
        const sugestaoCls = dia.chegada_sugestao > 0 ? 'sc-text-alerta fw-bold' : '';

        // Indicador de POs atrasados projetados em D0
        let chegadaPoHtml = dia.chegada_po > 0 ? formatarNumero(dia.chegada_po, 0) : '-';
        if (dia.chegada_atrasada > 0) {
            chegadaPoHtml = formatarNumero(dia.chegada_po, 0)
                + ' <span class="sc-badge sc-badge-atrasado">'
                + formatarNumero(dia.chegada_atrasada, 0) + ' atrasado</span>';
        }

        return `<tr class="${rowClass}">
            <td>${formatarData(dia.data)}</td>
            <td class="text-end">${formatarNumero(dia.estoque_inicial, 0)}</td>
            <td class="text-end">${dia.consumo > 0 ? formatarNumero(dia.consumo, 0) : '-'}</td>
            <td class="text-end">${chegadaPoHtml}</td>
            <td class="text-end ${sugestaoCls}">${dia.chegada_sugestao > 0 ? formatarNumero(dia.chegada_sugestao, 0) : '-'}</td>
            <td class="text-end ${saldoCls}">${formatarNumero(dia.saldo_final, 0)}</td>
        </tr>`;
    }).join('');
}
