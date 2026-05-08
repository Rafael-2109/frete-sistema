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

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function render(btn) {
    var modulo = moduloAtual();
    if (!modulo) return;

    var paraTela = window.OnboardingEngine.listForCurrentRoute();
    var todos = window.OnboardingEngine.listAllVisible();

    var html = '<div class="onboarding-dropdown-menu">';

    if (paraTela.length > 0) {
      html += '<div class="onboarding-dropdown-section">';
      html += '<div class="onboarding-dropdown-header"><i class="fas fa-bullseye"></i> Tour desta tela</div>';
      paraTela.forEach(function (t) {
        html += '<a class="onboarding-dropdown-item onboarding-highlight" href="#" data-tour="' + escapeHtml(t.id) + '">';
        html += '<i class="fas fa-play-circle"></i> ' + escapeHtml(t.titulo);
        html += '</a>';
      });
      html += '</div>';
    } else {
      html += '<div class="onboarding-dropdown-section onboarding-dropdown-info">';
      html += '<i class="fas fa-info-circle"></i> Esta tela ainda nao tem tour proprio.';
      html += '</div>';
    }

    html += '<div class="onboarding-dropdown-section">';
    html += '<div class="onboarding-dropdown-header"><i class="fas fa-list"></i> Tours de ' + escapeHtml(moduloLabel(modulo)) + '</div>';
    var demais = todos.filter(function (t) {
      return !paraTela.some(function (pt) { return pt.id === t.id; });
    });
    if (demais.length === 0) {
      html += '<div class="onboarding-dropdown-info-light">Nenhum outro tour disponivel.</div>';
    } else {
      demais.forEach(function (t) {
        html += '<a class="onboarding-dropdown-item" href="#" data-tour="' + escapeHtml(t.id) + '">';
        html += escapeHtml(t.titulo);
        html += '</a>';
      });
    }
    html += '</div>';

    html += '<div class="onboarding-dropdown-section onboarding-dropdown-footer">';
    html += '<a class="onboarding-dropdown-item onboarding-reset" href="#" data-reset="' + escapeHtml(modulo) + '">';
    html += '<i class="fas fa-redo"></i> Resetar tours vistos';
    html += '</a>';
    html += '</div>';

    html += '</div>';

    closeExisting();

    // Append direto ao body (escapa qualquer stacking context isolado por
    // ancestor com transform/filter/will-change). O wrapper e meramente
    // um container para event delegation e cleanup.
    var wrapper = document.createElement('div');
    wrapper.id = 'onboarding-dropdown';
    wrapper.innerHTML = html;
    // Estilos do wrapper aplicados via !important para vencer qualquer CSS
    // residual de modulos (ex: motos_assai/_motochefe usa z-index 9999).
    wrapper.style.setProperty('position', 'fixed', 'important');
    wrapper.style.setProperty('z-index', '2147483647', 'important'); // max int32
    wrapper.style.setProperty('top', '0', 'important');
    wrapper.style.setProperty('left', '0', 'important');
    wrapper.style.setProperty('width', '0', 'important');
    wrapper.style.setProperty('height', '0', 'important');
    wrapper.style.setProperty('pointer-events', 'none', 'important');
    document.body.appendChild(wrapper);

    // posicionar o menu fixed relativo ao botao (dentro da viewport)
    var rect = btn.getBoundingClientRect();
    var menu = wrapper.firstElementChild;
    menu.style.setProperty('position', 'fixed', 'important');
    menu.style.setProperty('z-index', '2147483647', 'important');
    menu.style.setProperty('top', (rect.bottom + 6) + 'px', 'important');
    var rightOffset = window.innerWidth - rect.right;
    if (rightOffset < 10) rightOffset = 10;
    menu.style.setProperty('right', rightOffset + 'px', 'important');
    menu.style.setProperty('left', 'auto', 'important');
    menu.style.setProperty('pointer-events', 'auto', 'important');

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
      closeExisting();
    });

    var closeListener = function (e) {
      if (!wrapper.contains(e.target) && e.target !== btn && !btn.contains(e.target)) {
        closeExisting();
      }
    };
    wrapper._closeListener = closeListener;
    setTimeout(function () {
      document.addEventListener('click', closeListener);
    }, 100);
  }

  function closeExisting() {
    var existing = document.getElementById('onboarding-dropdown');
    if (!existing) return;
    if (existing._closeListener) {
      document.removeEventListener('click', existing._closeListener);
    }
    existing.remove();
  }

  function injectStyles() {
    if (document.getElementById('onboarding-dropdown-styles')) return;
    var css = ''
      + '#onboarding-dropdown { z-index: 2147483647 !important; }'
      + '#onboarding-dropdown .onboarding-dropdown-menu {'
      + '  background: #fff; border: 1px solid #d4d4d4; border-radius: 10px;'
      + '  box-shadow: 0 12px 32px rgba(0,0,0,0.18); min-width: 280px; max-width: 360px;'
      + '  z-index: 2147483647 !important; padding: 0; overflow: hidden;'
      + '  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;'
      + '  font-size: 14px; color: #2d2d2d;'
      + '}'
      + '#onboarding-dropdown .onboarding-dropdown-section {'
      + '  border-bottom: 1px solid #efefef; padding: 8px 0;'
      + '}'
      + '#onboarding-dropdown .onboarding-dropdown-section:last-child { border-bottom: none; }'
      + '#onboarding-dropdown .onboarding-dropdown-header {'
      + '  font-size: 11px; font-weight: 700; text-transform: uppercase;'
      + '  color: #6c6c6c; padding: 4px 14px 6px; letter-spacing: 0.4px;'
      + '}'
      + '#onboarding-dropdown .onboarding-dropdown-header i { margin-right: 6px; color: #0d6efd; }'
      + '#onboarding-dropdown .onboarding-dropdown-item {'
      + '  display: block; padding: 8px 14px; color: #2d2d2d; text-decoration: none;'
      + '  transition: background 120ms;'
      + '}'
      + '#onboarding-dropdown .onboarding-dropdown-item:hover {'
      + '  background: #f0f7ff; color: #0d6efd;'
      + '}'
      + '#onboarding-dropdown .onboarding-dropdown-item i { margin-right: 8px; }'
      + '#onboarding-dropdown .onboarding-highlight {'
      + '  background: linear-gradient(90deg, #fff8e1, #fff);'
      + '  font-weight: 600; border-left: 3px solid #ffc107;'
      + '}'
      + '#onboarding-dropdown .onboarding-highlight:hover { background: #fff3cd; }'
      + '#onboarding-dropdown .onboarding-highlight i { color: #ffc107; }'
      + '#onboarding-dropdown .onboarding-dropdown-info {'
      + '  padding: 12px 14px; font-style: italic; color: #6c6c6c; background: #f8f9fa;'
      + '}'
      + '#onboarding-dropdown .onboarding-dropdown-info-light {'
      + '  padding: 6px 14px; font-size: 13px; color: #888; font-style: italic;'
      + '}'
      + '#onboarding-dropdown .onboarding-dropdown-footer {'
      + '  background: #f8f9fa;'
      + '}'
      + '#onboarding-dropdown .onboarding-reset {'
      + '  color: #b02a37; font-size: 13px;'
      + '}'
      + '#onboarding-dropdown .onboarding-reset:hover {'
      + '  background: #f8d7da; color: #842029;'
      + '}'
      + '[data-bs-theme="dark"] #onboarding-dropdown .onboarding-dropdown-menu {'
      + '  background: #2b2b2b; border-color: #444; color: #e8e8e8;'
      + '}'
      + '[data-bs-theme="dark"] #onboarding-dropdown .onboarding-dropdown-section {'
      + '  border-bottom-color: #3a3a3a;'
      + '}'
      + '[data-bs-theme="dark"] #onboarding-dropdown .onboarding-dropdown-header { color: #a8a8a8; }'
      + '[data-bs-theme="dark"] #onboarding-dropdown .onboarding-dropdown-item { color: #e8e8e8; }'
      + '[data-bs-theme="dark"] #onboarding-dropdown .onboarding-dropdown-item:hover { background: #3a3a3a; color: #6cf; }'
      + '[data-bs-theme="dark"] #onboarding-dropdown .onboarding-highlight { background: linear-gradient(90deg, #3a3220, #2b2b2b); }'
      + '[data-bs-theme="dark"] #onboarding-dropdown .onboarding-dropdown-info, '
      + '[data-bs-theme="dark"] #onboarding-dropdown .onboarding-dropdown-footer { background: #232323; }'
      + '[data-bs-theme="dark"] #onboarding-dropdown .onboarding-dropdown-info-light { color: #a8a8a8; }'
      ;
    var style = document.createElement('style');
    style.id = 'onboarding-dropdown-styles';
    style.textContent = css;
    document.head.appendChild(style);
  }

  document.addEventListener('DOMContentLoaded', function () {
    injectStyles();
    var btn = document.getElementById('help-button');
    if (!btn) return;
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      e.stopPropagation();
      var existing = document.getElementById('onboarding-dropdown');
      if (existing) {
        closeExisting();
        return;
      }
      render(btn);
    });
  });
})(window);
