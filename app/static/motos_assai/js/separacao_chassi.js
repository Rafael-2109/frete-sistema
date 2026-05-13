(function() {
  const cfg = window.MOTOS_ASSAI_SEP;
  if (!cfg) return;

  const inputChassi = document.getElementById('input-chassi');
  const alerta = document.getElementById('alerta-sep');

  // CSRF token (injetado pelo base.html via meta[name="csrf-token"])
  function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.content : '';
  }

  // K9: escape HTML para prevenir XSS interno (admin pode cadastrar modelo
  // com `<` no nome). Usar em TODAS interpolacoes que viram innerHTML.
  function escapeHtml(s) {
    if (s === null || s === undefined) return '';
    return String(s).replace(/[&<>"'`/]/g, function(c) {
      return {
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;',
        "'": '&#39;', '`': '&#96;', '/': '&#x2F;',
      }[c];
    });
  }

  function showAlerta(level, html) {
    alerta.className = `alert alert-${level} small`;
    alerta.innerHTML = html;
    alerta.classList.remove('d-none');
    setTimeout(() => alerta.classList.add('d-none'), 4000);
  }

  // Câmera (igual aos outros componentes)
  let html5Qr = null;
  document.getElementById('btn-camera')?.addEventListener('click', () => {
    const div = document.getElementById('qr-reader');
    if (html5Qr) {
      html5Qr.stop().then(() => { html5Qr = null; div.classList.add('d-none'); });
      return;
    }
    if (!window.isSecureContext) { showAlerta('warning', 'Câmera requer HTTPS'); return; }
    div.classList.remove('d-none');
    html5Qr = new Html5Qrcode('qr-reader');
    html5Qr.start({facingMode: 'environment'}, {fps: 10, qrbox: 240}, (txt) => {
      inputChassi.value = txt.trim().toUpperCase();
      html5Qr.stop().then(() => { html5Qr = null; div.classList.add('d-none'); });
      registrar();
    });
  });

  inputChassi?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') { e.preventDefault(); registrar(); }
  });

  async function registrar() {
    const chassi = inputChassi.value.trim().toUpperCase();
    if (!chassi) return;
    const r = await fetch(cfg.endpoints.registrar, {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken()},
      body: JSON.stringify({
        pedido_id: cfg.pedidoId, loja_id: cfg.lojaId, chassi,
        separacao_id: cfg.separacaoId,  // Plano 5 — alvo explicito quando ha N seps ativas
      }),
    });
    const data = await r.json();

    // Plano 4 Task 4: cenario=cross_loja => abre modal de substituicao
    // Pacote B (2026-05-13): popula dropdown de seps destino (paridade com carregamento).
    if (r.status === 409 && data.cenario === 'cross_loja') {
      _pendingCrossLoja = {
        chassi: data.chassi,
        sep_origem_id: data.sep_origem_id,
        loja_origem_id: data.loja_origem_id,
        sep_destino_id_default: data.sep_destino_id || cfg.separacaoId,
        loja_destino_id: data.loja_destino_id,
      };
      document.getElementById('cross-chassi').textContent = _pendingCrossLoja.chassi;
      document.getElementById('cross-sep-origem-id').textContent = _pendingCrossLoja.sep_origem_id;
      document.getElementById('cross-loja-origem').textContent = _pendingCrossLoja.loja_origem_id;
      document.getElementById('cross-loja-destino').textContent = _pendingCrossLoja.loja_destino_id;

      // Carregar seps ativas do (pedido, loja) atuais para popular dropdown
      const sel = document.getElementById('cross-sep-destino-select');
      sel.innerHTML = '<option value="">— Carregando... —</option>';
      sel.disabled = true;
      try {
        const sepsUrl = (cfg.endpoints.sepsAtivas || '/motos-assai/api/seps-ativas')
                      + '?pedido_id=' + cfg.pedidoId + '&loja_id=' + cfg.lojaId;
        const sepsR = await fetch(sepsUrl, {headers: {'X-CSRFToken': getCsrfToken()}});
        const sepsResp = await sepsR.json();
        if (!sepsResp.ok || !sepsResp.seps || sepsResp.seps.length === 0) {
          sel.innerHTML = '<option value="">— Nenhuma sep ativa nesta loja —</option>';
          showAlerta('warning', 'Nao ha sep ativa nesta loja. Crie uma sep antes.');
        } else {
          sel.innerHTML = '<option value="">— Selecione —</option>';
          sepsResp.seps.forEach(function (s) {
            const opt = document.createElement('option');
            opt.value = s.id;
            opt.textContent = 'Sep #' + s.id + ' — ' + s.status
                            + (s.iniciada_em ? ' (' + s.iniciada_em + ')' : '');
            // Pre-selecionar a sep da tela atual (caso comum: 1 sep ativa)
            if (s.id === _pendingCrossLoja.sep_destino_id_default) opt.selected = true;
            sel.appendChild(opt);
          });
          sel.disabled = false;
        }
      } catch (err) {
        sel.innerHTML = '<option value="">— Erro ao carregar seps —</option>';
        showAlerta('danger', 'Erro ao carregar seps: ' + err.message);
      }

      bootstrap.Modal.getOrCreateInstance(document.getElementById('modal-substituir-chassi-sep')).show();
      return;
    }

    if (!data.ok) {
      showAlerta('danger', data.erro);
      return;
    }
    showAlerta('success', `Chassi ${data.chassi} registrado.`);
    inputChassi.value = '';
    inputChassi.focus();
    setTimeout(() => location.reload(), 800);  // recarrega para atualizar saldo + lista
  }

  // Plano 4 Task 4: estado e handler para modal "Substituir chassi" cross-loja
  let _pendingCrossLoja = null;
  document.getElementById('btn-confirmar-substituir-chassi-sep')?.addEventListener('click', async () => {
    if (!_pendingCrossLoja) return;
    // Pacote B: ler sep destino do dropdown (multipla escolha possivel)
    const sel = document.getElementById('cross-sep-destino-select');
    const sepDestinoId = sel ? sel.value : null;
    if (!sepDestinoId) {
      showAlerta('warning', 'Selecione a sep destino.');
      return;
    }
    const btn = document.getElementById('btn-confirmar-substituir-chassi-sep');
    btn.disabled = true;
    try {
      const r = await fetch(cfg.endpoints.substituirChassi, {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken()},
        body: JSON.stringify({
          chassi: _pendingCrossLoja.chassi,
          sep_origem_id: _pendingCrossLoja.sep_origem_id,
          sep_destino_id: parseInt(sepDestinoId, 10),
        }),
      });
      const data = await r.json();
      if (!data.ok) {
        // Pacote C (Bug 6): backend bloqueia se origem FATURADA/CARREGADA.
        // Mostrar link explicito para Divergencias.
        const ehBloqueio = r.status === 403 || (data.erro || '').toLowerCase().indexOf('faturad') >= 0
                         || (data.erro || '').toLowerCase().indexOf('carregad') >= 0;
        if (ehBloqueio) {
          showAlerta('danger',
            (data.erro || 'Sep origem em status que bloqueia substituicao direta.') +
            ' <a href="/motos-assai/divergencias" class="alert-link">Ir para Divergencias</a>');
        } else {
          showAlerta('danger', data.erro || 'Erro ao substituir chassi');
        }
        btn.disabled = false;
        return;
      }
      const msgExtra = data.divergencia_id
        ? ` (divergencia #${data.divergencia_id} criada)`
        : '';
      showAlerta('success', `Chassi ${data.chassi} movido${msgExtra}.`);
      bootstrap.Modal.getInstance(document.getElementById('modal-substituir-chassi-sep'))?.hide();
      setTimeout(() => location.reload(), 1000);
    } catch (err) {
      showAlerta('danger', 'Erro de rede: ' + err.message);
      btn.disabled = false;
    }
  });

  // ============ Desfazer chassi — Bootstrap modal ============
  let _pendingDesfazerItemId = null;

  document.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-action="desfazer"]');
    if (!btn) return;
    const row = btn.closest('tr');
    const chassiCode = row ? row.querySelector('code')?.textContent : btn.dataset.itemId;
    _pendingDesfazerItemId = btn.dataset.itemId;
    const chassiEl = document.getElementById('sep-desfazer-chassi');
    if (chassiEl) chassiEl.textContent = chassiCode;
    bootstrap.Modal.getOrCreateInstance(document.getElementById('modal-desfazer-sep')).show();
  });

  document.getElementById('sep-btn-confirmar-desfazer')?.addEventListener('click', async () => {
    bootstrap.Modal.getInstance(document.getElementById('modal-desfazer-sep'))?.hide();
    if (!_pendingDesfazerItemId) return;
    const url = cfg.endpoints.desfazerBase + _pendingDesfazerItemId;
    const r = await fetch(url, {method: 'POST', headers: {'X-CSRFToken': getCsrfToken()}});
    const data = await r.json();
    if (data.ok) location.reload();
    else showAlerta('danger', data.erro || 'Erro ao desfazer.');
    _pendingDesfazerItemId = null;
  });

  // ============ Finalizar separação — Bootstrap modal ============
  // Fluxo (Tasks #11/#12/#13 — 2026-05-12):
  //   1. Click "Finalizar" -> chama analisarFinalizacao para ver cenario
  //   2a. cenario=sem_saldo -> abre modal padrao (confirmacao simples)
  //   2b. cenario=caso_a    -> abre modal-finalizar-caso-a (Voltar saldo / Manter)
  //   2c. cenario=caso_b    -> abre modal-finalizar-caso-b (alocacao manual)
  document.getElementById('btn-finalizar')?.addEventListener('click', async () => {
    try {
      const r = await fetch(cfg.endpoints.analisarFinalizacao, {
        method: 'GET',
        headers: {'X-CSRFToken': getCsrfToken()},
      });
      const data = await r.json();
      if (!data.ok) {
        showAlerta('danger', data.erro || 'Erro ao analisar finalizacao.');
        return;
      }
      // H3: guardar saldo_version do GET para enviar no POST e detectar TOCTOU
      window.__casoB_saldoVersion = data.saldo_version || null;
      if (data.cenario === 'sem_saldo') {
        bootstrap.Modal.getOrCreateInstance(document.getElementById('modal-finalizar-sep')).show();
        return;
      }
      if (data.cenario === 'caso_a') {
        montarModalCasoA(data);
        bootstrap.Modal.getOrCreateInstance(document.getElementById('modal-finalizar-caso-a')).show();
        return;
      }
      if (data.cenario === 'caso_b') {
        montarModalCasoB(data);
        bootstrap.Modal.getOrCreateInstance(document.getElementById('modal-finalizar-caso-b')).show();
        return;
      }
      showAlerta('danger', 'Cenario desconhecido: ' + data.cenario);
    } catch (err) {
      showAlerta('danger', 'Erro de rede: ' + err.message);
    }
  });

  async function postFinalizar(body) {
    const r = await fetch(cfg.endpoints.finalizar, {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken()},
      body: JSON.stringify(body || {}),
    });
    const data = await r.json();
    if (r.ok && data.ok) {
      location.reload();
      return;
    }
    // H3: TOCTOU detectado — saldo mudou entre GET analisar e POST finalizar
    if (r.status === 409 && data.requer_decisao) {
      showAlerta('warning',
        'O saldo mudou enquanto voce decidia (outro operador escaneou). '
        + 'Re-abrindo modal com plano atualizado.');
      // Re-renderiza modal apropriado
      window.__casoB_saldoVersion = data.saldo_version || null;
      // Fechar modais abertos
      ['modal-finalizar-sep', 'modal-finalizar-caso-a', 'modal-finalizar-caso-b'].forEach(function(id) {
        const inst = bootstrap.Modal.getInstance(document.getElementById(id));
        if (inst) inst.hide();
      });
      setTimeout(function() {
        if (data.cenario === 'caso_a') {
          montarModalCasoA(data);
          bootstrap.Modal.getOrCreateInstance(document.getElementById('modal-finalizar-caso-a')).show();
        } else if (data.cenario === 'caso_b') {
          montarModalCasoB(data);
          bootstrap.Modal.getOrCreateInstance(document.getElementById('modal-finalizar-caso-b')).show();
        }
      }, 400);
      return;
    }
    showAlerta('danger', data.erro || 'Erro ao finalizar.');
  }

  // Modal padrao (sem saldo) — comportamento original
  document.getElementById('sep-btn-confirmar-finalizar')?.addEventListener('click', () => {
    bootstrap.Modal.getInstance(document.getElementById('modal-finalizar-sep'))?.hide();
    postFinalizar({modo: 'auto'});
  });

  // ============ Caso A: 2 opcoes (voltar saldo / manter planejado) ============
  function montarModalCasoA(data) {
    const listaEl = document.getElementById('caso-a-lista-saldo');
    if (!listaEl) return;
    listaEl.innerHTML = '';
    (data.modelos_info || []).forEach(function(m) {
      const li = document.createElement('li');
      li.innerHTML = '<strong>' + escapeHtml(m.codigo) + '</strong> — '
                   + escapeHtml(m.nome) + ' · saldo: <strong>'
                   + escapeHtml(m.qtd_nao_separada) + '</strong>';
      listaEl.appendChild(li);
    });
  }

  document.getElementById('caso-a-btn-voltar-saldo')?.addEventListener('click', () => {
    bootstrap.Modal.getInstance(document.getElementById('modal-finalizar-caso-a'))?.hide();
    postFinalizar({modo: 'voltar_saldo'});
  });

  document.getElementById('caso-a-btn-manter-planejado')?.addEventListener('click', () => {
    bootstrap.Modal.getInstance(document.getElementById('modal-finalizar-caso-a'))?.hide();
    postFinalizar({modo: 'manter_planejado'});
  });

  // ============ Caso B: alocacao manual entre N seps ============
  function montarModalCasoB(data) {
    const tableBody = document.getElementById('caso-b-tbody');
    if (!tableBody) return;
    tableBody.innerHTML = '';
    const thead = document.getElementById('caso-b-thead');
    if (thead) {
      // Header: modelo | qtd saldo | sep#1 | sep#2 | ... | voltar ao pedido
      let html = '<tr><th>Modelo</th><th class="text-end">Saldo</th>';
      (data.outras_seps || []).forEach(function(s) {
        html += '<th class="text-end">Sep #' + escapeHtml(s.id)
              + '<br><small class="text-muted">' + escapeHtml(s.iniciada_em || '') + '</small></th>';
      });
      html += '<th class="text-end">Voltar ao pedido</th></tr>';
      thead.innerHTML = html;
    }

    (data.modelos_info || []).forEach(function(m) {
      const tr = document.createElement('tr');
      tr.dataset.modeloId = m.modelo_id;
      tr.dataset.qtdSaldo = m.qtd_nao_separada;
      const codSafe = escapeHtml(m.codigo);
      const nomeSafe = escapeHtml(m.nome);
      const qtdSafe = escapeHtml(m.qtd_nao_separada);
      const modIdSafe = escapeHtml(m.modelo_id);
      let html = '<td><strong>' + codSafe + '</strong> — ' + nomeSafe + '</td>'
               + '<td class="text-end"><span class="badge bg-warning text-dark">' + qtdSafe + '</span></td>';
      (data.outras_seps || []).forEach(function(s) {
        const sepIdSafe = escapeHtml(s.id);
        html += '<td><input type="number" min="0" max="' + qtdSafe + '" value="0"'
             + ' class="form-control form-control-sm text-end caso-b-input"'
             + ' data-modelo-id="' + modIdSafe + '" data-sep-destino="' + sepIdSafe + '"></td>';
      });
      // H5: coluna "voltar ao pedido" pre-fill 0 (operador escolhe explicitamente)
      html += '<td><input type="number" min="0" max="' + qtdSafe + '" value="0"'
           + ' class="form-control form-control-sm text-end caso-b-input"'
           + ' data-modelo-id="' + modIdSafe + '" data-sep-destino="null"></td>';
      tr.innerHTML = html;
      tableBody.appendChild(tr);
    });

    // Validacao em tempo real
    document.querySelectorAll('.caso-b-input').forEach(function(inp) {
      inp.addEventListener('input', validarCasoB);
    });
    validarCasoB();
  }

  function validarCasoB() {
    const erroEl = document.getElementById('caso-b-erro');
    const btn = document.getElementById('caso-b-btn-confirmar');
    let ok = true;
    let msgs = [];
    document.querySelectorAll('#caso-b-tbody tr').forEach(function(tr) {
      const qtdSaldo = parseInt(tr.dataset.qtdSaldo, 10) || 0;
      let soma = 0;
      tr.querySelectorAll('.caso-b-input').forEach(function(inp) {
        soma += parseInt(inp.value, 10) || 0;
      });
      const td = tr.querySelector('td:nth-child(2) .badge');
      if (soma === qtdSaldo) {
        if (td) { td.className = 'badge bg-success'; td.textContent = qtdSaldo + ' ✓'; }
      } else {
        ok = false;
        if (td) { td.className = 'badge bg-danger'; td.textContent = soma + '/' + qtdSaldo; }
        const cod = tr.querySelector('td:nth-child(1) strong').textContent;
        msgs.push(cod + ': alocado ' + soma + ', precisa ' + qtdSaldo);
      }
    });
    if (erroEl) {
      if (ok) {
        erroEl.className = 'alert alert-success mt-2';
        erroEl.textContent = 'Alocacao completa. Pode confirmar.';
      } else {
        erroEl.className = 'alert alert-warning mt-2';
        erroEl.textContent = msgs.join(' · ');
      }
    }
    if (btn) btn.disabled = !ok;
  }

  document.getElementById('caso-b-btn-confirmar')?.addEventListener('click', () => {
    const alocacoes = [];
    document.querySelectorAll('.caso-b-input').forEach(function(inp) {
      const qtd = parseInt(inp.value, 10) || 0;
      if (qtd <= 0) return;
      const modeloId = parseInt(inp.dataset.modeloId, 10);
      const sepDest = inp.dataset.sepDestino;
      alocacoes.push({
        modelo_id: modeloId,
        qtd: qtd,
        sep_destino_id: (sepDest === 'null') ? null : parseInt(sepDest, 10),
      });
    });
    bootstrap.Modal.getInstance(document.getElementById('modal-finalizar-caso-b'))?.hide();
    postFinalizar({
      modo: 'realocar',
      alocacoes: alocacoes,
      saldo_version: window.__casoB_saldoVersion || null,  // H3 TOCTOU
    });
  });

  // ============ Cancelar separação — Bootstrap modal com input ============
  document.getElementById('btn-cancelar')?.addEventListener('click', () => {
    const inputMotivo = document.getElementById('sep-input-motivo-cancelar');
    const erroEl = document.getElementById('sep-erro-cancelar');
    if (inputMotivo) inputMotivo.value = '';
    if (erroEl) erroEl.classList.add('d-none');
    bootstrap.Modal.getOrCreateInstance(document.getElementById('modal-cancelar-sep')).show();
    setTimeout(() => inputMotivo?.focus(), 300);
  });

  document.getElementById('sep-btn-confirmar-cancelar')?.addEventListener('click', async () => {
    const inputMotivo = document.getElementById('sep-input-motivo-cancelar');
    const erroEl = document.getElementById('sep-erro-cancelar');
    const motivo = inputMotivo?.value.trim() || '';
    if (motivo.length < 3) {
      if (erroEl) {
        erroEl.textContent = 'Motivo precisa ter pelo menos 3 caracteres.';
        erroEl.classList.remove('d-none');
      }
      return;
    }
    bootstrap.Modal.getInstance(document.getElementById('modal-cancelar-sep'))?.hide();
    const r = await fetch(cfg.endpoints.cancelar, {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken()},
      body: JSON.stringify({motivo}),
    });
    const data = await r.json();
    if (data.ok) location.reload();
    else showAlerta('danger', data.erro || 'Erro ao cancelar.');
  });

  inputChassi?.focus();
})();
