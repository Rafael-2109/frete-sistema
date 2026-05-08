// app/static/onboarding/core/tour_engine.js
(function (window) {
  'use strict';

  var registry = {};

  function isPermVisible(req) {
    if (!req) return true;
    var ctx = window.OnboardingContext || {};
    if (ctx.is_admin) return true;
    if (!ctx.permissoes) return false;
    var modulo = req.modulo;
    var acao = req.acao;
    return ctx.permissoes[modulo] && ctx.permissoes[modulo][acao] === true;
  }

  function isVisible(tour) {
    var ctx = window.OnboardingContext || {};
    if (tour.adminOnly && !ctx.is_admin) return false;
    return isPermVisible(tour.requirePerm);
  }

  function filterSteps(steps) {
    var ctx = window.OnboardingContext || {};
    return steps.filter(function (s) {
      if (s.adminOnly && !ctx.is_admin) return false;
      return isPermVisible(s.requirePerm);
    }).filter(function (s) {
      return document.querySelector(s.element);
    });
  }

  function routeMatches(pattern, currentPath) {
    if (!pattern) return false;
    var escaped = pattern.replace(/[.+?^${}()|[\]\\]/g, '\\$&');
    var glob = escaped.replace(/\*/g, '[^/]+');
    var re = new RegExp('^' + glob + '/?$');
    return re.test(currentPath);
  }

  function buildDriverSteps(steps) {
    return steps.map(function (s) {
      return {
        element: s.element,
        popover: {
          title: s.title || '',
          description: s.description || '',
          side: s.side || 'auto'
        }
      };
    });
  }

  window.OnboardingEngine = {
    register: function (tour) {
      registry[tour.id] = tour;
    },
    isVisible: function (tourId) {
      var t = registry[tourId];
      return t ? isVisible(t) : false;
    },
    listForCurrentRoute: function () {
      var path = window.location.pathname;
      var out = [];
      for (var id in registry) {
        var t = registry[id];
        if (!isVisible(t)) continue;
        if (!routeMatches(t.autoStartRoute, path)) continue;
        // Defesa: nao listar tour sem ao menos 1 step com elemento visivel
        // (selector quebrado, IDs faltando, etc.) — evita usuario clicar e
        // o tour abortar com warning silencioso.
        if (filterSteps(t.steps).length === 0) continue;
        out.push({ id: id, titulo: t.titulo });
      }
      return out;
    },
    listAllVisible: function () {
      var out = [];
      for (var id in registry) {
        if (isVisible(registry[id])) {
          out.push({ id: id, titulo: registry[id].titulo });
        }
      }
      return out;
    },
    start: function (tourId) {
      var t = registry[tourId];
      if (!t || !isVisible(t)) return false;
      var steps = filterSteps(t.steps);
      if (steps.length === 0) {
        console.warn('[onboarding] Tour ' + tourId + ' sem passos visiveis (selectors faltam?)');
        return false;
      }
      var foiPulado = false;
      var d = window.driver.js.driver({
        showProgress: true,
        progressText: 'Passo {{current}} de {{total}}',
        nextBtnText: 'Proximo →',
        prevBtnText: '← Anterior',
        doneBtnText: 'Concluir',
        showButtons: ['next', 'previous', 'close'],
        steps: buildDriverSteps(steps),
        onCloseClick: function () {
          foiPulado = true;
          d.destroy();
        },
        onDestroyed: function () {
          window.OnboardingTracker.markSeen(tourId, foiPulado ? 'pulou' : 'visto');
          if (t.onFinish) t.onFinish();
        }
      });
      d.drive();
      return true;
    },
    autoStartIfFirstVisit: function () {
      var path = window.location.pathname;
      for (var id in registry) {
        var t = registry[id];
        if (!isVisible(t)) continue;
        if (!routeMatches(t.autoStartRoute, path)) continue;
        if (window.OnboardingTracker.wasSeen(id)) continue;
        window.OnboardingEngine.start(id);
        return id;
      }
      return null;
    },
    _registry: registry
  };

  document.addEventListener('DOMContentLoaded', function () {
    setTimeout(function () {
      window.OnboardingEngine.autoStartIfFirstVisit();
    }, 250);
  });
})(window);
