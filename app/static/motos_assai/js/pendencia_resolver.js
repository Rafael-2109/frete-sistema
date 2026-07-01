/* pendencia_resolver.js — tela /pendencias/<pid>/resolver (Spec 2 Task 7)
 *
 * Comportamento:
 *  - Ao mudar o radio "tratativa": mostra/esconde bloco de peca+qtd (USAR_ESTOQUE /
 *    USAR_OUTRA_MOTO) e bloco de chassi doador (USAR_OUTRA_MOTO).
 *  - Ao mudar peca ou quantidade: se qtd > saldo da peca selecionada, exibe
 *    #aviso-saldo (nao bloqueante). Form posta normalmente.
 */
(function () {
  'use strict';

  var TRATATIVAS_COM_PECA = ['USAR_ESTOQUE', 'USAR_OUTRA_MOTO'];
  var TRATATIVAS_COM_DOADOR = ['USAR_OUTRA_MOTO'];

  function getRadioTratativa() {
    var checked = document.querySelector('input[name="tratativa"]:checked');
    return checked ? checked.value : null;
  }

  function toggleBlocos() {
    var tratativa = getRadioTratativa();
    var blocoPeca = document.getElementById('bloco-peca');
    var blocoDoador = document.getElementById('bloco-doador');

    if (!blocoPeca) return;

    var comPeca = tratativa && TRATATIVAS_COM_PECA.indexOf(tratativa) !== -1;
    var comDoador = tratativa && TRATATIVAS_COM_DOADOR.indexOf(tratativa) !== -1;

    if (comPeca) {
      blocoPeca.classList.remove('d-none');
    } else {
      blocoPeca.classList.add('d-none');
      verificarSaldo(); // limpa aviso quando esconde
    }

    if (blocoDoador) {
      if (comDoador) {
        blocoDoador.classList.remove('d-none');
      } else {
        blocoDoador.classList.add('d-none');
      }
    }
  }

  function verificarSaldo() {
    var avisoEl = document.getElementById('aviso-saldo');
    if (!avisoEl) return;

    var selPeca = document.getElementById('sel-peca');
    var inpQtd = document.getElementById('inp-quantidade');

    // esconde se peca ou qtd nao selecionados ou bloco oculto
    var blocoPeca = document.getElementById('bloco-peca');
    if (!blocoPeca || blocoPeca.classList.contains('d-none')) {
      avisoEl.classList.add('d-none');
      return;
    }

    if (!selPeca || !inpQtd) {
      avisoEl.classList.add('d-none');
      return;
    }

    var selectedOption = selPeca.options[selPeca.selectedIndex];
    if (!selectedOption || !selectedOption.value) {
      avisoEl.classList.add('d-none');
      return;
    }

    var saldo = parseFloat(selectedOption.getAttribute('data-saldo') || '0');
    var qtd = parseFloat(inpQtd.value || '0');

    if (!isNaN(qtd) && !isNaN(saldo) && qtd > saldo) {
      avisoEl.classList.remove('d-none');
    } else {
      avisoEl.classList.add('d-none');
    }
  }

  // Wire eventos
  document.addEventListener('change', function (ev) {
    if (ev.target && ev.target.name === 'tratativa') {
      toggleBlocos();
    }
    if (ev.target && (ev.target.id === 'sel-peca' || ev.target.id === 'inp-quantidade')) {
      verificarSaldo();
    }
  });

  document.addEventListener('input', function (ev) {
    if (ev.target && ev.target.id === 'inp-quantidade') {
      verificarSaldo();
    }
  });

  // Estado inicial: esconde blocos (nenhum radio selecionado na carga)
  toggleBlocos();
})();
