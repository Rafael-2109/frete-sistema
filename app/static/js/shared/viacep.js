/**
 * ViaCEP — Componente compartilhado de busca de CEP
 * ==================================================
 *
 * Auto-preenche endereco (logradouro, bairro, cidade, UF) a partir do CEP.
 * Usa a API publica ViaCEP (viacep.com.br).
 *
 * Uso basico (auto-init via data-cep-lookup):
 *   <input type="text" id="cep" data-cep-lookup
 *          data-cep-logradouro="#logradouro"
 *          data-cep-bairro="#bairro"
 *          data-cep-cidade="#cidade"
 *          data-cep-uf="#uf"
 *          data-cep-complemento="#complemento">
 *
 * Ou com botao dedicado:
 *   <input type="text" id="cep" data-cep-lookup>
 *   <button data-cep-trigger="#cep">Buscar CEP</button>
 *
 * Atributos:
 *   data-cep-lookup       : marca o input de CEP (obrigatorio)
 *   data-cep-logradouro   : selector do campo logradouro
 *   data-cep-bairro       : selector do campo bairro
 *   data-cep-cidade       : selector do campo cidade
 *   data-cep-uf           : selector do campo UF
 *   data-cep-complemento  : selector do campo complemento (preenche apenas se vazio)
 *   data-cep-trigger      : em um botao, aponta para o selector do input CEP
 *
 * O componente se auto-inicializa via DOMContentLoaded.
 */

(function () {
    'use strict';

    const VIACEP_URL = 'https://viacep.com.br/ws';
    const CEP_REGEX = /^\d{8}$/;

    function init() {
        // Auto-init: inputs com data-cep-lookup
        document.querySelectorAll('[data-cep-lookup]').forEach(attachCepLookup);

        // Botoes com data-cep-trigger
        document.querySelectorAll('[data-cep-trigger]').forEach(attachTriggerButton);
    }

    function attachCepLookup(input) {
        // Buscar ao sair do campo (blur) se CEP tem 8 digitos
        input.addEventListener('blur', function () {
            var cep = this.value.replace(/\D/g, '');
            if (CEP_REGEX.test(cep)) {
                buscarCep(this);
            }
        });

        // Buscar ao pressionar Enter
        input.addEventListener('keydown', function (e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                var cep = this.value.replace(/\D/g, '');
                if (CEP_REGEX.test(cep)) {
                    buscarCep(this);
                }
            }
        });

        // Mascara CEP (se jquery.mask disponivel)
        if (window.jQuery && jQuery.fn.mask) {
            jQuery(input).mask('00000-000');
        }
    }

    function attachTriggerButton(btn) {
        btn.addEventListener('click', function (e) {
            e.preventDefault();
            var selector = this.getAttribute('data-cep-trigger');
            var input = document.querySelector(selector);
            if (input) {
                buscarCep(input);
            }
        });
    }

    function buscarCep(input) {
        var cep = input.value.replace(/\D/g, '');
        if (!CEP_REGEX.test(cep)) {
            showFeedback(input, 'CEP deve ter 8 digitos.', 'error');
            return;
        }

        // Indicador de loading
        input.disabled = true;
        var originalPlaceholder = input.placeholder;
        input.placeholder = 'Buscando CEP...';

        fetch(VIACEP_URL + '/' + cep + '/json/')
            .then(function (r) { return r.json(); })
            .then(function (data) {
                input.disabled = false;
                input.placeholder = originalPlaceholder;

                if (data.erro) {
                    showFeedback(input, 'CEP nao encontrado.', 'error');
                    return;
                }

                // Preencher campos via data-cep-* selectors
                // ORDEM: UF primeiro (pode acionar cascade de cidades), depois cidade com delay
                fillField(input, 'data-cep-logradouro', data.logradouro);
                fillField(input, 'data-cep-bairro', data.bairro);
                fillField(input, 'data-cep-uf', data.uf);

                // Cidade com delay — se o alvo e um <select> populado por cascade,
                // precisa esperar o cascade carregar as opcoes
                var cidadeSelector = input.getAttribute('data-cep-cidade');
                if (cidadeSelector) {
                    var cidadeEl = document.querySelector(cidadeSelector);
                    if (cidadeEl && cidadeEl.tagName === 'SELECT') {
                        // Select cascading: tentar 3x com delay crescente
                        var tentativas = [300, 800, 1500];
                        tentativas.forEach(function(delay) {
                            setTimeout(function() {
                                setCidadeSelect(cidadeEl, data.localidade);
                            }, delay);
                        });
                    } else {
                        fillField(input, 'data-cep-cidade', data.localidade);
                    }
                }

                // Complemento: preenche apenas se campo esta vazio
                var complSelector = input.getAttribute('data-cep-complemento');
                if (complSelector) {
                    var complEl = document.querySelector(complSelector);
                    if (complEl && !complEl.value && data.complemento) {
                        complEl.value = data.complemento;
                        triggerChange(complEl);
                    }
                }

                showFeedback(input, 'Endereco preenchido!', 'success');
            })
            .catch(function (err) {
                input.disabled = false;
                input.placeholder = originalPlaceholder;
                showFeedback(input, 'Erro ao buscar CEP: ' + err.message, 'error');
            });
    }

    function setCidadeSelect(selectEl, cidade) {
        if (!selectEl || !cidade) return;
        var cidadeUpper = cidade.toUpperCase();
        // Tentar match exato e parcial nas opcoes disponiveis
        for (var i = 0; i < selectEl.options.length; i++) {
            var optText = selectEl.options[i].text.toUpperCase();
            var optVal = selectEl.options[i].value.toUpperCase();
            if (optText === cidadeUpper || optVal === cidadeUpper ||
                optText.indexOf(cidadeUpper) >= 0 || cidadeUpper.indexOf(optText) >= 0) {
                selectEl.selectedIndex = i;
                triggerChange(selectEl);
                return;
            }
        }
    }

    function fillField(cepInput, attr, value) {
        var selector = cepInput.getAttribute(attr);
        if (!selector) return;

        var el = document.querySelector(selector);
        if (!el) return;

        el.value = value || '';
        triggerChange(el);
    }

    function triggerChange(el) {
        el.dispatchEvent(new Event('change', { bubbles: true }));
        el.dispatchEvent(new Event('input', { bubbles: true }));
    }

    function showFeedback(input, msg, type) {
        // Usar toastr se disponivel
        if (window.toastr) {
            if (type === 'error') {
                toastr.warning(msg);
            } else {
                toastr.success(msg);
            }
            return;
        }

        // Fallback: feedback inline temporario
        var wrapper = input.parentElement;
        var existing = wrapper.querySelector('.viacep-feedback');
        if (existing) existing.remove();

        var feedback = document.createElement('small');
        feedback.className = 'viacep-feedback text-' + (type === 'error' ? 'danger' : 'success');
        feedback.textContent = msg;
        wrapper.appendChild(feedback);

        setTimeout(function () { feedback.remove(); }, 3000);
    }

    // Auto-init
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Expor para uso programatico
    window.ViaCEP = { buscarCep: buscarCep, init: init };
})();
