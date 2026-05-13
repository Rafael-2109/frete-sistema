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
})();
