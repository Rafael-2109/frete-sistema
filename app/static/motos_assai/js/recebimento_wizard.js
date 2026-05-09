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
    // Valores esperados pelo recibo — usados APENAS como dica visual em B/C.
    // Não pré-preenchem o SELECT (operador deve confirmar manualmente).
    modeloEsperadoId: null,
    modeloEsperadoTexto: null,
    corEsperada: null,
  };

  // Mapa gênero feminino → masculino para match visual da cor
  // (espelha _COR_GENERO_FEMININO_PARA_MASCULINO em recebimento_service.py).
  const COR_FEM_PARA_MASC = {
    'PRETA': 'PRETO',
    'BRANCA': 'BRANCO',
    'VERMELHA': 'VERMELHO',
  };

  function normalizarCor(cor) {
    if (!cor) return null;
    const upper = String(cor).trim().toUpperCase();
    if (!upper) return null;
    return COR_FEM_PARA_MASC[upper] || upper;
  }

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

  // Detecta erro de CSRF no body retornado e exibe modal "Sessão expirada"
  // que recarrega a página. Retorna true se o erro foi de CSRF (caller deve abortar).
  function tratarErroCsrf(resp, body) {
    const isCsrfError = (
      resp && resp.status === 400 &&
      body && (body.csrf_error === true || /csrf/i.test(String(body.message || body.erro || '')))
    );
    if (!isCsrfError) return false;
    const modalEl = document.getElementById('modal-sessao-expirada');
    if (modalEl) {
      bootstrap.Modal.getOrCreateInstance(modalEl).show();
    } else {
      // fallback: alerta + reload manual
      showAlerta('danger', 'Sessão expirada. Recarregue a página.');
    }
    return true;
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

  // Avança para o passo B SEM pré-preencher modelo/cor — operador confirma
  // manualmente. Os valores esperados ficam apenas como dica visual.
  function aplicarContextoEAvancar(data) {
    state.modeloEsperadoId = data.modelo_id_esperado || null;
    state.modeloEsperadoTexto = data.modelo_texto_recibo || null;
    state.corEsperada = data.cor_esperada || null;

    // Garante que o SELECT começa sem seleção (não herda valor de chassi anterior)
    const sel = document.getElementById('select-modelo');
    if (sel) sel.value = '';
    state.modeloId = null;

    // Dica visual no Step B (não bloqueia, é só referência)
    const dicaModelo = document.getElementById('dica-modelo-recibo');
    if (dicaModelo) {
      if (state.modeloEsperadoTexto || state.modeloEsperadoId) {
        const txt = state.modeloEsperadoTexto || `id ${state.modeloEsperadoId}`;
        dicaModelo.className = 'small mt-2 text-muted';
        dicaModelo.innerHTML = `<i class="fas fa-circle-info"></i> Recibo esperava: <code>${txt}</code> — confirme se bate.`;
      } else {
        dicaModelo.className = 'small mt-2 text-warning';
        dicaModelo.innerHTML = '<i class="fas fa-triangle-exclamation"></i> Recibo não traz modelo de referência (CHASSI_EXTRA ou item livre). Selecione manualmente.';
      }
      dicaModelo.classList.remove('d-none');
    }

    setStep('B');
  }

  // Atualiza a dica visual de cor no Step C com base na cor selecionada vs esperada
  function atualizarDicaCor() {
    const dica = document.getElementById('dica-cor-recibo');
    if (!dica) return;
    const sel = document.getElementById('select-cor');
    const escolhida = sel ? (sel.value || null) : null;
    const esperadaRaw = state.corEsperada;
    const esperadaNorm = normalizarCor(esperadaRaw);
    const escolhidaNorm = normalizarCor(escolhida);

    if (!esperadaRaw) {
      dica.className = 'small mt-2 text-muted';
      dica.innerHTML = '<i class="fas fa-circle-info"></i> Recibo não traz cor de referência. Selecione a cor visual da moto.';
    } else if (!escolhidaNorm) {
      dica.className = 'small mt-2 text-muted';
      dica.innerHTML = `<i class="fas fa-circle-info"></i> Recibo: <code>${esperadaRaw}</code> — selecione a cor visual da moto.`;
    } else if (escolhidaNorm === esperadaNorm) {
      dica.className = 'small mt-2 text-success';
      dica.innerHTML = `<i class="fas fa-check"></i> Bate com o recibo (<code>${esperadaRaw}</code>).`;
    } else {
      // Match visual divergente — NÃO bloqueia, apenas alerta. Backend grava o que foi escolhido.
      dica.className = 'small mt-2 text-warning';
      dica.innerHTML = `<i class="fas fa-triangle-exclamation"></i> Recibo: <code>${esperadaRaw}</code> · Você selecionou: <code>${escolhida}</code>. Será gravada como divergência <code>COR_DIFERENTE</code>.`;
    }
    dica.classList.remove('d-none');
  }

  async function validarChassi(chassi) {
    const norm = chassi.trim().toUpperCase();
    if (!norm) { showAlerta('warning', 'Digite um chassi.'); return; }

    state.chassi = norm;

    let r, data;
    try {
      r = await fetch(cfg.endpoints.validar, {
        method: 'POST',
        headers: jsonHeaders(),
        body: JSON.stringify({recibo_id: cfg.reciboId, chassi: norm}),
      });
      data = await r.json();
    } catch (e) {
      showAlerta('danger', 'Falha de rede ao validar chassi. Tente novamente.');
      return;
    }

    if (tratarErroCsrf(r, data)) return;

    state.chassiContext = data;

    if (data.ja_conferido) {
      showAlerta('warning', `Chassi ${norm} já foi conferido. Avance para o próximo.`);
      return;
    }

    if (!data.na_nf) {
      // Mensagem neutra (não vermelha) — a confirmação real vem no modal abaixo
      showAlerta(
        'warning',
        `<strong>${norm}</strong> NÃO consta na relação do recibo. Aguardando sua confirmação para receber como CHASSI_EXTRA…`
      );
      // Modal explícito de confirmação ANTES de seguir para Step B
      const codigoEl = document.getElementById('extra-chassi-codigo');
      if (codigoEl) codigoEl.textContent = norm;
      const modalEl = document.getElementById('modal-chassi-extra');
      if (!modalEl) {
        // fallback: prossegue (template antigo sem modal)
        aplicarContextoEAvancar(data);
        return;
      }
      const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
      const btnConfirmar = document.getElementById('wiz-btn-confirmar-extra');
      const btnCancelar = document.getElementById('wiz-btn-cancelar-extra');
      const onConfirmar = () => {
        modal.hide();
        showAlerta(
          'warning',
          `<strong>${norm}</strong> será registrado como CHASSI_EXTRA (divergência). Selecione modelo e cor manualmente.`
        );
        aplicarContextoEAvancar(data);
        cleanup();
      };
      const onCancelar = () => {
        modal.hide();
        // Limpa input e volta para Step A para novo scan
        showAlerta('info', `Chassi ${norm} cancelado pelo operador. Escaneie outro chassi.`);
        document.getElementById('input-chassi').value = '';
        setStep('A');
        document.getElementById('input-chassi').focus();
        cleanup();
      };
      const cleanup = () => {
        btnConfirmar?.removeEventListener('click', onConfirmar);
        btnCancelar?.removeEventListener('click', onCancelar);
      };
      btnConfirmar?.addEventListener('click', onConfirmar);
      btnCancelar?.addEventListener('click', onCancelar);
      modal.show();
      return;
    }

    // Caso happy path: chassi pertence ao recibo
    let msg = `Chassi pertence ao recibo. Modelo esperado: <code>${data.modelo_texto_recibo || '-'}</code>`;
    if (data.regex_check && !data.regex_check.ok) {
      msg += `<br><span class="text-warning">⚠ Regex: ${data.regex_check.mensagem}</span>`;
    }
    showAlerta('info', msg);
    aplicarContextoEAvancar(data);
  }

  async function registrarConferencia() {
    if (!state.chassi || !state.modeloId) {
      showAlerta('danger', 'Chassi e modelo são obrigatórios.');
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

    let r, data;
    try {
      r = await fetch(cfg.endpoints.registrar, {
        method: 'POST',
        headers: jsonHeaders(),
        body: JSON.stringify(payload),
      });
      data = await r.json();
    } catch (e) {
      showAlerta('danger', 'Falha de rede ao registrar conferência. Tente novamente.');
      return;
    }

    if (tratarErroCsrf(r, data)) return;

    if (r.status === 409) {
      // Race condition: chassis já conferido por outro operador (H2)
      showAlerta('danger', data.erro || 'Conflito: chassi já conferido. Atualize a tela e tente outro chassi.');
      // Recarrega a página para atualizar lista de pendentes
      setTimeout(() => window.location.reload(), 2000);
      return;
    }

    if (!data.ok) {
      showAlerta('danger', 'Erro: ' + (data.erro || data.message || 'desconhecido'));
      return;
    }

    document.getElementById('resumo-conferencia').innerHTML =
      `<div class="alert alert-success">` +
      `Chassi <code>${state.chassi}</code> conferido com sucesso.<br>` +
      (data.tipo_divergencia ? `<strong>⚠ ${data.tipo_divergencia}</strong><br>` : '') +
      `Total conferido: ${data.conferidos} / ${data.total}` +
      `</div>`;

    // Atualiza contador dinâmico de pendentes no botão Finalizar (C4)
    const remaining = Math.max(0, (data.total || 0) - (data.conferidos || 0));
    const btnFinalizar = document.getElementById('btn-finalizar');
    if (btnFinalizar) {
      btnFinalizar.dataset.pendentes = String(remaining);
    }

    setStep('D');
  }

  async function uploadFoto(file) {
    const fd = new FormData();
    fd.append('foto', file);
    fd.append('recibo_id', cfg.reciboId);
    fd.append('chassi', state.chassi);
    // FormData com CSRF token no header (não no body — evita conflito com multipart)
    let r, data;
    try {
      r = await fetch(cfg.endpoints.fotoUpload, {
        method: 'POST',
        headers: {'X-CSRFToken': getCSRFToken()},
        body: fd,
      });
      data = await r.json();
    } catch (e) {
      return false;
    }
    if (tratarErroCsrf(r, data)) return false;
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
    state.modeloEsperadoId = null;
    state.modeloEsperadoTexto = null;
    state.corEsperada = null;
    document.getElementById('input-chassi').value = '';
    document.getElementById('select-modelo').value = '';
    const selCor = document.getElementById('select-cor');
    if (selCor) selCor.value = '';
    document.getElementById('input-foto').value = '';
    document.getElementById('chk-avaria').checked = false;
    document.getElementById('alerta-chassi').classList.add('d-none');
    document.getElementById('dica-modelo-recibo')?.classList.add('d-none');
    document.getElementById('dica-cor-recibo')?.classList.add('d-none');
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
      showAlerta('warning', 'Selecione um modelo.');
      return;
    }
    // SELECT de cor começa SEM seleção a cada chassi (operador confirma manualmente)
    const selCor = document.getElementById('select-cor');
    if (selCor) selCor.value = '';
    atualizarDicaCor();
    setStep('C');
  });

  document.getElementById('btn-voltar-B').addEventListener('click', () => setStep('B'));

  // Atualiza dica visual sempre que o operador troca a cor no SELECT
  document.getElementById('select-cor')?.addEventListener('change', atualizarDicaCor);

  // btn-avancar-C: se foto falhar, abre modal de confirmação
  document.getElementById('btn-avancar-C').addEventListener('click', async () => {
    const selCor = document.getElementById('select-cor');
    const corEscolhida = selCor ? (selCor.value || '').trim().toUpperCase() : '';
    if (!corEscolhida) {
      showAlerta('warning', 'Selecione a cor da moto.');
      return;
    }
    state.cor = corEscolhida;
    state.avaria = document.getElementById('chk-avaria').checked;
    const fileInput = document.getElementById('input-foto');
    if (fileInput.files && fileInput.files[0]) {
      const ok = await uploadFoto(fileInput.files[0]);
      if (!ok) {
        // Bootstrap modal para confirmar continuar sem foto
        const modalEl = document.getElementById('modal-falha-foto');
        if (modalEl) {
          bootstrap.Modal.getOrCreateInstance(modalEl).show();
          // O handler do botão "Continuar sem foto" executa registrarConferencia
          document.getElementById('wiz-btn-confirmar-sem-foto').onclick = async () => {
            bootstrap.Modal.getInstance(modalEl)?.hide();
            await registrarConferencia();
          };
          // "Cancelar" no modal não faz nada (modal fecha via data-bs-dismiss)
        } else {
          // fallback: prosseguir sem modal
          await registrarConferencia();
        }
        return;
      }
    }
    await registrarConferencia();
  });

  document.getElementById('btn-proximo-chassi').addEventListener('click', reset);

  // Finalizar recebimento — Bootstrap modal
  document.getElementById('btn-finalizar').addEventListener('click', () => {
    const pend = document.getElementById('btn-finalizar').dataset.pendentes;
    const pendNum = pend ? parseInt(pend, 10) : 0;
    const msgEl = document.getElementById('wiz-msg-finalizar');
    if (msgEl) {
      msgEl.textContent = pendNum > 0
        ? `Há ${pendNum} chassis não conferidos. Finalizar marca-os como MOTO_FALTANDO. Continuar?`
        : 'Finalizar o recebimento?';
    }
    bootstrap.Modal.getOrCreateInstance(document.getElementById('modal-finalizar-wiz')).show();
  });

  document.getElementById('wiz-btn-confirmar-finalizar')?.addEventListener('click', async () => {
    bootstrap.Modal.getInstance(document.getElementById('modal-finalizar-wiz'))?.hide();
    const pend = document.getElementById('btn-finalizar').dataset.pendentes;
    const confirmar_faltantes = pend && parseInt(pend, 10) > 0;
    let r, data;
    try {
      r = await fetch(cfg.endpoints.finalizar, {
        method: 'POST',
        headers: jsonHeaders(),
        body: JSON.stringify({confirmar_faltantes}),
      });
      data = await r.json();
    } catch (e) {
      showAlerta('danger', 'Falha de rede ao finalizar. Tente novamente.');
      return;
    }
    if (tratarErroCsrf(r, data)) return;
    if (data.ok) {
      window.location.href = data.redirect;
    } else {
      showAlerta('danger', 'Erro: ' + (data.erro || data.message || ''));
    }
  });

  // Handler do botão "Recarregar página" do modal de sessão expirada (CSRF)
  document.getElementById('wiz-btn-recarregar-sessao')?.addEventListener('click', () => {
    window.location.reload();
  });

  // ============== Init ==============
  setStep('A');
  document.getElementById('input-chassi').focus();
})();
