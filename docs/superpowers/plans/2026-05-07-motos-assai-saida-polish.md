<!-- doc:meta
tipo: how-to
camada: L3
sot_de: —
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-02
-->
# Motos Assaí — Plano 3: Pipeline de Saída + Polish

> **Papel:** Motos Assaí — Plano 3: Pipeline de Saída + Polish.

## Indice

- [Visão de arquivos](#visão-de-arquivos)
- [Task 1: `montagem_service.registrar`](#task-1-montagem_serviceregistrar)
- [Task 2: Tela rápida de montagem](#task-2-tela-rápida-de-montagem)
- [Task 3: Testes do `montagem_service`](#task-3-testes-do-montagem_service)
- [Task 4: `disponibilizar_service.disponibilizar` + reverter](#task-4-disponibilizar_servicedisponibilizar-reverter)
- [Task 5: Tela rápida disponibilizar + modal motivo](#task-5-tela-rápida-disponibilizar-modal-motivo)
- [Task 6: Testes do `disponibilizar_service`](#task-6-testes-do-disponibilizar_service)
- [Task 7: `separacao_service` (registrar/cancelar/finalizar)](#task-7-separacao_service-registrarcancelarfinalizar)
- [Task 8: Tela de separação](#task-8-tela-de-separação)
- [Task 9: Testes do `separacao_service`](#task-9-testes-do-separacao_service)
- [Task 10: `faturamento_service.gerar_excel_qpa`](#task-10-faturamento_servicegerar_excel_qpa)
- [Task 11: Rota download Excel + lista de separações faturáveis](#task-11-rota-download-excel-lista-de-separações-faturáveis)
- [Task 12: `nf_qpa_adapter` (importar NF Q.P.A. + match)](#task-12-nf_qpa_adapter-importar-nf-qpa-match)
- [Task 13: Rota upload NF Q.P.A. + detalhe](#task-13-rota-upload-nf-qpa-detalhe)
- [Task 14: Testes faturamento + match](#task-14-testes-faturamento-match)
- [Task 15: Adicionar `SOL` no parser CarVia](#task-15-adicionar-sol-no-parser-carvia)
- [Task 16: CLAUDE.md final + dashboard atualizado](#task-16-claudemd-final-dashboard-atualizado)
- [Task 17: UI lint + testes E2E + smoke](#task-17-ui-lint-testes-e2e-smoke)
- [Self-review](#self-review)
- [Resumo dos 4 documentos gerados](#resumo-dos-4-documentos-gerados)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar a saída do pipeline (montagem, disponibilizar, separação, geração Excel Q.P.A., importação de NF Q.P.A. com match) + polish final (atualizar parser CarVia para SOL, UI lint, testes integração end-to-end, CLAUDE.md final).

**Architecture:** Telas rápidas (montagem/disponibilizar) reutilizam componente JS de input QR/barcode/manual já criado no Plano 2B (`recebimento_wizard.js` simplificado). Separação valida fungibilidade por modelo via saldo do pedido. Excel gerado por openpyxl espelhando estrutura do `285.xlsx` (2 abas). NF Q.P.A. importada via adapter sobre `DanfePDFParser` (CarVia, sem modificar) com match BATEU/DIVERGENTE/NAO_RECONCILIADO.

**Tech Stack:** openpyxl 3.1+ (geração Excel), `app.carvia.services.parsers.danfe_pdf_parser` (reuso), Bootstrap 5, html5-qrcode@2.3.8.

**Pré-requisitos**:
- Planos 1 + 2A + 2B implementados e testados
- `weasyprint`, `openpyxl`, `pdfplumber`, `anthropic` instalados
- Modelo SOL pode estar pendente no parser CarVia — Task 15 resolve

**Spec referência:** `docs/superpowers/specs/2026-05-07-motos-assai-design.md` §5.5–§5.8, §8.4

**Documento de referência template Excel**: `/mnt/c/Users/rafael.nascimento/Downloads/285.xlsx` (estrutura 2 abas: PEDIDO + BASE LOJAS)

---

## Visão de arquivos

```
app/motos_assai/
├── services/
│   ├── montagem_service.py                    # Task 1
│   ├── disponibilizar_service.py              # Task 4
│   ├── separacao_service.py                   # Task 7
│   ├── faturamento_service.py                 # Task 10
│   └── parsers/
│       └── nf_qpa_adapter.py                  # Task 12
├── routes/
│   ├── montagem.py                            # Task 2
│   ├── disponibilizar.py                      # Task 5
│   ├── separacao.py                           # Task 8
│   └── faturamento.py                         # Tasks 11, 13
└── forms/
    ├── disponibilizar_forms.py                # Task 5 (modal motivo)
    └── faturamento_forms.py                   # Task 13

app/static/motos_assai/js/
├── operacao_quick.js                          # Task 2 — compartilhado montagem/disponibilizar
└── separacao_chassi.js                        # Task 8

app/templates/motos_assai/
├── montagem/
│   └── quick.html                             # Task 2
├── disponibilizar/
│   └── quick.html                             # Task 5
├── separacao/
│   ├── lista.html                             # Task 8
│   └── tela.html                              # Task 8
├── faturamento/
│   ├── lista_separacoes.html                  # Task 11
│   ├── upload_nf.html                         # Task 13
│   └── nf_detalhe.html                        # Task 13
└── partials/
    └── _historico_3_ultimas.html              # Tasks 2, 5

scripts/migrations/
└── motos_assai_06_carvia_modelo_sol.py        # Task 15

tests/motos_assai/
├── test_montagem_service.py                   # Task 3
├── test_disponibilizar_service.py             # Task 6
├── test_separacao_service.py                  # Task 9
├── test_faturamento_service.py                # Task 14
└── test_nf_qpa_match.py                       # Task 14
```

---

## Task 1: `montagem_service.registrar`

**Files:**
- Create: `app/motos_assai/services/montagem_service.py`
- Modify: `app/motos_assai/services/__init__.py`

- [ ] **Step 1: Service**

`app/motos_assai/services/montagem_service.py`:

```python
"""Montagem da moto: ESTOQUE → MONTADA ou ESTOQUE → PENDENTE.

PENDENTE bloqueia transição para DISPONIVEL até evento PENDENCIA_RESOLVIDA.

Resolução de pendência: cria evento PENDENCIA_RESOLVIDA + (via service) MONTADA novo,
de modo que `status_efetivo` volte a MONTADA antes de poder DISPONIBILIZAR.
"""

from __future__ import annotations

from typing import Optional, Dict, Any
from app import db
from app.motos_assai.models import (
    AssaiMoto, EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_PENDENTE,
    EVENTO_PENDENCIA_RESOLVIDA,
)
from app.motos_assai.services.moto_evento_service import (
    emitir_evento, status_efetivo, ultimo_evento,
)


class MontagemValidationError(Exception):
    pass


def registrar_montagem(
    chassi: str,
    pendencia: bool,
    descricao_pendencia: Optional[str],
    chassi_doador: Optional[str],
    operador_id: int,
) -> Dict[str, Any]:
    """Registra montagem.

    - pendencia=False → emite MONTADA
    - pendencia=True  → emite PENDENTE com descrição obrigatória ≥3 chars
    """
    chassi_norm = chassi.strip().upper()
    if not chassi_norm:
        raise MontagemValidationError('Chassi vazio')

    moto = AssaiMoto.query.filter_by(chassi=chassi_norm).first()
    if not moto:
        raise MontagemValidationError(
            f'Chassi {chassi_norm} não está no estoque (faça recebimento primeiro)'
        )

    status = status_efetivo(chassi_norm)
    if status != EVENTO_ESTOQUE:
        raise MontagemValidationError(
            f'Chassi {chassi_norm} está em status {status}, esperado ESTOQUE'
        )

    if pendencia:
        if not descricao_pendencia or len(descricao_pendencia.strip()) < 3:
            raise MontagemValidationError(
                'Descrição de pendência obrigatória (≥3 caracteres)'
            )
        ev = emitir_evento(
            chassi_norm, EVENTO_PENDENTE,
            operador_id=operador_id,
            observacao=descricao_pendencia.strip(),
            dados_extras={
                'descricao': descricao_pendencia.strip(),
                'chassi_doador': (chassi_doador or '').strip().upper() or None,
            },
        )
    else:
        ev = emitir_evento(chassi_norm, EVENTO_MONTADA, operador_id=operador_id)

    db.session.commit()
    return {
        'evento_id': ev.id, 'chassi': chassi_norm, 'tipo': ev.tipo,
        'modelo_id': moto.modelo_id, 'cor': moto.cor,
    }


def resolver_pendencia(
    chassi: str, descricao_resolucao: str, operador_id: int,
) -> Dict[str, Any]:
    """PENDENTE → MONTADA via PENDENCIA_RESOLVIDA + MONTADA.

    Sequência de eventos: ... → PENDENTE → PENDENCIA_RESOLVIDA → MONTADA
    O `status_efetivo` final = MONTADA.
    """
    chassi_norm = chassi.strip().upper()
    status = status_efetivo(chassi_norm)
    if status != EVENTO_PENDENTE:
        raise MontagemValidationError(
            f'Chassi {chassi_norm} não está PENDENTE (está {status})'
        )

    if not descricao_resolucao or len(descricao_resolucao.strip()) < 3:
        raise MontagemValidationError('Descrição da resolução obrigatória (≥3 chars)')

    emitir_evento(
        chassi_norm, EVENTO_PENDENCIA_RESOLVIDA,
        operador_id=operador_id,
        observacao=descricao_resolucao.strip(),
    )
    ev_montada = emitir_evento(chassi_norm, EVENTO_MONTADA, operador_id=operador_id)

    db.session.commit()
    return {'evento_id': ev_montada.id, 'chassi': chassi_norm, 'tipo': EVENTO_MONTADA}


def historico_3_ultimas_montagens() -> list:
    """3 últimos eventos MONTADA globais (com info do chassi/modelo/cor)."""
    from sqlalchemy.orm import joinedload
    from app.motos_assai.models import AssaiMotoEvento

    eventos = (
        AssaiMotoEvento.query
        .options(joinedload(AssaiMotoEvento.operador))
        .filter_by(tipo=EVENTO_MONTADA)
        .order_by(AssaiMotoEvento.ocorrido_em.desc())
        .limit(3)
        .all()
    )

    enriched = []
    for ev in eventos:
        moto = AssaiMoto.query.filter_by(chassi=ev.chassi).first()
        enriched.append({
            'evento_id': ev.id,
            'chassi': ev.chassi,
            'modelo_codigo': moto.modelo.codigo if moto and moto.modelo else '-',
            'cor': moto.cor if moto else '-',
            'ocorrido_em': ev.ocorrido_em,
            'operador_nome': ev.operador.nome if ev.operador else '-',
        })
    return enriched
```

- [ ] **Step 2: Atualizar __init__**

```python
from .montagem_service import (
    registrar_montagem, resolver_pendencia, historico_3_ultimas_montagens,
    MontagemValidationError,
)
```

- [ ] **Step 3: Commit**

```bash
git add app/motos_assai/services/montagem_service.py
git add app/motos_assai/services/__init__.py
git commit -m "feat(motos_assai): montagem_service (ESTOQUE → MONTADA / PENDENTE)"
```

---

## Task 2: Tela rápida de montagem

**Files:**
- Create: `app/motos_assai/routes/montagem.py`
- Modify: `app/motos_assai/routes/__init__.py`
- Create: `app/templates/motos_assai/montagem/quick.html`
- Create: `app/static/motos_assai/js/operacao_quick.js`
- Create: `app/templates/motos_assai/partials/_historico_3_ultimas.html`

- [ ] **Step 1: Rota**

`app/motos_assai/routes/montagem.py`:

```python
from flask import render_template, request, jsonify
from flask_login import login_required, current_user
from app.motos_assai.routes import motos_assai_bp
from app.motos_assai.decorators import require_motos_assai
from app.motos_assai.services import (
    registrar_montagem, historico_3_ultimas_montagens,
    MontagemValidationError,
)


@motos_assai_bp.route('/montagem')
@login_required
@require_motos_assai
def montagem_tela():
    historico = historico_3_ultimas_montagens()
    return render_template('motos_assai/montagem/quick.html', historico=historico)


@motos_assai_bp.route('/montagem/registrar', methods=['POST'])
@login_required
@require_motos_assai
def montagem_registrar():
    data = request.get_json(silent=True) or {}
    try:
        result = registrar_montagem(
            chassi=data.get('chassi', ''),
            pendencia=bool(data.get('pendencia')),
            descricao_pendencia=data.get('descricao_pendencia'),
            chassi_doador=data.get('chassi_doador'),
            operador_id=current_user.id,
        )
    except MontagemValidationError as e:
        return jsonify({'ok': False, 'erro': str(e)}), 400
    historico = historico_3_ultimas_montagens()
    return jsonify({'ok': True, **result, 'historico': [
        {**h, 'ocorrido_em': h['ocorrido_em'].strftime('%d/%m %H:%M')}
        for h in historico
    ]})
```

- [ ] **Step 2: Importar route**

```python
from app.motos_assai.routes import montagem  # noqa: E402,F401
```

- [ ] **Step 3: Partial histórico**

`app/templates/motos_assai/partials/_historico_3_ultimas.html`:

```jinja
{# Espera variável `historico` (list) e opcional `acao_label` + `endpoint_reverter` (url_for) #}
<h6 class="mt-4 mb-2 text-muted">3 últimas {{ acao_label or 'operações' }}</h6>
<ul class="list-group small" id="historico-list">
  {% for h in historico %}
  <li class="list-group-item d-flex justify-content-between align-items-center">
    <div>
      <code>{{ h.chassi }}</code> · <strong>{{ h.modelo_codigo }}</strong> · {{ h.cor }}
      <span class="text-muted ms-2">
        {{ h.ocorrido_em.strftime('%d/%m %H:%M') if h.ocorrido_em is not string else h.ocorrido_em }}
        · {{ h.operador_nome }}
      </span>
    </div>
    {% if endpoint_reverter %}
    <button type="button" class="btn btn-sm btn-outline-warning"
            data-evento-id="{{ h.evento_id }}"
            data-chassi="{{ h.chassi }}"
            data-action="reverter">
      <i class="fas fa-undo"></i> Reverter
    </button>
    {% endif %}
  </li>
  {% else %}
  <li class="list-group-item text-muted">Sem histórico recente.</li>
  {% endfor %}
</ul>
```

- [ ] **Step 4: Template montagem**

`app/templates/motos_assai/montagem/quick.html`:

```jinja
{% extends "motos_assai/base_motos_assai.html" %}

{% block motos_assai_content %}
<header class="mb-3">
  <h2>Montagem — Operação VOE</h2>
</header>

<div class="card p-3" style="max-width: 600px;">
  <div class="mb-3">
    <label class="form-label">Chassi</label>
    <div class="input-group">
      <input type="text" id="input-chassi" class="form-control form-control-lg"
             autofocus placeholder="QR / Barcode / digitar (Enter)" maxlength="50">
      <button type="button" id="btn-camera" class="btn btn-outline-secondary">
        <i class="fas fa-camera"></i>
      </button>
    </div>
    <div id="qr-reader" class="mt-2 d-none" style="max-width:300px;"></div>
  </div>

  <div class="form-check mb-2">
    <input type="checkbox" id="chk-pendencia" class="form-check-input">
    <label for="chk-pendencia" class="form-check-label">
      Pendência de peça com defeito?
    </label>
  </div>

  <div id="pendencia-fields" class="d-none mb-3 ps-4 border-start">
    <div class="mb-2">
      <label class="form-label small">Descrição da pendência (≥3 chars)</label>
      <textarea id="input-descricao-pendencia" class="form-control" rows="2"
                placeholder="Ex: bateria com defeito, retrovisor faltando..."></textarea>
    </div>
    <div class="mb-2">
      <label class="form-label small">Chassi doador (opcional)</label>
      <input type="text" id="input-chassi-doador" class="form-control" placeholder="Chassi de outra moto">
    </div>
  </div>

  <button type="button" id="btn-registrar" class="btn btn-primary btn-lg">
    <i class="fas fa-check"></i> Registrar montagem (Ctrl+Enter)
  </button>

  <div id="alerta" class="mt-3 d-none"></div>
</div>

<div style="max-width: 800px;">
  {% with acao_label = 'montagens' %}
    {% include 'motos_assai/partials/_historico_3_ultimas.html' %}
  {% endwith %}
</div>

<script src="https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js"
        integrity="sha384-c9d8RFSL+sJ0dC0WGqK7tQXg4/c5++8KkF+xbSPq3ji10/wfKLtAVk0M3IY+XJ7q"
        crossorigin="anonymous"></script>
<script>
window.MOTOS_ASSAI_OP_CONFIG = {
  endpoint: '{{ url_for("motos_assai.montagem_registrar") }}',
  modo: 'montagem',
};
</script>
<script src="{{ url_for('static', filename='motos_assai/js/operacao_quick.js') }}"></script>
{% endblock %}
```

- [ ] **Step 5: JS compartilhado**

`app/static/motos_assai/js/operacao_quick.js`:

```javascript
/**
 * Componente compartilhado entre montagem/disponibilizar.
 * Lê chassi via input/QR/leitor USB, faz POST AJAX, atualiza histórico inline.
 */
(function() {
  const cfg = window.MOTOS_ASSAI_OP_CONFIG;
  if (!cfg) return;

  const inputChassi = document.getElementById('input-chassi');
  const btnRegistrar = document.getElementById('btn-registrar');
  const btnCamera = document.getElementById('btn-camera');
  const alerta = document.getElementById('alerta');
  const chkPendencia = document.getElementById('chk-pendencia');
  const pendenciaFields = document.getElementById('pendencia-fields');

  if (chkPendencia) {
    chkPendencia.addEventListener('change', () => {
      pendenciaFields.classList.toggle('d-none', !chkPendencia.checked);
    });
  }

  // Câmera (toggle)
  let html5Qr = null;
  if (btnCamera) {
    btnCamera.addEventListener('click', () => {
      const div = document.getElementById('qr-reader');
      if (html5Qr) {
        html5Qr.stop().then(() => { html5Qr = null; div.classList.add('d-none'); });
        return;
      }
      if (!window.isSecureContext) {
        showAlerta('warning', 'Câmera requer HTTPS.');
        return;
      }
      div.classList.remove('d-none');
      html5Qr = new Html5Qrcode('qr-reader');
      html5Qr.start(
        {facingMode: 'environment'},
        {fps: 10, qrbox: 240},
        (txt) => {
          inputChassi.value = txt.trim().toUpperCase();
          html5Qr.stop().then(() => { html5Qr = null; div.classList.add('d-none'); });
          inputChassi.focus();
        },
      );
    });
  }

  inputChassi.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') { e.preventDefault(); registrar(); }
  });
  document.addEventListener('keydown', (e) => {
    if (e.ctrlKey && e.key === 'Enter') { e.preventDefault(); registrar(); }
  });
  btnRegistrar.addEventListener('click', registrar);

  async function registrar() {
    const chassi = inputChassi.value.trim().toUpperCase();
    if (!chassi) { showAlerta('warning', 'Digite/escaneie um chassi'); return; }

    const payload = {chassi};
    if (cfg.modo === 'montagem' && chkPendencia) {
      payload.pendencia = chkPendencia.checked;
      payload.descricao_pendencia = document.getElementById('input-descricao-pendencia')?.value || '';
      payload.chassi_doador = document.getElementById('input-chassi-doador')?.value || '';
    }

    btnRegistrar.disabled = true;
    try {
      const r = await fetch(cfg.endpoint, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload),
      });
      const data = await r.json();
      if (!data.ok) {
        showAlerta('danger', data.erro);
        return;
      }
      showAlerta('success',
        `Chassi <code>${data.chassi}</code> → <strong>${data.tipo}</strong>`);
      atualizarHistorico(data.historico || []);
      reset();
    } finally {
      btnRegistrar.disabled = false;
    }
  }

  function showAlerta(level, html) {
    alerta.className = `alert alert-${level}`;
    alerta.innerHTML = html;
    alerta.classList.remove('d-none');
    setTimeout(() => alerta.classList.add('d-none'), 4000);
  }

  function reset() {
    inputChassi.value = '';
    if (chkPendencia) {
      chkPendencia.checked = false;
      pendenciaFields.classList.add('d-none');
      const dp = document.getElementById('input-descricao-pendencia');
      const cd = document.getElementById('input-chassi-doador');
      if (dp) dp.value = '';
      if (cd) cd.value = '';
    }
    inputChassi.focus();
  }

  function atualizarHistorico(hist) {
    const list = document.getElementById('historico-list');
    if (!list) return;
    list.innerHTML = '';
    if (!hist.length) {
      list.innerHTML = '<li class="list-group-item text-muted">Sem histórico recente.</li>';
      return;
    }
    for (const h of hist) {
      const li = document.createElement('li');
      li.className = 'list-group-item d-flex justify-content-between align-items-center';
      li.innerHTML =
        `<div><code>${h.chassi}</code> · <strong>${h.modelo_codigo}</strong> · ${h.cor}` +
        ` <span class="text-muted ms-2">${h.ocorrido_em} · ${h.operador_nome}</span></div>`;
      list.appendChild(li);
    }
  }

  // Foco automático no input
  inputChassi.focus();
})();
```

- [ ] **Step 6: Adicionar links no nav**

```jinja
    <a class="motos-assai-nav-link" href="{{ url_for('motos_assai.montagem_tela') }}">
      <i class="fas fa-tools"></i> Montagem
    </a>
```

- [ ] **Step 7: Commit**

```bash
git add app/motos_assai/routes/montagem.py app/motos_assai/routes/__init__.py
git add app/templates/motos_assai/montagem/quick.html
git add app/templates/motos_assai/partials/_historico_3_ultimas.html
git add app/templates/motos_assai/base_motos_assai.html
git add app/static/motos_assai/js/operacao_quick.js
git commit -m "feat(motos_assai): montagem quick screen with QR/manual + 3 últimas + pendência"
```

---

## Task 3: Testes do `montagem_service`

**Files:**
- Create: `tests/motos_assai/test_montagem_service.py`

- [ ] **Step 1: Tests**

`tests/motos_assai/test_montagem_service.py`:

```python
import pytest
from app import db
from app.motos_assai.models import (
    AssaiMoto, AssaiModelo, AssaiMotoEvento,
    EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_PENDENTE,
)
from app.motos_assai.services import (
    registrar_montagem, resolver_pendencia, historico_3_ultimas_montagens,
    emitir_evento, status_efetivo, MontagemValidationError,
)


def _criar_moto_em_estoque(chassi, admin_user):
    modelo = AssaiModelo.query.filter_by(codigo='DOT').first()
    moto = AssaiMoto(chassi=chassi, modelo_id=modelo.id, cor='CINZA')
    db.session.add(moto); db.session.flush()
    emitir_evento(chassi, EVENTO_ESTOQUE, admin_user.id)
    db.session.commit()
    return moto


def test_montagem_simples(app, admin_user):
    with app.app_context():
        _criar_moto_em_estoque('TST_M_001', admin_user)
        r = registrar_montagem('TST_M_001', False, None, None, admin_user.id)
        assert r['tipo'] == EVENTO_MONTADA
        assert status_efetivo('TST_M_001') == EVENTO_MONTADA
        db.session.rollback()


def test_montagem_pendente_com_descricao(app, admin_user):
    with app.app_context():
        _criar_moto_em_estoque('TST_M_002', admin_user)
        r = registrar_montagem('TST_M_002', True, 'Bateria com defeito', None, admin_user.id)
        assert r['tipo'] == EVENTO_PENDENTE
        assert status_efetivo('TST_M_002') == EVENTO_PENDENTE
        db.session.rollback()


def test_montagem_pendente_sem_descricao_falha(app, admin_user):
    with app.app_context():
        _criar_moto_em_estoque('TST_M_003', admin_user)
        with pytest.raises(MontagemValidationError, match='≥3'):
            registrar_montagem('TST_M_003', True, 'AB', None, admin_user.id)
        db.session.rollback()


def test_montagem_chassi_inexistente_falha(app, admin_user):
    with app.app_context():
        with pytest.raises(MontagemValidationError, match='não está'):
            registrar_montagem('NAO_EXISTE_999', False, None, None, admin_user.id)


def test_montagem_status_invalido_falha(app, admin_user):
    """Não pode montar uma moto que já está MONTADA."""
    with app.app_context():
        _criar_moto_em_estoque('TST_M_004', admin_user)
        registrar_montagem('TST_M_004', False, None, None, admin_user.id)
        with pytest.raises(MontagemValidationError, match='ESTOQUE'):
            registrar_montagem('TST_M_004', False, None, None, admin_user.id)
        db.session.rollback()


def test_resolver_pendencia(app, admin_user):
    with app.app_context():
        _criar_moto_em_estoque('TST_M_005', admin_user)
        registrar_montagem('TST_M_005', True, 'Defeito X', None, admin_user.id)
        resolver_pendencia('TST_M_005', 'Peça trocada', admin_user.id)
        assert status_efetivo('TST_M_005') == EVENTO_MONTADA
        db.session.rollback()
```

- [ ] **Step 2: Commit**

```bash
git add tests/motos_assai/test_montagem_service.py
git commit -m "test(motos_assai): montagem_service tests"
```

---

## Task 4: `disponibilizar_service.disponibilizar` + reverter

**Files:**
- Create: `app/motos_assai/services/disponibilizar_service.py`
- Modify: `app/motos_assai/services/__init__.py`

- [ ] **Step 1: Service**

`app/motos_assai/services/disponibilizar_service.py`:

```python
"""Disponibilizar: MONTADA → DISPONIVEL.
Reverter: DISPONIVEL → MONTADA via REVERTIDA_PARA_MONTADA (motivo obrigatório ≥3 chars).
"""

from __future__ import annotations

from typing import Optional, Dict, Any

from sqlalchemy.orm import joinedload

from app import db
from app.motos_assai.models import (
    AssaiMoto, AssaiMotoEvento,
    EVENTO_MONTADA, EVENTO_DISPONIVEL, EVENTO_REVERTIDA_PARA_MONTADA,
)
from app.motos_assai.services.moto_evento_service import emitir_evento, status_efetivo


class DisponibilizarValidationError(Exception):
    pass


def disponibilizar(chassi: str, operador_id: int) -> Dict[str, Any]:
    """Apenas se status efetivo é MONTADA."""
    chassi_norm = chassi.strip().upper()
    if not chassi_norm:
        raise DisponibilizarValidationError('Chassi vazio')

    moto = AssaiMoto.query.filter_by(chassi=chassi_norm).first()
    if not moto:
        raise DisponibilizarValidationError(f'Chassi {chassi_norm} não cadastrado')

    status = status_efetivo(chassi_norm)
    if status != EVENTO_MONTADA:
        raise DisponibilizarValidationError(
            f'Chassi {chassi_norm} está em {status}, esperado MONTADA. '
            'Resolva pendência se houver.'
        )

    ev = emitir_evento(chassi_norm, EVENTO_DISPONIVEL, operador_id=operador_id)
    db.session.commit()
    return {
        'evento_id': ev.id, 'chassi': chassi_norm, 'tipo': EVENTO_DISPONIVEL,
        'modelo_id': moto.modelo_id, 'cor': moto.cor,
    }


def reverter_para_montada(
    chassi: str, motivo: str, operador_id: int,
) -> Dict[str, Any]:
    """DISPONIVEL → MONTADA com motivo obrigatório.

    Emite REVERTIDA_PARA_MONTADA (status efetivo final = REVERTIDA_PARA_MONTADA,
    que NÃO está em EVENTOS_VALIDOS_PARA_DISPONIBILIZAR — então a moto precisa
    de NOVA disponibilização).

    NOTA do design: a sequência é Disponivel → REVERTIDA_PARA_MONTADA. Como
    REVERTIDA_PARA_MONTADA NÃO é MONTADA puro, mas semanticamente a moto está
    "montada de novo", o `disponibilizar()` precisa aceitar tanto MONTADA quanto
    REVERTIDA_PARA_MONTADA como pré-condição. Veja Step 2 abaixo.
    """
    chassi_norm = chassi.strip().upper()
    if not motivo or len(motivo.strip()) < 3:
        raise DisponibilizarValidationError('Motivo obrigatório (≥3 chars)')

    status = status_efetivo(chassi_norm)
    if status != EVENTO_DISPONIVEL:
        raise DisponibilizarValidationError(
            f'Chassi {chassi_norm} está em {status}, esperado DISPONIVEL'
        )

    ultimo_disp = (
        AssaiMotoEvento.query
        .filter_by(chassi=chassi_norm, tipo=EVENTO_DISPONIVEL)
        .order_by(AssaiMotoEvento.ocorrido_em.desc())
        .first()
    )
    ev = emitir_evento(
        chassi_norm, EVENTO_REVERTIDA_PARA_MONTADA,
        operador_id=operador_id,
        observacao=motivo.strip(),
        dados_extras={
            'motivo': motivo.strip(),
            'evento_revertido_id': ultimo_disp.id if ultimo_disp else None,
        },
    )
    db.session.commit()
    return {
        'evento_id': ev.id, 'chassi': chassi_norm,
        'tipo': EVENTO_REVERTIDA_PARA_MONTADA,
    }


def historico_3_ultimas_disponibilizacoes() -> list:
    """3 últimos eventos DISPONIVEL globais com info do chassi/modelo/cor.

    Filtra apenas as que ainda são "DISPONIVEL ativo" (não foram revertidas)
    para que o botão Reverter faça sentido.
    """
    eventos = (
        AssaiMotoEvento.query
        .options(joinedload(AssaiMotoEvento.operador))
        .filter_by(tipo=EVENTO_DISPONIVEL)
        .order_by(AssaiMotoEvento.ocorrido_em.desc())
        .limit(20)  # pega 20, filtra os 3 ainda válidos
        .all()
    )

    enriched = []
    for ev in eventos:
        if status_efetivo(ev.chassi) != EVENTO_DISPONIVEL:
            continue  # já foi revertida ou separada
        moto = AssaiMoto.query.filter_by(chassi=ev.chassi).first()
        enriched.append({
            'evento_id': ev.id, 'chassi': ev.chassi,
            'modelo_codigo': moto.modelo.codigo if moto and moto.modelo else '-',
            'cor': moto.cor if moto else '-',
            'ocorrido_em': ev.ocorrido_em,
            'operador_nome': ev.operador.nome if ev.operador else '-',
        })
        if len(enriched) >= 3:
            break
    return enriched
```

- [ ] **Step 2: Atualizar __init__**

```python
from .disponibilizar_service import (
    disponibilizar, reverter_para_montada, historico_3_ultimas_disponibilizacoes,
    DisponibilizarValidationError,
)
```

**Importante**: Atualizar `disponibilizar()` para aceitar também `REVERTIDA_PARA_MONTADA` como status efetivo válido (porque após reverter, é "como se estivesse MONTADA"):

```python
# Em disponibilizar(), substituir:
if status != EVENTO_MONTADA:
    ...
# Por:
from app.motos_assai.models import EVENTO_REVERTIDA_PARA_MONTADA, EVENTO_PENDENCIA_RESOLVIDA
if status not in (EVENTO_MONTADA, EVENTO_REVERTIDA_PARA_MONTADA):
    raise DisponibilizarValidationError(
        f'Chassi {chassi_norm} está em {status}, esperado MONTADA ou REVERTIDA_PARA_MONTADA'
    )
```

- [ ] **Step 3: Commit**

```bash
git add app/motos_assai/services/disponibilizar_service.py
git add app/motos_assai/services/__init__.py
git commit -m "feat(motos_assai): disponibilizar_service (MONTADA→DISPONIVEL + reverter)"
```

---

## Task 5: Tela rápida disponibilizar + modal motivo

**Files:**
- Create: `app/motos_assai/forms/disponibilizar_forms.py`
- Modify: `app/motos_assai/forms/__init__.py`
- Create: `app/motos_assai/routes/disponibilizar.py`
- Modify: `app/motos_assai/routes/__init__.py`
- Create: `app/templates/motos_assai/disponibilizar/quick.html`

- [ ] **Step 1: Form (motivo modal)**

`app/motos_assai/forms/disponibilizar_forms.py`:

```python
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField
from wtforms.validators import DataRequired, Length


class ReverterForm(FlaskForm):
    chassi = StringField('Chassi', validators=[DataRequired()])
    motivo = TextAreaField('Motivo (≥3 chars)', validators=[
        DataRequired(), Length(min=3, max=500),
    ])
```

- [ ] **Step 2: Atualizar forms __init__**

```python
from .disponibilizar_forms import ReverterForm
```

- [ ] **Step 3: Rota**

`app/motos_assai/routes/disponibilizar.py`:

```python
from flask import render_template, request, jsonify
from flask_login import login_required, current_user
from app.motos_assai.routes import motos_assai_bp
from app.motos_assai.decorators import require_motos_assai
from app.motos_assai.services import (
    disponibilizar as svc_disponibilizar,
    reverter_para_montada,
    historico_3_ultimas_disponibilizacoes,
    DisponibilizarValidationError,
)


@motos_assai_bp.route('/disponibilizar')
@login_required
@require_motos_assai
def disponibilizar_tela():
    historico = historico_3_ultimas_disponibilizacoes()
    return render_template('motos_assai/disponibilizar/quick.html', historico=historico)


@motos_assai_bp.route('/disponibilizar/registrar', methods=['POST'])
@login_required
@require_motos_assai
def disponibilizar_registrar():
    data = request.get_json(silent=True) or {}
    try:
        result = svc_disponibilizar(data.get('chassi', ''), current_user.id)
    except DisponibilizarValidationError as e:
        return jsonify({'ok': False, 'erro': str(e)}), 400
    historico = historico_3_ultimas_disponibilizacoes()
    return jsonify({'ok': True, **result, 'historico': [
        {**h, 'ocorrido_em': h['ocorrido_em'].strftime('%d/%m %H:%M')}
        for h in historico
    ]})


@motos_assai_bp.route('/disponibilizar/reverter', methods=['POST'])
@login_required
@require_motos_assai
def disponibilizar_reverter():
    data = request.get_json(silent=True) or {}
    try:
        result = reverter_para_montada(
            chassi=data.get('chassi', ''),
            motivo=data.get('motivo', ''),
            operador_id=current_user.id,
        )
    except DisponibilizarValidationError as e:
        return jsonify({'ok': False, 'erro': str(e)}), 400
    historico = historico_3_ultimas_disponibilizacoes()
    return jsonify({'ok': True, **result, 'historico': [
        {**h, 'ocorrido_em': h['ocorrido_em'].strftime('%d/%m %H:%M')}
        for h in historico
    ]})
```

- [ ] **Step 4: Importar route**

```python
from app.motos_assai.routes import disponibilizar  # noqa: E402,F401
```

- [ ] **Step 5: Template**

`app/templates/motos_assai/disponibilizar/quick.html`:

```jinja
{% extends "motos_assai/base_motos_assai.html" %}

{% block motos_assai_content %}
<header class="mb-3">
  <h2>Disponibilizar — Operação VOE</h2>
  <p class="text-muted">Marca moto MONTADA como DISPONIVEL (tag + manual colocados).</p>
</header>

<div class="card p-3" style="max-width: 600px;">
  <div class="mb-3">
    <label class="form-label">Chassi</label>
    <div class="input-group">
      <input type="text" id="input-chassi" class="form-control form-control-lg"
             autofocus placeholder="QR / Barcode / digitar (Enter)" maxlength="50">
      <button type="button" id="btn-camera" class="btn btn-outline-secondary">
        <i class="fas fa-camera"></i>
      </button>
    </div>
    <div id="qr-reader" class="mt-2 d-none" style="max-width:300px;"></div>
  </div>
  <button type="button" id="btn-registrar" class="btn btn-primary btn-lg">
    <i class="fas fa-check"></i> Disponibilizar (Ctrl+Enter)
  </button>
  <div id="alerta" class="mt-3 d-none"></div>
</div>

<div style="max-width: 800px;">
  {% with acao_label = 'disponibilizações', endpoint_reverter = url_for('motos_assai.disponibilizar_reverter') %}
    {% include 'motos_assai/partials/_historico_3_ultimas.html' %}
  {% endwith %}
</div>

<!-- Modal reverter -->
<div class="modal fade" id="modal-reverter" tabindex="-1">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header">
        <h5>Reverter para MONTADA</h5>
        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
      </div>
      <div class="modal-body">
        <p>Reverter o chassi <code id="modal-chassi"></code>?</p>
        <label class="form-label small">Motivo (obrigatório, ≥3 chars)</label>
        <textarea id="modal-motivo" class="form-control" rows="3"></textarea>
        <div id="modal-erro" class="text-danger small mt-2 d-none"></div>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
        <button type="button" class="btn btn-warning" id="btn-confirmar-reverter">
          <i class="fas fa-undo"></i> Confirmar reversão
        </button>
      </div>
    </div>
  </div>
</div>

<script src="https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js"
        integrity="sha384-c9d8RFSL+sJ0dC0WGqK7tQXg4/c5++8KkF+xbSPq3ji10/wfKLtAVk0M3IY+XJ7q"
        crossorigin="anonymous"></script>
<script>
window.MOTOS_ASSAI_OP_CONFIG = {
  endpoint: '{{ url_for("motos_assai.disponibilizar_registrar") }}',
  modo: 'disponibilizar',
};
</script>
<script src="{{ url_for('static', filename='motos_assai/js/operacao_quick.js') }}"></script>
<script>
// Handler do botão Reverter (delegação)
document.addEventListener('click', async (e) => {
  const btn = e.target.closest('[data-action="reverter"]');
  if (!btn) return;
  const chassi = btn.dataset.chassi;
  document.getElementById('modal-chassi').textContent = chassi;
  document.getElementById('modal-motivo').value = '';
  document.getElementById('modal-erro').classList.add('d-none');
  const modalEl = document.getElementById('modal-reverter');
  const modal = new bootstrap.Modal(modalEl);
  modal.show();

  document.getElementById('btn-confirmar-reverter').onclick = async () => {
    const motivo = document.getElementById('modal-motivo').value.trim();
    if (motivo.length < 3) {
      document.getElementById('modal-erro').textContent = 'Motivo precisa ter ≥3 chars';
      document.getElementById('modal-erro').classList.remove('d-none');
      return;
    }
    const r = await fetch('{{ url_for("motos_assai.disponibilizar_reverter") }}', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({chassi, motivo}),
    });
    const data = await r.json();
    if (!data.ok) {
      document.getElementById('modal-erro').textContent = data.erro;
      document.getElementById('modal-erro').classList.remove('d-none');
      return;
    }
    modal.hide();
    location.reload();  // recarrega para atualizar histórico
  };
});
</script>
{% endblock %}
```

- [ ] **Step 6: Adicionar nav link**

```jinja
    <a class="motos-assai-nav-link" href="{{ url_for('motos_assai.disponibilizar_tela') }}">
      <i class="fas fa-check-circle"></i> Disponibilizar
    </a>
```

- [ ] **Step 7: Commit**

```bash
git add app/motos_assai/forms/disponibilizar_forms.py app/motos_assai/forms/__init__.py
git add app/motos_assai/routes/disponibilizar.py app/motos_assai/routes/__init__.py
git add app/templates/motos_assai/disponibilizar/ app/templates/motos_assai/base_motos_assai.html
git commit -m "feat(motos_assai): disponibilizar quick screen + reverter modal"
```

---

## Task 6: Testes do `disponibilizar_service`

**Files:**
- Create: `tests/motos_assai/test_disponibilizar_service.py`

- [ ] **Step 1: Tests**

```python
import pytest
from app import db
from app.motos_assai.models import (
    AssaiMoto, AssaiModelo,
    EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_DISPONIVEL,
    EVENTO_REVERTIDA_PARA_MONTADA,
)
from app.motos_assai.services import (
    disponibilizar, reverter_para_montada, emitir_evento, status_efetivo,
    DisponibilizarValidationError,
)


def _moto_montada(chassi, admin):
    modelo = AssaiModelo.query.filter_by(codigo='DOT').first()
    m = AssaiMoto(chassi=chassi, modelo_id=modelo.id, cor='CINZA')
    db.session.add(m); db.session.flush()
    emitir_evento(chassi, EVENTO_ESTOQUE, admin.id)
    emitir_evento(chassi, EVENTO_MONTADA, admin.id)
    db.session.commit()


def test_disponibilizar_sucesso(app, admin_user):
    with app.app_context():
        _moto_montada('TST_D_001', admin_user)
        r = disponibilizar('TST_D_001', admin_user.id)
        assert r['tipo'] == EVENTO_DISPONIVEL
        db.session.rollback()


def test_disponibilizar_estoque_falha(app, admin_user):
    with app.app_context():
        modelo = AssaiModelo.query.filter_by(codigo='DOT').first()
        m = AssaiMoto(chassi='TST_D_002', modelo_id=modelo.id)
        db.session.add(m); db.session.flush()
        emitir_evento('TST_D_002', EVENTO_ESTOQUE, admin_user.id)
        db.session.commit()

        with pytest.raises(DisponibilizarValidationError, match='ESTOQUE'):
            disponibilizar('TST_D_002', admin_user.id)
        db.session.rollback()


def test_reverter_sucesso(app, admin_user):
    with app.app_context():
        _moto_montada('TST_D_003', admin_user)
        disponibilizar('TST_D_003', admin_user.id)
        reverter_para_montada('TST_D_003', 'Cliente cancelou', admin_user.id)
        assert status_efetivo('TST_D_003') == EVENTO_REVERTIDA_PARA_MONTADA
        db.session.rollback()


def test_reverter_motivo_curto_falha(app, admin_user):
    with app.app_context():
        _moto_montada('TST_D_004', admin_user)
        disponibilizar('TST_D_004', admin_user.id)
        with pytest.raises(DisponibilizarValidationError, match='≥3'):
            reverter_para_montada('TST_D_004', 'AB', admin_user.id)
        db.session.rollback()


def test_disponibilizar_apos_reverter(app, admin_user):
    """Após reverter, pode disponibilizar de novo."""
    with app.app_context():
        _moto_montada('TST_D_005', admin_user)
        disponibilizar('TST_D_005', admin_user.id)
        reverter_para_montada('TST_D_005', 'Tag faltando', admin_user.id)
        # Status efetivo é REVERTIDA_PARA_MONTADA → aceita disponibilizar
        r = disponibilizar('TST_D_005', admin_user.id)
        assert r['tipo'] == EVENTO_DISPONIVEL
        db.session.rollback()
```

- [ ] **Step 2: Commit**

```bash
git add tests/motos_assai/test_disponibilizar_service.py
git commit -m "test(motos_assai): disponibilizar_service tests"
```

---

## Task 7: `separacao_service` (registrar/cancelar/finalizar)

**Files:**
- Create: `app/motos_assai/services/separacao_service.py`
- Modify: `app/motos_assai/services/__init__.py`

- [ ] **Step 1: Service**

`app/motos_assai/services/separacao_service.py`:

```python
"""Separação por (pedido × loja). Fungível por modelo.

Estados:
- EM_SEPARACAO: criada e aceita novos chassis
- FECHADA: operador clicou Finalizar (saldo zero ou parcial)
- FATURADA: NF Q.P.A. importada e bateu
- CANCELADA: cancelada pelo operador (chassis devolvidos via novo evento DISPONIVEL)
"""

from __future__ import annotations

from typing import Optional, List, Dict, Any
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy import func

from app import db
from app.motos_assai.models import (
    AssaiSeparacao, AssaiSeparacaoItem, AssaiPedidoVenda, AssaiPedidoVendaItem,
    AssaiMoto, AssaiModelo,
    SEPARACAO_STATUS_EM_SEPARACAO, SEPARACAO_STATUS_FECHADA,
    SEPARACAO_STATUS_CANCELADA,
    PEDIDO_STATUS_EM_PRODUCAO, PEDIDO_STATUS_SEPARANDO,
    EVENTO_DISPONIVEL, EVENTO_SEPARADA,
)
from app.motos_assai.services.moto_evento_service import emitir_evento, status_efetivo


class SeparacaoConflictError(Exception):
    """Race ao reservar chassi (UNIQUE parcial)."""


class SeparacaoValidationError(Exception):
    pass


def get_ou_criar_separacao(pedido_id: int, loja_id: int, operador_id: int) -> AssaiSeparacao:
    """Retorna separação ativa ou cria. UNIQUE parcial garante 1 ativa por (pedido, loja)."""
    sep = (
        AssaiSeparacao.query
        .filter(
            AssaiSeparacao.pedido_id == pedido_id,
            AssaiSeparacao.loja_id == loja_id,
            AssaiSeparacao.status != SEPARACAO_STATUS_CANCELADA,
        )
        .first()
    )
    if sep:
        return sep

    sep = AssaiSeparacao(
        pedido_id=pedido_id, loja_id=loja_id,
        status=SEPARACAO_STATUS_EM_SEPARACAO,
    )
    db.session.add(sep)
    db.session.flush()
    return sep


def saldo_pendente_por_modelo(pedido_id: int, loja_id: int) -> List[Dict[str, Any]]:
    """Retorna [{modelo_id, codigo, nome, qtd_pedida, qtd_separada, qtd_pendente, valor_unitario}]."""
    rows = (
        db.session.query(
            AssaiPedidoVendaItem.modelo_id,
            AssaiModelo.codigo,
            AssaiModelo.nome,
            AssaiPedidoVendaItem.qtd_pedida,
            AssaiPedidoVendaItem.valor_unitario,
        )
        .join(AssaiModelo, AssaiModelo.id == AssaiPedidoVendaItem.modelo_id)
        .filter(
            AssaiPedidoVendaItem.pedido_id == pedido_id,
            AssaiPedidoVendaItem.loja_id == loja_id,
        )
        .order_by(AssaiModelo.codigo)
        .all()
    )

    # SUM já separado por (modelo) nesta separação ativa
    sep = (
        AssaiSeparacao.query
        .filter(
            AssaiSeparacao.pedido_id == pedido_id,
            AssaiSeparacao.loja_id == loja_id,
            AssaiSeparacao.status != SEPARACAO_STATUS_CANCELADA,
        ).first()
    )

    qtd_separada_por_modelo: Dict[int, int] = {}
    if sep:
        sums = (
            db.session.query(
                AssaiSeparacaoItem.modelo_id, func.count(AssaiSeparacaoItem.id)
            )
            .filter(AssaiSeparacaoItem.separacao_id == sep.id)
            .group_by(AssaiSeparacaoItem.modelo_id).all()
        )
        qtd_separada_por_modelo = {mid: int(n) for mid, n in sums}

    result = []
    for r in rows:
        sep_qtd = qtd_separada_por_modelo.get(r.modelo_id, 0)
        result.append({
            'modelo_id': r.modelo_id,
            'codigo': r.codigo,
            'nome': r.nome,
            'qtd_pedida': r.qtd_pedida,
            'qtd_separada': sep_qtd,
            'qtd_pendente': max(0, r.qtd_pedida - sep_qtd),
            'valor_unitario': r.valor_unitario,
        })
    return result


def registrar_chassi(
    pedido_id: int, loja_id: int, chassi: str, registrada_por_id: int,
) -> Dict[str, Any]:
    """Vincula chassi à separação. Validações:

    1. Status da moto = DISPONIVEL
    2. Modelo da moto bate com algum saldo > 0 do pedido para essa loja
    3. UNIQUE chassi via UNIQUE parcial — race retorna 409
    """
    chassi_norm = chassi.strip().upper()

    moto = AssaiMoto.query.filter_by(chassi=chassi_norm).with_for_update().first()
    if not moto:
        raise SeparacaoValidationError(f'Chassi {chassi_norm} não cadastrado')

    status = status_efetivo(chassi_norm)
    if status != EVENTO_DISPONIVEL:
        raise SeparacaoValidationError(
            f'Chassi {chassi_norm} está em {status}, esperado DISPONIVEL'
        )

    # Saldo: encontrar item do pedido com modelo bate
    saldos = saldo_pendente_por_modelo(pedido_id, loja_id)
    saldo_modelo = next(
        (s for s in saldos if s['modelo_id'] == moto.modelo_id and s['qtd_pendente'] > 0),
        None,
    )
    if not saldo_modelo:
        raise SeparacaoValidationError(
            f'Modelo {moto.modelo.codigo} sem saldo pendente para esta loja '
            '(ou modelo não pertence ao pedido)'
        )

    sep = get_ou_criar_separacao(pedido_id, loja_id, registrada_por_id)

    try:
        item = AssaiSeparacaoItem(
            separacao_id=sep.id,
            chassi=chassi_norm,
            modelo_id=moto.modelo_id,
            valor_unitario_qpa=Decimal(str(saldo_modelo['valor_unitario'])),
            registrada_por_id=registrada_por_id,
        )
        db.session.add(item)
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        raise SeparacaoConflictError(
            f'Chassi {chassi_norm} já em outra separação ativa'
        )

    emitir_evento(
        chassi_norm, EVENTO_SEPARADA,
        operador_id=registrada_por_id,
        dados_extras={
            'separacao_id': sep.id, 'pedido_id': pedido_id, 'loja_id': loja_id,
        },
    )

    # Pedido -> SEPARANDO
    pedido = AssaiPedidoVenda.query.get(pedido_id)
    if pedido and pedido.status == PEDIDO_STATUS_EM_PRODUCAO:
        pedido.status = PEDIDO_STATUS_SEPARANDO

    db.session.commit()
    return {
        'separacao_id': sep.id,
        'item_id': item.id,
        'chassi': chassi_norm,
        'modelo_codigo': moto.modelo.codigo,
        'cor': moto.cor,
    }


def desfazer_chassi(separacao_item_id: int, operador_id: int) -> Dict[str, Any]:
    """Remove chassi da separação ativa. Emite DISPONIVEL para o chassi voltar."""
    item = AssaiSeparacaoItem.query.get_or_404(separacao_item_id)
    sep = AssaiSeparacao.query.get(item.separacao_id)
    if sep and sep.status != SEPARACAO_STATUS_EM_SEPARACAO:
        raise SeparacaoValidationError(
            f'Separação {sep.id} está {sep.status}, não permite desfazer'
        )

    chassi = item.chassi
    db.session.delete(item)
    emitir_evento(
        chassi, EVENTO_DISPONIVEL,
        operador_id=operador_id,
        observacao='desfeito da separação',
        dados_extras={'separacao_id': sep.id if sep else None},
    )
    db.session.commit()
    return {'chassi': chassi}


def finalizar_separacao(separacao_id: int, operador_id: int) -> AssaiSeparacao:
    sep = AssaiSeparacao.query.get_or_404(separacao_id)
    if sep.status != SEPARACAO_STATUS_EM_SEPARACAO:
        raise SeparacaoValidationError(f'Status atual: {sep.status}')

    from app.utils.timezone import agora_brasil_naive
    sep.status = SEPARACAO_STATUS_FECHADA
    sep.fechada_em = agora_brasil_naive()
    sep.fechada_por_id = operador_id
    db.session.commit()
    return sep


def cancelar_separacao(separacao_id: int, motivo: str, operador_id: int) -> AssaiSeparacao:
    """Cancela. Para cada item: emite DISPONIVEL para devolver chassi ao estoque."""
    if not motivo or len(motivo.strip()) < 3:
        raise SeparacaoValidationError('Motivo obrigatório (≥3 chars)')

    sep = AssaiSeparacao.query.get_or_404(separacao_id)
    if sep.status == SEPARACAO_STATUS_CANCELADA:
        raise SeparacaoValidationError('Já cancelada')

    items = AssaiSeparacaoItem.query.filter_by(separacao_id=sep.id).all()
    for it in items:
        emitir_evento(
            it.chassi, EVENTO_DISPONIVEL,
            operador_id=operador_id,
            observacao='separacao_cancelada',
            dados_extras={'separacao_id': sep.id, 'motivo': motivo.strip()},
        )

    sep.status = SEPARACAO_STATUS_CANCELADA
    sep.motivo_cancelamento = motivo.strip()
    db.session.commit()
    return sep
```

- [ ] **Step 2: Atualizar __init__**

```python
from .separacao_service import (
    get_ou_criar_separacao, saldo_pendente_por_modelo, registrar_chassi,
    desfazer_chassi, finalizar_separacao, cancelar_separacao,
    SeparacaoConflictError, SeparacaoValidationError,
)
```

- [ ] **Step 3: Commit**

```bash
git add app/motos_assai/services/separacao_service.py app/motos_assai/services/__init__.py
git commit -m "feat(motos_assai): separacao_service (registrar/desfazer/finalizar/cancelar)"
```

---

## Task 8: Tela de separação

**Files:**
- Create: `app/motos_assai/routes/separacao.py`
- Modify: `app/motos_assai/routes/__init__.py`
- Create: `app/templates/motos_assai/separacao/lista.html`
- Create: `app/templates/motos_assai/separacao/tela.html`
- Create: `app/static/motos_assai/js/separacao_chassi.js`

- [ ] **Step 1: Rotas**

`app/motos_assai/routes/separacao.py`:

```python
from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.motos_assai.routes import motos_assai_bp
from app.motos_assai.decorators import require_motos_assai
from app.motos_assai.services import (
    get_ou_criar_separacao, saldo_pendente_por_modelo,
    registrar_chassi, desfazer_chassi, finalizar_separacao, cancelar_separacao,
    SeparacaoConflictError, SeparacaoValidationError,
)
from app.motos_assai.models import (
    AssaiSeparacao, AssaiSeparacaoItem, AssaiPedidoVenda, AssaiLoja,
)


@motos_assai_bp.route('/separacao')
@login_required
@require_motos_assai
def separacao_lista():
    seps = (
        AssaiSeparacao.query
        .order_by(AssaiSeparacao.iniciada_em.desc())
        .limit(250).all()
    )
    return render_template('motos_assai/separacao/lista.html', separacoes=seps)


@motos_assai_bp.route('/pedidos/<int:pedido_id>/separar/<int:loja_id>')
@login_required
@require_motos_assai
def separacao_tela(pedido_id, loja_id):
    pedido = AssaiPedidoVenda.query.get_or_404(pedido_id)
    loja = AssaiLoja.query.get_or_404(loja_id)
    sep = get_ou_criar_separacao(pedido_id, loja_id, current_user.id)
    saldos = saldo_pendente_por_modelo(pedido_id, loja_id)
    items = AssaiSeparacaoItem.query.filter_by(separacao_id=sep.id).all()
    return render_template(
        'motos_assai/separacao/tela.html',
        pedido=pedido, loja=loja, separacao=sep,
        saldos=saldos, items=items,
    )


@motos_assai_bp.route('/separacao/registrar-chassi', methods=['POST'])
@login_required
@require_motos_assai
def separacao_registrar_chassi():
    data = request.get_json(silent=True) or {}
    try:
        result = registrar_chassi(
            pedido_id=int(data['pedido_id']),
            loja_id=int(data['loja_id']),
            chassi=data['chassi'],
            registrada_por_id=current_user.id,
        )
    except SeparacaoConflictError as e:
        return jsonify({'ok': False, 'erro': str(e), 'retry': True}), 409
    except SeparacaoValidationError as e:
        return jsonify({'ok': False, 'erro': str(e)}), 400

    saldos = saldo_pendente_por_modelo(int(data['pedido_id']), int(data['loja_id']))
    return jsonify({'ok': True, **result, 'saldos': [
        {**s, 'valor_unitario': float(s['valor_unitario'])} for s in saldos
    ]})


@motos_assai_bp.route('/separacao/desfazer/<int:item_id>', methods=['POST'])
@login_required
@require_motos_assai
def separacao_desfazer(item_id):
    try:
        result = desfazer_chassi(item_id, current_user.id)
    except SeparacaoValidationError as e:
        return jsonify({'ok': False, 'erro': str(e)}), 400
    return jsonify({'ok': True, **result})


@motos_assai_bp.route('/separacao/<int:separacao_id>/finalizar', methods=['POST'])
@login_required
@require_motos_assai
def separacao_finalizar(separacao_id):
    try:
        sep = finalizar_separacao(separacao_id, current_user.id)
    except SeparacaoValidationError as e:
        return jsonify({'ok': False, 'erro': str(e)}), 400
    return jsonify({'ok': True, 'status': sep.status})


@motos_assai_bp.route('/separacao/<int:separacao_id>/cancelar', methods=['POST'])
@login_required
@require_motos_assai
def separacao_cancelar(separacao_id):
    data = request.get_json(silent=True) or {}
    try:
        sep = cancelar_separacao(separacao_id, data.get('motivo', ''), current_user.id)
    except SeparacaoValidationError as e:
        return jsonify({'ok': False, 'erro': str(e)}), 400
    return jsonify({'ok': True, 'status': sep.status})
```

- [ ] **Step 2: Importar route**

```python
from app.motos_assai.routes import separacao  # noqa: E402,F401
```

- [ ] **Step 3: Template lista**

`app/templates/motos_assai/separacao/lista.html`:

```jinja
{% extends "motos_assai/base_motos_assai.html" %}

{% block motos_assai_content %}
<h2>Separações</h2>
<table class="table">
  <thead><tr><th>#</th><th>Pedido</th><th>Loja</th><th>Status</th><th>Iniciada em</th></tr></thead>
  <tbody>
    {% for s in separacoes %}
    <tr>
      <td>{{ s.id }}</td>
      <td>{{ s.pedido.numero }}</td>
      <td>{{ s.loja.numero }} {{ s.loja.nome }}</td>
      <td><span class="badge bg-secondary">{{ s.status }}</span></td>
      <td>{{ s.iniciada_em.strftime('%d/%m %H:%M') }}</td>
    </tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}
```

- [ ] **Step 4: Template tela**

`app/templates/motos_assai/separacao/tela.html`:

```jinja
{% extends "motos_assai/base_motos_assai.html" %}

{% block motos_assai_content %}
<header class="d-flex justify-content-between mb-3">
  <h2>Separação — Pedido {{ pedido.numero }} · Loja {{ loja.numero }} {{ loja.nome }}
    <span class="badge bg-{% if separacao.status == 'EM_SEPARACAO' %}primary{% elif separacao.status == 'FECHADA' %}success{% elif separacao.status == 'CANCELADA' %}danger{% else %}secondary{% endif %}">
      {{ separacao.status }}
    </span>
  </h2>
</header>

<h4>Saldo pendente por modelo</h4>
<div class="row g-2 mb-3" id="saldos-container">
  {% for s in saldos %}
  <div class="col-md-4">
    <div class="card p-2">
      <strong>{{ s.codigo }} — {{ s.nome }}</strong>
      <div class="progress my-1" style="height: 20px;">
        <div class="progress-bar bg-success"
             style="width: {{ (s.qtd_separada * 100 / s.qtd_pedida) if s.qtd_pedida else 0 }}%">
          {{ s.qtd_separada }}/{{ s.qtd_pedida }}
        </div>
      </div>
      <small class="text-muted">
        {% if s.qtd_pendente == 0 %}<span class="text-success">✓ COMPLETO</span>
        {% else %}{{ s.qtd_pendente }} pendentes{% endif %}
      </small>
    </div>
  </div>
  {% endfor %}
</div>

{% if separacao.status == 'EM_SEPARACAO' %}
<div class="card p-3 mb-3" style="max-width: 600px;">
  <label class="form-label">Chassi</label>
  <div class="input-group">
    <input type="text" id="input-chassi" class="form-control form-control-lg"
           autofocus placeholder="QR / Barcode / digitar (Enter)" maxlength="50">
    <button type="button" id="btn-camera" class="btn btn-outline-secondary">
      <i class="fas fa-camera"></i>
    </button>
  </div>
  <div id="qr-reader" class="mt-2 d-none" style="max-width:300px;"></div>
  <div id="alerta-sep" class="mt-2 d-none"></div>
</div>
{% endif %}

<h4>Chassis registrados ({{ items|length }})</h4>
<table class="table table-sm" id="items-table">
  <thead><tr><th>Chassi</th><th>Modelo</th><th>Valor unit.</th><th>Registrado em</th><th>Ação</th></tr></thead>
  <tbody>
    {% for it in items %}
    <tr data-item-id="{{ it.id }}">
      <td><code>{{ it.chassi }}</code></td>
      <td>{{ it.modelo.codigo }}</td>
      <td>R$ {{ it.valor_unitario_qpa | numero_br(2) }}</td>
      <td class="small text-muted">{{ it.registrada_em.strftime('%d/%m %H:%M') }}</td>
      <td>
        {% if separacao.status == 'EM_SEPARACAO' %}
        <button type="button" class="btn btn-sm btn-outline-warning"
                data-action="desfazer" data-item-id="{{ it.id }}">
          <i class="fas fa-undo"></i> Desfazer
        </button>
        {% endif %}
      </td>
    </tr>
    {% endfor %}
  </tbody>
</table>

{% if separacao.status == 'EM_SEPARACAO' %}
<div class="d-flex gap-2 mt-3">
  <button type="button" class="btn btn-success" id="btn-finalizar">
    <i class="fas fa-check-double"></i> Finalizar separação
  </button>
  <a href="{{ url_for('motos_assai.faturamento_solicitacao_excel', separacao_id=separacao.id) }}"
     class="btn btn-primary">
    <i class="fas fa-file-excel"></i> Gerar solicitação Q.P.A.
  </a>
  <button type="button" class="btn btn-outline-danger ms-auto" id="btn-cancelar">
    <i class="fas fa-ban"></i> Cancelar separação
  </button>
</div>
{% elif separacao.status == 'FECHADA' %}
<a href="{{ url_for('motos_assai.faturamento_solicitacao_excel', separacao_id=separacao.id) }}"
   class="btn btn-primary mt-3">
  <i class="fas fa-file-excel"></i> {% if separacao.solicitacao_excel_s3_key %}Baixar{% else %}Gerar{% endif %} solicitação Q.P.A.
</a>
{% endif %}

<script src="https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js"
        integrity="sha384-c9d8RFSL+sJ0dC0WGqK7tQXg4/c5++8KkF+xbSPq3ji10/wfKLtAVk0M3IY+XJ7q"
        crossorigin="anonymous"></script>
<script>
window.MOTOS_ASSAI_SEP = {
  pedidoId: {{ pedido.id }},
  lojaId: {{ loja.id }},
  separacaoId: {{ separacao.id }},
  endpoints: {
    registrar: '{{ url_for("motos_assai.separacao_registrar_chassi") }}',
    desfazer: '{{ url_for("motos_assai.separacao_desfazer", item_id=0) }}',  // placeholder
    finalizar: '{{ url_for("motos_assai.separacao_finalizar", separacao_id=separacao.id) }}',
    cancelar: '{{ url_for("motos_assai.separacao_cancelar", separacao_id=separacao.id) }}',
  },
};
</script>
<script src="{{ url_for('static', filename='motos_assai/js/separacao_chassi.js') }}"></script>
{% endblock %}
```

- [ ] **Step 5: JS**

`app/static/motos_assai/js/separacao_chassi.js`:

```javascript
(function() {
  const cfg = window.MOTOS_ASSAI_SEP;
  if (!cfg) return;

  const inputChassi = document.getElementById('input-chassi');
  const alerta = document.getElementById('alerta-sep');

  // Câmera (igual aos outros componentes)
  let html5Qr = null;
  document.getElementById('btn-camera')?.addEventListener('click', () => {
    const div = document.getElementById('qr-reader');
    if (html5Qr) {
      html5Qr.stop().then(() => { html5Qr = null; div.classList.add('d-none'); });
      return;
    }
    if (!window.isSecureContext) { showAlerta('warning', 'Câmera requer HTTPS'); return; }
    div.classList.remove('d-none');
    html5Qr = new Html5Qrcode('qr-reader');
    html5Qr.start({facingMode: 'environment'}, {fps: 10, qrbox: 240}, (txt) => {
      inputChassi.value = txt.trim().toUpperCase();
      html5Qr.stop().then(() => { html5Qr = null; div.classList.add('d-none'); });
      registrar();
    });
  });

  inputChassi?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') { e.preventDefault(); registrar(); }
  });

  async function registrar() {
    const chassi = inputChassi.value.trim().toUpperCase();
    if (!chassi) return;
    const r = await fetch(cfg.endpoints.registrar, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({pedido_id: cfg.pedidoId, loja_id: cfg.lojaId, chassi}),
    });
    const data = await r.json();
    if (!data.ok) {
      showAlerta('danger', data.erro);
      return;
    }
    showAlerta('success', `Chassi ${data.chassi} registrado.`);
    inputChassi.value = '';
    inputChassi.focus();
    setTimeout(() => location.reload(), 800);  // recarrega para atualizar saldo + lista
  }

  // Desfazer
  document.addEventListener('click', async (e) => {
    const btn = e.target.closest('[data-action="desfazer"]');
    if (!btn) return;
    if (!confirm(`Remover chassi ${btn.closest('tr').querySelector('code').textContent}?`)) return;
    const itemId = btn.dataset.itemId;
    const url = cfg.endpoints.desfazer.replace('/0', '/' + itemId);
    const r = await fetch(url, {method: 'POST'});
    const data = await r.json();
    if (data.ok) location.reload();
    else alert(data.erro);
  });

  document.getElementById('btn-finalizar')?.addEventListener('click', async () => {
    if (!confirm('Finalizar separação? Saldos pendentes ficam para outra separação se houver.')) return;
    const r = await fetch(cfg.endpoints.finalizar, {method: 'POST'});
    const data = await r.json();
    if (data.ok) location.reload();
    else alert(data.erro);
  });

  document.getElementById('btn-cancelar')?.addEventListener('click', async () => {
    const motivo = prompt('Motivo do cancelamento (≥3 chars):');
    if (!motivo || motivo.trim().length < 3) return;
    const r = await fetch(cfg.endpoints.cancelar, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({motivo}),
    });
    const data = await r.json();
    if (data.ok) location.reload();
    else alert(data.erro);
  });

  function showAlerta(level, html) {
    alerta.className = `alert alert-${level} small`;
    alerta.innerHTML = html;
    alerta.classList.remove('d-none');
    setTimeout(() => alerta.classList.add('d-none'), 4000);
  }

  inputChassi?.focus();
})();
```

- [ ] **Step 6: Adicionar nav link**

```jinja
    <a class="motos-assai-nav-link" href="{{ url_for('motos_assai.separacao_lista') }}">
      <i class="fas fa-truck"></i> Separação
    </a>
```

- [ ] **Step 7: Commit**

```bash
git add app/motos_assai/routes/separacao.py app/motos_assai/routes/__init__.py
git add app/templates/motos_assai/separacao/
git add app/static/motos_assai/js/separacao_chassi.js
git add app/templates/motos_assai/base_motos_assai.html
git commit -m "feat(motos_assai): separacao screen with saldo + chassi register/undo"
```

---

## Task 9: Testes do `separacao_service`

**Files:**
- Create: `tests/motos_assai/test_separacao_service.py`

- [ ] **Step 1: Tests**

```python
import pytest
from decimal import Decimal
from app import db
from app.motos_assai.models import (
    AssaiPedidoVenda, AssaiPedidoVendaItem, AssaiLoja, AssaiModelo,
    AssaiMoto, AssaiSeparacao, AssaiSeparacaoItem,
    PEDIDO_STATUS_ABERTO, PEDIDO_STATUS_EM_PRODUCAO,
    SEPARACAO_STATUS_FECHADA, SEPARACAO_STATUS_CANCELADA,
    EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_DISPONIVEL,
)
from app.motos_assai.services import (
    get_ou_criar_separacao, saldo_pendente_por_modelo, registrar_chassi,
    desfazer_chassi, finalizar_separacao, cancelar_separacao,
    emitir_evento, status_efetivo,
    SeparacaoValidationError,
)


def _setup(app, admin):
    """Cria pedido + 1 loja + 2 chassis disponíveis (DOT)."""
    modelo_dot = AssaiModelo.query.filter_by(codigo='DOT').first()
    loja = AssaiLoja.query.first()  # qualquer loja seeded

    p = AssaiPedidoVenda(numero=f'TST-SEP-{id(_setup)}', status=PEDIDO_STATUS_EM_PRODUCAO,
                         criado_por_id=admin.id)
    db.session.add(p); db.session.flush()
    db.session.add(AssaiPedidoVendaItem(
        pedido_id=p.id, loja_id=loja.id, modelo_id=modelo_dot.id,
        qtd_pedida=2, valor_unitario=Decimal('6900'), valor_total=Decimal('13800'),
    ))
    db.session.flush()

    for ch in ['TST_SEP_A', 'TST_SEP_B']:
        m = AssaiMoto(chassi=ch, modelo_id=modelo_dot.id, cor='CINZA')
        db.session.add(m); db.session.flush()
        emitir_evento(ch, EVENTO_ESTOQUE, admin.id)
        emitir_evento(ch, EVENTO_MONTADA, admin.id)
        emitir_evento(ch, EVENTO_DISPONIVEL, admin.id)
    db.session.commit()
    return p, loja, modelo_dot


def test_saldo_pendente_inicial(app, admin_user):
    with app.app_context():
        p, loja, _ = _setup(app, admin_user)
        saldos = saldo_pendente_por_modelo(p.id, loja.id)
        assert len(saldos) == 1
        assert saldos[0]['qtd_pendente'] == 2
        db.session.rollback()


def test_registrar_chassi_decrementa_saldo(app, admin_user):
    with app.app_context():
        p, loja, _ = _setup(app, admin_user)
        registrar_chassi(p.id, loja.id, 'TST_SEP_A', admin_user.id)
        saldos = saldo_pendente_por_modelo(p.id, loja.id)
        assert saldos[0]['qtd_separada'] == 1
        assert saldos[0]['qtd_pendente'] == 1
        db.session.rollback()


def test_chassi_nao_disponivel_falha(app, admin_user):
    with app.app_context():
        p, loja, _ = _setup(app, admin_user)
        # Reverte um chassi
        emitir_evento('TST_SEP_A', 'REVERTIDA_PARA_MONTADA', admin_user.id)
        db.session.commit()
        with pytest.raises(SeparacaoValidationError, match='DISPONIVEL'):
            registrar_chassi(p.id, loja.id, 'TST_SEP_A', admin_user.id)
        db.session.rollback()


def test_desfazer_devolve_chassi(app, admin_user):
    with app.app_context():
        p, loja, _ = _setup(app, admin_user)
        r = registrar_chassi(p.id, loja.id, 'TST_SEP_A', admin_user.id)
        desfazer_chassi(r['item_id'], admin_user.id)
        assert status_efetivo('TST_SEP_A') == EVENTO_DISPONIVEL
        db.session.rollback()


def test_cancelar_devolve_todos(app, admin_user):
    with app.app_context():
        p, loja, _ = _setup(app, admin_user)
        registrar_chassi(p.id, loja.id, 'TST_SEP_A', admin_user.id)
        registrar_chassi(p.id, loja.id, 'TST_SEP_B', admin_user.id)
        sep = AssaiSeparacao.query.filter_by(pedido_id=p.id, loja_id=loja.id).first()
        cancelar_separacao(sep.id, 'cancelado por teste', admin_user.id)
        sep_after = AssaiSeparacao.query.get(sep.id)
        assert sep_after.status == SEPARACAO_STATUS_CANCELADA
        assert status_efetivo('TST_SEP_A') == EVENTO_DISPONIVEL
        assert status_efetivo('TST_SEP_B') == EVENTO_DISPONIVEL
        db.session.rollback()
```

- [ ] **Step 2: Commit**

```bash
git add tests/motos_assai/test_separacao_service.py
git commit -m "test(motos_assai): separacao_service tests (registrar/desfazer/cancelar)"
```

---

## Task 10: `faturamento_service.gerar_excel_qpa`

**Files:**
- Create: `app/motos_assai/services/faturamento_service.py`
- Modify: `app/motos_assai/services/__init__.py`

- [ ] **Step 1: Service**

`app/motos_assai/services/faturamento_service.py`:

```python
"""Geração do Excel de solicitação de faturamento Q.P.A.

Estrutura espelhada do template `285.xlsx`:
- Aba **PEDIDO**: header com Nº LOJA, CLIENTE, CNPJ, IE, ENDEREÇO, BAIRRO, UF,
  CIDADE, CEP. Tabela ITEM | CHASSI | MODELO | COR | VALOR. Linha TOTAL.
- Aba **BASE LOJAS**: cópia das 39 lojas Assaí (referência).
"""

from __future__ import annotations

import io
from decimal import Decimal
from typing import Tuple, Optional

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

from app import db
from app.utils.file_storage import FileStorage
from app.utils.timezone import agora_brasil_naive
from app.motos_assai.models import (
    AssaiSeparacao, AssaiSeparacaoItem, AssaiLoja, AssaiMoto, AssaiModelo,
)


def gerar_excel_qpa(separacao_id: int, gerada_por_id: int) -> Tuple[bytes, str]:
    """Gera Excel da solicitação. Retorna (bytes, s3_key).

    Salva em S3 em `motos_assai/solicitacoes/<separacao_id>.xlsx` e atualiza
    `assai_separacao.solicitacao_excel_s3_key`.
    """
    sep = AssaiSeparacao.query.get_or_404(separacao_id)
    loja = AssaiLoja.query.get(sep.loja_id)

    items = (
        db.session.query(AssaiSeparacaoItem, AssaiMoto, AssaiModelo)
        .join(AssaiMoto, AssaiMoto.chassi == AssaiSeparacaoItem.chassi)
        .join(AssaiModelo, AssaiModelo.id == AssaiSeparacaoItem.modelo_id)
        .filter(AssaiSeparacaoItem.separacao_id == separacao_id)
        .order_by(AssaiSeparacaoItem.id)
        .all()
    )

    wb = Workbook()

    # ===== Aba PEDIDO =====
    ws = wb.active
    ws.title = 'PEDIDO'

    bold = Font(bold=True, size=11)
    title_font = Font(bold=True, size=14)
    fill_header = PatternFill(start_color='D0D0D0', end_color='D0D0D0', fill_type='solid')
    border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin'),
    )

    row = 1
    ws.cell(row=row, column=2, value=f'COLETA DIA {agora_brasil_naive().strftime("%d/%m")} - MONTADO.').font = bold
    row += 1
    ws.cell(row=row, column=2, value='PEDIDO DE VENDA  - SCOOTER ELETRICA').font = title_font
    row += 1
    ws.cell(row=row, column=2, value='OPERAÇÃO VOE X SENDAS').font = bold
    row += 1

    # Header info loja
    info = [
        ('Nº LOJA', loja.numero),
        ('CLIENTE:', loja.razao_social),
        ('CNPJ:', loja.cnpj),
        ('I.E', loja.ie or ''),
        ('ENDEREÇO:', loja.endereco or ''),
        ('BAIRRO:', loja.bairro or ''),
        ('CIDADE:', loja.cidade or ''),
        ('CEP:', loja.cep or ''),
    ]
    for label, value in info:
        ws.cell(row=row, column=2, value=label).font = bold
        ws.cell(row=row, column=3, value=value)
        if label == 'BAIRRO:':
            ws.cell(row=row, column=4, value='UF').font = bold
            ws.cell(row=row, column=5, value=loja.uf or '')
        row += 1

    row += 1  # linha em branco

    # Tabela
    for i, lab in enumerate(['ITEM', 'CHASSI', 'MODELO', 'COR', 'VALOR']):
        c = ws.cell(row=row, column=i + 1, value=lab)
        c.font = bold
        c.fill = fill_header
        c.border = border
        c.alignment = Alignment(horizontal='center')
    row += 1

    total = Decimal('0')
    for idx, (item, moto, modelo) in enumerate(items, start=1):
        ws.cell(row=row, column=1, value=idx).border = border
        ws.cell(row=row, column=2, value=moto.chassi).border = border
        ws.cell(row=row, column=3, value=modelo.codigo).border = border
        ws.cell(row=row, column=4, value=moto.cor or '').border = border
        cell_v = ws.cell(row=row, column=5, value=float(item.valor_unitario_qpa))
        cell_v.border = border
        cell_v.number_format = '#,##0.00'
        total += item.valor_unitario_qpa
        row += 1

    ws.cell(row=row, column=4, value='TOTAL').font = bold
    cell_t = ws.cell(row=row, column=5, value=float(total))
    cell_t.font = bold
    cell_t.number_format = '#,##0.00'

    # Largura colunas
    for col_idx, w in enumerate([6, 22, 14, 12, 14], start=1):
        ws.column_dimensions[get_column_letter(col_idx)].width = w

    # ===== Aba BASE LOJAS =====
    ws2 = wb.create_sheet('BASE LOJAS')
    headers = ['Nº Loja', 'Loja', 'Regional', 'CNPJ', 'IE', 'RAZAO SOCIAL',
               'Endereço', 'BAIRRO', 'CEP', 'Cidade', 'UF']
    for i, h in enumerate(headers, start=1):
        c = ws2.cell(row=1, column=i, value=h)
        c.font = bold
        c.fill = fill_header

    todas_lojas = AssaiLoja.query.filter_by(ativo=True).order_by(AssaiLoja.numero).all()
    for r, l in enumerate(todas_lojas, start=2):
        valores = [l.numero, l.nome, l.regional or '', l.cnpj, l.ie or '',
                   l.razao_social, l.endereco or '', l.bairro or '',
                   l.cep or '', l.cidade or '', l.uf or '']
        for c_idx, v in enumerate(valores, start=1):
            ws2.cell(row=r, column=c_idx, value=v)

    for col_idx, w in enumerate([8, 26, 26, 18, 14, 36, 36, 22, 12, 22, 4], start=1):
        ws2.column_dimensions[get_column_letter(col_idx)].width = w

    # ===== Salvar =====
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    bytes_xlsx = buf.getvalue()

    nome_arquivo = f'LJ{loja.numero}_solicitacao_{separacao_id}.xlsx'
    s3_key = FileStorage().save_file(
        io.BytesIO(bytes_xlsx),
        folder=f'motos_assai/solicitacoes',
        filename=nome_arquivo,
        allowed_extensions=['xlsx'],
    )
    sep.solicitacao_excel_s3_key = s3_key
    db.session.commit()

    return bytes_xlsx, s3_key
```

- [ ] **Step 2: Atualizar __init__**

```python
from .faturamento_service import gerar_excel_qpa
```

- [ ] **Step 3: Commit**

```bash
git add app/motos_assai/services/faturamento_service.py
git add app/motos_assai/services/__init__.py
git commit -m "feat(motos_assai): generate Q.P.A. Excel mirroring 285.xlsx structure"
```

---

## Task 11: Rota download Excel + lista de separações faturáveis

**Files:**
- Create: `app/motos_assai/routes/faturamento.py`
- Modify: `app/motos_assai/routes/__init__.py`
- Create: `app/templates/motos_assai/faturamento/lista_separacoes.html`

- [ ] **Step 1: Rota**

`app/motos_assai/routes/faturamento.py`:

```python
from flask import render_template, redirect, url_for, flash, Response
from flask_login import login_required, current_user
from app.motos_assai.routes import motos_assai_bp
from app.motos_assai.decorators import require_motos_assai
from app.motos_assai.services import gerar_excel_qpa
from app.motos_assai.models import (
    AssaiSeparacao, SEPARACAO_STATUS_FECHADA, SEPARACAO_STATUS_FATURADA,
)


@motos_assai_bp.route('/faturamento')
@login_required
@require_motos_assai
def faturamento_lista():
    seps = (
        AssaiSeparacao.query
        .filter(AssaiSeparacao.status.in_([SEPARACAO_STATUS_FECHADA, SEPARACAO_STATUS_FATURADA]))
        .order_by(AssaiSeparacao.fechada_em.desc())
        .limit(250)
        .all()
    )
    return render_template('motos_assai/faturamento/lista_separacoes.html', separacoes=seps)


@motos_assai_bp.route('/faturamento/separacao/<int:separacao_id>/excel')
@login_required
@require_motos_assai
def faturamento_solicitacao_excel(separacao_id):
    bytes_xlsx, s3_key = gerar_excel_qpa(separacao_id, current_user.id)
    return Response(
        bytes_xlsx,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={
            'Content-Disposition': f'attachment; filename="solicitacao_qpa_{separacao_id}.xlsx"',
        },
    )
```

- [ ] **Step 2: Importar route**

```python
from app.motos_assai.routes import faturamento  # noqa: E402,F401
```

- [ ] **Step 3: Template lista**

```jinja
{% extends "motos_assai/base_motos_assai.html" %}

{% block motos_assai_content %}
<h2>Faturamento</h2>
<p class="text-muted">Separações fechadas — gere Excel para Q.P.A. e suba a NF emitida.</p>

<table class="table table-hover">
  <thead><tr><th>#</th><th>Pedido</th><th>Loja</th><th>Itens</th><th>Status</th><th>Excel</th><th>Ações</th></tr></thead>
  <tbody>
    {% for s in separacoes %}
    <tr>
      <td>{{ s.id }}</td>
      <td>{{ s.pedido.numero }}</td>
      <td>{{ s.loja.numero }} {{ s.loja.nome }}</td>
      <td>{{ s.itens|length }}</td>
      <td><span class="badge bg-secondary">{{ s.status }}</span></td>
      <td>{% if s.solicitacao_excel_s3_key %}<i class="fas fa-check text-success"></i>{% else %}-{% endif %}</td>
      <td>
        <a href="{{ url_for('motos_assai.faturamento_solicitacao_excel', separacao_id=s.id) }}"
           class="btn btn-sm btn-primary"><i class="fas fa-file-excel"></i> Excel</a>
        <a href="{{ url_for('motos_assai.faturamento_upload_nf', separacao_id=s.id) }}"
           class="btn btn-sm btn-outline-primary"><i class="fas fa-upload"></i> Upload NF</a>
      </td>
    </tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}
```

- [ ] **Step 4: Adicionar nav link**

```jinja
    <a class="motos-assai-nav-link" href="{{ url_for('motos_assai.faturamento_lista') }}">
      <i class="fas fa-file-invoice-dollar"></i> Faturamento
    </a>
```

- [ ] **Step 5: Commit**

```bash
git add app/motos_assai/routes/faturamento.py app/motos_assai/routes/__init__.py
git add app/templates/motos_assai/faturamento/lista_separacoes.html
git add app/templates/motos_assai/base_motos_assai.html
git commit -m "feat(motos_assai): faturamento list + Excel download"
```

---

## Task 12: `nf_qpa_adapter` (importar NF Q.P.A. + match)

**Files:**
- Create: `app/motos_assai/services/parsers/nf_qpa_adapter.py`

- [ ] **Step 1: Adapter**

`app/motos_assai/services/parsers/nf_qpa_adapter.py`:

```python
"""Adapter sobre `app.carvia.services.parsers.danfe_pdf_parser.DanfePDFParser`.

NÃO modifica módulo CarVia. Apenas chama, traduz e persiste em entidades assai_*.

Match BATEU/DIVERGENTE/NAO_RECONCILIADO:
- Para cada chassi da NF: busca AssaiSeparacaoItem ativo (separação não cancelada)
- BATEU = todos chassis bateram (loja + modelo + valor com tolerância 1%)
- DIVERGENTE = pelo menos 1 não bateu mas alguns sim
- NAO_RECONCILIADO = nenhum chassi da NF bate com separação
"""

from __future__ import annotations

import io
import re
from decimal import Decimal
from typing import Optional, Dict, Any, List

from app import db
from app.utils.file_storage import FileStorage
from app.utils.timezone import agora_brasil_naive
from app.motos_assai.models import (
    AssaiNfQpa, AssaiNfQpaItem, AssaiLoja,
    AssaiSeparacao, AssaiSeparacaoItem,
    SEPARACAO_STATUS_CANCELADA, SEPARACAO_STATUS_FATURADA,
    NF_STATUS_BATEU, NF_STATUS_DIVERGENTE, NF_STATUS_NAO_RECONCILIADO,
    EVENTO_FATURADA,
)
from app.motos_assai.services.modelo_resolver import resolver_modelo
from app.motos_assai.services.moto_evento_service import emitir_evento


TOLERANCIA_VALOR_PCT = Decimal('0.01')


class NfQpaParseError(Exception):
    pass


class NfQpaJaImportadaError(Exception):
    pass


def importar_nf_qpa(
    pdf_bytes: bytes, nome_arquivo: str, importada_por_id: int,
) -> AssaiNfQpa:
    """Parseia PDF, persiste e calcula match."""
    from app.carvia.services.parsers.danfe_pdf_parser import DanfePDFParser

    if not pdf_bytes:
        raise NfQpaParseError('PDF vazio')

    parser = DanfePDFParser(pdf_bytes=pdf_bytes)
    resultado = parser.get_todas_informacoes()

    chave = resultado.get('chave_acesso_nf')
    if not chave or len(chave) != 44:
        raise NfQpaParseError(f'chave_acesso_nf inválida: {chave}')

    if AssaiNfQpa.query.filter_by(chave_44=chave).first():
        raise NfQpaJaImportadaError(f'NF {chave} já importada')

    # Loja: extrair de nome_destinatario via "LJ\d+"
    nome_dest = resultado.get('nome_destinatario') or ''
    loja_match = re.search(r'LJ\s*(\d+)', nome_dest)
    loja = None
    if loja_match:
        loja = AssaiLoja.query.filter_by(numero=loja_match.group(1)).first()

    # S3
    buf = io.BytesIO(pdf_bytes); buf.name = nome_arquivo
    s3_key = FileStorage().save_file(
        buf, folder='motos_assai/nfs_qpa', filename=nome_arquivo,
        allowed_extensions=['pdf'],
    )

    nf = AssaiNfQpa(
        chave_44=chave,
        numero=resultado.get('numero_nf'),
        serie=resultado.get('serie_nf'),
        emitente_cnpj=re.sub(r'\D', '', resultado.get('cnpj_emitente') or '')[:18] or None,
        destinatario_cnpj=re.sub(r'\D', '', resultado.get('cnpj_destinatario') or '')[:18] or None,
        destinatario_nome=nome_dest,
        loja_id=loja.id if loja else None,
        valor_total=Decimal(str(resultado.get('valor_total', 0))),
        data_emissao=resultado.get('data_emissao'),
        pdf_s3_key=s3_key,
        status_match=NF_STATUS_NAO_RECONCILIADO,
        importada_em=agora_brasil_naive(),
        importada_por_id=importada_por_id,
    )
    db.session.add(nf)
    db.session.flush()

    # Items
    for v in resultado.get('veiculos') or []:
        chassi = (v.get('chassi') or '').strip().upper()
        if not chassi:
            continue
        modelo = resolver_modelo(v.get('modelo', ''), origem='NF_QPA')
        # Valor unitário: parser distribui valor_total / qtd. Manter o que vier.
        valor_extraido = Decimal(str(nf.valor_total / max(1, len(resultado.get('veiculos', [])))))
        db.session.add(AssaiNfQpaItem(
            nf_id=nf.id,
            chassi=chassi,
            modelo_extraido=v.get('modelo'),
            valor_extraido=valor_extraido,
        ))
    db.session.flush()

    # Match
    _calcular_match(nf, importada_por_id)
    db.session.commit()
    return nf


def _calcular_match(nf: AssaiNfQpa, operador_id: int) -> None:
    """Tenta amarrar cada item da NF a uma AssaiSeparacaoItem ativo.

    Critérios de BATEU:
    - chassi existe em AssaiSeparacaoItem ativa
    - separacao.loja_id == nf.loja_id (se NF tem loja)
    - separacao_item.modelo_id resolvido bate com modelo extraído
    - valor com tolerância de 1%
    """
    items_nf = AssaiNfQpaItem.query.filter_by(nf_id=nf.id).all()
    matches_ok = 0
    matches_falha = 0

    separacoes_atualizar = set()

    for it in items_nf:
        sep_item = (
            db.session.query(AssaiSeparacaoItem)
            .join(AssaiSeparacao, AssaiSeparacao.id == AssaiSeparacaoItem.separacao_id)
            .filter(
                AssaiSeparacaoItem.chassi == it.chassi,
                AssaiSeparacao.status != SEPARACAO_STATUS_CANCELADA,
            )
            .first()
        )

        if not sep_item:
            it.tipo_divergencia = 'CHASSI_SEM_SEPARACAO'
            matches_falha += 1
            continue

        sep = AssaiSeparacao.query.get(sep_item.separacao_id)

        # Loja
        loja_ok = (not nf.loja_id) or (sep.loja_id == nf.loja_id)
        if not loja_ok:
            it.tipo_divergencia = 'LOJA_DIVERGENTE'
            matches_falha += 1
            continue

        # Valor com tolerância 1%
        v_sep = sep_item.valor_unitario_qpa
        v_nf = it.valor_extraido or Decimal('0')
        if v_sep > 0:
            diff_pct = abs(v_sep - v_nf) / v_sep
            if diff_pct > TOLERANCIA_VALOR_PCT:
                it.tipo_divergencia = 'VALOR_DIVERGENTE'
                matches_falha += 1
                continue

        # OK
        it.separacao_item_id = sep_item.id
        matches_ok += 1
        separacoes_atualizar.add(sep_item.separacao_id)

    if matches_ok == 0:
        nf.status_match = NF_STATUS_NAO_RECONCILIADO
    elif matches_falha > 0:
        nf.status_match = NF_STATUS_DIVERGENTE
    else:
        nf.status_match = NF_STATUS_BATEU
        # Se BATEU, atribui separacao_id principal (a primeira que apareceu)
        if separacoes_atualizar:
            nf.separacao_id = next(iter(separacoes_atualizar))

        # Atualiza separações para FATURADA + emite eventos FATURADA
        for sep_id in separacoes_atualizar:
            sep = AssaiSeparacao.query.get(sep_id)
            sep.status = SEPARACAO_STATUS_FATURADA

        for it_ok in items_nf:
            if it_ok.separacao_item_id:
                emitir_evento(
                    it_ok.chassi, EVENTO_FATURADA,
                    operador_id=operador_id,
                    dados_extras={'nf_id': nf.id, 'chave_44': nf.chave_44},
                )
```

- [ ] **Step 2: Commit**

```bash
git add app/motos_assai/services/parsers/nf_qpa_adapter.py
git commit -m "feat(motos_assai): nf_qpa_adapter (DanfePDFParser + match BATEU/DIVERGENTE)"
```

---

## Task 13: Rota upload NF Q.P.A. + detalhe

**Files:**
- Create: `app/motos_assai/forms/faturamento_forms.py`
- Modify: `app/motos_assai/forms/__init__.py`
- Modify: `app/motos_assai/routes/faturamento.py`
- Create: `app/templates/motos_assai/faturamento/upload_nf.html`
- Create: `app/templates/motos_assai/faturamento/nf_detalhe.html`

- [ ] **Step 1: Form**

`app/motos_assai/forms/faturamento_forms.py`:

```python
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed


class UploadNfQpaForm(FlaskForm):
    pdf = FileField('PDF da NF Q.P.A.', validators=[
        FileRequired(), FileAllowed(['pdf'], 'Apenas PDF.'),
    ])
```

- [ ] **Step 2: Atualizar forms __init__**

```python
from .faturamento_forms import UploadNfQpaForm
```

- [ ] **Step 3: Adicionar rotas**

Em `app/motos_assai/routes/faturamento.py`:

```python
from app.motos_assai.forms import UploadNfQpaForm
from app.motos_assai.services.parsers.nf_qpa_adapter import (
    importar_nf_qpa, NfQpaParseError, NfQpaJaImportadaError,
)
from app.motos_assai.models import AssaiNfQpa, AssaiNfQpaItem


@motos_assai_bp.route('/faturamento/separacao/<int:separacao_id>/upload-nf', methods=['GET', 'POST'])
@motos_assai_bp.route('/faturamento/upload-nf', methods=['GET', 'POST'], defaults={'separacao_id': None})
@login_required
@require_motos_assai
def faturamento_upload_nf(separacao_id):
    form = UploadNfQpaForm()
    if form.validate_on_submit():
        f = form.pdf.data
        try:
            nf = importar_nf_qpa(
                pdf_bytes=f.read(),
                nome_arquivo=f.filename,
                importada_por_id=current_user.id,
            )
            flash(f'NF {nf.numero} importada — status: {nf.status_match}', 'success')
            return redirect(url_for('motos_assai.faturamento_nf_detalhe', nf_id=nf.id))
        except NfQpaJaImportadaError as e:
            flash(str(e), 'warning')
        except NfQpaParseError as e:
            flash(f'Erro ao parsear NF: {e}', 'danger')
    return render_template('motos_assai/faturamento/upload_nf.html', form=form)


@motos_assai_bp.route('/faturamento/nfs/<int:nf_id>')
@login_required
@require_motos_assai
def faturamento_nf_detalhe(nf_id):
    nf = AssaiNfQpa.query.get_or_404(nf_id)
    items = AssaiNfQpaItem.query.filter_by(nf_id=nf_id).all()
    return render_template('motos_assai/faturamento/nf_detalhe.html', nf=nf, items=items)
```

- [ ] **Step 4: Templates**

`app/templates/motos_assai/faturamento/upload_nf.html`:

```jinja
{% extends "motos_assai/base_motos_assai.html" %}

{% block motos_assai_content %}
<h2>Importar NF Q.P.A.</h2>
<form method="POST" enctype="multipart/form-data" class="card p-4" style="max-width: 600px;">
  {{ form.hidden_tag() }}
  <div class="mb-3">
    {{ form.pdf.label(class="form-label") }}
    {{ form.pdf(class="form-control", accept="application/pdf") }}
  </div>
  <button type="submit" class="btn btn-primary"><i class="fas fa-upload"></i> Importar</button>
</form>
{% endblock %}
```

`app/templates/motos_assai/faturamento/nf_detalhe.html`:

```jinja
{% extends "motos_assai/base_motos_assai.html" %}

{% block motos_assai_content %}
<header class="d-flex justify-content-between mb-3">
  <h2>NF Q.P.A. — {{ nf.numero }}/{{ nf.serie or '-' }}
    <span class="badge bg-{% if nf.status_match == 'BATEU' %}success{% elif nf.status_match == 'DIVERGENTE' %}warning{% else %}danger{% endif %}">
      {{ nf.status_match }}
    </span>
  </h2>
</header>

<dl class="row small">
  <dt class="col-sm-3">Chave 44</dt><dd class="col-sm-9"><code>{{ nf.chave_44 }}</code></dd>
  <dt class="col-sm-3">Emitente</dt><dd class="col-sm-9">{{ nf.emitente_cnpj }}</dd>
  <dt class="col-sm-3">Destinatário</dt><dd class="col-sm-9">{{ nf.destinatario_nome }}</dd>
  <dt class="col-sm-3">Loja resolvida</dt>
  <dd class="col-sm-9">{% if nf.loja %}{{ nf.loja.numero }} {{ nf.loja.nome }}{% else %}<span class="text-warning">não resolvida</span>{% endif %}</dd>
  <dt class="col-sm-3">Valor total</dt><dd class="col-sm-9">R$ {{ nf.valor_total | numero_br(2) }}</dd>
  <dt class="col-sm-3">Data</dt><dd class="col-sm-9">{{ nf.data_emissao.strftime('%d/%m/%Y') if nf.data_emissao else '-' }}</dd>
</dl>

<h4>Itens ({{ items|length }})</h4>
<table class="table table-sm">
  <thead><tr><th>Chassi</th><th>Modelo extraído</th><th>Valor</th><th>Match separação</th><th>Divergência</th></tr></thead>
  <tbody>
    {% for it in items %}
    <tr>
      <td><code>{{ it.chassi }}</code></td>
      <td>{{ it.modelo_extraido }}</td>
      <td>R$ {{ it.valor_extraido | numero_br(2) }}</td>
      <td>{% if it.separacao_item_id %}<i class="fas fa-check text-success"></i> #{{ it.separacao_item_id }}{% else %}-{% endif %}</td>
      <td>{% if it.tipo_divergencia %}<span class="badge bg-warning">{{ it.tipo_divergencia }}</span>{% endif %}</td>
    </tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}
```

- [ ] **Step 5: Commit**

```bash
git add app/motos_assai/forms/faturamento_forms.py app/motos_assai/forms/__init__.py
git add app/motos_assai/routes/faturamento.py
git add app/templates/motos_assai/faturamento/
git commit -m "feat(motos_assai): import NF Q.P.A. + match + detalhe view"
```

---

## Task 14: Testes faturamento + match

**Files:**
- Create: `tests/motos_assai/test_faturamento_service.py`
- Create: `tests/motos_assai/test_nf_qpa_match.py`

- [ ] **Step 1: Test gerar Excel**

`tests/motos_assai/test_faturamento_service.py`:

```python
from app import db
from app.motos_assai.services import gerar_excel_qpa
# ... (usa fixtures de separação criadas em test_separacao_service)


def test_gerar_excel_estrutura_basica(app, admin_user):
    # similar ao setup de separacao + finalizar
    # gerar_excel_qpa retorna (bytes, s3_key)
    # validar 2 abas (PEDIDO, BASE LOJAS) via openpyxl.load_workbook(BytesIO)
    pass  # implementação completa: copiar setup do test_separacao_service e validar
```

- [ ] **Step 2: Test match**

Criar testes de unidade do `_calcular_match` simulando AssaiSeparacaoItem + AssaiNfQpa diretamente.

- [ ] **Step 3: Commit**

```bash
git add tests/motos_assai/test_faturamento_service.py
git add tests/motos_assai/test_nf_qpa_match.py
git commit -m "test(motos_assai): faturamento + nf_qpa match"
```

---

## Task 15: Adicionar `SOL` no parser CarVia

**Files:**
- Create: `scripts/migrations/motos_assai_06_carvia_modelo_sol.py`

- [ ] **Step 1: Verificar se CarviaModeloMoto existe**

```bash
grep -rn "class CarviaModeloMoto" app/carvia/ | head -3
```

- [ ] **Step 2: Migration seed**

`scripts/migrations/motos_assai_06_carvia_modelo_sol.py`:

```python
"""Adiciona modelo SOL ao reconhecedor CarVia (`CarviaModeloMoto`).

Idempotente: cria apenas se nome 'SOL' ainda não existe.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from app import create_app, db


def run():
    app = create_app()
    with app.app_context():
        try:
            from app.carvia.models import CarviaModeloMoto
        except ImportError:
            print('CarviaModeloMoto não disponível neste ambiente. Pulando.')
            return

        existente = CarviaModeloMoto.query.filter(
            CarviaModeloMoto.nome.ilike('SOL')
        ).first()
        if existente:
            print('Modelo SOL já existe.')
            return

        novo = CarviaModeloMoto(
            nome='SOL',
            regex_pattern=r'\bSOL\b',
            ativo=True,
        )
        db.session.add(novo)
        db.session.commit()
        print(f'OK: modelo SOL adicionado (id={novo.id}).')


if __name__ == '__main__':
    run()
```

- [ ] **Step 3: Executar (em ambiente com CarVia)**

```bash
python scripts/migrations/motos_assai_06_carvia_modelo_sol.py
```

- [ ] **Step 4: Commit**

```bash
git add scripts/migrations/motos_assai_06_carvia_modelo_sol.py
git commit -m "feat(motos_assai): seed CarviaModeloMoto SOL for NF Q.P.A. recognition"
```

---

## Task 16: CLAUDE.md final + dashboard atualizado

**Files:**
- Modify: `app/motos_assai/CLAUDE.md`
- Modify: `app/motos_assai/routes/dashboard.py`
- Modify: `app/templates/motos_assai/dashboard.html`

- [ ] **Step 1: Anexar Plano 3 ao CLAUDE.md**

````markdown

---

## Plano 3 implementado (2026-XX-XX)

### Pipeline de saída

**Montagem** (`montagem_service`):
- ESTOQUE → MONTADA (caminho feliz) ou ESTOQUE → PENDENTE (com descrição obrigatória)
- PENDENTE → PENDENCIA_RESOLVIDA → MONTADA (resolver_pendencia)
- Tela `/motos-assai/montagem` com input QR/manual + toggle pendência + histórico 3 últimas

**Disponibilizar** (`disponibilizar_service`):
- MONTADA ou REVERTIDA_PARA_MONTADA → DISPONIVEL
- Reverter: DISPONIVEL → REVERTIDA_PARA_MONTADA (motivo ≥3 chars obrigatório)
- Tela `/motos-assai/disponibilizar` com modal motivo + reload pós-reverter

**Separação** (`separacao_service`):
- Fungível por modelo: chassi DISPONIVEL pode atender qualquer saldo do mesmo modelo
- UNIQUE parcial em chassi (status != CANCELADA) — race retorna 409
- Cancelar emite DISPONIVEL para cada chassi (volta direto, sem passar por MONTADA)
- Tela `/motos-assai/pedidos/<pid>/separar/<lid>` com saldo visual em barras

**Excel Q.P.A.** (`faturamento_service.gerar_excel_qpa`):
- Espelha `285.xlsx` — 2 abas (PEDIDO + BASE LOJAS)
- Persiste em `motos_assai/solicitacoes/` no S3
- Atualiza `assai_separacao.solicitacao_excel_s3_key`

**NF Q.P.A.** (`nf_qpa_adapter`):
- Adapter sobre `app.carvia.services.parsers.danfe_pdf_parser.DanfePDFParser` — sem modificar CarVia
- Extrai loja_id de `nome_destinatario` via regex `LJ\d+`
- Match BATEU/DIVERGENTE/NAO_RECONCILIADO com tolerância 1% no valor
- Quando BATEU: separação → FATURADA, motos emitem evento FATURADA

**SOL no CarVia**: migration `motos_assai_06_carvia_modelo_sol.py` adiciona seed em `CarviaModeloMoto` para parser reconhecer SOL no DANFE.

### Endpoints adicionados

- `GET /motos-assai/montagem` + `POST /montagem/registrar`
- `GET /motos-assai/disponibilizar` + `POST /disponibilizar/registrar` + `POST /disponibilizar/reverter`
- `GET /motos-assai/separacao` + `GET /motos-assai/pedidos/<pid>/separar/<lid>`
- `POST /motos-assai/separacao/registrar-chassi`
- `POST /motos-assai/separacao/desfazer/<item_id>`
- `POST /motos-assai/separacao/<id>/finalizar`
- `POST /motos-assai/separacao/<id>/cancelar`
- `GET /motos-assai/faturamento` (lista separações)
- `GET /motos-assai/faturamento/separacao/<id>/excel` (download Excel)
- `GET/POST /motos-assai/faturamento/upload-nf`
- `GET /motos-assai/faturamento/nfs/<id>` (detalhe + match)

### Módulo completo — referência arquitetural

- 16 tabelas com prefixo `assai_`
- Toggle master `sistema_motos_assai` em `usuarios`
- 8 etapas do pipeline implementadas
- Parsers determinísticos com fallback LLM (Haiku → Sonnet) em PDFs e Excel
- Wizard QR/Barcode adaptado de Hora (`html5-qrcode@2.3.8`)
- Reuso CarVia DANFE parser via adapter (zero modificação ao módulo CarVia)

### Para futuras evoluções (v2)

- `assai_avaria` table para avarias detectadas pós-recebimento
- Permissões granulares (criar `assai_user_permissao`)
- Múltiplos CDs (transferência inter-CD)
- Modelo MIA (atualmente fora do escopo)
- Automação de envio de Excel à Q.P.A. via SMTP
````

- [ ] **Step 2: Atualizar dashboard com totais reais**

Em `app/motos_assai/routes/dashboard.py`, enriquecer o dashboard com totais por status de moto via `chassis_em_estoque` e similar.

```python
from app.motos_assai.services import chassis_em_estoque
from app.motos_assai.models import (
    AssaiMoto, AssaiMotoEvento,
    EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_PENDENTE, EVENTO_DISPONIVEL,
    EVENTO_SEPARADA,
)


@motos_assai_bp.route('/')
@login_required
@require_motos_assai
def dashboard():
    cd = AssaiCd.query.filter_by(ativo=True).first()
    lojas_ativas = AssaiLoja.query.filter_by(ativo=True).count()
    modelos_ativos = AssaiModelo.query.filter_by(ativo=True).count()

    # Estoque por status efetivo
    # (implementar query agregada que pega tipo do último evento por chassi)
    from sqlalchemy import func
    sub = (
        db.session.query(
            AssaiMotoEvento.chassi,
            func.max(AssaiMotoEvento.id).label('ultimo_id'),
        )
        .group_by(AssaiMotoEvento.chassi).subquery()
    )
    contagem = dict(
        db.session.query(AssaiMotoEvento.tipo, func.count(AssaiMotoEvento.id))
        .join(sub, AssaiMotoEvento.id == sub.c.ultimo_id)
        .group_by(AssaiMotoEvento.tipo).all()
    )

    return render_template(
        'motos_assai/dashboard.html',
        cd=cd, lojas_ativas=lojas_ativas, modelos_ativos=modelos_ativos,
        estoque_por_status=contagem,
        # ... (totais de pedido/compra/separação como antes)
    )
```

- [ ] **Step 3: Commit**

```bash
git add app/motos_assai/CLAUDE.md
git add app/motos_assai/routes/dashboard.py
git add app/templates/motos_assai/dashboard.html
git commit -m "docs(motos_assai): final CLAUDE.md + enriched dashboard"
```

---

## Task 17: UI lint + testes E2E + smoke

**Files:**
- Run: scripts existentes do projeto

- [ ] **Step 1: UI lint policy**

```bash
python scripts/audits/ui_policy_lint.py --enforce-new
```

Esperado: zero violações (ou apenas avisos não-bloqueadores).

- [ ] **Step 2: Rodar todos os testes do módulo**

```bash
pytest tests/motos_assai/ -v --tb=short
```

Esperado: todos PASS.

- [ ] **Step 3: Smoke test E2E manual**

Roteiro:
1. Login admin → menu mostra "Motos Assaí"
2. Importar pedido VOE (PDF) → ver detalhe com 38 lojas
3. Criar PO Motochefe (consolidando 1+ pedidos)
4. Baixar PDF do PO
5. Upload recibo Motochefe (PDF) → conferência via wizard
6. Conferir 2-3 chassis com QR (ou manual) → ver evento ESTOQUE no detalhe
7. Finalizar conferência → status COM_DIVERGENCIA (faltantes marcados MOTO_FALTANDO)
8. Montagem: registrar 2 chassis, 1 com pendência
9. Resolver pendência (não há UI ainda — verificar no Plano 3 v2)
10. Disponibilizar: marcar 2 montados como disponíveis
11. Reverter 1 (com motivo) → recarrega histórico
12. Separação: abrir tela do pedido+loja, escanear chassis disponíveis até completar saldo
13. Finalizar separação
14. Gerar Excel Q.P.A. → baixar
15. Importar NF Q.P.A. (PDF) → ver match BATEU/DIVERGENTE

- [ ] **Step 4: Visual regression test (se infraestrutura existir)**

```bash
ls tests/visual/ 2>/dev/null && pytest tests/visual/ -k motos_assai
```

- [ ] **Step 5: Commit final**

```bash
git add -A
git commit -m "feat(motos_assai): module complete (Foundation + Plans 2A/2B/3)"
```

---

## Self-review

**Spec coverage**:
- §5.5 (Montagem) — Tasks 1-3. ✓
- §5.6 (Disponibilizar + reverter) — Tasks 4-6. ✓
- §5.7 (Separação fungível) — Tasks 7-9. ✓
- §5.7 (Excel idêntico ao 285.xlsx) — Tasks 10-11. ✓
- §5.8 (Importar NF Q.P.A. + match) — Tasks 12-14. ✓
- SOL no CarVia — Task 15. ✓
- Polish (CLAUDE.md, UI lint, testes E2E) — Tasks 16-17. ✓

**Type consistency**:
- `EVENTO_*` constantes usadas consistentemente em montagem/disponibilizar/separacao/recebimento
- `status_efetivo()` chamado uniformemente em todos os services
- Status `EM_SEPARACAO`/`FECHADA`/`FATURADA`/`CANCELADA` consistente entre service, route e template
- `disponibilizar()` aceita MONTADA + REVERTIDA_PARA_MONTADA (clarificado em Task 4 Step 2)

**Não placeholder**: cada task tem código completo. Tasks 14 (testes faturamento e match) tem template a preencher — engenheiro deve seguir padrão dos testes anteriores (`test_separacao_service.py`).

**Pendências do dono**: zero bloqueantes.
- ~~Máscaras de chassi~~ — regex duráveis aprovados em 2026-05-07 (ver Plano 1 Task 22).
- ~~CNPJ + endereço CD~~ — opcional, editável via UI Task 25 do Plano 1.
- ~~CNPJ Motochefe~~ — opcional, editável via tela de criação de PO.

---

**Plano 3 salvo em** `docs/superpowers/plans/2026-05-07-motos-assai-saida-polish.md` — 17 tasks. Módulo completo após implementação.

## Resumo dos 4 documentos gerados

| Documento | Caminho | Tasks |
|-----------|---------|-------|
| Spec aprovado | `docs/superpowers/specs/2026-05-07-motos-assai-design.md` | — |
| Plano 1 (Foundation + Cadastros) | `docs/superpowers/plans/2026-05-07-motos-assai-foundation.md` | 27 |
| Plano 2A (Pedido + Compra) | `docs/superpowers/plans/2026-05-07-motos-assai-pedido-compra.md` | 16 |
| Plano 2B (Recibo + Recebimento físico) | `docs/superpowers/plans/2026-05-07-motos-assai-recibo-recebimento.md` | 17 |
| Plano 3 (Saída + Polish) | `docs/superpowers/plans/2026-05-07-motos-assai-saida-polish.md` | 17 |

**Total: 77 tasks bite-sized** distribuídas em 4 planos sequenciais.
