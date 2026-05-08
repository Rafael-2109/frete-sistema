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
      body: JSON.stringify({pedido_id: cfg.pedidoId, loja_id: cfg.lojaId, chassi}),
    });
    const data = await r.json();
    if (!data.ok) {
      showAlerta('danger', data.erro);
      return;
    }
    showAlerta('success', `Chassi ${data.chassi} registrado.`);
    inputChassi.value = '';
    inputChassi.focus();
    setTimeout(() => location.reload(), 800);  // recarrega para atualizar saldo + lista
  }

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
  document.getElementById('btn-finalizar')?.addEventListener('click', () => {
    bootstrap.Modal.getOrCreateInstance(document.getElementById('modal-finalizar-sep')).show();
  });

  document.getElementById('sep-btn-confirmar-finalizar')?.addEventListener('click', async () => {
    bootstrap.Modal.getInstance(document.getElementById('modal-finalizar-sep'))?.hide();
    const r = await fetch(cfg.endpoints.finalizar, {
      method: 'POST',
      headers: {'X-CSRFToken': getCsrfToken()},
    });
    const data = await r.json();
    if (data.ok) location.reload();
    else showAlerta('danger', data.erro || 'Erro ao finalizar.');
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
