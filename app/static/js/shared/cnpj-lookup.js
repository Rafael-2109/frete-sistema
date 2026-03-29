/**
 * CNPJ Lookup — Componente compartilhado de consulta ReceitaWS
 * =============================================================
 *
 * Auto-preenche dados da empresa a partir do CNPJ via ReceitaWS.
 * Preenche: razao social, fantasia, logradouro, bairro, cidade, UF, CEP, telefone, email.
 *
 * Uso (auto-init via data-cnpj-lookup):
 *
 *   <input type="text" id="cnpj" name="cnpj"
 *          data-cnpj-lookup
 *          data-cnpj-razao="#razao_social"
 *          data-cnpj-fantasia="#fantasia"
 *          data-cnpj-logradouro="#logradouro"
 *          data-cnpj-bairro="#bairro"
 *          data-cnpj-cidade="#cidade"
 *          data-cnpj-uf="#uf"
 *          data-cnpj-cep="#cep"
 *          data-cnpj-telefone="#telefone"
 *          data-cnpj-email="#email">
 *
 * Ou com botao dedicado:
 *   <button data-cnpj-trigger="#cnpj">Consultar CNPJ</button>
 *
 * Atributos:
 *   data-cnpj-lookup     : marca o input de CNPJ (obrigatorio)
 *   data-cnpj-razao      : selector do campo razao social
 *   data-cnpj-fantasia   : selector do campo nome fantasia
 *   data-cnpj-logradouro : selector do campo logradouro
 *   data-cnpj-bairro     : selector do campo bairro
 *   data-cnpj-cidade     : selector do campo cidade
 *   data-cnpj-uf         : selector do campo UF
 *   data-cnpj-cep        : selector do campo CEP
 *   data-cnpj-telefone   : selector do campo telefone
 *   data-cnpj-email      : selector do campo email
 *   data-cnpj-trigger    : em um botao, aponta para o selector do input CNPJ
 *   data-cnpj-api        : URL da API (default: /transportadoras/api/consultar-cnpj/)
 *
 * O componente se auto-inicializa via DOMContentLoaded.
 */

(function () {
    'use strict';

    var DEFAULT_API = '/transportadoras/api/consultar-cnpj/';

    function init() {
        document.querySelectorAll('[data-cnpj-lookup]').forEach(attachLookup);
        document.querySelectorAll('[data-cnpj-trigger]').forEach(attachTrigger);
    }

    function attachLookup(input) {
        // Consultar ao sair do campo se CNPJ tem 14 digitos
        input.addEventListener('blur', function () {
            var cnpj = this.value.replace(/\D/g, '');
            if (cnpj.length === 14) {
                consultarCnpj(this);
            }
        });
    }

    function attachTrigger(btn) {
        btn.addEventListener('click', function (e) {
            e.preventDefault();
            var selector = this.getAttribute('data-cnpj-trigger');
            var input = document.querySelector(selector);
            if (input) {
                consultarCnpj(input);
            }
        });
    }

    function consultarCnpj(input) {
        var cnpj = input.value.replace(/\D/g, '');
        if (cnpj.length !== 14) {
            showFeedback('CNPJ deve ter 14 digitos.', 'error');
            return;
        }

        var apiUrl = input.getAttribute('data-cnpj-api') || DEFAULT_API;

        // Indicador de loading
        input.disabled = true;
        var originalBg = input.style.background;
        input.style.background = 'var(--bg-light, #f8f9fa)';

        fetch(apiUrl + cnpj, {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                input.disabled = false;
                input.style.background = originalBg;

                if (!data.success) {
                    showFeedback(data.message || 'CNPJ nao encontrado.', 'error');
                    return;
                }

                var d = data.dados;
                var fieldMap = {
                    'data-cnpj-razao': d.razao_social,
                    'data-cnpj-fantasia': d.fantasia,
                    'data-cnpj-logradouro': d.logradouro,
                    'data-cnpj-bairro': d.bairro,
                    'data-cnpj-cidade': d.cidade,
                    'data-cnpj-uf': d.uf,
                    'data-cnpj-cep': d.cep,
                    'data-cnpj-telefone': d.telefone,
                    'data-cnpj-email': d.email,
                };

                for (var attr in fieldMap) {
                    if (fieldMap.hasOwnProperty(attr)) {
                        fillField(input, attr, fieldMap[attr]);
                    }
                }

                showFeedback('Dados preenchidos!', 'success');
            })
            .catch(function (err) {
                input.disabled = false;
                input.style.background = originalBg;
                showFeedback('Erro ao consultar CNPJ: ' + err.message, 'error');
            });
    }

    function fillField(cnpjInput, attr, value) {
        var selector = cnpjInput.getAttribute(attr);
        if (!selector || !value) return;

        var el = document.querySelector(selector);
        if (!el) return;

        el.value = value;
        el.dispatchEvent(new Event('change', { bubbles: true }));
        el.dispatchEvent(new Event('input', { bubbles: true }));
    }

    function showFeedback(msg, type) {
        if (window.toastr) {
            type === 'error' ? toastr.warning(msg) : toastr.success(msg);
        }
    }

    // Auto-init
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    window.CnpjLookup = { consultarCnpj: consultarCnpj, init: init };
})();
