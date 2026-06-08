/* Transferência de Estoque (Odoo) — 3 modos. Vanilla JS, sem libs externas. */
(function () {
  'use strict';
  const CSRF = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
  const $ = (id) => document.getElementById(id);
  const BASE = '/estoque/transferencia-estoque';
  let dados = null;        // resposta de /api/dados-codigo
  let ultimoPayload = null;

  function alerta(msg, tipo) {
    $('te-alerta').innerHTML =
      `<div class="alert alert-${tipo} alert-dismissible fade show">${msg}` +
      `<button class="btn-close" data-bs-dismiss="alert"></button></div>`;
  }
  function num(v) { return (v === null || v === undefined) ? '-' : Number(v).toLocaleString('pt-BR'); }

  /* ---------- autocomplete genérico ---------- */
  function autocomplete(input, urlFn, onPick) {
    const dd = document.createElement('div');
    dd.className = 'list-group position-absolute shadow';
    dd.style.cssText = 'z-index:1080;max-height:260px;overflow:auto;display:none;min-width:260px;';
    input.parentNode.style.position = 'relative';
    input.parentNode.appendChild(dd);
    let t;
    function hide() { dd.style.display = 'none'; }
    input.addEventListener('input', () => {
      clearTimeout(t);
      const q = input.value.trim();
      if (q.length < 2) { hide(); return; }
      t = setTimeout(async () => {
        const url = urlFn(q);
        if (!url) { hide(); return; }
        const r = await fetch(url); const items = await r.json();
        dd.innerHTML = '';
        if (!items.length) { hide(); return; }
        items.forEach((it) => {
          const a = document.createElement('button');
          a.type = 'button'; a.className = 'list-group-item list-group-item-action';
          a.textContent = it.label;
          a.addEventListener('click', () => { onPick(it); hide(); });
          dd.appendChild(a);
        });
        dd.style.display = 'block';
      }, 200);
    });
    input.addEventListener('blur', () => setTimeout(hide, 200));
  }

  /* ---------- carregar painel A/B/C ---------- */
  async function carregarDados() {
    const cod = $('te-cod-origem-val').value || $('te-cod-origem').value.trim();
    const empresa = $('te-empresa').value;
    if (!cod) return;
    const r = await fetch(`${BASE}/api/dados-codigo?codigo=${encodeURIComponent(cod)}&empresa=${empresa}`);
    dados = await r.json();
    if (!dados.success) { alerta(dados.message, 'danger'); $('te-painel').classList.add('d-none'); return; }
    if (!dados.produto) { alerta(dados.message || 'Sem saldo', 'warning'); $('te-painel').classList.add('d-none'); renderForm(); return; }
    $('te-prod-origem-info').textContent = `${dados.produto.cod} — ${dados.produto.name} (tracking: ${dados.produto.tracking})`;
    if ($('te-reservada-total')) $('te-reservada-total').textContent = num(dados.reservada_total);
    // Saldo por Local × Lote em grid de 2 colunas (col-md-6)
    const celulas = dados.por_local_lote || [];
    $('te-detalhe').innerHTML = celulas.length ? celulas.map((r) =>
      `<div class="col-md-6 mb-2"><div class="border rounded p-2 h-100 small">` +
        `<div class="d-flex justify-content-between">` +
          `<span><strong>${r.location_name}</strong>${r.is_indisp ? ' <span class="badge bg-secondary">Indisp.</span>' : ''}</span>` +
          `<span class="text-muted">${r.lote}${r.is_migracao ? ' <span class="badge bg-secondary">MIGRAÇÃO</span>' : ''}</span></div>` +
        `<div class="mt-1">Qtd <b>${num(r.qty)}</b> · Reserv. ${num(r.reservada)} · ` +
          `Disp. <b class="text-success">${num(r.disponivel)}</b></div>` +
      `</div></div>`).join('') : '<div class="col-12 text-muted">Sem saldo.</div>';
    $('te-painel').classList.remove('d-none');
    renderForm();
  }

  function optLocais() {
    return (dados?.por_local || []).map((l) =>
      `<option value="${l.location_id}">${l.location_name} (disp ${num(l.disponivel)})</option>`).join('');
  }
  function optLotes() {
    return (dados?.por_lote || []).map((l) =>
      `<option value="${l.lote === '(sem lote)' ? '' : l.lote}">${l.lote} (disp ${num(l.disponivel)})</option>`).join('');
  }

  /* ---------- Modo 1: opções cruzadas (local × lote) ---------- */
  function pll() { return dados?.por_local_lote || []; }
  function optLocaisFiltrado(loteDisplay) {
    const by = new Map();
    pll().filter((r) => !loteDisplay || r.lote === loteDisplay).forEach((r) => {
      const cur = by.get(r.location_id) ||
        { location_id: r.location_id, location_name: r.location_name, disponivel: 0 };
      cur.disponivel += r.disponivel; by.set(r.location_id, cur);
    });
    return [...by.values()].map((l) =>
      `<option value="${l.location_id}">${l.location_name} (disp ${num(l.disponivel)})</option>`).join('');
  }
  function optLotesFiltrado(locId) {
    const by = new Map();
    pll().filter((r) => !locId || String(r.location_id) === String(locId)).forEach((r) => {
      const cur = by.get(r.lote) || { lote: r.lote, disponivel: 0 };
      cur.disponivel += r.disponivel; by.set(r.lote, cur);
    });
    return [...by.values()].map((l) =>
      `<option value="${l.lote === '(sem lote)' ? '' : l.lote}" data-lote="${l.lote}">` +
      `${l.lote} (disp ${num(l.disponivel)})</option>`).join('');
  }
  function setSelectOptions(sel, html, prevValue) {
    sel.innerHTML = html;
    if (prevValue !== undefined && prevValue !== null &&
        [...sel.options].some((o) => o.value === prevValue)) sel.value = prevValue;
  }
  function loteDisplaySel() {
    const sel = $('m-lote');
    if (!sel || sel.selectedIndex < 0) return '';
    const opt = sel.options[sel.selectedIndex];
    return opt ? (opt.getAttribute('data-lote') || opt.value || '(sem lote)') : '';
  }
  // Repopula o "outro" select sem disparar change (evita loop). origem = 'lote'|'local'.
  function refiltrarModo1(origem) {
    const loteSel = $('m-lote'); const locSel = $('m-loc-o');
    if (!loteSel || !locSel) return;
    if (origem === 'lote') setSelectOptions(locSel, optLocaisFiltrado(loteDisplaySel()), locSel.value);
    else setSelectOptions(loteSel, optLotesFiltrado(locSel.value), loteSel.value);
  }

  function inputLocalDestino(id) {
    return `<input type="text" id="${id}" class="form-control" autocomplete="off" placeholder="local destino">` +
           `<input type="hidden" id="${id}-val">`;
  }

  /* ---------- formulário por modo ---------- */
  function renderForm() {
    const modo = $('te-modo').value;
    const C = $('te-campos');
    if (modo === '1') {
      $('te-form-titulo').textContent = 'Modo 1 · Local → Local (mesmo código e lote)';
      C.innerHTML =
        `<div class="col-md-3"><label class="form-label">Lote</label><select id="m-lote" class="form-select"></select></div>` +
        `<div class="col-md-3"><label class="form-label">Local origem</label><select id="m-loc-o" class="form-select"></select></div>` +
        `<div class="col-md-3"><label class="form-label">Local destino</label>${inputLocalDestino('m-loc-d')}</div>` +
        `<div class="col-md-3"><label class="form-label">Qtd</label><input type="number" id="m-qty" class="form-control" min="0" step="0.001"></div>`;
      // Popula selects e aplica filtro cruzado inicial (locais do lote pré-selecionado)
      $('m-lote').innerHTML = optLotesFiltrado(null);
      $('m-loc-o').innerHTML = optLocaisFiltrado(null);
      refiltrarModo1('lote');
      // Filtro cruzado bidirecional: Lote considera o Local e vice-versa
      $('m-lote').addEventListener('change', () => refiltrarModo1('lote'));
      $('m-loc-o').addEventListener('change', () => refiltrarModo1('local'));
      // FIX: autocomplete do Local destino (estava ausente → location_id_destino vazio → int(''))
      const empresa1 = $('te-empresa').value;
      autocomplete($('m-loc-d'),
        (q) => `${BASE}/api/autocomplete/local?q=${encodeURIComponent(q)}&empresa=${empresa1}`,
        (it) => { $('m-loc-d').value = it.complete_name; $('m-loc-d-val').value = it.location_id; });
    } else if (modo === '2') {
      $('te-form-titulo').textContent = 'Modo 2 · Lote → Lote (mesmo código e local)';
      C.innerHTML =
        `<div class="col-md-3"><label class="form-label">Local</label><select id="m-loc" class="form-select">${optLocais()}</select></div>` +
        `<div class="col-md-3"><label class="form-label">Lote origem</label><select id="m-lote-o" class="form-select">${optLotes()}</select></div>` +
        `<div class="col-md-3"><label class="form-label">Lote destino</label><input type="text" id="m-lote-d" class="form-control" placeholder="lote destino"></div>` +
        `<div class="col-md-3"><label class="form-label">Qtd</label><input type="number" id="m-qty" class="form-control" min="0" step="0.001"></div>`;
      $('m-lote-o').addEventListener('change', () => { $('m-lote-d').value = $('m-lote-o').value; }); // prefill 3.2
      $('m-lote-d').value = $('m-lote-o')?.value || '';
    } else {
      $('te-form-titulo').textContent = 'Modo 3 · Código → Código';
      C.innerHTML =
        `<div class="col-md-4"><label class="form-label">Código destino</label><input type="text" id="m-cod-d" class="form-control" autocomplete="off" placeholder="código destino"><input type="hidden" id="m-cod-d-val"><div id="m-aviso-par" class="form-text"></div></div>` +
        `<div class="col-md-4"><label class="form-label">Lote origem</label><select id="m-lote-o" class="form-select"><option value="">(sem lote)</option>${optLotes()}</select></div>` +
        `<div class="col-md-4"><label class="form-label">Lote destino</label><input type="text" id="m-lote-d" class="form-control" placeholder="lote destino"></div>` +
        `<div class="col-md-4 mt-2"><label class="form-label">Local origem</label><select id="m-loc-o" class="form-select">${optLocais()}</select></div>` +
        `<div class="col-md-4 mt-2"><label class="form-label">Local destino</label>${inputLocalDestino('m-loc-d')}</div>` +
        `<div class="col-md-4 mt-2"><label class="form-label">Qtd</label><input type="number" id="m-qty" class="form-control" min="0" step="0.001"></div>`;
      // prefills 3.2 / 3.3
      $('m-lote-o').addEventListener('change', () => { $('m-lote-d').value = $('m-lote-o').value; });
      $('m-lote-d').value = $('m-lote-o')?.value || '';
      $('m-loc-o').addEventListener('change', () => {
        const sel = $('m-loc-o'); $('m-loc-d').value = sel.options[sel.selectedIndex].text.split(' (')[0];
        $('m-loc-d-val').value = sel.value;
      });
      if ($('m-loc-o').options.length) { $('m-loc-o').dispatchEvent(new Event('change')); }
      const empresa = $('te-empresa').value;
      autocomplete($('m-cod-d'), (q) => `${BASE}/api/autocomplete/produto?q=${encodeURIComponent(q)}`,
        (it) => { $('m-cod-d').value = it.label; $('m-cod-d-val').value = it.cod; });
      autocomplete($('m-loc-d'), (q) => `${BASE}/api/autocomplete/local?q=${encodeURIComponent(q)}&empresa=${empresa}`,
        (it) => { $('m-loc-d').value = it.complete_name; $('m-loc-d-val').value = it.location_id; });
    }
    $('te-form').classList.remove('d-none');
    $('te-preview').classList.add('d-none');
  }

  /* ---------- montar payload por modo ---------- */
  function montarPayload() {
    const modo = $('te-modo').value;
    const base = { modo, empresa: $('te-empresa').value,
      cod_origem: $('te-cod-origem-val').value || $('te-cod-origem').value.trim(),
      qty: parseFloat($('m-qty').value) };
    if (modo === '1') return { ...base, lote_nome: $('m-lote').value || null,
      location_id_origem: $('m-loc-o').value, location_id_destino: $('m-loc-d-val').value };
    if (modo === '2') return { ...base, location_id: $('m-loc').value,
      lote_nome_origem: $('m-lote-o').value || null, lote_nome_destino: $('m-lote-d').value };
    return { ...base, cod_destino: $('m-cod-d-val').value || $('m-cod-d').value.trim(),
      lote_nome_origem: $('m-lote-o').value || null, lote_nome_destino: $('m-lote-d').value || null,
      location_id_origem: $('m-loc-o').value, location_id_destino: $('m-loc-d-val').value };
  }

  async function chamar(endpoint, payload) {
    const r = await fetch(`${BASE}/api/${endpoint}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
      body: JSON.stringify(payload) });
    return r.json();
  }

  async function simular() {
    ultimoPayload = montarPayload();
    if (!ultimoPayload.qty || ultimoPayload.qty <= 0) { alerta('Informe a quantidade', 'warning'); return; }
    const modoS = $('te-modo').value;
    if (modoS === '1' || modoS === '3') {
      if (!ultimoPayload.location_id_origem) { alerta('Selecione o local origem', 'warning'); return; }
      if (!ultimoPayload.location_id_destino) {
        alerta('Selecione o local destino na lista (autocomplete)', 'warning'); return;
      }
    }
    $('te-btn-simular').disabled = true;
    const d = await chamar('simular', ultimoPayload);
    $('te-btn-simular').disabled = false;
    if (!d.success) { alerta(d.message, 'danger'); $('te-preview').classList.add('d-none'); return; }
    const p = d.preview;
    $('te-preview-body').innerHTML =
      (d.aviso_par ? '<div class="alert alert-warning py-1">⚠ Código destino não é par cadastrado em Unificação.</div>' : '') +
      `<p>Origem <code>${p.origem.label}</code>: <b>${num(p.origem.antes)} → ${num(p.origem.apos)}</b></p>` +
      `<p>Destino <code>${p.destino.label}</code>: <b>${num(p.destino.antes)} → ${num(p.destino.apos)}</b>` +
      (p.destino.lote_criado ? ' <span class="badge bg-info">lote será criado</span>' : '') + '</p>';
    $('te-preview').classList.remove('d-none');
  }

  async function confirmar() {
    if (!ultimoPayload) return;
    $('te-btn-confirmar').disabled = true;
    const d = await chamar('executar', ultimoPayload);
    $('te-btn-confirmar').disabled = false;
    alerta(d.success ? `✔ Transferência executada (${d.status}).` : d.message, d.success ? 'success' : 'danger');
    if (d.success) { $('te-preview').classList.add('d-none'); carregarDados(); }
  }

  /* ---------- wiring ---------- */
  document.addEventListener('DOMContentLoaded', () => {
    autocomplete($('te-cod-origem'),
      (q) => `${BASE}/api/autocomplete/produto?q=${encodeURIComponent(q)}`,
      (it) => { $('te-cod-origem').value = it.label; $('te-cod-origem-val').value = it.cod; carregarDados(); });
    $('te-empresa').addEventListener('change', carregarDados);
    $('te-modo').addEventListener('change', renderForm);
    $('te-btn-simular').addEventListener('click', simular);
    $('te-btn-confirmar').addEventListener('click', confirmar);
    $('te-btn-cancelar').addEventListener('click', () => $('te-preview').classList.add('d-none'));
  });
})();
