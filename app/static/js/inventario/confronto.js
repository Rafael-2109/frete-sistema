// Confronto de Inventário — frontend interativo
let LINHAS_CACHE = [];

function fmt(v) {
  if (v == null || v === '') return '';
  const n = Number(v);
  if (isNaN(n)) return '';
  return n.toLocaleString('pt-BR',
    {minimumFractionDigits: 3, maximumFractionDigits: 3});
}

function drillUrl(cod, empresa, tipo) {
  const params = new URLSearchParams({
    cod: cod, empresa: empresa || '', tipo: tipo || 'ESTOQUE',
    data_inicio: '2026-05-16',
  });
  return `/inventario/movimentacoes?${params}`;
}

function renderLinhas(linhas) {
  const tbody = document.getElementById('tbody-confronto');
  if (!linhas.length) {
    tbody.innerHTML = '<tr><td colspan="22" class="text-center">Nenhuma linha</td></tr>';
    return;
  }
  let html = '';
  for (const l of linhas) {
    const divergente = Math.abs(l.odoo_menos_mov || 0) > 1 ||
                       Math.abs(l.sist_menos_mov || 0) > 1;
    html += `<tr class="${divergente ? 'inv-row-divergente' : ''}">` +
      `<td><strong>${l.cod_produto}</strong></td>` +
      `<td>${l.nome_produto || ''}</td>` +
      `<td class="num">${fmt(l.inv_fb)}</td>` +
      `<td class="num">${fmt(l.inv_cd)}</td>` +
      `<td class="num">${fmt(l.inv_lf)}</td>` +
      `<td class="num"><strong>${fmt(l.inv_total)}</strong></td>` +
      `<td class="num inv-cell-drill" title="Ver movimentações de COMPRAS"` +
      ` onclick="window.open('${drillUrl(l.cod_produto, '', 'ESTOQUE')}','_blank')">${fmt(l.compras)}</td>` +
      `<td class="num inv-cell-drill" title="Ver produção (PA + componentes)"` +
      ` onclick="window.open('${drillUrl(l.cod_produto, '', 'PRODUCAO')}','_blank')">${fmt(l.pa)}</td>` +
      `<td class="num inv-cell-drill" title="Ver consumo de componentes"` +
      ` onclick="window.open('${drillUrl(l.cod_produto, '', 'PRODUCAO')}','_blank')">${fmt(l.componente)}</td>` +
      `<td class="num">${fmt(l.vendas)}</td>` +
      `<td class="num">${fmt(l.consumo)}</td>` +
      `<td class="num">${fmt(l.producao)}</td>` +
      `<td>${l.ajuste_local || ''}</td>` +
      `<td class="num">${fmt(l.ajuste_qtd)}</td>` +
      `<td class="num"><strong>${fmt(l.odoo)}</strong></td>` +
      `<td class="num"><strong>${fmt(l.mov)}</strong></td>` +
      `<td class="num"><strong>${fmt(l.sist)}</strong></td>` +
      `<td class="num">${fmt(l.odoo_menos_mov)}</td>` +
      `<td class="num">${fmt(l.sist_menos_mov)}</td>` +
      `<td class="num inv-cell-drill" title="Movimentações FB"` +
      ` onclick="window.open('${drillUrl(l.cod_produto, 'FB', 'ESTOQUE')}','_blank')">${fmt(l.est_fb)}</td>` +
      `<td class="num inv-cell-drill" title="Movimentações CD"` +
      ` onclick="window.open('${drillUrl(l.cod_produto, 'CD', 'ESTOQUE')}','_blank')">${fmt(l.est_cd)}</td>` +
      `<td class="num inv-cell-drill" title="Movimentações LF"` +
      ` onclick="window.open('${drillUrl(l.cod_produto, 'LF', 'ESTOQUE')}','_blank')">${fmt(l.est_lf)}</td>` +
      `</tr>`;
  }
  tbody.innerHTML = html;
  document.getElementById('resumo').textContent = `${linhas.length} produtos`;
}

function aplicarFiltros() {
  const busca = (document.getElementById('filtro-busca').value || '').toLowerCase();
  const soDiv = document.getElementById('filtro-divergente').checked;
  let f = LINHAS_CACHE;
  if (busca) {
    f = f.filter(l => (l.cod_produto || '').toLowerCase().includes(busca) ||
                       (l.nome_produto || '').toLowerCase().includes(busca));
  }
  if (soDiv) {
    f = f.filter(l => Math.abs(l.odoo_menos_mov || 0) > 1 ||
                      Math.abs(l.sist_menos_mov || 0) > 1);
  }
  renderLinhas(f);
}

function carregar() {
  fetch(`/inventario/confronto/${CICLO_ID}/api`)
    .then(r => r.json())
    .then(data => {
      LINHAS_CACHE = data.linhas || [];
      aplicarFiltros();
    })
    .catch(err => {
      document.getElementById('tbody-confronto').innerHTML =
        `<tr><td colspan="22" class="text-danger">Erro: ${err}</td></tr>`;
    });
}

function pollJob(jobId) {
  const interval = setInterval(() => {
    fetch(`/inventario/snapshot/${CICLO_ID}/status/${jobId}`)
      .then(r => r.json())
      .then(d => {
        const bar = document.querySelector('#job-progress .progress-bar');
        bar.style.width = (d.progress || 0) + '%';
        document.getElementById('job-msg').textContent = d.msg || d.status;
        if (d.status === 'finished') {
          clearInterval(interval);
          document.getElementById('job-progress').classList.add('d-none');
          carregar();
        } else if (d.status === 'failed') {
          clearInterval(interval);
          document.getElementById('job-msg').textContent = 'FALHOU — ver logs';
        }
      })
      .catch(() => {});
  }, 2000);
}

document.getElementById('btn-refresh').addEventListener('click', () => {
  document.getElementById('job-progress').classList.remove('d-none');
  fetch(`/inventario/snapshot/${CICLO_ID}/refresh`, {method: 'POST'})
    .then(r => r.json()).then(d => pollJob(d.job_id));
});
document.getElementById('filtro-busca').addEventListener('input', aplicarFiltros);
document.getElementById('filtro-divergente').addEventListener('change', aplicarFiltros);
carregar();
