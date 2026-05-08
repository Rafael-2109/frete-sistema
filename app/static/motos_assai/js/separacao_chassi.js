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

  // Desfazer (H4: usar desfazerBase em vez de replace('/0') frágil)
  document.addEventListener('click', async (e) => {
    const btn = e.target.closest('[data-action="desfazer"]');
    if (!btn) return;
    if (!confirm(`Remover chassi ${btn.closest('tr').querySelector('code').textContent}?`)) return;
    const itemId = btn.dataset.itemId;
    const url = cfg.endpoints.desfazerBase + itemId;
    const r = await fetch(url, {method: 'POST', headers: {'X-CSRFToken': getCsrfToken()}});
    const data = await r.json();
    if (data.ok) location.reload();
    else alert(data.erro);
  });

  document.getElementById('btn-finalizar')?.addEventListener('click', async () => {
    if (!confirm('Finalizar separação? Saldos pendentes ficam para outra separação se houver.')) return;
    const r = await fetch(cfg.endpoints.finalizar, {
      method: 'POST',
      headers: {'X-CSRFToken': getCsrfToken()},
    });
    const data = await r.json();
    if (data.ok) location.reload();
    else alert(data.erro);
  });

  document.getElementById('btn-cancelar')?.addEventListener('click', async () => {
    const motivo = prompt('Motivo do cancelamento (≥3 chars):');
    if (!motivo || motivo.trim().length < 3) return;
    const r = await fetch(cfg.endpoints.cancelar, {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken()},
      body: JSON.stringify({motivo}),
    });
    const data = await r.json();
    if (data.ok) location.reload();
    else alert(data.erro);
  });

  function showAlerta(level, html) {
    alerta.className = `alert alert-${level} small`;
    alerta.innerHTML = html;
    alerta.classList.remove('d-none');
    setTimeout(() => alerta.classList.add('d-none'), 4000);
  }

  inputChassi?.focus();
})();
