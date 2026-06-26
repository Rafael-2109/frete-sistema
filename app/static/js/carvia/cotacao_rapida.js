/* cotacao_rapida.js — JS compartilhado da Cotacao Rapida (logado + publico).
 * Parametrizado via nó #cr-app (data-endpoint-* + data-modo).
 * Nao editar endpoints aqui — mudar no template que gera o #cr-app.
 */
(function () {
  const APP = document.getElementById('cr-app');
  const CFG = {
    calcular: APP.dataset.endpointCalcular,
    upload:   APP.dataset.endpointUpload,
    pdf:      APP.dataset.endpointPdf,
    cep:      APP.dataset.endpointCep,        // base; o CEP vai no path
    modo:     APP.dataset.modo || 'login',   // 'login' | 'publico'
  };
  const MODELOS = JSON.parse(document.getElementById('cr-modelos-data').textContent || '[]');
  const csrf = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
  const fmtBRL = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });
  const ultimaCotacao = { inputs: null };

  // ---------- helpers ----------
  function el(html) { const t = document.createElement('template'); t.innerHTML = html.trim(); return t.content.firstChild; }
  function esc(s) { const d = document.createElement('div'); d.textContent = s == null ? '' : s; return d.innerHTML; }

  function optionsModelos(selected) {
    let html = '<option value="">— modelo —</option>';
    MODELOS.forEach(m => {
      const cat = m.categoria_nome ? ` (${m.categoria_nome})` : ' (sem categoria)';
      html += `<option value="${m.id}" ${String(m.id) === String(selected) ? 'selected' : ''}>${esc(m.nome)}${esc(cat)}</option>`;
    });
    return html;
  }

  // ---------- linhas de moto ----------
  const motosBox = document.getElementById('cr-motos');

  function addMotoRow(modeloId, qtd) {
    const row = el(`
      <div class="row g-2 mb-2 cr-moto-row align-items-center">
        <div class="col-7"><select class="form-select form-select-sm js-modelo">${optionsModelos(modeloId)}</select></div>
        <div class="col-3"><input type="number" min="1" class="form-control form-control-sm js-qtd" value="${qtd || 1}" placeholder="Qtd"></div>
        <div class="col-2 text-end">
          <button type="button" class="btn btn-sm btn-outline-danger js-remove" title="Remover"><i class="fas fa-times"></i></button>
        </div>
      </div>`);
    row.querySelector('.js-remove').addEventListener('click', () => row.remove());
    motosBox.appendChild(row);
    return row;
  }

  function coletarMotos() {
    const itens = [];
    motosBox.querySelectorAll('.cr-moto-row').forEach(r => {
      const modelo_id = parseInt(r.querySelector('.js-modelo').value, 10);
      const quantidade = parseInt(r.querySelector('.js-qtd').value, 10);
      if (modelo_id && quantidade > 0) itens.push({ modelo_id, quantidade });
    });
    return itens;
  }

  document.getElementById('cr-add-moto').addEventListener('click', () => addMotoRow());
  addMotoRow();

  // ---------- cidades por UF (com código IBGE — chave canônica) ----------
  const ufSel = document.getElementById('cr-uf');
  const cidadeInput = document.getElementById('cr-cidade');
  let cidadesIbge = {};      // nome(UPPER) -> codigo_ibge
  let codigoIbgeSel = null;  // IBGE do destino corrente (enviado no payload)
  ufSel.addEventListener('change', () => { codigoIbgeSel = null; carregarCidades(); });
  cidadeInput.addEventListener('input', () => {
    codigoIbgeSel = cidadesIbge[cidadeInput.value.trim().toUpperCase()] || null;
  });
  function carregarCidades() {
    const uf = ufSel.value;
    const dl = document.getElementById('cr-cidades-list');
    dl.innerHTML = ''; cidadesIbge = {};
    if (!uf) return;
    fetch(`/localidades/ajax/cidades_por_uf_ibge/${uf}`)
      .then(r => r.json())
      .then(list => {
        dl.innerHTML = (list || []).map(c => `<option value="${esc(c.nome)}">`).join('');
        (list || []).forEach(c => { cidadesIbge[(c.nome || '').toUpperCase()] = c.codigo_ibge; });
        // re-resolve o IBGE da cidade já preenchida (preserva o do CEP se não casar)
        codigoIbgeSel = cidadesIbge[cidadeInput.value.trim().toUpperCase()] || codigoIbgeSel;
      })
      .catch(() => {});
  }

  // ---------- CEP ----------
  document.getElementById('cr-btn-cep').addEventListener('click', resolverCep);
  document.getElementById('cr-cep').addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); resolverCep(); } });
  function resolverCep() {
    const cep = document.getElementById('cr-cep').value.replace(/\D/g, '');
    const msg = document.getElementById('cr-cep-msg');
    if (cep.length !== 8) { msg.className = 'text-danger'; msg.textContent = 'CEP deve ter 8 digitos.'; return; }
    msg.className = 'text-muted'; msg.textContent = 'Buscando...';
    fetch(`${CFG.cep}/${cep}`)
      .then(r => r.json())
      .then(d => {
        if (!d.ok) { msg.className = 'text-danger'; msg.textContent = 'CEP nao encontrado.'; return; }
        // adiciona a UF ao select se nao existir
        if (![...ufSel.options].some(o => o.value === d.uf)) ufSel.add(new Option(d.uf, d.uf));
        ufSel.value = d.uf;
        carregarCidades();
        cidadeInput.value = d.cidade;
        codigoIbgeSel = d.codigo_ibge || null;  // IBGE autoritativo do ViaCEP
        msg.className = 'text-success'; msg.textContent = `${d.cidade}/${d.uf}`;
      })
      .catch(() => { msg.className = 'text-danger'; msg.textContent = 'Erro ao consultar CEP.'; });
  }

  // ---------- upload (LLM) ----------
  const dz = document.getElementById('cr-dropzone');
  const fileInput = document.getElementById('cr-file');
  dz.addEventListener('click', () => fileInput.click());
  dz.addEventListener('dragover', e => { e.preventDefault(); dz.classList.add('dragover'); });
  dz.addEventListener('dragleave', () => dz.classList.remove('dragover'));
  dz.addEventListener('drop', e => { e.preventDefault(); dz.classList.remove('dragover'); if (e.dataTransfer.files[0]) enviarArquivo(e.dataTransfer.files[0]); });
  fileInput.addEventListener('change', () => { if (fileInput.files[0]) enviarArquivo(fileInput.files[0]); });

  function enviarArquivo(file) {
    const msg = document.getElementById('cr-upload-msg');
    msg.className = 'small text-muted'; msg.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Lendo arquivo com IA...';
    const fd = new FormData(); fd.append('arquivo', file);
    fetch(CFG.upload, { method: 'POST', headers: { 'X-CSRFToken': csrf }, body: fd })
      .then(r => r.json())
      .then(d => {
        if (!d.ok) { msg.className = 'small text-danger'; msg.textContent = d.erro || 'Falha ao ler arquivo.'; return; }
        aplicarExtracao(d);
      })
      .catch(() => { msg.className = 'small text-danger'; msg.textContent = 'Erro de rede no upload.'; });
  }

  function aplicarExtracao(d) {
    const msg = document.getElementById('cr-upload-msg');
    // motos
    const reconhecidas = (d.motos || []).filter(m => m.reconhecido);
    const naoRec = (d.motos || []).filter(m => !m.reconhecido);
    if (reconhecidas.length) {
      motosBox.innerHTML = '';
      reconhecidas.forEach(m => addMotoRow(m.modelo_id, m.quantidade));
    }
    // regiao
    if (d.regiao) {
      if (d.regiao.uf) {
        if (![...ufSel.options].some(o => o.value === d.regiao.uf)) ufSel.add(new Option(d.regiao.uf, d.regiao.uf));
        ufSel.value = d.regiao.uf; carregarCidades();
      }
      if (d.regiao.cidade) { cidadeInput.value = d.regiao.cidade; codigoIbgeSel = cidadesIbge[d.regiao.cidade.toUpperCase()] || null; }
      if (d.regiao.cep) document.getElementById('cr-cep').value = d.regiao.cep;
    }
    let txt;
    if (reconhecidas.length === 0 && naoRec.length === 0) {
      txt = '<span class="text-warning"><i class="fas fa-exclamation-triangle"></i> Nenhuma moto identificada no arquivo — adicione manualmente.</span>';
    } else if (reconhecidas.length === 0) {
      txt = `<span class="text-warning"><i class="fas fa-exclamation-triangle"></i> Nenhum modelo reconhecido. Não reconhecidos: ${naoRec.map(m => esc(m.texto_original)).join(', ')}.</span>`;
    } else {
      txt = `<span class="text-success"><i class="fas fa-check"></i> ${reconhecidas.length} modelo(s) reconhecido(s).</span>`;
      if (naoRec.length) txt += ` <span class="text-warning">Não reconhecidos: ${naoRec.map(m => esc(m.texto_original)).join(', ')}.</span>`;
    }
    msg.className = 'small'; msg.innerHTML = txt;
  }

  // ---------- calcular ----------
  document.getElementById('cr-calcular').addEventListener('click', calcular);

  function montarPayload() {
    const payload = {
      itens: coletarMotos(),
      uf_destino: ufSel.value,
      cidade_destino: cidadeInput.value.trim(),
      codigo_ibge: codigoIbgeSel || '',
      cep: document.getElementById('cr-cep').value.trim(),
      cnpj_cliente: document.getElementById('cr-cnpj').value.trim(),
      cliente_nome: document.getElementById('cr-cliente-nome').value.trim(),
    };
    if (CFG.modo === 'publico') {
      const nomeEl = document.getElementById('cr-solicitante-nome');
      payload.solicitante_nome = (nomeEl ? nomeEl.value.trim() : '');
    }
    return payload;
  }

  function calcular() {
    const payload = montarPayload();
    if (CFG.modo === 'publico' && !payload.solicitante_nome) {
      renderErro('Informe seu nome para cotar.');
      return;
    }
    if (!payload.itens.length) { renderErro('Adicione pelo menos uma moto + quantidade.'); return; }
    if (!payload.uf_destino && !payload.cep) { renderErro('Informe a UF de destino ou um CEP.'); return; }
    const box = document.getElementById('cr-resultado');
    box.innerHTML = '<div class="text-center text-muted py-5"><i class="fas fa-spinner fa-spin fa-2x"></i><p class="mt-2">Calculando...</p></div>';
    fetch(CFG.calcular, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
      body: JSON.stringify(payload),
    })
      .then(r => r.json())
      .then(d => { if (d.ok === false && d.erro) { renderErro(d.erro); return; } ultimaCotacao.inputs = payload; render(d); })
      .catch(() => renderErro('Erro de rede ao calcular.'));
  }

  function renderErro(msg) {
    document.getElementById('cr-resultado').innerHTML = `<div class="alert alert-warning"><i class="fas fa-exclamation-triangle"></i> ${esc(msg)}</div>`;
  }

  // ---------- render resultado ----------
  function render(d) {
    const box = document.getElementById('cr-resultado');
    let html = '';

    (d.avisos || []).forEach(a => {
      html += `<div class="alert alert-warning py-2 small mb-2"><i class="fas fa-exclamation-triangle"></i> ${esc(a)}</div>`;
    });

    if (!d.opcoes || !d.opcoes.length) {
      box.innerHTML = html || '<div class="alert alert-secondary">Sem opcoes de frete para este destino.</div>';
      return;
    }

    const reg = d.regiao || {};
    const destinoTxt = (reg.cidade_destino ? reg.cidade_destino + '/' : '') + (reg.uf_destino || '');
    html += `<div class="d-flex justify-content-between align-items-center mb-2">
      <h5 class="mb-0">Destino: ${esc(destinoTxt)} <small class="text-muted">(${d.opcoes.length} tabela(s))</small></h5>
      <button class="btn btn-success" id="cr-emitir"><i class="fas fa-file-pdf"></i> Emitir Cotacao (PDF)</button>
    </div>`;

    // todas as opcoes detalhadas juntas
    html += '<div class="row g-3">';
    d.opcoes.forEach(op => {
      html += '<div class="col-12"><div class="card cr-opcao-card">';
      html += `<div class="card-header d-flex justify-content-between align-items-center">
        <span><strong>${esc(op.tabela_nome)}</strong>
          ${op.grupo_cliente ? `<span class="badge bg-info ms-1">${esc(op.grupo_cliente)}</span>` : ''}
        </span>
        <span class="fs-5 text-primary fw-bold">${fmtBRL.format(op.valor_total || 0)}</span>
      </div>`;
      html += '<div class="card-body p-0"><table class="table table-sm mb-0"><thead><tr>'
        + '<th>Modelo</th><th>Categoria</th><th class="text-center">Qtd</th>'
        + '<th class="text-end">Valor/moto</th><th class="text-end">Total</th></tr></thead><tbody>';
      (op.modelos || []).forEach(m => {
        if (m.sem_preco) {
          html += `<tr class="text-muted"><td>${esc(m.modelo_nome)}</td><td>${esc(m.categoria_nome || '—')}</td>`
            + `<td class="text-center">${m.quantidade}</td><td colspan="2" class="text-end fst-italic">sem preco nesta tabela</td></tr>`;
        } else {
          html += `<tr><td>${esc(m.modelo_nome)}</td><td>${esc(m.categoria_nome || '—')}</td>`
            + `<td class="text-center">${m.quantidade}</td>`
            + `<td class="text-end">${fmtBRL.format(m.valor_unitario || 0)}</td>`
            + `<td class="text-end">${fmtBRL.format(m.valor_total || 0)}</td></tr>`;
        }
      });
      html += `<tr class="table-light cr-total-linha"><td colspan="4" class="text-end">Total da cotacao</td>`
        + `<td class="text-end text-primary">${fmtBRL.format(op.valor_total || 0)}</td></tr>`;
      html += '</tbody></table></div>';
      if (op.lead_time != null) html += `<div class="card-footer py-1 small text-muted"><i class="fas fa-clock"></i> Prazo estimado: ${op.lead_time} dia(s)</div>`;
      html += '</div></div>';
    });
    html += '</div>';

    // historico
    html += renderHistoricos(d.historicos || {});

    box.innerHTML = html;
    const btn = document.getElementById('cr-emitir');
    if (btn) btn.addEventListener('click', emitirPdf);
  }

  function renderHistoricos(historicos) {
    const nomes = Object.keys(historicos);
    if (!nomes.length) return '';
    let html = '<hr><h6 class="text-muted mt-3"><i class="fas fa-history"></i> Ultimas cotacoes de moto por tabela</h6>';
    nomes.forEach(nome => {
      const lista = historicos[nome] || [];
      html += `<div class="mb-2"><strong class="small">${esc(nome)}</strong>`;
      if (!lista.length) { html += ' <span class="text-muted small">— sem historico</span></div>'; return; }
      html += '<table class="table table-sm table-borderless small mb-0"><thead><tr class="text-muted">'
        + '<th>Data</th><th>Destinatario</th><th class="text-center">Motos</th>'
        + '<th class="text-end">Valor/moto</th><th class="text-end">Total</th></tr></thead><tbody>';
      lista.forEach(h => {
        const data = h.data ? new Date(h.data).toLocaleDateString('pt-BR') : '—';
        const dest = (h.destinatario && h.destinatario.nome) || '—';
        const destCid = h.destinatario && h.destinatario.cidade ? ` <span class="text-muted">(${esc(h.destinatario.cidade)})</span>` : '';
        html += `<tr><td>${esc(data)}</td><td>${esc(dest)}${destCid}</td>`
          + `<td class="text-center">${h.qtd_motos || 0}</td>`
          + `<td class="text-end">${h.valor_por_moto != null ? fmtBRL.format(h.valor_por_moto) : '—'}</td>`
          + `<td class="text-end">${h.valor_total != null ? fmtBRL.format(h.valor_total) : '—'}</td></tr>`;
      });
      html += '</tbody></table></div>';
    });
    return html;
  }

  // ---------- emitir PDF ----------
  function emitirPdf() {
    const payload = ultimaCotacao.inputs || montarPayload();
    const btn = document.getElementById('cr-emitir');
    const orig = btn.innerHTML;
    btn.disabled = true; btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Gerando...';
    fetch(CFG.pdf, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
      body: JSON.stringify(payload),
    })
      .then(async r => {
        if (!r.ok) {
          let m = 'Nao foi possivel gerar o PDF.';
          try { const d = await r.json(); if (d && d.erro) m = d.erro; } catch (e) { /* resposta não-JSON */ }
          throw new Error(m);
        }
        return r.blob();
      })
      .then(blob => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = 'cotacao_carvia.pdf';
        document.body.appendChild(a); a.click(); a.remove();
        URL.revokeObjectURL(url);
      })
      .catch(err => alert(err.message || 'Nao foi possivel gerar o PDF.'))
      .finally(() => { btn.disabled = false; btn.innerHTML = orig; });
  }
})();
