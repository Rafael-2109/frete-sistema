/* Botão "Enviar p/ Pendência": MONTADA/DISPONIVEL/SEPARADA -> PENDENTE.
 *
 * Compartilhado entre Montagem, Disponibilizar e Separação. Espera no DOM:
 * - botões [data-action="enviar-pendencia"][data-chassi]
 * - modal #modal-enviar-pendencia (partial _modal_enviar_pendencia.html) com
 *   #ep-chassi, #ep-descricao, #ep-erro, #ep-btn-confirmar
 * - window.MOTOS_ASSAI_PENDENCIA_ENDPOINT = url do POST /pendencias/criar
 *
 * CSRF lido de meta[name="csrf-token"] (injetado pelo base.html).
 */
(function () {
  'use strict';

  var endpoint = window.MOTOS_ASSAI_PENDENCIA_ENDPOINT;
  if (!endpoint) return;

  var modalEl = document.getElementById('modal-enviar-pendencia');
  if (!modalEl) return;

  var chassiSpan = document.getElementById('ep-chassi');
  var descricaoEl = document.getElementById('ep-descricao');
  var erroEl = document.getElementById('ep-erro');
  var btnConfirmar = document.getElementById('ep-btn-confirmar');
  var pendingChassi = null;

  function getCsrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
  }

  function mostrarErro(msg) {
    if (erroEl) {
      erroEl.textContent = msg;
      erroEl.classList.remove('d-none');
    }
  }

  document.addEventListener('click', function (e) {
    var btn = e.target.closest('[data-action="enviar-pendencia"]');
    if (!btn) return;
    pendingChassi = btn.getAttribute('data-chassi');
    if (chassiSpan) chassiSpan.textContent = pendingChassi || '';
    if (descricaoEl) descricaoEl.value = '';
    if (erroEl) erroEl.classList.add('d-none');
    bootstrap.Modal.getOrCreateInstance(modalEl).show();
    setTimeout(function () { if (descricaoEl) descricaoEl.focus(); }, 300);
  });

  if (btnConfirmar) {
    btnConfirmar.addEventListener('click', async function () {
      var descricao = ((descricaoEl && descricaoEl.value) || '').trim();
      if (descricao.length < 3) {
        mostrarErro('Descrição obrigatória (≥3 caracteres).');
        return;
      }
      btnConfirmar.disabled = true;
      try {
        var r = await fetch(endpoint, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken(),
          },
          body: JSON.stringify({
            chassi: pendingChassi,
            descricao_pendencia: descricao,
          }),
        });
        var data = await r.json();
        if (!data.ok) {
          mostrarErro(data.erro || 'Erro ao enviar para pendência.');
          btnConfirmar.disabled = false;
          return;
        }
        bootstrap.Modal.getInstance(modalEl)?.hide();
        location.reload();
      } catch (err) {
        mostrarErro('Erro de rede: ' + err.message);
        btnConfirmar.disabled = false;
      }
    });
  }
})();
