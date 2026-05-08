/**
 * Componente compartilhado entre montagem/disponibilizar.
 * Lê chassi via input/QR/leitor USB, faz POST AJAX, atualiza histórico inline.
 * CSRF token lido de meta[name="csrf-token"] (injetado pelo base.html).
 */
(function() {
  const cfg = window.MOTOS_ASSAI_OP_CONFIG;
  if (!cfg) return;

  const inputChassi = document.getElementById('input-chassi');
  const btnRegistrar = document.getElementById('btn-registrar');
  const btnCamera = document.getElementById('btn-camera');
  const alerta = document.getElementById('alerta');
  const chkPendencia = document.getElementById('chk-pendencia');
  const pendenciaFields = document.getElementById('pendencia-fields');

  if (chkPendencia) {
    chkPendencia.addEventListener('change', () => {
      pendenciaFields.classList.toggle('d-none', !chkPendencia.checked);
    });
  }

  // Câmera (toggle)
  let html5Qr = null;
  if (btnCamera) {
    btnCamera.addEventListener('click', () => {
      const div = document.getElementById('qr-reader');
      if (html5Qr) {
        html5Qr.stop().then(() => { html5Qr = null; div.classList.add('d-none'); });
        return;
      }
      if (!window.isSecureContext) {
        showAlerta('warning', 'Câmera requer HTTPS.');
        return;
      }
      div.classList.remove('d-none');
      html5Qr = new Html5Qrcode('qr-reader');
      html5Qr.start(
        {facingMode: 'environment'},
        {fps: 10, qrbox: 240},
        (txt) => {
          inputChassi.value = txt.trim().toUpperCase();
          html5Qr.stop().then(() => { html5Qr = null; div.classList.add('d-none'); });
          inputChassi.focus();
        },
      );
    });
  }

  inputChassi.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') { e.preventDefault(); registrar(); }
  });
  document.addEventListener('keydown', (e) => {
    if (e.ctrlKey && e.key === 'Enter') { e.preventDefault(); registrar(); }
  });
  btnRegistrar.addEventListener('click', registrar);

  function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
  }

  async function registrar() {
    const chassi = inputChassi.value.trim().toUpperCase();
    if (!chassi) { showAlerta('warning', 'Digite/escaneie um chassi'); return; }

    const payload = {chassi};
    if (cfg.modo === 'montagem' && chkPendencia) {
      payload.pendencia = chkPendencia.checked;
      payload.descricao_pendencia = document.getElementById('input-descricao-pendencia')?.value || '';
      payload.chassi_doador = document.getElementById('input-chassi-doador')?.value || '';
    }

    btnRegistrar.disabled = true;
    try {
      const r = await fetch(cfg.endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken(),
        },
        body: JSON.stringify(payload),
      });
      const data = await r.json();
      if (!data.ok) {
        showAlerta('danger', data.erro);
        return;
      }
      showAlerta('success',
        `Chassi <code>${data.chassi}</code> → <strong>${data.tipo}</strong>`);
      atualizarHistorico(data.historico || []);
      reset();
    } finally {
      btnRegistrar.disabled = false;
    }
  }

  function showAlerta(level, html) {
    alerta.className = `alert alert-${level}`;
    alerta.innerHTML = html;
    alerta.classList.remove('d-none');
    setTimeout(() => alerta.classList.add('d-none'), 4000);
  }

  function reset() {
    inputChassi.value = '';
    if (chkPendencia) {
      chkPendencia.checked = false;
      pendenciaFields.classList.add('d-none');
      const dp = document.getElementById('input-descricao-pendencia');
      const cd = document.getElementById('input-chassi-doador');
      if (dp) dp.value = '';
      if (cd) cd.value = '';
    }
    inputChassi.focus();
  }

  function atualizarHistorico(hist) {
    const list = document.getElementById('historico-list');
    if (!list) return;
    list.innerHTML = '';
    if (!hist.length) {
      list.innerHTML = '<li class="list-group-item text-muted">Sem histórico recente.</li>';
      return;
    }
    for (const h of hist) {
      const li = document.createElement('li');
      li.className = 'list-group-item d-flex justify-content-between align-items-center';
      li.innerHTML =
        `<div><code>${h.chassi}</code> · <strong>${h.modelo_codigo}</strong> · ${h.cor}` +
        ` <span class="text-muted ms-2">${h.ocorrido_em} · ${h.operador_nome}</span></div>`;
      list.appendChild(li);
    }
  }

  // Foco automático no input
  inputChassi.focus();
})();
