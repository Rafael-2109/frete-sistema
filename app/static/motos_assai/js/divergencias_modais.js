/**
 * Divergencias - JS para os 5 modais de resolucao.
 *
 * Plano 3 Tasks 16, 22.
 * Spec: docs/superpowers/specs/2026-05-12-motos-assai-carregamento-divergencia-design.md S7
 *
 * Cada botao "btn-resolver" abre um modal especifico via Bootstrap data-bs-target.
 * Os botoes "btn-confirmar-*" enviam AJAX para POST /motos-assai/divergencias/<id>/resolver.
 */
(function() {
  'use strict';

  function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
  }

  // Pre-popula campos hidden do modal com data-* do botao clicado
  document.querySelectorAll('.btn-resolver').forEach(btn => {
    btn.addEventListener('click', function() {
      const divId = this.getAttribute('data-div-id');
      const tipo = this.getAttribute('data-tipo');
      const nfId = this.getAttribute('data-nf-id') || '';
      const carId = this.getAttribute('data-car-id') || '';

      if (tipo === 'CANCELAR_NF') {
        document.getElementById('cancelar-div-id').value = divId;
        document.getElementById('cancelar-nf-id').value = nfId;
      } else if (tipo === 'CCE') {
        document.getElementById('cce-div-id').value = divId;
        document.getElementById('cce-nf-id').value = nfId;
      } else if (tipo === 'ALTERAR_CARREGAMENTO') {
        document.getElementById('alterar-div-id').value = divId;
        document.getElementById('alterar-car-id').value = carId;
      } else if (tipo === 'SUBSTITUIR_CHASSI') {
        // Pacote C (2026-05-13): preenche info + carrega dropdown sep destino.
        document.getElementById('subst-div-id').value = divId;
        const chassi = this.getAttribute('data-chassi') || '';
        const sepOrigemId = this.getAttribute('data-sep-origem-id') || '';
        const pedidoId = this.getAttribute('data-pedido-id') || '';
        const lojaId = this.getAttribute('data-loja-id') || '';
        document.getElementById('subst-chassi-label').textContent = chassi || '—';
        document.getElementById('subst-sep-origem-id').textContent = sepOrigemId;
        document.getElementById('subst-sep-origem-id-value').value = sepOrigemId;
        document.getElementById('subst-pedido-id').value = pedidoId;
        document.getElementById('subst-loja-id').value = lojaId;
        // Erro/observacao limpos
        document.getElementById('subst-erro')?.classList.add('d-none');
        document.getElementById('subst-observacao').value = '';
        // Carregar seps ativas via API
        const sel = document.getElementById('subst-sep-destino-select');
        sel.innerHTML = '<option value="">— Carregando... —</option>';
        sel.disabled = true;
        if (pedidoId && lojaId) {
          fetch('/motos-assai/api/seps-ativas?pedido_id=' + encodeURIComponent(pedidoId)
                + '&loja_id=' + encodeURIComponent(lojaId), {
            headers: {'X-CSRFToken': getCsrfToken()},
            credentials: 'same-origin',
          }).then(r => r.json()).then(resp => {
            if (!resp.ok || !resp.seps || resp.seps.length === 0) {
              sel.innerHTML = '<option value="">— Nenhuma sep ativa nesta loja —</option>';
              return;
            }
            sel.innerHTML = '<option value="">— Selecione —</option>';
            resp.seps.forEach(function (s) {
              // Pular sep_origem (n&atilde;o pode mover para a mesma)
              if (String(s.id) === String(sepOrigemId)) return;
              const opt = document.createElement('option');
              opt.value = s.id;
              opt.textContent = 'Sep #' + s.id + ' — ' + s.status
                              + (s.iniciada_em ? ' (' + s.iniciada_em + ')' : '');
              sel.appendChild(opt);
            });
            sel.disabled = false;
          }).catch(err => {
            sel.innerHTML = '<option value="">— Erro ao carregar seps —</option>';
            console.error('seps-ativas falhou:', err);
          });
        } else {
          sel.innerHTML = '<option value="">— Diverg&ecirc;ncia sem sep origem —</option>';
        }
      } else if (tipo === 'IGNORAR') {
        document.getElementById('ignorar-div-id').value = divId;
      }
    });
  });

  async function resolverDivergencia(divId, payload) {
    const url = `/motos-assai/divergencias/${divId}/resolver`;
    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken(),
          'Accept': 'application/json',
        },
        body: JSON.stringify(payload),
      });
      const data = await res.json().catch(() => ({}));
      if (res.ok && data.ok) {
        alert('Divergencia resolvida com sucesso.');
        window.location.reload();
        return true;
      } else {
        alert('Erro: ' + (data.erro || data.error || `HTTP ${res.status}`));
        return false;
      }
    } catch (err) {
      alert('Erro de rede: ' + err.message);
      return false;
    }
  }

  // Cancelar NF
  const btnCancelar = document.getElementById('btn-confirmar-cancelar-nf');
  if (btnCancelar) {
    btnCancelar.addEventListener('click', () => {
      const divId = document.getElementById('cancelar-div-id').value;
      const motivo = document.getElementById('cancelar-motivo').value.trim();
      if (motivo.length < 3) {
        alert('Motivo obrigatorio (>= 3 caracteres)');
        return;
      }
      resolverDivergencia(divId, {
        tipo_resolucao: 'CANCELAR_NF',
        observacao: motivo,
      });
    });
  }

  // Plano 4 Task 10: CCe via upload PDF (parser deterministico + LLM fallback)
  const btnCCe = document.getElementById('btn-confirmar-cce');
  if (btnCCe) {
    btnCCe.addEventListener('click', async () => {
      const divId = document.getElementById('cce-div-id').value;
      const fileInput = document.getElementById('cce-pdf-input');
      const erroDiv = document.getElementById('cce-erro');
      const previewCard = document.getElementById('cce-preview');

      erroDiv?.classList.add('d-none');
      if (!divId) {
        if (erroDiv) {
          erroDiv.textContent = 'Divergencia sem ID — fechar e reabrir modal';
          erroDiv.classList.remove('d-none');
        }
        return;
      }
      if (!fileInput || !fileInput.files || fileInput.files.length === 0) {
        if (erroDiv) {
          erroDiv.textContent = 'Selecione o PDF da CCe';
          erroDiv.classList.remove('d-none');
        }
        return;
      }

      btnCCe.disabled = true;
      try {
        const csrfMeta = document.querySelector('meta[name="csrf-token"]');
        const csrf = csrfMeta ? csrfMeta.content : '';
        const formData = new FormData();
        formData.append('cce_pdf', fileInput.files[0]);

        const url = '/motos-assai/divergencias/' + divId + '/upload-cce';
        const r = await fetch(url, {
          method: 'POST',
          headers: {'X-CSRFToken': csrf},
          body: formData,
        });
        const data = await r.json();
        if (!data.ok) {
          if (erroDiv) {
            erroDiv.textContent = data.erro || 'Erro ao processar CCe';
            erroDiv.classList.remove('d-none');
          }
          btnCCe.disabled = false;
          return;
        }

        // Sucesso — mostrar preview brevemente e recarregar
        if (previewCard) {
          previewCard.classList.remove('d-none');
          document.getElementById('cce-prev-numero').textContent = data.numero_cce || '—';
          document.getElementById('cce-prev-nf').textContent = data.numero_nf_referenciada || '—';
          document.getElementById('cce-prev-confianca').textContent
            = (data.confianca !== undefined ? data.confianca.toFixed(2) : '—')
            + (data.parser_usado ? ' (' + data.parser_usado + ')' : '');
          document.getElementById('cce-prev-count').textContent = (data.chassis_trocados || 0);
          const ul = document.getElementById('cce-prev-chassis');
          ul.innerHTML = '';
          (data.chassis_corrigidos_aplicados || []).forEach(par => {
            const li = document.createElement('li');
            li.textContent = par[0] + ' → ' + par[1];
            ul.appendChild(li);
          });
        }
        alert('CCe ' + (data.numero_cce || '') + ' aplicada — '
              + (data.chassis_trocados || 0) + ' chassis trocados');
        setTimeout(() => location.reload(), 800);
      } catch (err) {
        if (erroDiv) {
          erroDiv.textContent = 'Erro de rede: ' + err.message;
          erroDiv.classList.remove('d-none');
        }
        btnCCe.disabled = false;
      }
    });
  }

  // Alterar Carregamento
  const btnAlterar = document.getElementById('btn-confirmar-alterar-carregamento');
  if (btnAlterar) {
    btnAlterar.addEventListener('click', () => {
      const divId = document.getElementById('alterar-div-id').value;
      const carId = document.getElementById('alterar-car-id').value;
      const chassisRaw = document.getElementById('alterar-chassis').value;
      const motivo = document.getElementById('alterar-motivo').value.trim();
      const chassis = chassisRaw.split(/\r?\n/).map(s => s.trim()).filter(Boolean);
      if (!chassis.length) {
        alert('Liste pelo menos 1 chassi.');
        return;
      }
      resolverDivergencia(divId, {
        tipo_resolucao: 'ALTERAR_CARREGAMENTO',
        observacao: motivo || 'via UI divergencias',
        extras: {
          carregamento_id: parseInt(carId, 10),
          chassis: chassis,
          motivo: motivo,
        },
      });
    });
  }

  // Pacote C (2026-05-13): Substituir Chassi REAL via divergencia.
  // Envia tipo_resolucao=SUBSTITUIR_CHASSI + extras={sep_origem_id, sep_destino_id, chassi}.
  // Backend chama substituir_chassi_entre_seps(via_divergencia=True) e marca div resolvida.
  const btnSubst = document.getElementById('btn-confirmar-substituir-chassi');
  if (btnSubst) {
    btnSubst.addEventListener('click', () => {
      const divId = document.getElementById('subst-div-id').value;
      const sepOrigemId = document.getElementById('subst-sep-origem-id-value').value;
      const sepDestinoEl = document.getElementById('subst-sep-destino-select');
      const sepDestinoId = sepDestinoEl ? sepDestinoEl.value : '';
      const chassi = document.getElementById('subst-chassi-label').textContent.trim();
      const obs = document.getElementById('subst-observacao').value.trim();
      const erroEl = document.getElementById('subst-erro');

      function showErro(msg) {
        if (erroEl) {
          erroEl.textContent = msg;
          erroEl.classList.remove('d-none');
        } else {
          alert(msg);
        }
      }

      erroEl?.classList.add('d-none');

      if (!sepOrigemId) { showErro('Diverg&ecirc;ncia sem sep origem.'); return; }
      if (!sepDestinoId) { showErro('Selecione a sep destino.'); return; }
      if (sepOrigemId === sepDestinoId) { showErro('Sep destino igual &agrave; origem.'); return; }
      if (!chassi || chassi === '—') { showErro('Diverg&ecirc;ncia sem chassi.'); return; }

      btnSubst.disabled = true;
      resolverDivergencia(divId, {
        tipo_resolucao: 'SUBSTITUIR_CHASSI',
        observacao: obs || `Substitui&ccedil;&atilde;o ${chassi} sep ${sepOrigemId} -> ${sepDestinoId}`,
        extras: {
          chassi: chassi,
          sep_origem_id: parseInt(sepOrigemId, 10),
          sep_destino_id: parseInt(sepDestinoId, 10),
        },
      }).finally(() => {
        btnSubst.disabled = false;
      });
    });
  }

  // Ignorar
  const btnIgnorar = document.getElementById('btn-confirmar-ignorar');
  if (btnIgnorar) {
    btnIgnorar.addEventListener('click', () => {
      const divId = document.getElementById('ignorar-div-id').value;
      const obs = document.getElementById('ignorar-observacao').value.trim();
      if (!obs) {
        alert('Observacao obrigatoria para IGNORAR.');
        return;
      }
      resolverDivergencia(divId, {
        tipo_resolucao: 'IGNORAR',
        observacao: obs,
      });
    });
  }
})();
