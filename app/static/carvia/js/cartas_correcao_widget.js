/* Widget de Cartas de Correcao (CCe) CarVia (cotacao/NF).
 *
 * Delegacao de eventos no document — suporta N widgets na mesma pagina com este
 * unico script incluido uma vez. Espelha comprovantes_widget.js.
 *
 * HTML esperado (gerado por carvia/_cartas_correcao_card.html):
 *  - <form class="carvia-cce-form" data-upload-url="..."> com input[name=arquivo]
 *  - <button class="carvia-cce-excluir" data-carta-id="..."> por CCe
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

    // ---- Upload: submit em qualquer .carvia-cce-form ----
    document.addEventListener('submit', function (e) {
        var form = e.target;
        if (!form || !form.classList || !form.classList.contains('carvia-cce-form')) {
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
                    alert((data && data.erro) || 'Erro ao enviar CCe');
                    if (btn) { btn.disabled = false; btn.innerHTML = btnHtml; }
                }
            })
            .catch(function () {
                alert('Erro de conexao ao enviar CCe');
                if (btn) { btn.disabled = false; btn.innerHTML = btnHtml; }
            });
    });

    // ---- Excluir: click em qualquer .carvia-cce-excluir ----
    document.addEventListener('click', function (e) {
        var btn = e.target.closest ? e.target.closest('.carvia-cce-excluir') : null;
        if (!btn) return;
        e.preventDefault();

        var cartaId = btn.getAttribute('data-carta-id');
        if (!cartaId) return;
        if (!confirm('Excluir esta carta de correcao? (sera removida da cotacao e da NF da cadeia)')) return;

        btn.disabled = true;
        fetch('/carvia/api/carta-correcao/' + cartaId + '/excluir', {
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
                    alert((data && data.erro) || 'Erro ao excluir CCe');
                    btn.disabled = false;
                }
            })
            .catch(function () {
                alert('Erro de conexao ao excluir CCe');
                btn.disabled = false;
            });
    });
})();
