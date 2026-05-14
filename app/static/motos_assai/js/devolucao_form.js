/* devolucao_form.js — Form de devolucao pela NF de venda Q.P.A.
 *
 * Responsabilidades:
 *   - Atualizar contador de chassis selecionados + habilitar/desabilitar botao Devolver.
 *   - "Marcar todos elegiveis" / "Limpar selecao".
 *   - Carregar modal de pendencias do chassi (AJAX) ao clicar no botao Pendencias(qtd).
 *   - Validacao client-side antes do submit (motivo >= 3, >= 1 chassi).
 */
(function () {
  'use strict';

  function $(sel, root) { return (root || document).querySelector(sel); }
  function $all(sel, root) { return Array.from((root || document).querySelectorAll(sel)); }

  // ----- Selecao de chassis ------------------------------------------------
  function checkboxes() {
    return $all('input.chassi-checkbox');
  }

  function elegiveis() {
    return checkboxes().filter(function (cb) { return !cb.disabled; });
  }

  function selecionados() {
    return checkboxes().filter(function (cb) { return cb.checked && !cb.disabled; });
  }

  function atualizarContador() {
    var n = selecionados().length;
    var spanContador = $('#contador-selecionados');
    if (spanContador) spanContador.textContent = String(n);
    var btn = $('#btn-devolver');
    if (btn) btn.disabled = n === 0;
  }

  function bindCheckboxes() {
    checkboxes().forEach(function (cb) {
      cb.addEventListener('change', atualizarContador);
    });
  }

  function bindAtalhosSelecao() {
    var btnTodos = $('#btn-selecionar-todos');
    if (btnTodos) {
      btnTodos.addEventListener('click', function () {
        elegiveis().forEach(function (cb) { cb.checked = true; });
        atualizarContador();
      });
    }
    var btnLimpar = $('#btn-limpar-selecao');
    if (btnLimpar) {
      btnLimpar.addEventListener('click', function () {
        checkboxes().forEach(function (cb) { cb.checked = false; });
        atualizarContador();
      });
    }
  }

  // ----- Modal Pendencias do chassi ----------------------------------------
  function abrirModalPendencias(chassi) {
    var modalEl = $('#modal-pendencias-chassi');
    if (!modalEl) return;
    var codigo = $('#modal-pendencias-chassi-codigo');
    var loading = $('#modal-pendencias-loading');
    var vazio = $('#modal-pendencias-vazio');
    var erro = $('#modal-pendencias-erro');
    var conteudo = $('#modal-pendencias-conteudo');
    var total = $('#modal-pendencias-total');
    var tbody = $('#modal-pendencias-tbody');

    if (codigo) codigo.textContent = chassi;
    if (loading) loading.style.display = '';
    if (vazio) vazio.style.display = 'none';
    if (erro) {
      erro.style.display = 'none';
      erro.textContent = '';
    }
    if (conteudo) conteudo.style.display = 'none';
    if (tbody) tbody.innerHTML = '';

    // Bootstrap 5 — instancia/usa modal
    var modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    modal.show();

    var url = '/motos-assai/devolucoes/chassi/' + encodeURIComponent(chassi) + '/pendencias';
    fetch(url, {
      method: 'GET',
      headers: { 'Accept': 'application/json' },
      credentials: 'same-origin',
    })
      .then(function (res) {
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return res.json();
      })
      .then(function (data) {
        if (loading) loading.style.display = 'none';
        if (!data || !data.eventos || data.eventos.length === 0) {
          if (vazio) vazio.style.display = '';
          if (total) total.textContent = '0';
          return;
        }
        if (total) total.textContent = String(data.qtd || 0);
        if (tbody) {
          data.eventos.forEach(function (ev) {
            var tr = document.createElement('tr');
            tr.innerHTML = (
              '<td>' + escapeHtml(ev.ocorrido_em) + '</td>' +
              '<td><span class="badge bg-' +
                (ev.tipo === 'PENDENTE' ? 'warning text-dark' : 'success') +
                '">' + escapeHtml(ev.tipo) + '</span>' +
                (ev.origem_devolucao ? ' <small class="text-danger ms-1"><i class="fas fa-undo-alt"></i> Devolução</small>' : '') +
              '</td>' +
              '<td>' + escapeHtml(ev.operador) + '</td>' +
              '<td>' + escapeHtml(ev.observacao) + '</td>'
            );
            tbody.appendChild(tr);
          });
        }
        if (conteudo) conteudo.style.display = '';
      })
      .catch(function (err) {
        if (loading) loading.style.display = 'none';
        if (erro) {
          erro.style.display = '';
          erro.textContent = 'Erro ao carregar pendências: ' + err.message;
        }
      });
  }

  function escapeHtml(s) {
    if (s === null || s === undefined) return '';
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function bindBotoesPendencias() {
    $all('.btn-pendencias').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var chassi = btn.getAttribute('data-chassi');
        if (chassi) abrirModalPendencias(chassi);
      });
    });
  }

  // ----- Submit: validacao client-side --------------------------------------
  function bindSubmit() {
    var form = $('#form-devolucao');
    if (!form) return;
    form.addEventListener('submit', function (e) {
      var motivo = ($('#motivo') && $('#motivo').value || '').trim();
      var n = selecionados().length;
      if (motivo.length < 3) {
        e.preventDefault();
        alert('Motivo precisa ter pelo menos 3 caracteres.');
        return;
      }
      if (n === 0) {
        e.preventDefault();
        alert('Selecione pelo menos 1 chassi para devolver.');
        return;
      }
      if (!confirm('Confirma a devolução de ' + n + ' chassi(s)?')) {
        e.preventDefault();
      }
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    bindCheckboxes();
    bindAtalhosSelecao();
    bindBotoesPendencias();
    bindSubmit();
    atualizarContador();
  });
})();
