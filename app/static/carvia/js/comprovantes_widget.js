/* Widget de comprovantes de pagamento CarVia (cotacao/NF/CTe/fatura).
 *
 * Delegacao de eventos no document — suporta N widgets na mesma pagina com este
 * unico script incluido uma vez. Espelha anexos_widget.js.
 *
 * HTML esperado (gerado por carvia/_comprovantes_card.html):
 *  - <form class="carvia-comprovante-form" data-upload-url="..."> com input[name=arquivo]
 *  - <button class="carvia-comprovante-excluir" data-comprovante-id="..."> por comprovante
 *  - (opcional) <input class="carvia-cotacao-pago-toggle" type="checkbox"
 *               data-cotacao-id="..."> para a flag "Cotacao Paga"
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

    // ---- Upload: submit em qualquer .carvia-comprovante-form ----
    document.addEventListener('submit', function (e) {
        var form = e.target;
        if (!form || !form.classList || !form.classList.contains('carvia-comprovante-form')) {
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
                    alert((data && data.erro) || 'Erro ao enviar comprovante');
                    if (btn) { btn.disabled = false; btn.innerHTML = btnHtml; }
                }
            })
            .catch(function () {
                alert('Erro de conexao ao enviar comprovante');
                if (btn) { btn.disabled = false; btn.innerHTML = btnHtml; }
            });
    });

    // ---- Excluir: click em qualquer .carvia-comprovante-excluir ----
    document.addEventListener('click', function (e) {
        var btn = e.target.closest ? e.target.closest('.carvia-comprovante-excluir') : null;
        if (!btn) return;
        e.preventDefault();

        var compId = btn.getAttribute('data-comprovante-id');
        if (!compId) return;
        if (!confirm('Excluir este comprovante? (sera removido de todos os documentos da cadeia)')) return;

        btn.disabled = true;
        fetch('/carvia/api/comprovante/' + compId + '/excluir', {
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
                    alert((data && data.erro) || 'Erro ao excluir comprovante');
                    btn.disabled = false;
                }
            })
            .catch(function () {
                alert('Erro de conexao ao excluir comprovante');
                btn.disabled = false;
            });
    });

    // ---- Toggle "Cotacao Paga": change em qualquer .carvia-cotacao-pago-toggle ----
    document.addEventListener('change', function (e) {
        var chk = e.target;
        if (!chk || !chk.classList || !chk.classList.contains('carvia-cotacao-pago-toggle')) {
            return;
        }
        var cotacaoId = chk.getAttribute('data-cotacao-id');
        if (!cotacaoId) return;

        var fd = new FormData();
        fd.append('pago', chk.checked ? 'true' : 'false');
        chk.disabled = true;
        fetch('/carvia/api/cotacao/' + cotacaoId + '/marcar-pago', {
            method: 'POST',
            body: fd,
            headers: { 'X-CSRFToken': getCsrfToken(null) }
        })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                chk.disabled = false;
                if (!data || !data.sucesso) {
                    chk.checked = !chk.checked; // reverte
                    alert((data && data.erro) || 'Erro ao atualizar pagamento');
                }
            })
            .catch(function () {
                chk.disabled = false;
                chk.checked = !chk.checked;
                alert('Erro de conexao ao atualizar pagamento');
            });
    });
})();
