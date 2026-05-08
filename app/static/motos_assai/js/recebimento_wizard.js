/**
 * Wizard de recebimento Motos Assaí — A→B→C→D
 *
 * Fluxo:
 * A: scan QR ou digita chassi → POST /validar-chassi → recebe modelo/cor esperados
 * B: operador confirma/troca modelo
 * C: operador confirma/troca cor + foto opcional + flag avaria
 * D: POST /registrar → grava AssaiReciboItem + AssaiMoto + evento ESTOQUE
 *    → reset para chassi seguinte
 *
 * CSRF: token lido de meta[name="csrf-token"] (injetado pelo base.html)
 * e incluído em MOTOS_ASSAI_RECEBIMENTO.csrfToken para todos os POSTs JSON.
 */
(function() {
  const cfg = window.MOTOS_ASSAI_RECEBIMENTO;
  if (!cfg) { console.error('cfg ausente'); return; }

  const state = {
    chassi: null,
    qrLido: false,
    modeloId: null,
    cor: null,
    fotoS3Key: null,
    avaria: false,
    chassiContext: null,
  };

  // ============== Helpers ==============

  function getCSRFToken() {
    // Usa token do cfg (injetado no template via meta tag) ou lê diretamente
    if (cfg.csrfToken) return cfg.csrfToken;
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
  }

  function jsonHeaders() {
    return {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCSRFToken(),
    };
  }

  function setStep(step) {
    document.querySelectorAll('[id^="step-"]').forEach(el => el.classList.add('d-none'));
    document.getElementById('step-' + step).classList.remove('d-none');
    document.querySelectorAll('#stepper .badge').forEach(b => {
      b.classList.toggle('bg-primary', b.dataset.step === step);
      b.classList.toggle('bg-light', b.dataset.step !== step);
      b.classList.toggle('border', b.dataset.step !== step);
    });
  }

  function showAlerta(level, html) {
    const el = document.getElementById('alerta-chassi');
    el.className = `alert alert-${level} small mt-3`;
    el.innerHTML = html;
    el.classList.remove('d-none');
  }

  // ============== QR scanner ==============

  let html5Qr = null;
  function startQr() {
    if (!window.isSecureContext) {
      showAlerta('warning', 'Câmera requer HTTPS. Use leitor USB ou digite manualmente.');
      return;
    }
    html5Qr = new Html5Qrcode('qr-reader');
    html5Qr.start(
      { facingMode: 'environment' },
      { fps: 10, qrbox: 240 },
      (txt) => {
        state.qrLido = true;
        document.getElementById('input-chassi').value = txt.trim().toUpperCase();
        stopQr();
        validarChassi(txt);
      }
    ).then(() => {
      document.getElementById('btn-start-qr').classList.add('d-none');
      document.getElementById('btn-stop-qr').classList.remove('d-none');
    }).catch(e => showAlerta('danger', 'Erro ao iniciar câmera: ' + e));
  }

  function stopQr() {
    if (!html5Qr) return;
    html5Qr.stop().then(() => {
      document.getElementById('btn-start-qr').classList.remove('d-none');
      document.getElementById('btn-stop-qr').classList.add('d-none');
    }).catch(() => {});
  }

  // ============== AJAX ==============

  async function validarChassi(chassi) {
    const norm = chassi.trim().toUpperCase();
    if (!norm) { showAlerta('warning', 'Digite um chassi.'); return; }

    state.chassi = norm;

    const r = await fetch(cfg.endpoints.validar, {
      method: 'POST',
      headers: jsonHeaders(),
      body: JSON.stringify({recibo_id: cfg.reciboId, chassi: norm}),
    });
    const data = await r.json();

    state.chassiContext = data;

    if (data.ja_conferido) {
      showAlerta('warning', `Chassi ${norm} já foi conferido. Avance para o próximo.`);
      return;
    }

    if (!data.na_nf) {
      showAlerta('danger', `<strong>${norm}</strong> NÃO está no recibo (CHASSI_EXTRA). Conferência continua mas será marcada como divergência.`);
    } else {
      let msg = `Chassi pertence ao recibo. Modelo esperado: <code>${data.modelo_texto_recibo || '-'}</code>`;
      if (data.regex_check && !data.regex_check.ok) {
        msg += `<br><span class="text-warning">⚠ Regex: ${data.regex_check.mensagem}</span>`;
      }
      showAlerta('info', msg);
    }

    // Pré-seleciona modelo no Step B se conhecido
    if (data.modelo_id_esperado) {
      state.modeloId = data.modelo_id_esperado;
      document.getElementById('select-modelo').value = data.modelo_id_esperado;
    }
    if (data.cor_esperada) {
      state.cor = data.cor_esperada;
    }

    setStep('B');
  }

  async function registrarConferencia() {
    if (!state.chassi || !state.modeloId) {
      alert('Chassi e modelo são obrigatórios.');
      return;
    }

    const payload = {
      recibo_id: cfg.reciboId,
      chassi: state.chassi,
      modelo_id: state.modeloId,
      cor: state.cor,
      qr_code_lido: state.qrLido,
      foto_s3_key: state.fotoS3Key,
      avaria_fisica: state.avaria,
    };

    const r = await fetch(cfg.endpoints.registrar, {
      method: 'POST',
      headers: jsonHeaders(),
      body: JSON.stringify(payload),
    });

    if (r.status === 409) {
      alert('Conflito: outro operador conferindo este chassi simultaneamente. Tente novamente.');
      return;
    }

    const data = await r.json();
    if (!data.ok) {
      alert('Erro: ' + (data.erro || 'desconhecido'));
      return;
    }

    document.getElementById('resumo-conferencia').innerHTML =
      `<div class="alert alert-success">` +
      `Chassi <code>${state.chassi}</code> conferido com sucesso.<br>` +
      (data.tipo_divergencia ? `<strong>⚠ ${data.tipo_divergencia}</strong><br>` : '') +
      `Total conferido: ${data.conferidos} / ${data.total}` +
      `</div>`;
    setStep('D');
  }

  async function uploadFoto(file) {
    const fd = new FormData();
    fd.append('foto', file);
    fd.append('recibo_id', cfg.reciboId);
    fd.append('chassi', state.chassi);
    // FormData com CSRF token no header (não no body — evita conflito com multipart)
    const r = await fetch(cfg.endpoints.fotoUpload, {
      method: 'POST',
      headers: {'X-CSRFToken': getCSRFToken()},
      body: fd,
    });
    const data = await r.json();
    if (data.ok) state.fotoS3Key = data.s3_key;
    return data.ok;
  }

  function reset() {
    state.chassi = null;
    state.qrLido = false;
    state.modeloId = null;
    state.cor = null;
    state.fotoS3Key = null;
    state.avaria = false;
    state.chassiContext = null;
    document.getElementById('input-chassi').value = '';
    document.getElementById('select-modelo').value = '';
    document.getElementById('input-cor').value = '';
    document.getElementById('input-foto').value = '';
    document.getElementById('chk-avaria').checked = false;
    document.getElementById('alerta-chassi').classList.add('d-none');
    setStep('A');
    document.getElementById('input-chassi').focus();
  }

  // ============== Handlers ==============

  document.getElementById('btn-start-qr').addEventListener('click', startQr);
  document.getElementById('btn-stop-qr').addEventListener('click', stopQr);

  document.getElementById('btn-chassi-manual').addEventListener('click', () => {
    validarChassi(document.getElementById('input-chassi').value);
  });
  document.getElementById('input-chassi').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      validarChassi(e.target.value);
    }
  });

  document.getElementById('btn-voltar-A').addEventListener('click', () => setStep('A'));
  document.getElementById('btn-avancar-B').addEventListener('click', () => {
    state.modeloId = parseInt(document.getElementById('select-modelo').value, 10) || null;
    if (!state.modeloId) {
      alert('Selecione um modelo.');
      return;
    }
    if (state.cor) {
      document.getElementById('input-cor').value = state.cor;
    }
    setStep('C');
  });

  document.getElementById('btn-voltar-B').addEventListener('click', () => setStep('B'));
  document.getElementById('btn-avancar-C').addEventListener('click', async () => {
    state.cor = document.getElementById('input-cor').value.trim().toUpperCase() || null;
    state.avaria = document.getElementById('chk-avaria').checked;
    const fileInput = document.getElementById('input-foto');
    if (fileInput.files && fileInput.files[0]) {
      const ok = await uploadFoto(fileInput.files[0]);
      if (!ok) {
        if (!confirm('Falha ao subir foto. Continuar mesmo assim?')) return;
      }
    }
    await registrarConferencia();
  });

  document.getElementById('btn-proximo-chassi').addEventListener('click', reset);

  document.getElementById('btn-finalizar').addEventListener('click', async () => {
    const pend = document.getElementById('btn-finalizar').dataset.pendentes;
    let confirmar_faltantes = false;
    if (pend && parseInt(pend, 10) > 0) {
      if (!confirm(`Há ${pend} chassis não conferidos. Finalizar marca-os como MOTO_FALTANDO. Continuar?`)) return;
      confirmar_faltantes = true;
    }
    const r = await fetch(cfg.endpoints.finalizar, {
      method: 'POST',
      headers: jsonHeaders(),
      body: JSON.stringify({confirmar_faltantes}),
    });
    const data = await r.json();
    if (data.ok) {
      window.location.href = data.redirect;
    } else {
      alert('Erro: ' + (data.erro || ''));
    }
  });

  // ============== Init ==============
  setStep('A');
  document.getElementById('input-chassi').focus();
})();
