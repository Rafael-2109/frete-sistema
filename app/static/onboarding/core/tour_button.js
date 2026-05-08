// app/static/onboarding/core/tour_button.js
(function (window) {
  'use strict';

  function moduloAtual() {
    var path = window.location.pathname;
    if (path.indexOf('/hora') === 0) return 'hora';
    if (path.indexOf('/motos-assai') === 0) return 'motos_assai';
    return null;
  }

  function moduloLabel(m) {
    return m === 'hora' ? 'Lojas HORA' : 'Motos Assai';
  }

  function render(btn) {
    var modulo = moduloAtual();
    if (!modulo) return;

    var paraTela = window.OnboardingEngine.listForCurrentRoute();
    var todos = window.OnboardingEngine.listAllVisible();

    var html = '<ul class="dropdown-menu show" style="position:absolute;right:0;display:block;">';
    if (paraTela.length > 0) {
      html += '<li><h6 class="dropdown-header">Tour da pagina atual</h6></li>';
      paraTela.forEach(function (t) {
        html += '<li><a class="dropdown-item" href="#" data-tour="' + t.id + '">' + t.titulo + '</a></li>';
      });
      html += '<li><hr class="dropdown-divider"></li>';
    }
    html += '<li><h6 class="dropdown-header">Todos os tours de ' + moduloLabel(modulo) + '</h6></li>';
    todos.forEach(function (t) {
      html += '<li><a class="dropdown-item" href="#" data-tour="' + t.id + '">' + t.titulo + '</a></li>';
    });
    html += '<li><hr class="dropdown-divider"></li>';
    html += '<li><a class="dropdown-item text-danger" href="#" data-reset="' + modulo + '">Resetar tours vistos</a></li>';
    html += '</ul>';

    var existing = document.getElementById('onboarding-dropdown');
    if (existing) existing.remove();

    var wrapper = document.createElement('div');
    wrapper.id = 'onboarding-dropdown';
    wrapper.style.cssText = 'position:relative;display:inline-block;';
    wrapper.innerHTML = html;
    btn.parentNode.insertBefore(wrapper, btn.nextSibling);

    wrapper.addEventListener('click', function (e) {
      var a = e.target.closest('a');
      if (!a) return;
      e.preventDefault();
      if (a.dataset.tour) {
        window.OnboardingEngine.start(a.dataset.tour);
      } else if (a.dataset.reset) {
        var n = window.OnboardingTracker.resetModule(a.dataset.reset);
        alert(n + ' tours marcados como nao-vistos. Recarregue a pagina para ver os tours automaticos.');
      }
      wrapper.remove();
    });

    setTimeout(function () {
      document.addEventListener('click', function close(e) {
        if (!wrapper.contains(e.target) && e.target !== btn) {
          wrapper.remove();
          document.removeEventListener('click', close);
        }
      });
    }, 100);
  }

  document.addEventListener('DOMContentLoaded', function () {
    var btn = document.getElementById('help-button');
    if (!btn) return;
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      e.stopPropagation();
      var existing = document.getElementById('onboarding-dropdown');
      if (existing) {
        existing.remove();
        return;
      }
      render(btn);
    });
  });
})(window);
