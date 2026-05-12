/* Resolver pendencia: abre modal, valida descricao, POST + reload.
 * Espera window.MOTOS_ASSAI_PENDENCIAS.endpointResolver
 */
(function () {
  'use strict';

  var cfg = window.MOTOS_ASSAI_PENDENCIAS || {};
  var currentChassi = null;

  function getCsrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : null;
  }

  function showError(msg) {
    var el = document.getElementById('resolver-erro');
    if (!el) return;
    el.textContent = msg;
    el.classList.remove('d-none');
  }

  function clearError() {
    var el = document.getElementById('resolver-erro');
    if (el) el.classList.add('d-none');
  }

  document.addEventListener('click', function (ev) {
    var btn = ev.target.closest('.btn-resolver-pendencia');
    if (btn) {
      currentChassi = btn.getAttribute('data-chassi');
      document.getElementById('resolver-chassi').textContent = currentChassi || '';
      // data-observacao e JSON-encoded (|tojson) para suportar newlines/quotes
      var obsRaw = btn.getAttribute('data-observacao') || '""';
      var obsTxt = '';
      try {
        obsTxt = JSON.parse(obsRaw) || '';
      } catch (e) {
        obsTxt = obsRaw;
      }
      document.getElementById('resolver-observacao-original').textContent = obsTxt;
      document.getElementById('resolver-descricao').value = '';
      clearError();
      var modalEl = document.getElementById('modal-resolver-pendencia');
      bootstrap.Modal.getOrCreateInstance(modalEl).show();
      setTimeout(function () {
        var ta = document.getElementById('resolver-descricao');
        if (ta) ta.focus();
      }, 200);
      return;
    }

    if (ev.target.closest('#btn-confirmar-resolver')) {
      var descEl = document.getElementById('resolver-descricao');
      var descricao = (descEl ? descEl.value : '').trim();
      if (descricao.length < 3) {
        showError('Descricao obrigatoria (>=3 caracteres)');
        return;
      }
      if (!currentChassi) {
        showError('Chassi nao identificado');
        return;
      }
      clearError();

      var headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      };
      var csrf = getCsrfToken();
      if (csrf) headers['X-CSRFToken'] = csrf;

      var btn = document.getElementById('btn-confirmar-resolver');
      btn.disabled = true;
      btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Resolvendo...';

      fetch(cfg.endpointResolver, {
        method: 'POST',
        credentials: 'same-origin',
        headers: headers,
        body: JSON.stringify({
          chassi: currentChassi,
          descricao_resolucao: descricao,
        }),
      })
        .then(function (r) {
          return r.json().then(function (data) { return { status: r.status, data: data }; });
        })
        .then(function (res) {
          if (res.status >= 200 && res.status < 300 && res.data && res.data.ok) {
            window.location.reload();
          } else {
            showError((res.data && res.data.erro) || ('Erro HTTP ' + res.status));
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-check"></i> Confirmar resolucao';
          }
        })
        .catch(function (err) {
          showError('Falha na requisicao: ' + err.message);
          btn.disabled = false;
          btn.innerHTML = '<i class="fas fa-check"></i> Confirmar resolucao';
        });
    }
  });
})();
