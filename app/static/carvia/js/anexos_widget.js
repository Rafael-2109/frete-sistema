/* Widget de anexos polimorficos CarVia (Frete + Subcontrato).
 *
 * Usa delegacao de eventos no document, portanto suporta N widgets na mesma
 * pagina (1 frete + N subcontratos) com este unico script incluido uma vez.
 *
 * HTML esperado (gerado por carvia/_anexos_card.html):
 *  - <form class="carvia-anexo-form" data-upload-url="..."> com input[name=arquivo]
 *  - <button class="carvia-anexo-excluir" data-anexo-id="..."> por anexo
 *
 * CSRF: lido do <meta name="csrf-token"> (base.html) com fallback no input do form.
 */
(function () {
    'use strict';

    function getCsrfToken(form) {
        if (form) {
            var input = form.querySelector('input[name="csrf_token"]');
            if (input && input.value) return input.value;
        }
        var meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute('content') : '';
    }

    // ---- Upload: submit em qualquer .carvia-anexo-form ----
    document.addEventListener('submit', function (e) {
        var form = e.target;
        if (!form || !form.classList || !form.classList.contains('carvia-anexo-form')) {
            return;
        }
        e.preventDefault();

        var url = form.getAttribute('data-upload-url');
        if (!url) {
            alert('URL de upload nao configurada.');
            return;
        }

        var btn = form.querySelector('button[type="submit"]');
        var btnHtml = btn ? btn.innerHTML : '';
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        }

        fetch(url, {
            method: 'POST',
            body: new FormData(form),
            headers: { 'X-CSRFToken': getCsrfToken(form) }
        })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data && data.sucesso) {
                    location.reload();
                } else {
                    alert((data && data.erro) || 'Erro ao enviar anexo');
                    if (btn) { btn.disabled = false; btn.innerHTML = btnHtml; }
                }
            })
            .catch(function () {
                alert('Erro de conexao ao enviar anexo');
                if (btn) { btn.disabled = false; btn.innerHTML = btnHtml; }
            });
    });

    // ---- Excluir: click em qualquer .carvia-anexo-excluir ----
    document.addEventListener('click', function (e) {
        var btn = e.target.closest ? e.target.closest('.carvia-anexo-excluir') : null;
        if (!btn) return;
        e.preventDefault();

        var anexoId = btn.getAttribute('data-anexo-id');
        if (!anexoId) return;
        if (!confirm('Excluir este anexo?')) return;

        btn.disabled = true;
        fetch('/carvia/api/anexo/' + anexoId + '/excluir', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken(null)
            }
        })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data && data.sucesso) {
                    location.reload();
                } else {
                    alert((data && data.erro) || 'Erro ao excluir anexo');
                    btn.disabled = false;
                }
            })
            .catch(function () {
                alert('Erro de conexao ao excluir anexo');
                btn.disabled = false;
            });
    });
})();
