// Confronto de Inventario — frontend interativo
// CICLO_ID injetado pelo template (confronto.html)
let LINHAS_CACHE = [];
const SAVE_DEBOUNCE_MS = 600;
const _saveTimers = {};
const DIFF_THRESHOLD = 1;

function fmt(v) {
  if (v == null || v === '') return '-';
  const n = Number(v);
  if (isNaN(n)) return '-';
  if (Math.abs(n) < 0.0005) return '-';
  return n.toLocaleString('pt-BR',
    {minimumFractionDigits: 3, maximumFractionDigits: 3});
}

function diffClass(v) {
  const n = Number(v) || 0;
  if (n > DIFF_THRESHOLD) return 'inv-diff-pos';
  if (n < -DIFF_THRESHOLD) return 'inv-diff-neg';
  return '';
}

function escapeAttr(s) {
  if (s == null) return '';
  return String(s).replace(/&/g, '&amp;').replace(/"/g, '&quot;')
                  .replace(/</g, '&lt;').replace(/>/g, '&gt;');
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
    const divergente = Math.abs(l.odoo_menos_mov || 0) > DIFF_THRESHOLD ||
                       Math.abs(l.sist_menos_mov || 0) > DIFF_THRESHOLD;
    const cod = escapeAttr(l.cod_produto);
    const ajLocal = l.ajuste_local == null ? '' : escapeAttr(l.ajuste_local);
    const ajQtd = (l.ajuste_qtd == null || l.ajuste_qtd === '') ? '' :
                  Number(l.ajuste_qtd).toLocaleString('pt-BR',
                    {minimumFractionDigits: 3, maximumFractionDigits: 3,
                     useGrouping: false});
    html += `<tr class="${divergente ? 'inv-row-divergente' : ''}" data-cod="${cod}">` +
      `<td class="txt"><strong>${cod}</strong></td>` +
      `<td class="txt" title="${escapeAttr(l.nome_produto || '')}">${l.nome_produto || ''}</td>` +
      `<td class="num">${fmt(l.inv_fb)}</td>` +
      `<td class="num">${fmt(l.inv_cd)}</td>` +
      `<td class="num">${fmt(l.inv_lf)}</td>` +
      `<td class="num"><strong>${fmt(l.inv_total)}</strong></td>` +
      `<td class="num inv-cell-drill" title="Movimentações de COMPRAS"` +
      ` onclick="window.open('${drillUrl(l.cod_produto, '', 'ESTOQUE')}','_blank')">${fmt(l.compras)}</td>` +
      `<td class="num inv-cell-drill" title="Produção (PA + componentes)"` +
      ` onclick="window.open('${drillUrl(l.cod_produto, '', 'PRODUCAO')}','_blank')">${fmt(l.pa)}</td>` +
      `<td class="num inv-cell-drill" title="Consumo de componentes"` +
      ` onclick="window.open('${drillUrl(l.cod_produto, '', 'PRODUCAO')}','_blank')">${fmt(l.componente)}</td>` +
      `<td class="num">${fmt(l.vendas)}</td>` +
      `<td class="num">${fmt(l.consumo)}</td>` +
      `<td class="num">${fmt(l.producao)}</td>` +
      `<td class="txt inv-aj-local-cell">` +
        `<input class="inv-input" type="text" maxlength="20" ` +
               `value="${ajLocal}" placeholder="-" ` +
               `data-field="local" data-cod="${cod}">` +
      `</td>` +
      `<td class="num inv-aj-qtd-cell">` +
        `<input class="inv-input num" type="text" inputmode="decimal" ` +
               `value="${ajQtd}" placeholder="-" ` +
               `data-field="qtd" data-cod="${cod}">` +
      `</td>` +
      `<td class="num"><strong>${fmt(l.odoo)}</strong></td>` +
      `<td class="num"><strong>${fmt(l.mov)}</strong></td>` +
      `<td class="num"><strong>${fmt(l.sist)}</strong></td>` +
      `<td class="num ${diffClass(l.odoo_menos_mov)}">${fmt(l.odoo_menos_mov)}</td>` +
      `<td class="num ${diffClass(l.sist_menos_mov)}">${fmt(l.sist_menos_mov)}</td>` +
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
  wireInlineEdit();
}

function getCsrfToken() {
  // CSRF do meta tag (base.html) ou cookie
  const m = document.querySelector('meta[name="csrf-token"]');
  if (m) return m.getAttribute('content');
  const c = document.cookie.split('; ').find(r => r.startsWith('csrf_token='));
  return c ? decodeURIComponent(c.split('=')[1]) : '';
}

function getLinhaCache(cod) {
  return LINHAS_CACHE.find(l => l.cod_produto === cod);
}

function persistAjuste(cod, td, getLocal, getQtd) {
  td.classList.remove('inv-saved', 'inv-error');
  td.classList.add('inv-saving');
  const linha = getLinhaCache(cod);
  const fd = new FormData();
  fd.append('cod_produto', cod);
  fd.append('local', getLocal());
  fd.append('qtd', getQtd());
  if (linha && linha.nome_produto) fd.append('nome_produto', linha.nome_produto);
  const csrf = getCsrfToken();
  if (csrf) fd.append('csrf_token', csrf);

  fetch(`/inventario/ajustes/${CICLO_ID}/upsert`, {method: 'POST', body: fd})
    .then(async r => {
      const txt = await r.text();
      let data;
      try { data = JSON.parse(txt); } catch (_) { data = {erro: txt}; }
      if (!r.ok || data.erro) throw new Error(data.erro || `HTTP ${r.status}`);
      return data;
    })
    .then(data => {
      td.classList.remove('inv-saving');
      td.classList.add('inv-saved');
      // Atualiza cache local
      if (linha) {
        linha.ajuste_local = getLocal() || null;
        const q = getQtd();
        linha.ajuste_qtd = q ? Number(q.replace(',', '.')) : null;
      }
      setTimeout(() => td.classList.remove('inv-saved'), 1500);
    })
    .catch(err => {
      td.classList.remove('inv-saving');
      td.classList.add('inv-error');
      td.title = `Erro ao salvar: ${err.message}`;
    });
}

function wireInlineEdit() {
  const tbody = document.getElementById('tbody-confronto');
  tbody.querySelectorAll('input.inv-input').forEach(inp => {
    inp.addEventListener('input', () => {
      const cod = inp.dataset.cod;
      const td = inp.closest('td');
      clearTimeout(_saveTimers[`${cod}:${inp.dataset.field}`]);
      _saveTimers[`${cod}:${inp.dataset.field}`] = setTimeout(() => {
        const tr = inp.closest('tr');
        const localInp = tr.querySelector('input[data-field="local"]');
        const qtdInp = tr.querySelector('input[data-field="qtd"]');
        persistAjuste(
          cod, td,
          () => (localInp.value || '').trim(),
          () => (qtdInp.value || '').trim().replace(',', '.'),
        );
      }, SAVE_DEBOUNCE_MS);
    });
    inp.addEventListener('blur', () => {
      const cod = inp.dataset.cod;
      const timerKey = `${cod}:${inp.dataset.field}`;
      if (_saveTimers[timerKey]) {
        clearTimeout(_saveTimers[timerKey]);
        const tr = inp.closest('tr');
        const td = inp.closest('td');
        const localInp = tr.querySelector('input[data-field="local"]');
        const qtdInp = tr.querySelector('input[data-field="qtd"]');
        persistAjuste(
          cod, td,
          () => (localInp.value || '').trim(),
          () => (qtdInp.value || '').trim().replace(',', '.'),
        );
      }
    });
  });
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
    f = f.filter(l => Math.abs(l.odoo_menos_mov || 0) > DIFF_THRESHOLD ||
                      Math.abs(l.sist_menos_mov || 0) > DIFF_THRESHOLD);
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
