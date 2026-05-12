/* Pos-Venda - Motos Assai
 *
 * Tela:
 *   - Lista de motos vendidas (renderizada server-side).
 *   - Botao "Ocorrencias (N)" abre modal AJAX com 2 secoes (Loja x Cliente).
 *   - Modal permite CRUD de ocorrencias + upload/delete de anexos.
 *
 * Endpoints consumidos:
 *   GET    /motos-assai/pos-venda/ocorrencias/<chassi>?embed=1
 *   POST   /motos-assai/pos-venda/ocorrencias/<chassi>          { categoria, descricao }
 *   DELETE /motos-assai/pos-venda/ocorrencias/<oc_id>
 *   POST   /motos-assai/pos-venda/ocorrencias/<oc_id>/anexos    (multipart 'arquivos')
 *   DELETE /motos-assai/pos-venda/anexos/<anexo_id>
 *
 * CSRF: token lido de meta[name="csrf-token"] (injetado pelo base.html).
 */
(function () {
  'use strict';

  // -------------------------------------------------------------------------
  // Helpers
  // -------------------------------------------------------------------------

  function csrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
  }

  function jsonHeaders() {
    return {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      'X-CSRFToken': csrfToken(),
    };
  }

  function escapeHtml(s) {
    if (s == null) return '';
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function showAlert(target, msg, level) {
    level = level || 'danger';
    var div = document.createElement('div');
    div.className = 'alert alert-' + level + ' alert-dismissible fade show mt-2';
    div.role = 'alert';
    div.innerHTML = escapeHtml(msg) +
      '<button type="button" class="btn-close" data-bs-dismiss="alert"></button>';
    target.prepend(div);
    setTimeout(function () { div.remove(); }, 6000);
  }

  // -------------------------------------------------------------------------
  // Modal: abrir
  // -------------------------------------------------------------------------

  function abrirModalOcorrencias(chassi, btn) {
    var modalEl = document.getElementById('modalOcorrencias');
    if (!modalEl) return;

    var body = document.getElementById('modal-ocorrencias-body');
    var subtitulo = document.getElementById('modal-ocorrencias-subtitulo');
    if (subtitulo) subtitulo.textContent = 'Chassi ' + chassi;
    body.innerHTML = '<div class="text-center py-4">' +
      '<div class="spinner-border text-primary" role="status"></div></div>';

    var modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    modal.show();

    var url = '/motos-assai/pos-venda/ocorrencias/' + encodeURIComponent(chassi) + '?embed=1';
    fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.text();
      })
      .then(function (html) {
        body.innerHTML = html;
        // Guarda referencia ao botao de origem (para atualizar contador)
        body.dataset.btnOrigemChassi = chassi;
      })
      .catch(function (e) {
        body.innerHTML = '<div class="alert alert-danger">Erro ao carregar ocorrencias: ' +
          escapeHtml(e.message) + '</div>';
      });
  }

  // -------------------------------------------------------------------------
  // CRUD de ocorrencias e anexos (delegado em #modal-ocorrencias-body)
  // -------------------------------------------------------------------------

  function refrescarBotaoListagem(chassi, delta) {
    var btn = document.querySelector(
      '.btn-ocorrencias[data-chassi="' + chassi.replace(/"/g, '\\"') + '"]'
    );
    if (!btn) return;
    var span = btn.querySelector('.qtd-ocorrencias');
    if (!span) return;
    var atual = parseInt(span.textContent, 10) || 0;
    span.textContent = String(Math.max(0, atual + delta));
  }

  function refrescarContadorCategoria(modalBody, categoria, delta) {
    var badge = modalBody.querySelector(
      '.count-categoria[data-categoria="' + categoria + '"]'
    );
    if (!badge) return;
    var atual = parseInt(badge.textContent, 10) || 0;
    badge.textContent = String(Math.max(0, atual + delta));
  }

  function renderOcorrenciaCard(oc) {
    // HTML do card de ocorrencia (espelha o macro render_ocorrencia do Jinja).
    var anexosHtml = (oc.anexos || []).map(renderAnexoHtml).join('');
    return (
      '<article class="ocorrencia-card pos-venda-ocorrencia-card border rounded" ' +
        'data-ocorrencia-id="' + oc.id + '" data-categoria="' + escapeHtml(oc.categoria) + '">' +
        '<header class="pos-venda-ocorrencia-header">' +
          '<span>' +
            '<i class="far fa-clock me-1"></i>' +
            escapeHtml(oc.criado_em || '—') +
            '<span class="mx-1">•</span>' +
            '<i class="far fa-user me-1"></i>' +
            escapeHtml(oc.criado_por || '') +
          '</span>' +
          '<span>' +
            '<button type="button" class="btn btn-link btn-sm p-0 ms-2 btn-excluir-ocorrencia text-danger" ' +
              'title="Excluir ocorrencia"><i class="fas fa-trash-alt"></i></button>' +
          '</span>' +
        '</header>' +
        '<div class="pos-venda-ocorrencia-body">' +
          '<p class="descricao-texto pos-venda-descricao">' +
            escapeHtml(oc.descricao) + '</p>' +
          '<div class="anexos-wrapper">' +
            '<div class="anexos-grid d-flex flex-wrap gap-2 mb-2">' + anexosHtml + '</div>' +
            '<form class="form-upload-anexo d-flex align-items-center gap-2" ' +
              'data-ocorrencia-id="' + oc.id + '">' +
              '<input type="file" name="arquivos" class="form-control form-control-sm" multiple ' +
                'accept="image/*,video/*,audio/*">' +
              '<button type="submit" class="btn btn-sm btn-outline-primary flex-shrink-0">' +
                '<i class="fas fa-paperclip me-1"></i>Anexar</button>' +
            '</form>' +
          '</div>' +
        '</div>' +
      '</article>'
    );
  }

  function renderAnexoHtml(a) {
    var thumb;
    if (a.tipo === 'FOTO') {
      thumb = '<img src="' + escapeHtml(a.visualizar_url) + '" alt="' +
        escapeHtml(a.nome_original) + '" class="pos-venda-anexo-thumb" loading="lazy">';
    } else if (a.tipo === 'VIDEO') {
      thumb = '<div class="pos-venda-anexo-placeholder bg-dark text-white">' +
        '<i class="fas fa-film fa-2x"></i></div>';
    } else if (a.tipo === 'AUDIO') {
      thumb = '<div class="pos-venda-anexo-placeholder bg-info text-white">' +
        '<i class="fas fa-microphone fa-2x"></i></div>';
    } else {
      thumb = '<div class="pos-venda-anexo-placeholder bg-secondary text-white">' +
        '<i class="fas fa-file fa-2x"></i></div>';
    }
    return (
      '<div class="anexo-item pos-venda-anexo-item" data-anexo-id="' + a.id + '">' +
        '<a href="' + escapeHtml(a.visualizar_url) + '" target="_blank" ' +
          'class="d-block text-center text-decoration-none" title="' +
          escapeHtml(a.nome_original) + '">' +
          thumb +
          '<span class="d-block text-truncate small pos-venda-anexo-nome">' +
            escapeHtml(a.nome_original) +
          '</span>' +
        '</a>' +
        '<button type="button" ' +
          'class="btn-excluir-anexo pos-venda-anexo-excluir btn btn-sm btn-danger" ' +
          'title="Excluir anexo"><i class="fas fa-times"></i></button>' +
      '</div>'
    );
  }

  function adicionarOcorrenciaNaListagem(modalBody, oc) {
    var lista = modalBody.querySelector(
      '.lista-ocorrencias[data-categoria="' + oc.categoria + '"]'
    );
    if (!lista) return;
    var empty = lista.querySelector('.empty-msg');
    if (empty) empty.remove();
    lista.insertAdjacentHTML('afterbegin', renderOcorrenciaCard(oc));
  }

  function bindModalEvents() {
    var body = document.getElementById('modal-ocorrencias-body');
    if (!body) return;

    // Criar ocorrencia (submit do form .form-nova-ocorrencia)
    body.addEventListener('submit', function (e) {
      var form = e.target;
      if (form.classList.contains('form-nova-ocorrencia')) {
        e.preventDefault();
        var chassi = form.dataset.chassi;
        var categoria = form.dataset.categoria;
        var descricao = form.querySelector('[name="descricao"]').value.trim();
        if (!descricao) return;

        var btn = form.querySelector('button[type="submit"]');
        btn.disabled = true;
        fetch('/motos-assai/pos-venda/ocorrencias/' + encodeURIComponent(chassi), {
          method: 'POST',
          headers: jsonHeaders(),
          body: JSON.stringify({ categoria: categoria, descricao: descricao }),
        })
          .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
          .then(function (res) {
            if (!res.ok || !res.j.ok) {
              showAlert(body, 'Erro ao criar ocorrencia: ' + (res.j.erro || 'falha desconhecida'));
              return;
            }
            adicionarOcorrenciaNaListagem(body, res.j.ocorrencia);
            refrescarContadorCategoria(body, categoria, +1);
            refrescarBotaoListagem(chassi, +1);
            form.reset();
          })
          .catch(function (err) {
            showAlert(body, 'Erro de rede: ' + err.message);
          })
          .finally(function () { btn.disabled = false; });
        return;
      }

      // Upload de anexos
      if (form.classList.contains('form-upload-anexo')) {
        e.preventDefault();
        var ocId = form.dataset.ocorrenciaId;
        var input = form.querySelector('input[type="file"]');
        if (!input.files || input.files.length === 0) return;

        var fd = new FormData();
        for (var i = 0; i < input.files.length; i++) {
          fd.append('arquivos', input.files[i]);
        }
        var btn2 = form.querySelector('button[type="submit"]');
        btn2.disabled = true;
        fetch('/motos-assai/pos-venda/ocorrencias/' + ocId + '/anexos', {
          method: 'POST',
          headers: { 'X-CSRFToken': csrfToken() },
          body: fd,
        })
          .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
          .then(function (res) {
            if ((res.j.erros || []).length > 0) {
              var msgs = res.j.erros.map(function (e) { return e.arquivo + ': ' + e.erro; }).join('; ');
              showAlert(body, 'Alguns anexos falharam: ' + msgs, 'warning');
            }
            var card = form.closest('.ocorrencia-card');
            var grid = card && card.querySelector('.anexos-grid');
            if (grid) {
              (res.j.anexos || []).forEach(function (a) {
                grid.insertAdjacentHTML('beforeend', renderAnexoHtml(a));
              });
            }
            input.value = '';
          })
          .catch(function (err) {
            showAlert(body, 'Erro de rede: ' + err.message);
          })
          .finally(function () { btn2.disabled = false; });
        return;
      }
    });

    // Excluir ocorrencia / anexo (delegado)
    body.addEventListener('click', function (e) {
      var btnOc = e.target.closest('.btn-excluir-ocorrencia');
      if (btnOc) {
        var card = btnOc.closest('.ocorrencia-card');
        if (!card) return;
        if (!confirm('Excluir esta ocorrencia? Esta acao tambem remove os anexos.')) return;
        var ocId = card.dataset.ocorrenciaId;
        var categoria = card.dataset.categoria;
        var chassi = body.dataset.btnOrigemChassi;
        fetch('/motos-assai/pos-venda/ocorrencias/' + ocId, {
          method: 'DELETE',
          headers: { 'X-CSRFToken': csrfToken() },
        })
          .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
          .then(function (res) {
            if (!res.ok || !res.j.ok) {
              showAlert(body, 'Erro ao excluir: ' + (res.j.erro || ''));
              return;
            }
            card.remove();
            refrescarContadorCategoria(body, categoria, -1);
            if (chassi) refrescarBotaoListagem(chassi, -1);
          })
          .catch(function (err) { showAlert(body, 'Erro de rede: ' + err.message); });
        return;
      }

      var btnAn = e.target.closest('.btn-excluir-anexo');
      if (btnAn) {
        var item = btnAn.closest('.anexo-item');
        if (!item) return;
        if (!confirm('Excluir este anexo?')) return;
        var anexoId = item.dataset.anexoId;
        fetch('/motos-assai/pos-venda/anexos/' + anexoId, {
          method: 'DELETE',
          headers: { 'X-CSRFToken': csrfToken() },
        })
          .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
          .then(function (res) {
            if (!res.ok || !res.j.ok) {
              showAlert(body, 'Erro ao excluir anexo: ' + (res.j.erro || ''));
              return;
            }
            item.remove();
          })
          .catch(function (err) { showAlert(body, 'Erro de rede: ' + err.message); });
        return;
      }
    });
  }

  // -------------------------------------------------------------------------
  // Boot
  // -------------------------------------------------------------------------

  document.addEventListener('DOMContentLoaded', function () {
    // Botoes "Ocorrencias (N)" da listagem
    document.querySelectorAll('.btn-ocorrencias').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var chassi = btn.dataset.chassi;
        if (!chassi) return;
        abrirModalOcorrencias(chassi, btn);
      });
    });

    bindModalEvents();
  });
})();
