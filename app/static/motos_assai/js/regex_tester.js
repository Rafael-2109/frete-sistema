/**
 * regex_tester.js
 * Testador interativo de regex para o formulário de modelos.
 * Depende de: fetch API, CSRF meta tag.
 * Configuração: window.MOTOS_ASSAI_REGEX_ENDPOINT (URL da API de teste).
 */
(function () {
  document.addEventListener('DOMContentLoaded', function () {
    const btnTestar = document.getElementById('btn_testar');
    if (!btnTestar) return;

    btnTestar.addEventListener('click', async () => {
      const regex = document.getElementById('regex_chassi').value;
      const chassi = document.getElementById('teste_chassi').value;
      const resultEl = document.getElementById('resultado_teste');
      resultEl.textContent = '...';

      const csrfMeta = document.querySelector('meta[name="csrf-token"]');
      const csrfToken = csrfMeta ? csrfMeta.getAttribute('content') : '';
      const endpoint = window.MOTOS_ASSAI_REGEX_ENDPOINT || '';

      try {
        const r = await fetch(endpoint, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': csrfToken,
          },
          body: JSON.stringify({ regex, chassi }),
        });
        const data = await r.json();
        if (data.ok) {
          resultEl.innerHTML = data.bate
            ? '<span class="text-success">✓ BATE</span>'
            : '<span class="text-danger">✗ NÃO BATE</span>';
        } else {
          resultEl.innerHTML = '<span class="text-danger">' + (data.erro || 'erro') + '</span>';
        }
      } catch (e) {
        resultEl.innerHTML = '<span class="text-danger">erro: ' + e + '</span>';
      }
    });
  });
})();
