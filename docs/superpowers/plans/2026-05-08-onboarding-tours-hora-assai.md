<!-- doc:meta
tipo: how-to
camada: L3
sot_de: —
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-02
-->
# Onboarding Tours HORA + Motos Assaí — Implementation Plan

> **Papel:** Onboarding Tours HORA + Motos Assaí — Implementation Plan.

## Indice

- [File Structure](#file-structure)
- [Task 1: Foundation — self-host library + core engine](#task-1-foundation-self-host-library-core-engine)
- [Task 2: Endpoint `/api/onboarding/permissoes-matriz` com testes](#task-2-endpoint-apionboardingpermissoes-matriz-com-testes)
- [Task 3: Injetar context + scripts no `app/templates/hora/base.html` + IDs no menu](#task-3-injetar-context-scripts-no-apptemplateshorabasehtml-ids-no-menu)
- [Task 4: Injetar context + scripts no `base_motos_assai.html` + IDs no menu](#task-4-injetar-context-scripts-no-base_motos_assaihtml-ids-no-menu)
- [Task 5: Tour macro HORA (`_macro.js`)](#task-5-tour-macro-hora-_macrojs)
- [Task 6: Tour macro Motos Assaí (`_macro.js`)](#task-6-tour-macro-motos-assaí-_macrojs)
- [Task 7: Mini-tour HORA `recebimento_nf`](#task-7-mini-tour-hora-recebimento_nf)
- [Task 8: Mini-tour HORA `venda_manual_nova`](#task-8-mini-tour-hora-venda_manual_nova)
- [Task 9: Mini-tour HORA `transferencia_nova`](#task-9-mini-tour-hora-transferencia_nova)
- [Task 10: Mini-tour Motos Assaí `recebimento_wizard`](#task-10-mini-tour-motos-assaí-recebimento_wizard)
- [Task 11: Mini-tours Assaí operação chão (`montagem_quick`, `disponibilizar_quick`, `separacao_chassi`)](#task-11-mini-tours-assaí-operação-chão-montagem_quick-disponibilizar_quick-separacao_chassi)
- [Task 12: Mini-tours HORA admin pacote 1 (`vendas_aprovar`, `devolucao_venda`, `estoque_lista`, `avaria_nova`)](#task-12-mini-tours-hora-admin-pacote-1-vendas_aprovar-devolucao_venda-estoque_lista-avaria_nova)
- [Task 13: Mini-tours HORA admin pacote 2 (`pecas_estoque`, `modelos_novo`, `modelos_pendencias`, `modelos_unificar`)](#task-13-mini-tours-hora-admin-pacote-2-pecas_estoque-modelos_novo-modelos_pendencias-modelos_unificar)
- [Task 14: Mini-tours HORA admin pacote 3 (`tagplus_conta`, `permissoes`)](#task-14-mini-tours-hora-admin-pacote-3-tagplus_conta-permissoes)
- [Task 15: Mini-tours Motos Assaí admin (`pedidos_upload`, `compras_nova`, `recibos_upload`, `faturamento`, `modelos_assai`)](#task-15-mini-tours-motos-assaí-admin-pedidos_upload-compras_nova-recibos_upload-faturamento-modelos_assai)
- [Task 16: Página `/admin/onboarding/health`](#task-16-página-adminonboardinghealth)
- [Task 17: Página `/admin/onboarding/preview`](#task-17-página-adminonboardingpreview)
- [Task 18: Microcopy review + smoke test mobile real + cleanup](#task-18-microcopy-review-smoke-test-mobile-real-cleanup)
- [Self-Review](#self-review)
- [Execução](#execução)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar guided tour in-app (Driver.js) para os módulos `app/hora/` e `app/motos_assai/` com macro adaptativo + mini-tours por tela crítica, filtrados por permissão (HORA) ou flag admin (Assaí).

**Architecture:** JS estático self-hosted. 1 macro adaptativo por módulo + N mini-tours, registrados via `OnboardingEngine` global. Filtragem client-side via `OnboardingContext` injetado no `base.html`. Persistência em `localStorage` por `user_id+tour_id`.

**Tech Stack:** Driver.js 1.3.x (MIT, ~5KB gzip, self-hosted), Bootstrap 5 (já no projeto), Flask + Jinja2 + SQLAlchemy (server-side rendering existente), pytest (testes do endpoint matriz).

**Spec:** `docs/superpowers/specs/2026-05-08-onboarding-tours-hora-assai-design.md`

---

## File Structure

**Created:**
- `app/static/onboarding/lib/driver.min.js` — library self-hosted
- `app/static/onboarding/lib/driver.css` — estilos da library
- `app/static/onboarding/core/tour_engine.js` — wrapper sobre Driver.js (register/start/isVisible)
- `app/static/onboarding/core/localstorage_tracker.js` — get/set/reset com user_id namespace
- `app/static/onboarding/core/tour_button.js` — dropdown "?" no header
- `app/static/onboarding/tours/hora/_macro.js`
- `app/static/onboarding/tours/hora/<13 mini-tours>.js`
- `app/static/onboarding/tours/motos_assai/_macro.js`
- `app/static/onboarding/tours/motos_assai/<9 mini-tours>.js`
- `app/api/__init__.py` (se não existir) e `app/api/onboarding.py` — endpoint matriz
- `tests/api/test_onboarding_routes.py`
- `app/templates/admin/onboarding_health.html`
- `app/templates/admin/onboarding_preview.html`

**Modified:**
- `app/templates/hora/base.html` — injeta context + scripts core + IDs no menu
- `app/templates/motos_assai/base_motos_assai.html` — idem
- `app/templates/hora/dashboard.html` — `{% block onboarding_tours %}` para incluir _macro.js
- `app/templates/motos_assai/dashboard.html` — idem
- ~22 templates HORA + Assaí — adicionar IDs nos elementos alvo + bloco onboarding_tours
- `app/__init__.py` — registrar `app/api/onboarding.py` blueprint

---

## Task 1: Foundation — self-host library + core engine

**Files:**
- Create: `app/static/onboarding/lib/driver.min.js`
- Create: `app/static/onboarding/lib/driver.css`
- Create: `app/static/onboarding/core/tour_engine.js`
- Create: `app/static/onboarding/core/localstorage_tracker.js`
- Create: `app/static/onboarding/core/tour_button.js`

- [ ] **Step 1: Baixar Driver.js 1.3.1 self-hosted**

```bash
mkdir -p app/static/onboarding/lib
mkdir -p app/static/onboarding/core
mkdir -p app/static/onboarding/tours/hora
mkdir -p app/static/onboarding/tours/motos_assai
curl -sL https://cdn.jsdelivr.net/npm/driver.js@1.3.1/dist/driver.js.iife.js -o app/static/onboarding/lib/driver.min.js
curl -sL https://cdn.jsdelivr.net/npm/driver.js@1.3.1/dist/driver.css -o app/static/onboarding/lib/driver.css
ls -lh app/static/onboarding/lib/
```

Expected: 2 arquivos (~10KB driver.min.js + ~6KB driver.css).

- [ ] **Step 2: Criar `localstorage_tracker.js`**

```javascript
// app/static/onboarding/core/localstorage_tracker.js
(function (window) {
  'use strict';

  function key(modulo, tourId, userId) {
    return 'onboarding.' + modulo + '.' + tourId + '.u' + userId;
  }

  function getUserId() {
    return (window.OnboardingContext && window.OnboardingContext.user_id) || 0;
  }

  function moduloFromTourId(tourId) {
    var idx = tourId.indexOf('.');
    return idx > 0 ? tourId.substring(0, idx) : tourId;
  }

  window.OnboardingTracker = {
    wasSeen: function (tourId) {
      var userId = getUserId();
      var modulo = moduloFromTourId(tourId);
      var v = window.localStorage.getItem(key(modulo, tourId, userId));
      return v === 'visto' || v === 'pulou';
    },
    markSeen: function (tourId, status) {
      var userId = getUserId();
      var modulo = moduloFromTourId(tourId);
      window.localStorage.setItem(key(modulo, tourId, userId), status || 'visto');
    },
    resetModule: function (modulo) {
      var userId = getUserId();
      var prefix = 'onboarding.' + modulo + '.';
      var suffix = '.u' + userId;
      var toRemove = [];
      for (var i = 0; i < window.localStorage.length; i++) {
        var k = window.localStorage.key(i);
        if (k.indexOf(prefix) === 0 && k.indexOf(suffix) === k.length - suffix.length) {
          toRemove.push(k);
        }
      }
      toRemove.forEach(function (k) { window.localStorage.removeItem(k); });
      return toRemove.length;
    }
  };
})(window);
```

- [ ] **Step 3: Criar `tour_engine.js`**

```javascript
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
    var glob = pattern.replace(/\*/g, '[^/]+');
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
        if (routeMatches(t.autoStartRoute, path)) {
          out.push({ id: id, titulo: t.titulo });
        }
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
    start: function (tourId, opts) {
      opts = opts || {};
      var t = registry[tourId];
      if (!t || !isVisible(t)) return false;
      var steps = filterSteps(t.steps);
      if (steps.length === 0) {
        console.warn('[onboarding] Tour ' + tourId + ' sem passos visíveis (selectors faltam?)');
        return false;
      }
      var d = window.driver.js.driver({
        showProgress: true,
        progressText: 'Passo {{current}} de {{total}}',
        nextBtnText: 'Próximo →',
        prevBtnText: '← Anterior',
        doneBtnText: 'Concluir',
        showButtons: ['next', 'previous', 'close'],
        steps: buildDriverSteps(steps),
        onDestroyed: function () {
          window.OnboardingTracker.markSeen(tourId, opts.skipped ? 'pulou' : 'visto');
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
    }
  };

  document.addEventListener('DOMContentLoaded', function () {
    setTimeout(function () {
      window.OnboardingEngine.autoStartIfFirstVisit();
    }, 250);
  });
})(window);
```

- [ ] **Step 4: Criar `tour_button.js`**

```javascript
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
    return m === 'hora' ? 'Lojas HORA' : 'Motos Assaí';
  }

  function render(btn) {
    var modulo = moduloAtual();
    if (!modulo) return;

    var paraTela = window.OnboardingEngine.listForCurrentRoute();
    var todos = window.OnboardingEngine.listAllVisible();

    var html = '<ul class="dropdown-menu show" style="position:absolute;right:0;">';
    if (paraTela.length > 0) {
      html += '<li><h6 class="dropdown-header">Tour da página atual</h6></li>';
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
        alert(n + ' tours marcados como não-vistos. Recarregue a página para ver os tours automáticos.');
      }
      wrapper.remove();
    });

    document.addEventListener('click', function close(e) {
      if (!wrapper.contains(e.target) && e.target !== btn) {
        wrapper.remove();
        document.removeEventListener('click', close);
      }
    });
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
```

- [ ] **Step 5: Smoke test manual da foundation**

Crie `/tmp/onboarding_smoke.html`:
```html
<!DOCTYPE html>
<html><head>
<link rel="stylesheet" href="http://localhost:5000/static/onboarding/lib/driver.css">
</head><body>
<button id="help-button">?</button>
<div id="alvo">elemento alvo</div>
<script>window.OnboardingContext = {user_id: 999, is_admin: true, permissoes: null};</script>
<script src="http://localhost:5000/static/onboarding/lib/driver.min.js"></script>
<script src="http://localhost:5000/static/onboarding/core/tour_engine.js"></script>
<script src="http://localhost:5000/static/onboarding/core/localstorage_tracker.js"></script>
<script src="http://localhost:5000/static/onboarding/core/tour_button.js"></script>
<script>
window.OnboardingEngine.register({
  id: 'hora.smoke',
  titulo: 'Smoke test',
  steps: [{element: '#alvo', title: 'Achei', description: 'Funciona'}]
});
</script>
</body></html>
```

Subir Flask (`python run.py`), abrir `file:///tmp/onboarding_smoke.html`, clicar em "?", confirmar dropdown aparece com "Smoke test", clicar e ver tooltip + highlight.

Expected: dropdown abre com "Smoke test", clicar dispara tooltip funcional sobre `#alvo`.

- [ ] **Step 6: Commit**

```bash
git add app/static/onboarding/
git commit -m "$(cat <<'EOF'
feat(onboarding): foundation — Driver.js self-host + engine + tracker + button

- Self-host driver.js@1.3.1 em app/static/onboarding/lib/
- tour_engine.js: register/isVisible/start/autoStartIfFirstVisit com filtragem por permissão
- localstorage_tracker.js: keys com user_id namespace, resetModule
- tour_button.js: dropdown "Tour da pagina" + "Todos do modulo" + "Resetar"
- Smoke test em /tmp validado

Spec: docs/superpowers/specs/2026-05-08-onboarding-tours-hora-assai-design.md

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Endpoint `/api/onboarding/permissoes-matriz` com testes

**Files:**
- Create: `app/api/onboarding.py`
- Create: `tests/api/test_onboarding_routes.py`
- Modify: `app/__init__.py` — registrar blueprint

- [ ] **Step 1: Verificar se `app/api/__init__.py` existe e tem blueprint**

```bash
ls app/api/__init__.py 2>/dev/null && head -20 app/api/__init__.py
```

Se não existir, criar mínimo:
```python
# app/api/__init__.py
from flask import Blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api')
```

- [ ] **Step 2: Escrever teste pytest do endpoint**

```python
# tests/api/test_onboarding_routes.py
"""Testa endpoint GET /api/onboarding/permissoes-matriz."""
import pytest
from app import create_app, db
from app.auth.models import Usuario
from app.hora.models.permissao import HoraUserPermissao


@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def user_admin(app):
    u = Usuario(nome='admin', email='a@a.com', perfil='administrador', status='ativo')
    u.senha_hash = 'x'
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def user_vendedor(app):
    u = Usuario(nome='vendedor', email='v@v.com', perfil='vendedor', status='ativo')
    u.senha_hash = 'x'
    db.session.add(u)
    db.session.flush()
    p = HoraUserPermissao(user_id=u.id, modulo='vendas', pode_ver=True, pode_criar=True)
    db.session.add(p)
    db.session.commit()
    return u


def login_as(client, user):
    with client.session_transaction() as sess:
        sess['_user_id'] = str(user.id)


def test_permissoes_matriz_admin_retorna_is_admin_true(client, user_admin):
    login_as(client, user_admin)
    r = client.get('/api/onboarding/permissoes-matriz?modulo=hora')
    assert r.status_code == 200
    data = r.get_json()
    assert data['is_admin'] is True
    assert data['user_id'] == user_admin.id
    assert isinstance(data['permissoes'], dict)


def test_permissoes_matriz_vendedor_retorna_so_modulos_permitidos(client, user_vendedor):
    login_as(client, user_vendedor)
    r = client.get('/api/onboarding/permissoes-matriz?modulo=hora')
    assert r.status_code == 200
    data = r.get_json()
    assert data['is_admin'] is False
    assert data['permissoes']['vendas']['ver'] is True
    assert data['permissoes']['vendas']['criar'] is True
    assert data['permissoes']['recebimentos']['criar'] is False


def test_permissoes_matriz_assai_admin(client, user_admin):
    login_as(client, user_admin)
    r = client.get('/api/onboarding/permissoes-matriz?modulo=motos_assai')
    assert r.status_code == 200
    data = r.get_json()
    assert data['is_admin'] is True
    assert data['permissoes'] is None


def test_permissoes_matriz_modulo_invalido(client, user_admin):
    login_as(client, user_admin)
    r = client.get('/api/onboarding/permissoes-matriz?modulo=foo')
    assert r.status_code == 400


def test_permissoes_matriz_sem_login(client):
    r = client.get('/api/onboarding/permissoes-matriz?modulo=hora')
    assert r.status_code in (302, 401)
```

- [ ] **Step 3: Rodar teste para verificar que falha**

Run:
```bash
source .venv/bin/activate && pytest tests/api/test_onboarding_routes.py -v
```

Expected: FAIL com 404 ou ImportError (endpoint não existe).

- [ ] **Step 4: Implementar endpoint mínimo**

```python
# app/api/onboarding.py
"""Endpoint para fornecer matriz de permissões usada pelo onboarding JS."""
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user

from app.hora.services import permissao_service

onboarding_api_bp = Blueprint('onboarding_api', __name__, url_prefix='/api/onboarding')


@onboarding_api_bp.route('/permissoes-matriz', methods=['GET'])
@login_required
def permissoes_matriz():
    """Retorna o contexto que o JS injeta em window.OnboardingContext.

    Query param `modulo`:
      - 'hora': usa permissao_service.get_matriz (matriz granular)
      - 'motos_assai': retorna {is_admin, permissoes: None} (toggle único)
    """
    modulo = request.args.get('modulo', '').strip()
    if modulo not in ('hora', 'motos_assai'):
        return jsonify({'error': 'modulo invalido (use hora ou motos_assai)'}), 400

    is_admin = current_user.perfil == 'administrador'
    payload = {
        'user_id': current_user.id,
        'is_admin': is_admin,
        'permissoes': None,
    }

    if modulo == 'hora':
        payload['permissoes'] = permissao_service.get_matriz(current_user.id)

    return jsonify(payload)
```

- [ ] **Step 5: Registrar blueprint em `app/__init__.py`**

Localizar a seção de registros de blueprint (`grep -n "register_blueprint" app/__init__.py | head`). Adicionar:
```python
from app.api.onboarding import onboarding_api_bp
app.register_blueprint(onboarding_api_bp)
```

- [ ] **Step 6: Rodar testes — devem passar**

Run:
```bash
source .venv/bin/activate && pytest tests/api/test_onboarding_routes.py -v
```

Expected: PASS em 5 testes.

- [ ] **Step 7: Commit**

```bash
git add app/api/onboarding.py tests/api/test_onboarding_routes.py app/__init__.py
git commit -m "$(cat <<'EOF'
feat(onboarding): endpoint /api/onboarding/permissoes-matriz

GET /api/onboarding/permissoes-matriz?modulo=hora|motos_assai
- HORA: retorna matriz granular via permissao_service.get_matriz
- Assaí: retorna permissoes=None (so usa is_admin)
- Login obrigatorio
- 5 testes pytest cobrindo admin, vendedor, modulo invalido, sem login

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Injetar context + scripts no `app/templates/hora/base.html` + IDs no menu

**Files:**
- Modify: `app/templates/hora/base.html`
- Modify: `app/hora/routes/__init__.py` (adicionar `before_request` que carrega matriz no `g`)

- [ ] **Step 1: Adicionar `before_request` no blueprint HORA para carregar matriz**

Editar `app/hora/routes/__init__.py`. Após o `hora_bp = Blueprint(...)`, adicionar:
```python
from flask import g
from flask_login import current_user
from app.hora.services import permissao_service


@hora_bp.before_request
def carregar_matriz_onboarding():
    """Carrega matriz de permissões em g para o base.html injetar no JS."""
    if current_user.is_authenticated:
        g.onboarding_matriz = permissao_service.get_matriz(current_user.id)
        g.onboarding_is_admin = current_user.perfil == 'administrador'
    else:
        g.onboarding_matriz = None
        g.onboarding_is_admin = False
```

- [ ] **Step 2: Editar `app/templates/hora/base.html` — adicionar `<script>` de contexto e core**

Localizar bloco `</head>` ou bloco de scripts. Adicionar antes do fechamento do `<head>`:
```jinja
{% if current_user.is_authenticated %}
<link rel="stylesheet" href="{{ url_for('static', filename='onboarding/lib/driver.css') }}">
<script>
  window.OnboardingContext = {
    user_id: {{ current_user.id }},
    is_admin: {{ g.onboarding_is_admin | tojson }},
    permissoes: {{ g.onboarding_matriz | tojson }}
  };
</script>
{% endif %}
```

Antes de `</body>` adicionar:
```jinja
{% if current_user.is_authenticated %}
<script src="{{ url_for('static', filename='onboarding/lib/driver.min.js') }}"></script>
<script src="{{ url_for('static', filename='onboarding/core/localstorage_tracker.js') }}"></script>
<script src="{{ url_for('static', filename='onboarding/core/tour_engine.js') }}"></script>
<script src="{{ url_for('static', filename='onboarding/core/tour_button.js') }}"></script>
{% block onboarding_tours %}{% endblock %}
{% endif %}
```

- [ ] **Step 3: Adicionar botão "?" e IDs no menu HORA**

No `app/templates/hora/base.html`, localizar o navbar/menu. Adicionar atributo `id="help-button"` em um botão visível no header (criar se não existir):
```html
<button id="help-button" class="btn btn-link text-white" title="Ajuda">
  <i class="bi bi-question-circle"></i>
</button>
```

Localizar cada link de menu HORA e adicionar IDs. Usar `grep -n "url_for('hora\." app/templates/hora/base.html` para encontrar. Mapeamento dos IDs (corresponder aos passos do macro):
```jinja
<a id="menu-vendas"         href="{{ url_for('hora.vendas_lista') }}">Vendas (NF saída)</a>
<a id="menu-estoque"        href="{{ url_for('hora.estoque_lista') }}">Estoque</a>
<a id="menu-recebimentos"   href="{{ url_for('hora.recebimentos_lista') }}">Recebimentos</a>
<a id="menu-transferencias" href="{{ url_for('hora.transferencias_lista') }}">Transferências</a>
<a id="menu-pecas-estoque"  href="{{ url_for('hora.pecas_estoque_lista') }}">Peças estoque</a>
<a id="menu-tagplus"        href="{{ url_for('hora.tagplus_conta') }}">TagPlus</a>
<a id="menu-modelos"        href="{{ url_for('hora.modelos_lista') }}">Modelos</a>
<a id="menu-permissoes"     href="{{ url_for('hora.permissoes_lista') }}">Usuários</a>
```

(Apenas adicionar `id=`. Não remover/renomear hrefs existentes.)

- [ ] **Step 4: Smoke test no browser**

Run: `python run.py` e acessar `/hora/dashboard`. Abrir DevTools console, executar:
```javascript
console.log(window.OnboardingContext);
console.log(window.OnboardingEngine.listAllVisible());
```

Expected: objeto `OnboardingContext` com `user_id`, `is_admin`, `permissoes` populados. `listAllVisible()` retorna `[]` (nenhum tour registrado ainda — confirmado).

Clicar no `#help-button` — dropdown deve aparecer com "Resetar tours vistos" (lista vazia mas não quebra).

- [ ] **Step 5: Commit**

```bash
git add app/hora/routes/__init__.py app/templates/hora/base.html
git commit -m "$(cat <<'EOF'
feat(onboarding): inject contexto + scripts no base.html HORA

- before_request carrega matriz de permissoes em g
- base.html injeta window.OnboardingContext via tojson
- Inclui driver.js + 3 scripts core antes de </body>
- Adiciona id="help-button" no header e IDs em 8 links do menu
- {% block onboarding_tours %} para tours por tela

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Injetar context + scripts no `base_motos_assai.html` + IDs no menu

**Files:**
- Modify: `app/templates/motos_assai/base_motos_assai.html`
- Modify: `app/motos_assai/routes/__init__.py`

- [ ] **Step 1: Adicionar `before_request` no blueprint Motos Assaí**

Editar `app/motos_assai/routes/__init__.py`. Adicionar:
```python
from flask import g
from flask_login import current_user


@motos_assai_bp.before_request
def carregar_contexto_onboarding():
    if current_user.is_authenticated:
        g.onboarding_is_admin = current_user.perfil == 'administrador'
    else:
        g.onboarding_is_admin = False
```

- [ ] **Step 2: Editar `app/templates/motos_assai/base_motos_assai.html`**

Adicionar antes de `</head>`:
```jinja
{% if current_user.is_authenticated %}
<link rel="stylesheet" href="{{ url_for('static', filename='onboarding/lib/driver.css') }}">
<script>
  window.OnboardingContext = {
    user_id: {{ current_user.id }},
    is_admin: {{ g.onboarding_is_admin | tojson }},
    permissoes: null
  };
</script>
{% endif %}
```

Antes de `</body>`:
```jinja
{% if current_user.is_authenticated %}
<script src="{{ url_for('static', filename='onboarding/lib/driver.min.js') }}"></script>
<script src="{{ url_for('static', filename='onboarding/core/localstorage_tracker.js') }}"></script>
<script src="{{ url_for('static', filename='onboarding/core/tour_engine.js') }}"></script>
<script src="{{ url_for('static', filename='onboarding/core/tour_button.js') }}"></script>
{% block onboarding_tours %}{% endblock %}
{% endif %}
```

- [ ] **Step 3: Adicionar `#help-button` + IDs no menu Motos Assaí**

```html
<button id="help-button" class="btn btn-link text-white" title="Ajuda">
  <i class="bi bi-question-circle"></i>
</button>
```

IDs nos links do menu (verificar nomes via `grep -n "url_for('motos_assai" app/templates/motos_assai/base_motos_assai.html`):
```jinja
<a id="menu-recibos"        href="{{ url_for('motos_assai.recibos_lista') }}">Recibos</a>
<a id="menu-montagem"       href="{{ url_for('motos_assai.montagem') }}">Montagem</a>
<a id="menu-disponibilizar" href="{{ url_for('motos_assai.disponibilizar') }}">Disponibilizar</a>
<a id="menu-separacao"      href="{{ url_for('motos_assai.separacao_lista') }}">Separação</a>
<a id="menu-pedidos-voe"    href="{{ url_for('motos_assai.pedidos_lista') }}">Pedidos VOE</a>
<a id="menu-compras"        href="{{ url_for('motos_assai.compras_lista') }}">Compras Motochefe</a>
<a id="menu-faturamento"    href="{{ url_for('motos_assai.faturamento_lista') }}">Faturamento</a>
```

- [ ] **Step 4: Smoke test**

Run: `python run.py` e acessar `/motos-assai/dashboard`. Confirmar console:
```javascript
window.OnboardingContext  // {user_id: X, is_admin: bool, permissoes: null}
```

- [ ] **Step 5: Commit**

```bash
git add app/motos_assai/routes/__init__.py app/templates/motos_assai/base_motos_assai.html
git commit -m "feat(onboarding): inject contexto + scripts no base_motos_assai.html

- before_request define is_admin em g
- base injeta OnboardingContext (permissoes=null pois nao ha matriz granular)
- 4 scripts core + bloco onboarding_tours
- IDs em 7 links do menu

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: Tour macro HORA (`_macro.js`)

**Files:**
- Create: `app/static/onboarding/tours/hora/_macro.js`
- Modify: `app/templates/hora/dashboard.html` (ou `app/templates/hora/base.html` para carregar global)

- [ ] **Step 1: Criar `_macro.js`**

```javascript
// app/static/onboarding/tours/hora/_macro.js
window.OnboardingEngine.register({
  id: 'hora.macro',
  titulo: 'Bem-vindo à Lojas HORA',
  autoStartRoute: '/hora/dashboard',
  steps: [
    {
      element: '#menu-vendas',
      title: 'Vendas (NF saída)',
      description: 'Aqui você cria pedidos de venda, acompanha o que foi faturado e gerencia devoluções.',
      requirePerm: { modulo: 'vendas', acao: 'ver' }
    },
    {
      element: '#menu-estoque',
      title: 'Estoque de motos',
      description: 'Lista de motos por loja e por chassi. Mostra também avarias e reservas de pedido.',
      requirePerm: { modulo: 'estoque', acao: 'ver' }
    },
    {
      element: '#menu-recebimentos',
      title: 'Receber NF da Motochefe',
      description: 'Suba o PDF da NF, confira chassi por chassi e finalize o recebimento. <strong>Daqui sai a entrada de motos no estoque.</strong>',
      requirePerm: { modulo: 'recebimentos', acao: 'ver' }
    },
    {
      element: '#menu-transferencias',
      title: 'Transferir entre lojas',
      description: 'Movimentação de motos entre filiais. Precisa de confirmação na loja destino para concluir.',
      requirePerm: { modulo: 'transferencias', acao: 'ver' }
    },
    {
      element: '#menu-pecas-estoque',
      title: 'Peças e acessórios',
      description: 'Capacete, retrovisor, bateria. Saldo por loja, transferência e ajuste manual.',
      requirePerm: { modulo: 'pecas_estoque', acao: 'ver' }
    },
    {
      element: '#menu-tagplus',
      title: 'NFe via TagPlus',
      description: 'Emissão fiscal eletrônica. Precisa de OAuth configurado e mapeamento de produtos.',
      requirePerm: { modulo: 'tagplus', acao: 'ver' }
    },
    {
      element: '#menu-modelos',
      title: 'Catálogo de modelos',
      description: 'Cadastro central de modelos com preço à vista/à prazo. Resolve nomes divergentes (BOB AM = BOB).',
      requirePerm: { modulo: 'modelos', acao: 'ver' }
    },
    {
      element: '#menu-permissoes',
      title: 'Gerenciar usuários',
      description: 'Aprovar cadastros pendentes, atribuir lojas e configurar permissões granulares por módulo.',
      requirePerm: { modulo: 'usuarios', acao: 'ver' }
    },
    {
      element: '#help-button',
      title: 'Precisou de ajuda?',
      description: 'Clique no <strong>?</strong> em qualquer tela para ver o tour daquela tela específica.'
    }
  ]
});
```

- [ ] **Step 2: Carregar o macro em todas as páginas HORA**

Editar `app/templates/hora/base.html`. Localizar o trecho com os 4 scripts core (Task 3 step 2) e adicionar logo abaixo, dentro do mesmo `{% if current_user.is_authenticated %}`:
```jinja
<script src="{{ url_for('static', filename='onboarding/tours/hora/_macro.js') }}"></script>
```

Motivo: o macro só dispara em `/hora/dashboard` (via `autoStartRoute`), mas precisa estar registrado em todas as páginas para o botão "?" listar como "Tour completo do módulo".

- [ ] **Step 3: Smoke test**

Run: `python run.py`. Abrir aba anônima ou limpar localStorage do site. Logar e acessar `/hora/dashboard`.
Expected: tour macro dispara automaticamente. Como admin, vê os 9 passos. Como vendedor (sem permissões em vários módulos), vê só 2-3 passos (vendas + estoque + último).

Após o tour completar/fechar, recarregar `/hora/dashboard`. Expected: tour NÃO dispara (localStorage marca visto).

Clicar no `#help-button`. Expected: dropdown lista "Bem-vindo à Lojas HORA" como tour completo.

- [ ] **Step 4: Commit**

```bash
git add app/static/onboarding/tours/hora/_macro.js app/templates/hora/base.html
git commit -m "feat(onboarding): tour macro HORA com 9 passos filtraveis por permissao

Macro registrado em todas as paginas HORA via base.html.
Auto-start em /hora/dashboard no 1o acesso.
Cada passo tem requirePerm; engine pula se usuario nao tem.
Vendedor ve subset; admin ve tudo.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: Tour macro Motos Assaí (`_macro.js`)

**Files:**
- Create: `app/static/onboarding/tours/motos_assai/_macro.js`
- Modify: `app/templates/motos_assai/base_motos_assai.html`

- [ ] **Step 1: Criar `_macro.js` Assaí**

```javascript
// app/static/onboarding/tours/motos_assai/_macro.js
window.OnboardingEngine.register({
  id: 'motos_assai.macro',
  titulo: 'Bem-vindo ao Motos Assaí',
  autoStartRoute: '/motos-assai/dashboard',
  steps: [
    {
      element: '#menu-recibos',
      title: 'Recibos da Motochefe',
      description: 'Cada recibo lista os chassis que vão chegar. Suba o PDF/Excel para começar a conferência.'
    },
    {
      element: '#menu-montagem',
      title: 'Montagem (chão)',
      description: 'Marque a moto como MONTADA depois de conferir que está OK. Use o leitor QR ou digite o chassi.'
    },
    {
      element: '#menu-disponibilizar',
      title: 'Disponibilizar',
      description: 'Após colar a tag e o manual, a moto vai para DISPONIVEL e pode ser separada para um pedido.'
    },
    {
      element: '#menu-separacao',
      title: 'Separação',
      description: 'Vincula chassis DISPONIVEL aos pedidos. <strong>Fungível:</strong> qualquer chassi do mesmo modelo serve.'
    },
    {
      element: '#menu-pedidos-voe',
      title: 'Pedidos VOE Q.P.A.',
      description: 'Suba o PDF VOE do Sendas/Assaí. O sistema parseia 38 páginas em ~30s e cria os itens automaticamente.',
      adminOnly: true
    },
    {
      element: '#menu-compras',
      title: 'Compras Motochefe',
      description: 'Consolida N pedidos VOE em 1 pedido de compra (PO) para a Motochefe. Gera PDF com modelos e quantidades.',
      adminOnly: true
    },
    {
      element: '#menu-faturamento',
      title: 'Faturamento',
      description: 'Gera Excel Q.P.A. da separação concluída. Depois suba a NF Q.P.A. emitida para fazer o match BATEU/DIVERGENTE.',
      adminOnly: true
    },
    {
      element: '#help-button',
      title: 'Precisou de ajuda?',
      description: 'Clique no <strong>?</strong> em qualquer tela para ver o tour daquela tela.'
    }
  ]
});
```

- [ ] **Step 2: Carregar o macro em todas as páginas Assaí**

Editar `app/templates/motos_assai/base_motos_assai.html`. Adicionar dentro do bloco `{% if current_user.is_authenticated %}` antes de `</body>`:
```jinja
<script src="{{ url_for('static', filename='onboarding/tours/motos_assai/_macro.js') }}"></script>
```

- [ ] **Step 3: Smoke test**

Run: `python run.py`. Limpar localStorage. Acessar `/motos-assai/dashboard` como admin → tour com 8 passos. Como operador (não-admin) → 5 passos (4 universais + último).

- [ ] **Step 4: Commit**

```bash
git add app/static/onboarding/tours/motos_assai/_macro.js app/templates/motos_assai/base_motos_assai.html
git commit -m "feat(onboarding): tour macro Motos Assai com 8 passos (3 adminOnly)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: Mini-tour HORA `recebimento_nf`

**Files:**
- Create: `app/static/onboarding/tours/hora/recebimento_nf.js`
- Modify: `app/templates/hora/recebimento_novo.html` (IDs nos elementos + script)

- [ ] **Step 1: Criar `recebimento_nf.js`**

```javascript
// app/static/onboarding/tours/hora/recebimento_nf.js
window.OnboardingEngine.register({
  id: 'hora.recebimento_nf',
  titulo: 'Como receber NF da Motochefe',
  requirePerm: { modulo: 'recebimentos', acao: 'criar' },
  autoStartRoute: '/hora/recebimentos/novo',
  steps: [
    {
      element: '#nf-upload-area',
      title: 'Suba o PDF da NF',
      description: 'Arraste o DANFE recebido da Motochefe. <strong>Aceita só PDF</strong>. O parser extrai chassi, modelo e cor automaticamente.'
    },
    {
      element: '#campo-loja-destino',
      title: 'Loja que vai receber',
      description: 'Escolha qual loja física está recebendo. Define o estoque destino dos chassis.'
    },
    {
      element: '#btn-parsear',
      title: 'Parsear DANFE',
      description: 'Roda o parser. Se a NF estiver legível, lista todos os chassis em ~5s. Se vier ruim, fallback LLM (Haiku 4.5) entra em ação.'
    },
    {
      element: '#tabela-itens-extraidos',
      title: 'Confira o que veio',
      description: 'Cada linha = 1 chassi declarado. Você ainda vai conferir fisicamente cada um. <strong>Divergências entre NF e físico viram evento MOTO_FALTANDO.</strong>'
    },
    {
      element: '#btn-iniciar-conferencia',
      title: 'Iniciar conferência',
      description: 'Salva o registro e abre o wizard de conferência (chassi-por-chassi com QR ou digitação manual).'
    }
  ]
});
```

- [ ] **Step 2: Adicionar IDs no template `recebimento_novo.html`**

Localizar elementos via `grep -n "input\|button\|table\|form" app/templates/hora/recebimento_novo.html | head -30`. Adicionar IDs:
- Área de upload do PDF: `id="nf-upload-area"`
- Select de loja: `id="campo-loja-destino"`
- Botão "Parsear" / "Processar": `id="btn-parsear"`
- Tabela de itens extraídos: `id="tabela-itens-extraidos"`
- Botão final: `id="btn-iniciar-conferencia"`

- [ ] **Step 3: Carregar o JS na tela**

No final do `recebimento_novo.html`, dentro de `{% block onboarding_tours %}`:
```jinja
{% block onboarding_tours %}
<script src="{{ url_for('static', filename='onboarding/tours/hora/recebimento_nf.js') }}"></script>
{% endblock %}
```

- [ ] **Step 4: Smoke test**

Run: `python run.py`. Logar como gerente HORA com permissão `recebimentos/criar`. Limpar localStorage. Acessar `/hora/recebimentos/novo`.

Expected: tour dispara automaticamente, 5 passos, cada um destaca o elemento certo. Logar como vendedor (sem `recebimentos/criar`) → tour não aparece.

- [ ] **Step 5: Commit**

```bash
git add app/static/onboarding/tours/hora/recebimento_nf.js app/templates/hora/recebimento_novo.html
git commit -m "feat(onboarding): mini-tour HORA recebimento NF Motochefe (5 passos)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 8: Mini-tour HORA `venda_manual_nova`

**Files:**
- Create: `app/static/onboarding/tours/hora/venda_manual_nova.js`
- Modify: `app/templates/hora/tagplus/pedido_venda_novo.html`

- [ ] **Step 1: Criar `venda_manual_nova.js`**

```javascript
// app/static/onboarding/tours/hora/venda_manual_nova.js
window.OnboardingEngine.register({
  id: 'hora.venda_manual_nova',
  titulo: 'Criar pedido de venda',
  requirePerm: { modulo: 'vendas', acao: 'criar' },
  autoStartRoute: '/hora/tagplus/pedido-venda/novo',
  steps: [
    {
      element: '#campo-cliente-cpfcnpj',
      title: 'CPF ou CNPJ do cliente',
      description: 'Pode ser PF ou PJ. <strong>Toda NFe sai como consumidor final</strong>, não importa o tipo.'
    },
    {
      element: '#campo-cliente-nome',
      title: 'Nome do cliente',
      description: 'Vai no destinatário da NFe. Digite igual ao documento.'
    },
    {
      element: '#secao-itens',
      title: 'Itens do pedido',
      description: 'Adicione motos (por chassi) e/ou peças (por código). Pelo menos 1 item obrigatório.'
    },
    {
      element: '#btn-add-moto',
      title: 'Adicionar moto',
      description: 'Escolha modelo + chassi específico. <strong>Lock pessimista:</strong> ninguém mais pode reservar esse chassi até cancelar ou faturar.'
    },
    {
      element: '#campo-forma-pagamento',
      title: 'Forma de pagamento',
      description: 'PIX, cartão, dinheiro, misto. Define se entra preço à vista ou à prazo do modelo.'
    },
    {
      element: '#btn-salvar-cotacao',
      title: 'Salvar como COTAÇÃO',
      description: 'Status COTAÇÃO permite editar tudo. Quando confirmar, vira CONFIRMADO (só edita observação). NFe emite quando o gerente confirmar.'
    }
  ]
});
```

- [ ] **Step 2: Adicionar IDs no template `pedido_venda_novo.html`**

IDs alvo: `#campo-cliente-cpfcnpj`, `#campo-cliente-nome`, `#secao-itens`, `#btn-add-moto`, `#campo-forma-pagamento`, `#btn-salvar-cotacao`.

- [ ] **Step 3: Carregar JS no template**

```jinja
{% block onboarding_tours %}
<script src="{{ url_for('static', filename='onboarding/tours/hora/venda_manual_nova.js') }}"></script>
{% endblock %}
```

- [ ] **Step 4: Smoke test**

Run: `python run.py`. Logar como vendedor com `vendas/criar`. Acessar `/hora/tagplus/pedido-venda/novo`. Expected: 6 passos, cada destaca o campo certo.

- [ ] **Step 5: Commit**

```bash
git add app/static/onboarding/tours/hora/venda_manual_nova.js app/templates/hora/tagplus/pedido_venda_novo.html
git commit -m "feat(onboarding): mini-tour HORA criar pedido de venda manual (6 passos)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 9: Mini-tour HORA `transferencia_nova`

**Files:**
- Create: `app/static/onboarding/tours/hora/transferencia_nova.js`
- Modify: `app/templates/hora/transferencia_nova.html`

- [ ] **Step 1: Criar `transferencia_nova.js`**

```javascript
// app/static/onboarding/tours/hora/transferencia_nova.js
window.OnboardingEngine.register({
  id: 'hora.transferencia_nova',
  titulo: 'Transferir motos entre lojas',
  requirePerm: { modulo: 'transferencias', acao: 'criar' },
  autoStartRoute: '/hora/transferencias/nova',
  steps: [
    {
      element: '#campo-loja-origem',
      title: 'Loja de origem',
      description: 'A loja que está enviando. Você só vê lojas onde tem permissão de origem (ver auth_helper).'
    },
    {
      element: '#campo-loja-destino',
      title: 'Loja de destino',
      description: 'Para onde a moto vai. Não pode ser igual à origem.'
    },
    {
      element: '#secao-chassis',
      title: 'Selecione os chassis',
      description: 'Marque os chassis disponíveis na loja origem. Cada um vai virar 1 item de transferência.'
    },
    {
      element: '#btn-emitir',
      title: 'Emitir transferência',
      description: 'Status vira <strong>EM_TRANSITO</strong>. Loja destino precisa confirmar para virar TRANSFERIDA. Você pode cancelar enquanto em trânsito.'
    }
  ]
});
```

- [ ] **Step 2: Adicionar IDs**

`#campo-loja-origem`, `#campo-loja-destino`, `#secao-chassis`, `#btn-emitir`.

- [ ] **Step 3: Carregar JS**

```jinja
{% block onboarding_tours %}
<script src="{{ url_for('static', filename='onboarding/tours/hora/transferencia_nova.js') }}"></script>
{% endblock %}
```

- [ ] **Step 4: Commit**

```bash
git add app/static/onboarding/tours/hora/transferencia_nova.js app/templates/hora/transferencia_nova.html
git commit -m "feat(onboarding): mini-tour HORA transferencia entre lojas (4 passos)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 10: Mini-tour Motos Assaí `recebimento_wizard`

**Files:**
- Create: `app/static/onboarding/tours/motos_assai/recebimento_wizard.js`
- Modify: `app/templates/motos_assai/recebimento/wizard.html`

- [ ] **Step 1: Criar `recebimento_wizard.js`**

```javascript
// app/static/onboarding/tours/motos_assai/recebimento_wizard.js
window.OnboardingEngine.register({
  id: 'motos_assai.recebimento_wizard',
  titulo: 'Conferir recibo da Motochefe',
  autoStartRoute: '/motos-assai/recibos/*/conferir',
  steps: [
    {
      element: '#recibo-header',
      title: 'Recibo em conferência',
      description: 'O número do recibo vem do PDF/Excel que o admin subiu. Aqui você confere chassi por chassi.'
    },
    {
      element: '#progress-steps',
      title: 'Wizard em 4 passos',
      description: 'Recibo → Escanear → Confirmar → Finalizar. Você está no passo 2 (Escanear).'
    },
    {
      element: '#scan-area',
      title: 'Aponte o QR do chassi',
      description: 'Use a câmera traseira do celular. <strong>Se a câmera falhar</strong> ou QR estiver danificado, use a digitação manual logo abaixo.'
    },
    {
      element: '#chassi-input',
      title: 'Digitação manual (fallback)',
      description: 'Operadores rápidos digitam direto sem usar câmera. <strong>Pressione Enter</strong> para validar.'
    },
    {
      element: '#btn-validar',
      title: 'Validar antes de salvar',
      description: 'Checa: chassi pertence a este recibo? Já foi conferido? Modelo bate com o regex do cadastro?'
    },
    {
      element: '#lista-conferidos',
      title: 'Acompanhe o progresso',
      description: 'Quando todos os chassis estiverem conferidos, o botão <strong>Finalizar</strong> aparece. Faltantes viram evento MOTO_FALTANDO.'
    }
  ]
});
```

- [ ] **Step 2: Adicionar IDs no template `recebimento/wizard.html`**

`#recibo-header`, `#progress-steps`, `#scan-area`, `#chassi-input`, `#btn-validar`, `#lista-conferidos`.

- [ ] **Step 3: Carregar JS**

```jinja
{% block onboarding_tours %}
<script src="{{ url_for('static', filename='onboarding/tours/motos_assai/recebimento_wizard.js') }}"></script>
{% endblock %}
```

- [ ] **Step 4: Smoke test em mobile**

Acessar `/motos-assai/recibos/<id>/conferir` num celular real (ou DevTools mobile). Expected: tour dispara, tooltip se reposiciona em telas estreitas, botões 44px+.

- [ ] **Step 5: Commit**

```bash
git add app/static/onboarding/tours/motos_assai/recebimento_wizard.js app/templates/motos_assai/recebimento/wizard.html
git commit -m "feat(onboarding): mini-tour Assai recebimento wizard QR (6 passos, mobile-first)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 11: Mini-tours Assaí operação chão (`montagem_quick`, `disponibilizar_quick`, `separacao_chassi`)

**Files:**
- Create: `app/static/onboarding/tours/motos_assai/montagem_quick.js`
- Create: `app/static/onboarding/tours/motos_assai/disponibilizar_quick.js`
- Create: `app/static/onboarding/tours/motos_assai/separacao_chassi.js`
- Modify: 3 templates (`montagem/index.html`, `disponibilizar/index.html`, `separacao/index.html` ou nomes equivalentes)

- [ ] **Step 1: Criar `montagem_quick.js`**

```javascript
// app/static/onboarding/tours/motos_assai/montagem_quick.js
window.OnboardingEngine.register({
  id: 'motos_assai.montagem_quick',
  titulo: 'Montar moto (ESTOQUE → MONTADA)',
  autoStartRoute: '/motos-assai/montagem',
  steps: [
    {
      element: '#scan-input',
      title: 'Aponte o QR ou digite o chassi',
      description: 'Tela de chão de fábrica. Suporta leitor USB (Enter dispara), câmera mobile e digitação.'
    },
    {
      element: '#btn-marcar-montada',
      title: 'Marcar como MONTADA',
      description: 'Caminho feliz: chassi montado e OK → vira MONTADA, próxima parada é DISPONIVEL.'
    },
    {
      element: '#btn-marcar-pendente',
      title: 'Marcar como PENDENTE',
      description: 'Defeito de peça? Marca PENDENTE com descrição. Resolve depois com PENDENCIA_RESOLVIDA → MONTADA.'
    },
    {
      element: '#historico-3-ultimas',
      title: 'Últimas 3 ações',
      description: 'Vista rápida do que você acabou de fazer. Útil para ver se errou e desfazer.'
    }
  ]
});
```

- [ ] **Step 2: Criar `disponibilizar_quick.js`**

```javascript
// app/static/onboarding/tours/motos_assai/disponibilizar_quick.js
window.OnboardingEngine.register({
  id: 'motos_assai.disponibilizar_quick',
  titulo: 'Disponibilizar moto (MONTADA → DISPONIVEL)',
  autoStartRoute: '/motos-assai/disponibilizar',
  steps: [
    {
      element: '#scan-input',
      title: 'Escaneie o chassi',
      description: 'Faça depois de colar a tag e o manual. <strong>DISPONIVEL = pronta para separar para um pedido.</strong>'
    },
    {
      element: '#btn-disponibilizar',
      title: 'Confirmar disponibilização',
      description: 'Emite evento DISPONIVEL. Só funciona se o chassi está MONTADA ou REVERTIDA_PARA_MONTADA.'
    },
    {
      element: '#btn-reverter',
      title: 'Reverter (se errou)',
      description: 'Volta DISPONIVEL → REVERTIDA_PARA_MONTADA. <strong>Motivo obrigatório (≥3 caracteres).</strong>'
    }
  ]
});
```

- [ ] **Step 3: Criar `separacao_chassi.js`**

```javascript
// app/static/onboarding/tours/motos_assai/separacao_chassi.js
window.OnboardingEngine.register({
  id: 'motos_assai.separacao_chassi',
  titulo: 'Separar pedido (chassis para o cliente)',
  autoStartRoute: '/motos-assai/pedidos/*/separar/*',
  steps: [
    {
      element: '#header-pedido-loja',
      title: 'Pedido + loja Sendas',
      description: 'Você está separando o pedido X para a loja LJ12 do Assaí.'
    },
    {
      element: '#barras-saldo',
      title: 'Saldo por modelo',
      description: 'Cada barra = 1 modelo do pedido. Faltam X chassis pra completar. Fungível: qualquer chassi DISPONIVEL do mesmo modelo serve.'
    },
    {
      element: '#scan-input',
      title: 'Escaneie o chassi DISPONIVEL',
      description: 'Race condition: se 2 operadores escanearem o mesmo chassi, o segundo recebe 409 e tenta de novo.'
    },
    {
      element: '#btn-finalizar-separacao',
      title: 'Finalizar quando completo',
      description: 'Aparece quando saldo = 0. Move a separação para FECHADA e libera para gerar Excel Q.P.A.'
    }
  ]
});
```

- [ ] **Step 4: Adicionar IDs nos 3 templates + carregar scripts**

Para cada um dos 3 templates, adicionar IDs correspondentes e:
```jinja
{% block onboarding_tours %}
<script src="{{ url_for('static', filename='onboarding/tours/motos_assai/<nome>.js') }}"></script>
{% endblock %}
```

- [ ] **Step 5: Smoke test (3 telas)**

Rodar tours em `/motos-assai/montagem`, `/motos-assai/disponibilizar`, e numa separação real.

- [ ] **Step 6: Commit**

```bash
git add app/static/onboarding/tours/motos_assai/montagem_quick.js \
        app/static/onboarding/tours/motos_assai/disponibilizar_quick.js \
        app/static/onboarding/tours/motos_assai/separacao_chassi.js \
        app/templates/motos_assai/montagem/ \
        app/templates/motos_assai/disponibilizar/ \
        app/templates/motos_assai/separacao/
git commit -m "feat(onboarding): mini-tours Assai operacao chao (montagem/disponibilizar/separacao)

3 tours mobile-first (4+3+4 passos).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 12: Mini-tours HORA admin pacote 1 (`vendas_aprovar`, `devolucao_venda`, `estoque_lista`, `avaria_nova`)

**Files:**
- Create: `app/static/onboarding/tours/hora/vendas_aprovar.js`
- Create: `app/static/onboarding/tours/hora/devolucao_venda.js`
- Create: `app/static/onboarding/tours/hora/estoque_lista.js`
- Create: `app/static/onboarding/tours/hora/avaria_nova.js`
- Modify: 4 templates correspondentes

- [ ] **Step 1: `vendas_aprovar.js`**

```javascript
window.OnboardingEngine.register({
  id: 'hora.vendas_aprovar',
  titulo: 'Aprovar venda e emitir NFe',
  requirePerm: { modulo: 'vendas', acao: 'aprovar' },
  autoStartRoute: '/hora/vendas/*',
  steps: [
    {
      element: '#timeline-status',
      title: 'Status do pedido',
      description: 'Estados: COTAÇÃO → CONFIRMADO → FATURADO → CANCELADO. Cada um tem campos editáveis diferentes.'
    },
    {
      element: '#btn-confirmar',
      title: 'Confirmar pedido',
      description: 'Vira CONFIRMADO. Trava CPF/nome (vão pra NFe). Permite editar contato, endereço, observação.'
    },
    {
      element: '#btn-emitir-nfe',
      title: 'Emitir NFe via TagPlus',
      description: 'Enfileira job no Redis. Webhook do TagPlus avisa quando aprovou na SEFAZ → vira FATURADO.'
    },
    {
      element: '#secao-historico',
      title: 'Auditoria completa',
      description: '14 ações registradas (CRIOU, CONFIRMOU, EMITIU_NFE, CANCELOU...). Cada uma com usuário e timestamp.'
    },
    {
      element: '#btn-cancelar-pedido',
      title: 'Cancelar pedido',
      description: 'COTAÇÃO/CONFIRMADO: cancela direto. FATURADO: precisa cancelar NFe na SEFAZ antes (botão na seção NFe).'
    }
  ]
});
```

- [ ] **Step 2: `devolucao_venda.js`**

```javascript
window.OnboardingEngine.register({
  id: 'hora.devolucao_venda',
  titulo: 'Registrar devolução de venda',
  requirePerm: { modulo: 'devolucoes_venda', acao: 'criar' },
  autoStartRoute: '/hora/devolucoes-venda/novo',
  steps: [
    {
      element: '#campo-venda-origem',
      title: 'Venda original',
      description: 'Busque pelo número do pedido ou chave da NFe. Sistema lista os chassis que podem voltar.'
    },
    {
      element: '#secao-itens-devolvidos',
      title: 'Marque o que voltou',
      description: 'Pode ser devolução parcial. Cada chassi marcado emite evento DEVOLVIDA e volta ao estoque DISPONIVEL.'
    },
    {
      element: '#campo-motivo',
      title: 'Motivo da devolução',
      description: 'Obrigatório. Aparece na auditoria e pode subsidiar política comercial futura.'
    },
    {
      element: '#btn-salvar-devolucao',
      title: 'Confirmar devolução',
      description: 'Emite eventos, atualiza estoque e marca a venda como parcialmente/totalmente devolvida.'
    }
  ]
});
```

- [ ] **Step 3: `estoque_lista.js`**

```javascript
window.OnboardingEngine.register({
  id: 'hora.estoque_lista',
  titulo: 'Consultar estoque de motos',
  requirePerm: { modulo: 'estoque', acao: 'ver' },
  autoStartRoute: '/hora/estoque',
  steps: [
    {
      element: '#filtros-estoque',
      title: 'Filtros',
      description: 'Loja, modelo, busca por chassi (substring). Combinam — você pode filtrar tudo junto.'
    },
    {
      element: '#tabela-estoque',
      title: 'Lista de motos',
      description: 'Cada linha = 1 chassi. <strong>Status efetivo</strong> vem do último evento, não do banco.'
    },
    {
      element: '#badge-avaria',
      title: 'Avarias abertas',
      description: 'Badge amarelo "⚠ N" indica chassis com avarias registradas. Não bloqueia venda, só avisa.'
    },
    {
      element: '#badge-reservado',
      title: 'Reservas de pedido',
      description: 'Badge azul "Reservado em Pedido #X" = chassi em uma venda COTAÇÃO/CONFIRMADO/FATURADO.'
    }
  ]
});
```

- [ ] **Step 4: `avaria_nova.js`**

```javascript
window.OnboardingEngine.register({
  id: 'hora.avaria_nova',
  titulo: 'Registrar avaria',
  requirePerm: { modulo: 'avarias', acao: 'criar' },
  autoStartRoute: '/hora/avarias/nova',
  steps: [
    {
      element: '#campo-chassi',
      title: 'Chassi avariado',
      description: 'Pode estar em qualquer status (estoque, vendido, em trânsito). Avaria não muda status, só sinaliza.'
    },
    {
      element: '#campo-foto',
      title: 'Foto obrigatória',
      description: 'Suba no mínimo 1 foto da avaria. <strong>Vai pro S3</strong> e fica vinculada à avaria.'
    },
    {
      element: '#campo-descricao',
      title: 'Descrição (≥3 caracteres)',
      description: 'Texto curto explicando o problema. Aparece no detalhe e nos relatórios.'
    },
    {
      element: '#btn-salvar-avaria',
      title: 'Salvar',
      description: 'Cria registro + emite evento AVARIADA. Múltiplas avarias por chassi são permitidas.'
    }
  ]
});
```

- [ ] **Step 5: Adicionar IDs e includes nos 4 templates correspondentes**

Para cada template, adicionar os IDs listados nos passos e o `{% block onboarding_tours %}` com `<script src=".../<nome>.js"></script>`.

- [ ] **Step 6: Smoke test em todas as 4 telas**

- [ ] **Step 7: Commit**

```bash
git add app/static/onboarding/tours/hora/{vendas_aprovar,devolucao_venda,estoque_lista,avaria_nova}.js \
        app/templates/hora/venda_detalhe.html \
        app/templates/hora/devolucao_venda_novo.html \
        app/templates/hora/estoque_lista.html \
        app/templates/hora/avaria_nova.html
git commit -m "feat(onboarding): mini-tours HORA admin pacote 1 (4 tours: vendas/devolucao/estoque/avaria)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 13: Mini-tours HORA admin pacote 2 (`pecas_estoque`, `modelos_novo`, `modelos_pendencias`, `modelos_unificar`)

**Files:**
- Create: `app/static/onboarding/tours/hora/pecas_estoque.js`
- Create: `app/static/onboarding/tours/hora/modelos_novo.js`
- Create: `app/static/onboarding/tours/hora/modelos_pendencias.js`
- Create: `app/static/onboarding/tours/hora/modelos_unificar.js`
- Modify: 4 templates correspondentes

- [ ] **Step 1: `pecas_estoque.js`**

```javascript
window.OnboardingEngine.register({
  id: 'hora.pecas_estoque',
  titulo: 'Estoque de peças',
  requirePerm: { modulo: 'pecas_estoque', acao: 'editar' },
  autoStartRoute: '/hora/pecas/estoque',
  steps: [
    {
      element: '#filtro-loja',
      title: 'Filtre por loja',
      description: 'Cada peça tem saldo separado por loja. Saldo = SUM(movimentos), não há tabela materializada.'
    },
    {
      element: '#tabela-pecas',
      title: 'Lista de peças',
      description: 'Capacete, retrovisor, bateria, acessórios. Saldo positivo apenas. Negativo é bug — abrir issue.'
    },
    {
      element: '#btn-ajuste-manual',
      title: 'Ajuste manual',
      description: 'AJUSTE_POS / AJUSTE_NEG. Use só com motivo (inventário, achado, perda). <strong>Auditável.</strong>'
    },
    {
      element: '#btn-transferir',
      title: 'Transferir entre lojas',
      description: 'TRANSFERENCIA_OUT na origem + TRANSFERENCIA_IN no destino. Atômico — falha bloqueia ambos.'
    }
  ]
});
```

- [ ] **Step 2: `modelos_novo.js`**

```javascript
window.OnboardingEngine.register({
  id: 'hora.modelos_novo',
  titulo: 'Cadastrar modelo de moto',
  requirePerm: { modulo: 'modelos', acao: 'criar' },
  autoStartRoute: '/hora/modelos/novo',
  steps: [
    {
      element: '#campo-nome',
      title: 'Nome canônico',
      description: 'Nome principal. Variações virão como ALIASES (ex: "BOB AM" vira alias do modelo "BOB").'
    },
    {
      element: '#campo-preco-vista',
      title: 'Preço à vista',
      description: 'Aplica em vendas com forma de pagamento PIX, dinheiro, débito ou MISTO sem prazo.'
    },
    {
      element: '#campo-preco-prazo',
      title: 'Preço à prazo',
      description: 'Aplica em vendas com cartão crédito ou outras formas com tipo_pagamento = A_PRAZO.'
    },
    {
      element: '#campo-foto',
      title: 'Foto do modelo (opcional)',
      description: 'Mostrada na lista de modelos e no catálogo de venda. Sobe pro S3.'
    },
    {
      element: '#btn-salvar',
      title: 'Salvar',
      description: 'Cria modelo + alias inicial NOME_LIVRE. Pronto para receber chassis em recebimentos.'
    }
  ]
});
```

- [ ] **Step 3: `modelos_pendencias.js`**

```javascript
window.OnboardingEngine.register({
  id: 'hora.modelos_pendencias',
  titulo: 'Resolver modelos pendentes',
  requirePerm: { modulo: 'modelos', acao: 'editar' },
  autoStartRoute: '/hora/modelos/pendencias',
  steps: [
    {
      element: '#tabela-pendencias',
      title: 'Nomes desconhecidos',
      description: 'Cada linha = nome que apareceu numa NF/pedido/TagPlus mas não bate com nenhum modelo cadastrado.'
    },
    {
      element: '#btn-vincular',
      title: 'Vincular a modelo existente',
      description: 'Cria HoraModeloAlias apontando o nome para um modelo. Retroativamente cria HoraMoto pros chassis travados.'
    },
    {
      element: '#btn-criar-novo',
      title: 'Criar novo modelo',
      description: 'Se for modelo realmente novo. Cria HoraModelo + alias automaticamente.'
    },
    {
      element: '#btn-ignorar',
      title: 'Ignorar (lixo)',
      description: 'Para nomes mal extraídos pelo parser que não dá pra resolver. Não cria nada.'
    }
  ]
});
```

- [ ] **Step 4: `modelos_unificar.js`**

```javascript
window.OnboardingEngine.register({
  id: 'hora.modelos_unificar',
  titulo: 'Unificar modelos duplicados',
  requirePerm: { modulo: 'modelos', acao: 'aprovar' },
  autoStartRoute: '/hora/modelos/unificar',
  steps: [
    {
      element: '#campo-canonico',
      title: 'Modelo canônico',
      description: 'O modelo que vai PERMANECER. Todos os outros viram aliases dele.'
    },
    {
      element: '#campo-aliases',
      title: 'Modelos a fundir',
      description: 'Selecione N modelos duplicados. Suas tabelas (chassis, pedidos, conferências) vão apontar para o canônico.'
    },
    {
      element: '#btn-preview',
      title: 'Preview (dry-run)',
      description: '<strong>Sempre rode antes!</strong> Mostra exatamente quantos registros mudam, sem alterar banco.'
    },
    {
      element: '#btn-executar-merge',
      title: 'Executar merge',
      description: 'Operação de alta consequência. UPDATE em 6 FKs em transação única. Aliases ficam ativo=False.'
    }
  ]
});
```

- [ ] **Step 5: IDs + includes nos 4 templates**

- [ ] **Step 6: Smoke test**

- [ ] **Step 7: Commit**

```bash
git add app/static/onboarding/tours/hora/{pecas_estoque,modelos_novo,modelos_pendencias,modelos_unificar}.js \
        app/templates/hora/pecas_estoque_lista.html \
        app/templates/hora/modelos_novo.html \
        app/templates/hora/modelos/
git commit -m "feat(onboarding): mini-tours HORA admin pacote 2 (pecas + modelos cadastro/pendencias/unificar)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 14: Mini-tours HORA admin pacote 3 (`tagplus_conta`, `permissoes`)

**Files:**
- Create: `app/static/onboarding/tours/hora/tagplus_conta.js`
- Create: `app/static/onboarding/tours/hora/permissoes.js`
- Modify: 2 templates

- [ ] **Step 1: `tagplus_conta.js`**

```javascript
window.OnboardingEngine.register({
  id: 'hora.tagplus_conta',
  titulo: 'Configurar conta TagPlus',
  requirePerm: { modulo: 'tagplus', acao: 'editar' },
  autoStartRoute: '/hora/tagplus/conta',
  steps: [
    {
      element: '#campo-client-id',
      title: 'Client ID do TagPlus',
      description: 'Vem do painel do TagPlus. Cole aqui — é o identificador da sua conta OAuth.'
    },
    {
      element: '#campo-client-secret',
      title: 'Client Secret (criptografado)',
      description: 'Salvamos com Fernet (HORA_TAGPLUS_ENC_KEY). <strong>Nunca aparece em plaintext de novo.</strong>'
    },
    {
      element: '#btn-iniciar-oauth',
      title: 'Autorizar via OAuth',
      description: 'Abre TagPlus pra você logar. Token volta no callback e fica salvo em hora_tagplus_token.'
    },
    {
      element: '#secao-checklist',
      title: 'Checklist de prontidão',
      description: 'Conta + token + mapeamento de produtos + formas de pagamento. NFe só emite com tudo verde.'
    }
  ]
});
```

- [ ] **Step 2: `permissoes.js`**

```javascript
window.OnboardingEngine.register({
  id: 'hora.permissoes',
  titulo: 'Gerenciar permissões de usuários',
  requirePerm: { modulo: 'usuarios', acao: 'ver' },
  autoStartRoute: '/hora/permissoes',
  steps: [
    {
      element: '#card-pendentes',
      title: 'Cadastros pendentes',
      description: 'Usuários novos esperando aprovação. Você define a loja deles e aprova. Sem loja = sem acesso.'
    },
    {
      element: '#tabela-usuarios',
      title: 'Lista de usuários ativos',
      description: 'Cada linha = 1 usuário com permissão HORA. Clique no nome para abrir a matriz módulo × ação.'
    },
    {
      element: '#matriz-modulos',
      title: 'Matriz granular',
      description: '21 módulos × 5 ações (Ver/Criar/Editar/Apagar/Aprovar). Marque só o que o usuário precisa.'
    },
    {
      element: '#btn-salvar-matriz',
      title: 'Salvar',
      description: 'Upsert em batch. Toma efeito no próximo refresh do usuário (cache por instância no current_user).'
    }
  ]
});
```

- [ ] **Step 3: IDs + includes nos 2 templates**

- [ ] **Step 4: Smoke test (logado como admin)**

- [ ] **Step 5: Commit**

```bash
git add app/static/onboarding/tours/hora/{tagplus_conta,permissoes}.js \
        app/templates/hora/tagplus/conta_form.html \
        app/templates/hora/permissoes_lista.html
git commit -m "feat(onboarding): mini-tours HORA admin pacote 3 (tagplus + permissoes)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 15: Mini-tours Motos Assaí admin (`pedidos_upload`, `compras_nova`, `recibos_upload`, `faturamento`, `modelos_assai`)

**Files:**
- Create: 5 arquivos JS em `app/static/onboarding/tours/motos_assai/`
- Modify: 5 templates

- [ ] **Step 1: `pedidos_upload.js`**

```javascript
window.OnboardingEngine.register({
  id: 'motos_assai.pedidos_upload',
  titulo: 'Subir pedido VOE Q.P.A.',
  adminOnly: true,
  autoStartRoute: '/motos-assai/pedidos/upload',
  steps: [
    {
      element: '#upload-area',
      title: 'PDF VOE do Sendas/Assaí',
      description: '38 páginas × 3 modelos = 114 itens em ~30s. Parser determinístico primeiro, fallback Haiku 4.5 → Sonnet 4.6.'
    },
    {
      element: '#area-preview',
      title: 'Preview por loja',
      description: 'Cada página = 1 loja Sendas (LJ12, LJ34...). Confira se identificou todas antes de salvar.'
    },
    {
      element: '#campo-confianca',
      title: 'Score de confiança',
      description: 'lojas_distintas / total_paginas. Abaixo de 70% dispara LLM. Abaixo de 50% bloqueia salvamento.'
    },
    {
      element: '#btn-salvar-pedido',
      title: 'Salvar como ABERTO',
      description: 'Cria assai_pedido_venda + N itens (loja × modelo). Pronto pra consolidar em compra Motochefe.'
    }
  ]
});
```

- [ ] **Step 2: `compras_nova.js`**

```javascript
window.OnboardingEngine.register({
  id: 'motos_assai.compras_nova',
  titulo: 'Consolidar compra Motochefe',
  adminOnly: true,
  autoStartRoute: '/motos-assai/compras/nova',
  steps: [
    {
      element: '#multiselect-pedidos',
      title: 'Selecione pedidos VOE',
      description: 'N pedidos viram 1 compra (PO). Sistema soma quantidades por modelo automaticamente.'
    },
    {
      element: '#preview-totalizadores',
      title: 'Preview do PO',
      description: 'Lista consolidada: modelo X qtd_total. Verifique antes de gerar — não tem desfazer trivial.'
    },
    {
      element: '#btn-gerar-compra',
      title: 'Criar compra MA-AAAA-NNNN',
      description: 'Cria assai_compra_motochefe + assai_compra_motochefe_pedido (N:N). Pedidos viram EM_PRODUCAO.'
    },
    {
      element: '#btn-baixar-pdf',
      title: 'Baixar PO em PDF',
      description: 'WeasyPrint renderiza modelo, qtd, total. Esse PDF vai pro vendedor da Motochefe.'
    }
  ]
});
```

- [ ] **Step 3: `recibos_upload.js`**

```javascript
window.OnboardingEngine.register({
  id: 'motos_assai.recibos_upload',
  titulo: 'Subir recibo Motochefe',
  adminOnly: true,
  autoStartRoute: '/motos-assai/recibos/upload',
  steps: [
    {
      element: '#upload-recibo',
      title: 'PDF ou XLSX',
      description: 'Recibo emitido pela equipe Motochefe (Haroldo SP, etc.). Lista os chassis que vão chegar fisicamente.'
    },
    {
      element: '#preview-chassis',
      title: 'Preview dos chassis extraídos',
      description: 'Confirme que o número total bate. Limiar de confiança 80% — abaixo disso aciona LLM.'
    },
    {
      element: '#btn-salvar-recibo',
      title: 'Salvar como AGUARDANDO',
      description: 'Status RECEBIDO_AGUARDANDO_CONFERENCIA. Operadores começam a conferir via wizard QR.'
    }
  ]
});
```

- [ ] **Step 4: `faturamento.js`**

```javascript
window.OnboardingEngine.register({
  id: 'motos_assai.faturamento',
  titulo: 'Faturamento Q.P.A.',
  adminOnly: true,
  autoStartRoute: '/motos-assai/faturamento',
  steps: [
    {
      element: '#tabela-separacoes-fechadas',
      title: 'Separações prontas',
      description: 'Aparecem aqui quando todos os chassis foram separados. Próximo passo: gerar Excel Q.P.A.'
    },
    {
      element: '#btn-gerar-excel',
      title: 'Gerar Excel Q.P.A.',
      description: '2 abas (PEDIDO + BASE LOJAS). Persiste em S3 + atualiza solicitacao_excel_s3_key. Espelha 285.xlsx.'
    },
    {
      element: '#btn-upload-nf',
      title: 'Subir NF Q.P.A.',
      description: 'Após Sendas emitir a NF, suba aqui. Parser DANFE adapter (CarVia) faz match BATEU/DIVERGENTE com tolerância 1%.'
    },
    {
      element: '#secao-resultado-match',
      title: 'Resultado do match',
      description: 'BATEU = separação vira FATURADA, chassis emitem evento FATURADA. DIVERGENTE = revisar manualmente.'
    }
  ]
});
```

- [ ] **Step 5: `modelos_assai.js`**

```javascript
window.OnboardingEngine.register({
  id: 'motos_assai.modelos_assai',
  titulo: 'Catálogo de modelos Q.P.A.',
  adminOnly: true,
  autoStartRoute: '/motos-assai/modelos',
  steps: [
    {
      element: '#tabela-modelos',
      title: 'Modelos cadastrados',
      description: 'X11_MINI, DOT, SOL... Cada um tem código + descrição + regex de chassi para validação.'
    },
    {
      element: '#campo-regex-chassi',
      title: 'Regex de chassi',
      description: 'Padrão esperado (ex: ^MZX\\d{10}$). Validação não-bloqueante na conferência — só sinaliza divergência.'
    },
    {
      element: '#secao-aliases',
      title: 'Aliases',
      description: '3 tipos: ALIAS_TIPO_QPA (código exato), ALIAS_TIPO_DESCRICAO_QPA (substring), ALIAS_TIPO_LIVRE.'
    },
    {
      element: '#btn-salvar-modelo',
      title: 'Salvar',
      description: 'Modelo + aliases ficam disponíveis para todos os parsers (pedido, recibo, NF Q.P.A.).'
    }
  ]
});
```

- [ ] **Step 6: IDs + includes nos 5 templates**

- [ ] **Step 7: Smoke test admin nas 5 telas**

- [ ] **Step 8: Commit**

```bash
git add app/static/onboarding/tours/motos_assai/{pedidos_upload,compras_nova,recibos_upload,faturamento,modelos_assai}.js \
        app/templates/motos_assai/pedidos/ \
        app/templates/motos_assai/compras/ \
        app/templates/motos_assai/recibos/ \
        app/templates/motos_assai/faturamento/ \
        app/templates/motos_assai/modelos/
git commit -m "feat(onboarding): mini-tours Assai admin (pedidos/compras/recibos/faturamento/modelos)

5 tours adminOnly com 4 passos cada.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 16: Página `/admin/onboarding/health`

**Files:**
- Create: `app/templates/admin/onboarding_health.html`
- Modify: `app/main/routes.py` ou módulo admin existente — adicionar rota

- [ ] **Step 1: Adicionar rota Flask (proteção admin-only)**

Localizar onde estão as rotas /admin (`grep -rn "@.*admin" app/main/routes.py | head`). Adicionar:
```python
from flask_login import login_required, current_user
from flask import abort, render_template

@main_bp.route('/admin/onboarding/health')
@login_required
def admin_onboarding_health():
    if current_user.perfil != 'administrador':
        abort(403)
    return render_template('admin/onboarding_health.html')
```

- [ ] **Step 2: Criar template `onboarding_health.html`**

```jinja
{% extends 'base.html' %}
{% block title %}Onboarding Health{% endblock %}
{% block content %}
<div class="container py-4">
  <h1>Onboarding — Health Check</h1>
  <p class="text-muted">Verifica se todos os selectors dos tours ainda existem no DOM das telas alvo.</p>

  <div class="mb-3">
    <button id="btn-run" class="btn btn-primary">Rodar verificação</button>
    <span id="status" class="ms-3 text-muted"></span>
  </div>

  <table class="table table-sm" id="results">
    <thead>
      <tr>
        <th>Tour</th>
        <th>Rota</th>
        <th>Passo</th>
        <th>Selector</th>
        <th>Encontrado?</th>
      </tr>
    </thead>
    <tbody></tbody>
  </table>
</div>

<script src="{{ url_for('static', filename='onboarding/lib/driver.min.js') }}"></script>
<script src="{{ url_for('static', filename='onboarding/core/localstorage_tracker.js') }}"></script>
<script src="{{ url_for('static', filename='onboarding/core/tour_engine.js') }}"></script>
{# Injeta TODOS os tours (HORA + Assai) — nesta tela queremos validar geral #}
<script>window.OnboardingContext = {user_id: 0, is_admin: true, permissoes: null};</script>
<script src="{{ url_for('static', filename='onboarding/tours/hora/_macro.js') }}"></script>
{# ... incluir todos os outros tours HORA + Assai aqui ... #}

<script>
document.getElementById('btn-run').addEventListener('click', async function () {
  const tbody = document.querySelector('#results tbody');
  tbody.innerHTML = '';
  const status = document.getElementById('status');
  status.textContent = 'Carregando...';

  // Lista todos os tours registrados
  const tours = window.OnboardingEngine.listAllVisible();

  for (const t of tours) {
    const tour = window.OnboardingEngine._registry?.[t.id]; // expor _registry no engine
    if (!tour) continue;
    const route = tour.autoStartRoute || '(sem rota)';

    // Para cada step, abre iframe na rota e verifica selector
    for (let i = 0; i < tour.steps.length; i++) {
      const step = tour.steps[i];
      const iframe = document.createElement('iframe');
      iframe.style.cssText = 'position:absolute;left:-9999px;width:1280px;height:800px;';
      iframe.src = route.replace(/\*/g, '1');
      document.body.appendChild(iframe);
      await new Promise(res => iframe.onload = res);
      let found = false;
      try {
        found = !!iframe.contentDocument.querySelector(step.element);
      } catch (e) {
        found = '(cross-origin?)';
      }
      iframe.remove();

      const tr = tbody.insertRow();
      tr.innerHTML = `<td>${t.id}</td><td>${route}</td><td>${i + 1}</td>
                     <td><code>${step.element}</code></td>
                     <td>${found === true ? '✅' : '❌'}</td>`;
    }
  }
  status.textContent = 'Concluído.';
});
</script>
{% endblock %}
```

- [ ] **Step 3: Expor `_registry` no engine para inspeção (mínima)**

Editar `app/static/onboarding/core/tour_engine.js`. No final do IIFE adicionar:
```javascript
window.OnboardingEngine._registry = registry;
```

- [ ] **Step 4: Smoke test**

Logar como admin, acessar `/admin/onboarding/health`, clicar "Rodar verificação". Expected: tabela popula com selectors encontrados (✅) e não-encontrados (❌). Útil pós-deploy.

- [ ] **Step 5: Commit**

```bash
git add app/templates/admin/onboarding_health.html app/main/routes.py app/static/onboarding/core/tour_engine.js
git commit -m "feat(onboarding): pagina /admin/onboarding/health para validar selectors

Itera todos os tours, abre cada autoStartRoute em iframe e checa querySelector
de cada step.element. Reporta ❌ quando selector quebrou apos mudanca de UI.
Admin-only.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 17: Página `/admin/onboarding/preview`

**Files:**
- Create: `app/templates/admin/onboarding_preview.html`
- Modify: `app/main/routes.py`

- [ ] **Step 1: Adicionar rota**

```python
@main_bp.route('/admin/onboarding/preview')
@login_required
def admin_onboarding_preview():
    if current_user.perfil != 'administrador':
        abort(403)
    tour_id = request.args.get('tour', '')
    return render_template('admin/onboarding_preview.html', tour_id=tour_id)
```

- [ ] **Step 2: Criar template**

```jinja
{% extends 'base.html' %}
{% block title %}Preview Tour: {{ tour_id }}{% endblock %}
{% block content %}
<div class="container py-4">
  <h1>Preview de Tour</h1>
  {% if not tour_id %}
    <p>Liste todos os tours via URL <code>?tour=&lt;id&gt;</code> e pressione Enter.</p>
    <ul id="lista-tours"></ul>
  {% else %}
    <p>Carregando tour <code>{{ tour_id }}</code> sem checar localStorage...</p>
    <div id="iframe-container"></div>
  {% endif %}
</div>

<script src="{{ url_for('static', filename='onboarding/lib/driver.min.js') }}"></script>
<script src="{{ url_for('static', filename='onboarding/core/localstorage_tracker.js') }}"></script>
<script src="{{ url_for('static', filename='onboarding/core/tour_engine.js') }}"></script>
<script>window.OnboardingContext = {user_id: 0, is_admin: true, permissoes: null};</script>
{# Incluir todos os tours HORA + Assai (mesmo bloco do health) #}
<script src="{{ url_for('static', filename='onboarding/tours/hora/_macro.js') }}"></script>

<script>
const tourId = "{{ tour_id }}";
if (!tourId) {
  const ul = document.getElementById('lista-tours');
  window.OnboardingEngine.listAllVisible().forEach(t => {
    const li = document.createElement('li');
    li.innerHTML = `<a href="?tour=${t.id}">${t.id}</a> — ${t.titulo}`;
    ul.appendChild(li);
  });
} else {
  const tour = window.OnboardingEngine._registry?.[tourId];
  if (tour && tour.autoStartRoute) {
    const iframe = document.createElement('iframe');
    iframe.src = tour.autoStartRoute.replace(/\*/g, '1');
    iframe.style.cssText = 'width:100%;height:80vh;border:1px solid #ccc;';
    iframe.onload = () => {
      // Inject helper to start tour ignoring localStorage
      try {
        iframe.contentWindow.OnboardingEngine.start(tourId);
      } catch (e) {
        alert('Erro ao iniciar tour: ' + e.message);
      }
    };
    document.getElementById('iframe-container').appendChild(iframe);
  } else {
    alert('Tour não encontrado: ' + tourId);
  }
}
</script>
{% endblock %}
```

- [ ] **Step 3: Smoke test**

Acessar `/admin/onboarding/preview?tour=hora.macro`. Expected: iframe carrega `/hora/dashboard` e dispara o macro automaticamente.

- [ ] **Step 4: Commit**

```bash
git add app/templates/admin/onboarding_preview.html app/main/routes.py
git commit -m "feat(onboarding): pagina /admin/onboarding/preview para revisar tours

Lista todos os tours OU dispara um especifico via ?tour=<id>.
Carrega iframe na autoStartRoute e chama start() ignorando localStorage.
Util para revisar tours sem precisar limpar conta de teste.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 18: Microcopy review + smoke test mobile real + cleanup

**Files:**
- Modify: arquivos `*.js` em `app/static/onboarding/tours/` (ajustes de texto)
- Create: `docs/onboarding/MICROCOPY_GUIDELINES.md` (opcional, referência futura)

- [ ] **Step 1: Audit de uniformidade de tom**

Run:
```bash
grep -rn "title:\|description:" app/static/onboarding/tours/ | wc -l
```

Para cada tour, conferir:
- Títulos em ≤5 palavras? Imperativo direto.
- Descrição em 1-2 frases?
- Uso de "Você" (não "O usuário")
- `<strong>` em pelo menos 1 destaque por mini-tour
- Sem emojis (registro profissional)

Editar inconsistências. Commit incrementais.

- [ ] **Step 2: Smoke test mobile real**

Pegar celular do usuário (Android padrão de operador). Acessar:
- `/motos-assai/recibos/<id>/conferir` → tour deve disparar, tooltip vira overlay full-width inferior
- `/motos-assai/montagem` → idem
- `/hora/recebimentos/novo` → idem (gerente pode usar tablet)

Se tooltip estiver cortado: adicionar `popoverOffset: 10` no `tour_engine.js` build.

- [ ] **Step 3: Verificar console limpo**

Em cada uma das 22 telas com tour, abrir DevTools console e checar:
- Sem `Tour <id> sem passos visíveis (selectors faltam?)` warning
- Sem 404 em `/static/onboarding/...`
- Sem erros JS

- [ ] **Step 4: Criar guideline curto (opcional)**

```markdown
# docs/onboarding/MICROCOPY_GUIDELINES.md

## Regras

- Título: ≤5 palavras, imperativo direto ("Suba o PDF da NF" — não "Aqui você sobe...")
- Descrição: 1-2 frases. Conteúdo operacional, não conceitual.
- Use "Você", não "O usuário".
- 1 `<strong>` por descrição para destacar a parte crítica.
- Sem emojis.
- Termos do domínio respeitados: chassi, recibo, Q.P.A., MONTADA, DISPONIVEL.

## Exemplo

```javascript
// Bom
{ title: 'Suba o PDF da NF', description: 'Arraste o DANFE recebido. <strong>Aceita só PDF</strong>. Parser extrai chassis em 5s.' }

// Ruim
{ title: 'Esta área serve para upload', description: 'O usuário deve, neste campo, fornecer o arquivo PDF da NFe contendo os dados a serem importados.' }
```
```

- [ ] **Step 5: Atualizar `app/hora/CLAUDE.md` e `app/motos_assai/CLAUDE.md`**

Adicionar seção:
```markdown
## Onboarding Tours

Tours guiados in-app via Driver.js. Spec: `docs/superpowers/specs/2026-05-08-onboarding-tours-hora-assai-design.md`.
- 1 macro adaptativo + N mini-tours por tela crítica
- Filtragem por permissão granular (HORA) ou is_admin (Assaí)
- Auto-start no 1º acesso, botão "?" no header sempre disponível
- Validação de saúde: `/admin/onboarding/health`
- Preview admin: `/admin/onboarding/preview?tour=<id>`
- Para adicionar tour novo: criar `app/static/onboarding/tours/<modulo>/<nome>.js` + IDs no template + include no `{% block onboarding_tours %}`
```

- [ ] **Step 6: Commit final**

```bash
git add docs/onboarding/MICROCOPY_GUIDELINES.md app/hora/CLAUDE.md app/motos_assai/CLAUDE.md
# + qualquer ajuste de microcopy
git commit -m "$(cat <<'EOF'
chore(onboarding): microcopy review + smoke mobile + docs

- Uniformizado tom dos tours (imperativo, 'Voce', 1 strong por descricao)
- Smoke test em mobile real validado (recebimento Assai + montagem)
- Console limpo em todas as 22 telas com tour
- MICROCOPY_GUIDELINES.md criado para tours futuros
- CLAUDE.md HORA + Assai atualizados com referencia ao onboarding

Encerra plano de implementacao 2026-05-08-onboarding-tours-hora-assai.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review

**Spec coverage:**
- Section 4.1 layout de arquivos → Tasks 1, 5, 6, 7-15 (cada arquivo coberto)
- Section 4.2 contexto injetado → Tasks 3, 4
- Section 4.3 endpoint API → Task 2
- Section 4.4 formato dos tours → Demonstrado em todos os tours das tasks 5-15
- Section 4.5 engine API → Task 1 step 3
- Section 4.6 macro adaptativo → Tasks 5 (HORA), 6 (Assaí)
- Section 5.1 catálogo HORA (1 macro + 13 minis) → Tasks 5, 7-9, 12-14 (3+4+4+2 = 13 minis ✓)
- Section 5.2 catálogo Assaí (1 macro + 9 minis) → Tasks 6, 10, 11 (3 minis chão), 15 (5 minis admin) — total 9 ✓
- Section 6 UX → Coberto em descrições dos tours + Task 18
- Section 7 ferramentas operação → Tasks 16 (health), 17 (preview)
- Section 8 manutenção → Task 18 step 4 (guideline)
- Section 9 plano faseado → Tasks 1-2 (F0), 3-6 (F1), 7-11 (F2), 12-15 (F3), 16-18 (F4)
- Section 10 riscos → Mitigações estão na implementação (locking, fallback selector, namespace user_id)

**Placeholder scan:**
- Sem TBD/TODO/etc
- Cada step tem código completo ou comando exato
- Templates referenciados pelo nome real (verificado em Task 1 lookup)

**Type consistency:**
- `OnboardingEngine.register/start/isVisible/listAllVisible` — consistente em tasks 1, 5, 6, etc
- `OnboardingTracker.wasSeen/markSeen/resetModule` — consistente
- `requirePerm: { modulo, acao }` (não `m, a` — corrigido na Section 4.6 do spec) → corrigido nos tours desta task
- `autoStartRoute` (não `auto_start_route`) — consistente

**Plano fechado.** Pronto para execução.

---

## Execução

**Plano completo e salvo em `docs/superpowers/plans/2026-05-08-onboarding-tours-hora-assai.md`. Duas opções de execução:**

**1. Subagent-Driven (recomendado)** — Subagente fresco por task, revisão entre tasks, iteração rápida

**2. Inline Execution** — Executa as tasks nesta sessão usando executing-plans, batch com checkpoints

**Qual abordagem?**
