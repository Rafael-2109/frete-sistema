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
        document.getElementById('subst-div-id').value = divId;
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
      } else {
        alert('Erro: ' + (data.erro || data.error || `HTTP ${res.status}`));
      }
    } catch (err) {
      alert('Erro de rede: ' + err.message);
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

  // CCe (placeholder)
  const btnCCe = document.getElementById('btn-confirmar-cce');
  if (btnCCe) {
    btnCCe.addEventListener('click', () => {
      const divId = document.getElementById('cce-div-id').value;
      const numero = document.getElementById('cce-numero').value.trim();
      const obs = document.getElementById('cce-observacao').value.trim();
      resolverDivergencia(divId, {
        tipo_resolucao: 'CCE',
        observacao: obs || `CCe ${numero}`,
        extras: { numero_cce: numero },
      });
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

  // Substituir Chassi (placeholder)
  const btnSubst = document.getElementById('btn-confirmar-substituir-chassi');
  if (btnSubst) {
    btnSubst.addEventListener('click', () => {
      const divId = document.getElementById('subst-div-id').value;
      const chassiNovo = document.getElementById('subst-chassi-novo').value.trim();
      const obs = document.getElementById('subst-observacao').value.trim();
      resolverDivergencia(divId, {
        tipo_resolucao: 'SUBSTITUIR_CHASSI',
        observacao: obs || `chassi novo: ${chassiNovo}`,
        extras: { chassi_novo: chassiNovo },
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
