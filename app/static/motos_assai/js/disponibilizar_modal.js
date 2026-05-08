/**
 * disponibilizar_modal.js
 * Handler do modal "Reverter para MONTADA" na tela de disponibilizar.
 * Depende de: Bootstrap (bootstrap.Modal), fetch API, CSRF meta tag.
 */
(function () {
  function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
  }

  // Handler do botão Reverter (delegação)
  document.addEventListener('click', async (e) => {
    const btn = e.target.closest('[data-action="reverter"]');
    if (!btn) return;
    const chassi = btn.dataset.chassi;
    document.getElementById('modal-chassi').textContent = chassi;
    document.getElementById('modal-motivo').value = '';
    document.getElementById('modal-erro').classList.add('d-none');
    const modalEl = document.getElementById('modal-reverter');
    const modal = new bootstrap.Modal(modalEl);
    modal.show();

    document.getElementById('btn-confirmar-reverter').onclick = async () => {
      const motivo = document.getElementById('modal-motivo').value.trim();
      if (motivo.length < 3) {
        document.getElementById('modal-erro').textContent = 'Motivo precisa ter ≥3 chars';
        document.getElementById('modal-erro').classList.remove('d-none');
        return;
      }
      const endpointReverter = document.getElementById('modal-reverter').dataset.endpointReverter;
      const r = await fetch(endpointReverter, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken(),
        },
        body: JSON.stringify({ chassi, motivo }),
      });
      const data = await r.json();
      if (!data.ok) {
        document.getElementById('modal-erro').textContent = data.erro;
        document.getElementById('modal-erro').classList.remove('d-none');
        return;
      }
      modal.hide();
      location.reload(); // recarrega para atualizar histórico
    };
  });
})();
