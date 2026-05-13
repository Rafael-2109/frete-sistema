/**
 * Modal Expedicao - Plano 3 Task 12.
 *
 * Acionado apos upload de NF que cria sep automaticamente em FATURADA (S1=b).
 * Abre modal com data-sep-id pre-popularizado para coletar expedicao + agendamento.
 *
 * S7=a: clicar X (close) ou Pular = mesma acao (apenas fecha modal sem salvar).
 */
(function() {
  'use strict';

  function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
  }

  // Auto-abrir modal se houver data-sep-criada-via-nf no body
  document.addEventListener('DOMContentLoaded', function() {
    const sepId = document.body.getAttribute('data-sep-criada-via-nf');
    if (sepId) {
      const modalEl = document.getElementById('modal-expedicao');
      if (modalEl && window.bootstrap) {
        document.getElementById('expedicao-sep-id').value = sepId;
        // Default expedicao = hoje
        const today = new Date().toISOString().slice(0, 10);
        document.getElementById('expedicao-data').value = today;
        const modal = new window.bootstrap.Modal(modalEl);
        modal.show();
      }
    }
  });

  const btnConfirmar = document.getElementById('btn-confirmar-expedicao');
  if (btnConfirmar) {
    btnConfirmar.addEventListener('click', async function() {
      const sepId = document.getElementById('expedicao-sep-id').value;
      const expedicao = document.getElementById('expedicao-data').value;
      const agendamento = document.getElementById('expedicao-agendamento').value;
      const protocolo = document.getElementById('expedicao-protocolo').value.trim();
      const confirmado = document.getElementById('expedicao-confirmado').checked;

      if (!expedicao) {
        alert('Data de expedição é obrigatória.');
        return;
      }

      try {
        const res = await fetch(`/motos-assai/faturamento/sep/${sepId}/expedicao`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken(),
            'Accept': 'application/json',
          },
          body: JSON.stringify({
            expedicao: expedicao,
            agendamento: agendamento || null,
            protocolo: protocolo || null,
            agendamento_confirmado: confirmado,
          }),
        });
        const data = await res.json().catch(() => ({}));
        if (res.ok && data.ok) {
          // Fechar modal e dar feedback
          const modalEl = document.getElementById('modal-expedicao');
          if (window.bootstrap) {
            const modal = window.bootstrap.Modal.getInstance(modalEl);
            if (modal) modal.hide();
          }
          alert('Expedição definida com sucesso.');
        } else {
          alert('Erro: ' + (data.erro || data.error || `HTTP ${res.status}`));
        }
      } catch (err) {
        alert('Erro de rede: ' + err.message);
      }
    });
  }
})();
