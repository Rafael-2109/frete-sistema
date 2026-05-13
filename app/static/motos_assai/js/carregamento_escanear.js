/**
 * Carregamento — escanear chassi + finalizar/cancelar/alterar.
 *
 * Cfg injetada por escanear.html via window.MOTOS_ASSAI_CAR.
 * Endpoints AJAX SEM @login_required (decisao N-B1) — checa is_authenticated
 * via response 401.
 */
(function () {
  'use strict';

  var cfg = window.MOTOS_ASSAI_CAR;
  if (!cfg) return;

  var inputChassi = document.getElementById('input-chassi');
  var alerta = document.getElementById('alerta-carregamento');
  var itemsTbody = document.getElementById('items-tbody');
  var btnFinalizar = document.getElementById('btn-finalizar');
  var btnCancelar = document.getElementById('btn-cancelar');
  var btnAlterar = document.getElementById('btn-alterar');

  // CSRF token (injetado pelo base.html via meta[name="csrf-token"])
  function getCsrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.content : '';
  }

  // K9: escape HTML para prevenir XSS interno
  function escapeHtml(s) {
    if (s === null || s === undefined) return '';
    return String(s).replace(/[&<>"'`/]/g, function (c) {
      return {
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;',
        "'": '&#39;', '`': '&#96;', '/': '&#x2F;',
      }[c];
    });
  }

  function showAlerta(level, html, persistir) {
    if (!alerta) return;
    alerta.className = 'alert alert-' + level + ' small';
    alerta.innerHTML = html;
    alerta.classList.remove('d-none');
    if (!persistir) {
      setTimeout(function () { alerta.classList.add('d-none'); }, 4000);
    }
  }

  // ============ Camera (compativel com separacao_chassi.js) ============
  var html5Qr = null;
  var btnCamera = document.getElementById('btn-camera');
  if (btnCamera) {
    btnCamera.addEventListener('click', function () {
      var div = document.getElementById('qr-reader');
      if (!div) return;
      if (html5Qr) {
        html5Qr.stop().then(function () { html5Qr = null; div.classList.add('d-none'); });
        return;
      }
      if (!window.isSecureContext) {
        showAlerta('warning', 'Câmera requer HTTPS.');
        return;
      }
      div.classList.remove('d-none');
      html5Qr = new Html5Qrcode('qr-reader');
      html5Qr.start(
        { facingMode: 'environment' },
        { fps: 10, qrbox: 240 },
        function (txt) {
          inputChassi.value = txt.trim().toUpperCase();
          html5Qr.stop().then(function () { html5Qr = null; div.classList.add('d-none'); });
          escanear();
        }
      );
    });
  }

  // ============ Escanear chassi (Enter / autocompletar) ============
  if (inputChassi) {
    inputChassi.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') { e.preventDefault(); escanear(); }
    });
    inputChassi.focus();
  }

  async function escanear() {
    var chassi = (inputChassi.value || '').trim().toUpperCase();
    if (!chassi) return;

    try {
      var r = await fetch(cfg.endpoints.escanear, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken(),
          'X-Requested-With': 'XMLHttpRequest',
        },
        body: JSON.stringify({ chassi: chassi }),
      });
      if (r.status === 401) {
        showAlerta('warning', 'Sessão expirada. Recarregue a página.', true);
        return;
      }
      var data = await r.json();
      // Plano 4 Task 5: cenario=cross_loja => abre modal de substituicao
      if (r.status === 409 && data.cenario === 'cross_loja') {
        await abrirModalCrossLoja(data);
        return;
      }
      if (!data.ok) {
        showAlerta('danger', escapeHtml(data.erro || 'Erro ao escanear.'));
        return;
      }
      // Sucesso: adicionar item na tabela sem reload
      adicionarItemNaTabela(data.item);
      showAlerta('success',
        'Chassi <code>' + escapeHtml(data.item.chassi) + '</code> escaneado ('
        + escapeHtml(data.item.modelo_codigo || '?') + ').');
      inputChassi.value = '';
      inputChassi.focus();
      // Habilitar finalizar (precisa pelo menos 1 item)
      if (btnFinalizar) {
        btnFinalizar.disabled = false;
        btnFinalizar.removeAttribute('title');
      }
    } catch (err) {
      showAlerta('danger', 'Erro de rede: ' + escapeHtml(err.message));
    }
  }

  function adicionarItemNaTabela(item) {
    if (!itemsTbody) return;
    // Remove linha "vazio" se existir
    var rowVazio = document.getElementById('row-vazio');
    if (rowVazio) rowVazio.remove();

    var tr = document.createElement('tr');
    tr.dataset.itemId = item.id;
    tr.innerHTML =
      '<td><code>' + escapeHtml(item.chassi) + '</code></td>'
      + '<td><strong>' + escapeHtml(item.modelo_codigo || '—') + '</strong>'
        + (item.modelo_nome ? '<br><small class="text-muted">' + escapeHtml(item.modelo_nome) + '</small>' : '')
      + '</td>'
      + '<td><small class="text-muted">' + escapeHtml(item.escaneado_em || '—') + '</small></td>'
      + '<td class="text-end">'
      + '  <button type="button" class="btn btn-sm btn-outline-warning"'
      + '          data-action="cancelar-item" data-item-id="' + escapeHtml(item.id) + '"'
      + '          data-chassi="' + escapeHtml(item.chassi) + '">'
      + '    <i class="fas fa-times"></i> Remover'
      + '  </button>'
      + '</td>';
    // Inserir no topo (mais recente primeiro)
    itemsTbody.insertBefore(tr, itemsTbody.firstChild);
  }

  // ============ Cancelar item (delegacao) ============
  document.addEventListener('click', async function (e) {
    var btn = e.target.closest('[data-action="cancelar-item"]');
    if (!btn) return;
    var itemId = btn.dataset.itemId;
    var chassi = btn.dataset.chassi || itemId;
    if (!confirm('Remover chassi ' + chassi + ' deste carregamento?')) return;

    try {
      var url = cfg.endpoints.cancelarItemBase + itemId + '/cancelar';
      var r = await fetch(url, {
        method: 'POST',
        headers: {
          'X-CSRFToken': getCsrfToken(),
          'X-Requested-With': 'XMLHttpRequest',
        },
      });
      if (r.status === 401) {
        showAlerta('warning', 'Sessão expirada. Recarregue a página.', true);
        return;
      }
      var data = await r.json();
      if (data.ok) {
        var tr = btn.closest('tr');
        if (tr) tr.remove();
        showAlerta('success', 'Chassi removido.');
        // Se ficou vazio, mostrar linha "vazio" + desabilitar finalizar
        if (itemsTbody && itemsTbody.children.length === 0) {
          itemsTbody.innerHTML = '<tr id="row-vazio"><td colspan="4" class="text-center text-muted py-3">'
                                + 'Nenhum chassi escaneado ainda.</td></tr>';
          if (btnFinalizar) {
            btnFinalizar.disabled = true;
            btnFinalizar.title = 'Escaneie pelo menos 1 chassi';
          }
        }
      } else {
        showAlerta('danger', escapeHtml(data.erro || 'Erro ao remover item.'));
      }
    } catch (err) {
      showAlerta('danger', 'Erro de rede: ' + escapeHtml(err.message));
    }
  });

  // ============ Finalizar carregamento ============
  if (btnFinalizar) {
    btnFinalizar.addEventListener('click', function () {
      bootstrap.Modal.getOrCreateInstance(document.getElementById('modal-finalizar-car')).show();
    });
  }

  var btnConfirmarFinalizar = document.getElementById('car-btn-confirmar-finalizar');
  if (btnConfirmarFinalizar) {
    btnConfirmarFinalizar.addEventListener('click', async function () {
      bootstrap.Modal.getInstance(document.getElementById('modal-finalizar-car'))?.hide();
      try {
        var r = await fetch(cfg.endpoints.finalizar, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken(),
            'X-Requested-With': 'XMLHttpRequest',
          },
        });
        if (r.status === 401) {
          showAlerta('warning', 'Sessão expirada. Recarregue a página.', true);
          return;
        }
        var data = await r.json();
        if (r.status === 409 && data.cenario === 'excedente') {
          // S14=a — abre modal_excedente
          mostrarModalExcedente(data);
          return;
        }
        if (data.ok) {
          showAlerta('success', 'Carregamento finalizado. Sep #' + escapeHtml(data.sep_id) + '.');
          if (data.redirect) {
            setTimeout(function () { window.location.href = data.redirect; }, 700);
          } else {
            setTimeout(function () { location.reload(); }, 700);
          }
          return;
        }
        showAlerta('danger', escapeHtml(data.erro || 'Erro ao finalizar.'));
      } catch (err) {
        showAlerta('danger', 'Erro de rede: ' + escapeHtml(err.message));
      }
    });
  }

  function mostrarModalExcedente(data) {
    var msgEl = document.getElementById('excedente-mensagem');
    var qtdEl = document.getElementById('excedente-qtd');
    var sepsContainer = document.getElementById('excedente-seps-bloqueadas-container');
    var sepsList = document.getElementById('excedente-seps-bloqueadas');
    if (msgEl) msgEl.textContent = data.erro || '';
    if (qtdEl) qtdEl.textContent = (data.qtd_excedente !== undefined && data.qtd_excedente !== null)
      ? String(data.qtd_excedente) : '—';
    if (sepsList && sepsContainer) {
      sepsList.innerHTML = '';
      var seps = data.seps_bloqueadas || [];
      if (seps.length > 0) {
        seps.forEach(function (sid) {
          var li = document.createElement('li');
          li.innerHTML = 'Sep #<strong>' + escapeHtml(sid) + '</strong>';
          sepsList.appendChild(li);
        });
        sepsContainer.classList.remove('d-none');
      } else {
        sepsContainer.classList.add('d-none');
      }
    }
    bootstrap.Modal.getOrCreateInstance(document.getElementById('modal-excedente-car')).show();
  }

  // ============ Cancelar carregamento ============
  if (btnCancelar) {
    btnCancelar.addEventListener('click', function () {
      var input = document.getElementById('car-input-motivo');
      var erro = document.getElementById('car-erro-cancelar');
      if (input) input.value = '';
      if (erro) erro.classList.add('d-none');
      bootstrap.Modal.getOrCreateInstance(document.getElementById('modal-cancelar-car')).show();
      setTimeout(function () { input?.focus(); }, 300);
    });
  }

  var btnConfirmarCancelar = document.getElementById('car-btn-confirmar-cancelar');
  if (btnConfirmarCancelar) {
    btnConfirmarCancelar.addEventListener('click', async function () {
      var input = document.getElementById('car-input-motivo');
      var erro = document.getElementById('car-erro-cancelar');
      var motivo = (input?.value || '').trim();
      if (motivo.length < 3) {
        if (erro) {
          erro.textContent = 'Motivo precisa ter pelo menos 3 caracteres.';
          erro.classList.remove('d-none');
        }
        return;
      }
      bootstrap.Modal.getInstance(document.getElementById('modal-cancelar-car'))?.hide();
      try {
        var r = await fetch(cfg.endpoints.cancelar, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken(),
            'X-Requested-With': 'XMLHttpRequest',
          },
          body: JSON.stringify({ motivo: motivo }),
        });
        if (r.status === 401) {
          showAlerta('warning', 'Sessão expirada. Recarregue a página.', true);
          return;
        }
        var data = await r.json();
        if (data.ok) {
          showAlerta('success', 'Carregamento cancelado.');
          if (data.redirect) {
            setTimeout(function () { window.location.href = data.redirect; }, 700);
          } else {
            setTimeout(function () { location.reload(); }, 700);
          }
          return;
        }
        showAlerta('danger', escapeHtml(data.erro || 'Erro ao cancelar.'));
      } catch (err) {
        showAlerta('danger', 'Erro de rede: ' + escapeHtml(err.message));
      }
    });
  }

  // ============ Alterar carregamento (S6=a) ============
  if (btnAlterar) {
    btnAlterar.addEventListener('click', function () {
      bootstrap.Modal.getOrCreateInstance(document.getElementById('modal-alterar-car')).show();
    });
  }

  var btnConfirmarAlterar = document.getElementById('car-btn-confirmar-alterar');
  if (btnConfirmarAlterar) {
    btnConfirmarAlterar.addEventListener('click', async function () {
      bootstrap.Modal.getInstance(document.getElementById('modal-alterar-car'))?.hide();
      try {
        var r = await fetch(cfg.endpoints.alterar, {
          method: 'POST',
          headers: {
            'X-CSRFToken': getCsrfToken(),
            'X-Requested-With': 'XMLHttpRequest',
          },
        });
        if (r.status === 401) {
          showAlerta('warning', 'Sessão expirada. Recarregue a página.', true);
          return;
        }
        var data = await r.json();
        if (data.ok) {
          showAlerta('success', 'Carregamento reaberto.');
          if (data.redirect) {
            setTimeout(function () { window.location.href = data.redirect; }, 700);
          } else {
            setTimeout(function () { location.reload(); }, 700);
          }
          return;
        }
        showAlerta('danger', escapeHtml(data.erro || 'Erro ao alterar.'));
      } catch (err) {
        showAlerta('danger', 'Erro de rede: ' + escapeHtml(err.message));
      }
    });
  }

  // ==========================================================
  // Plano 4 Task 5: modal "Substituir chassi" cross-loja
  // ==========================================================
  var _pendingCrossLoja = null;

  async function abrirModalCrossLoja(data) {
    _pendingCrossLoja = {
      chassi: data.chassi,
      sep_origem_id: data.sep_origem_id,
      loja_origem_id: data.loja_origem_id,
      carregamento_id: data.carregamento_id,
      loja_destino_id: data.loja_destino_id,
    };
    document.getElementById('cross-chassi').textContent = _pendingCrossLoja.chassi;
    document.getElementById('cross-sep-origem-id').textContent = _pendingCrossLoja.sep_origem_id;
    document.getElementById('cross-loja-origem').textContent = _pendingCrossLoja.loja_origem_id;
    document.getElementById('cross-car-id').textContent = _pendingCrossLoja.carregamento_id;
    document.getElementById('cross-loja-destino').textContent = _pendingCrossLoja.loja_destino_id;

    // Carregar seps ativas do (pedido, loja) deste carregamento
    var sel = document.getElementById('cross-sep-destino-select');
    sel.innerHTML = '<option value="">— Carregando... —</option>';
    sel.disabled = true;
    try {
      var url = cfg.endpoints.sepsAtivas + '?pedido_id=' + cfg.pedidoId
                + '&loja_id=' + cfg.lojaId;
      var r = await fetch(url, {
        headers: {'X-CSRFToken': getCsrfToken()},
      });
      var resp = await r.json();
      if (!resp.ok || !resp.seps || resp.seps.length === 0) {
        sel.innerHTML = '<option value="">— Nenhuma sep ativa nesta loja —</option>';
        showAlerta('danger',
          'Nao ha sep ativa nesta loja para o pedido. Crie uma sep antes.');
      } else {
        sel.innerHTML = '<option value="">— Selecione —</option>';
        resp.seps.forEach(function (s) {
          var opt = document.createElement('option');
          opt.value = s.id;
          opt.textContent = 'Sep #' + s.id + ' — ' + s.status
                          + (s.iniciada_em ? ' (' + s.iniciada_em + ')' : '');
          sel.appendChild(opt);
        });
        sel.disabled = false;
      }
    } catch (err) {
      sel.innerHTML = '<option value="">— Erro ao carregar seps —</option>';
      showAlerta('danger', 'Erro ao carregar seps: ' + escapeHtml(err.message));
    }

    bootstrap.Modal.getOrCreateInstance(document.getElementById('modal-substituir-chassi')).show();
  }

  document.getElementById('btn-confirmar-substituir-chassi-car')?.addEventListener('click', async function () {
    if (!_pendingCrossLoja) return;
    var sel = document.getElementById('cross-sep-destino-select');
    var sepDestinoId = sel.value;
    if (!sepDestinoId) {
      showAlerta('warning', 'Selecione a sep destino.');
      return;
    }
    var btn = document.getElementById('btn-confirmar-substituir-chassi-car');
    btn.disabled = true;

    try {
      // 1. Substituir chassi entre seps
      var rs = await fetch(cfg.endpoints.substituirChassi, {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken()},
        body: JSON.stringify({
          chassi: _pendingCrossLoja.chassi,
          sep_origem_id: _pendingCrossLoja.sep_origem_id,
          sep_destino_id: parseInt(sepDestinoId, 10),
        }),
      });
      var dataS = await rs.json();
      if (!dataS.ok) {
        showAlerta('danger', escapeHtml(dataS.erro || 'Erro ao substituir chassi'));
        btn.disabled = false;
        return;
      }

      bootstrap.Modal.getInstance(document.getElementById('modal-substituir-chassi'))?.hide();
      var msgExtra = dataS.divergencia_id
        ? ' (divergencia #' + dataS.divergencia_id + ' criada — sep origem FATURADA)'
        : '';
      showAlerta('success',
        'Chassi <code>' + escapeHtml(dataS.chassi) + '</code> substituido'
        + escapeHtml(msgExtra) + '. Re-tentando escanear no carregamento...');

      // 2. Re-tentar escanear no carregamento (chassi agora em SEPARADA na loja certa)
      inputChassi.value = _pendingCrossLoja.chassi;
      _pendingCrossLoja = null;
      setTimeout(escanear, 500);
    } catch (err) {
      showAlerta('danger', 'Erro de rede: ' + escapeHtml(err.message));
      btn.disabled = false;
    }
  });
})();
