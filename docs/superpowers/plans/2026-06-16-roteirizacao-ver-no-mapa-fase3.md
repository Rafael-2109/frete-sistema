<!-- doc:meta
tipo: scratch
camada: L3
sot_de: —
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-16
-->

# Roteirizacao "Ver no Mapa" — Fase 3 (Cotacao por rota + extras) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cotar frete a partir de uma rota salva (reusando o wizard de cotacao existente), permitir origem configuravel e reordenacao manual (drag-and-drop) da rota.

**Architecture:** Nova rota `POST /api/rota/<id>/cotar` em `mapa_routes.py` que carrega os `lotes` de uma `RotaSalva` e popula a sessao de cotacao (mesmo contrato de `cotar_frete_mapa`). UI no `mapa_pedidos.html`: botao "Cotar" na lista de rotas salvas, input de origem (ja aceito pelas APIs), e drag-and-drop HTML5 nativo no painel lateral.

**Tech Stack:** Flask 3.1 + SQLAlchemy 2.0, Jinja2 + jQuery + HTML5 Drag and Drop, pytest.

## Global Constraints

- Reusar o contrato de sessao de cotacao: `session['cotacao_lotes']` + `session['cotacao_pedidos']` (= lista de `separacao_lote_id`), `session.pop('alterando_embarque')`, redirect `url_for('cotacao.tela_cotacao')` — IDENTICO a `cotar_frete_mapa` (mapa_routes). NAO alterar o "step 1" da cotacao (memoria).
- `RotaSalva.lotes` JA sao `separacao_lote_id` — nao precisa resolver por num_pedido.
- Origem: APIs `/api/rota/otimizar` (Fase 1) e `/api/rota-clientes` (legado) JA aceitam `origem` no payload; falta a UI enviar. Default vazio = CD.
- Drag-and-drop: HTML5 nativo (`draggable`, `dragstart`/`dragover`/`drop`) — sem dependencia nova.
- Testes: fixtures `db`/`client` (savepoint; LOGIN_DISABLED, CSRF off); pytest da raiz do worktree; venv da raiz principal.
- Construido sobre Fases 1-2 (mesmo branch). `RotaSalva`, `cotar_frete_mapa` ja existem.

---

### Task 1: API cotar a partir de rota salva

**Files:**
- Modify: `app/carteira/routes/mapa_routes.py`
- Test: `tests/carteira/test_api_cotar_rota.py`

**Interfaces:**
- Consumes: `RotaSalva`, `session`, `url_for`.
- Produces: `POST /carteira/mapa/api/rota/<int:rota_id>/cotar` -> popula `session['cotacao_lotes']`/`['cotacao_pedidos']` com `rota.lotes`, `session.pop('alterando_embarque', None)`, retorna `{sucesso, total_lotes, lotes, redirect}`. 404 se rota inexistente; 400 se rota sem lotes.

- [ ] **Step 1: Teste que falha** — `tests/carteira/test_api_cotar_rota.py`

```python
from app.carteira.models import RotaSalva


def test_cotar_por_rota_salva(client, db):
    r = RotaSalva(nome='Rota Cotar', lotes=['LOTE-A', 'LOTE-B'], status='salva')
    db.session.add(r)
    db.session.flush()

    resp = client.post(f'/carteira/mapa/api/rota/{r.id}/cotar')
    assert resp.status_code == 200
    body = resp.get_json()
    assert body['sucesso'] is True
    assert set(body['lotes']) == {'LOTE-A', 'LOTE-B'}
    assert '/cotacao' in body['redirect'] or 'cotacao' in body['redirect']
    with client.session_transaction() as sess:
        assert set(sess['cotacao_lotes']) == {'LOTE-A', 'LOTE-B'}


def test_cotar_rota_inexistente_404(client, db):
    resp = client.post('/carteira/mapa/api/rota/999999/cotar')
    assert resp.status_code == 404
```

- [ ] **Step 2: Rodar — FAIL** (404 na rota nova)

Run: `pytest tests/carteira/test_api_cotar_rota.py -q`

- [ ] **Step 3: Implementar** — `app/carteira/routes/mapa_routes.py` (apos `rota_adicionar_cliente`)

```python
@bp.route('/api/rota/<int:rota_id>/cotar', methods=['POST'])
@login_required
def rota_cotar(rota_id):
    """Cota o frete a partir de uma rota salva: popula a sessao de cotacao com
    os lotes da rota e redireciona para o wizard (mesmo contrato de cotar_frete_mapa)."""
    try:
        rota = RotaSalva.query.get(rota_id)
        if not rota:
            return jsonify({'erro': 'Rota nao encontrada'}), 404
        lotes = list(rota.lotes or [])
        if not lotes:
            return jsonify({'erro': 'Rota sem lotes'}), 400
        session['cotacao_lotes'] = lotes
        session['cotacao_pedidos'] = lotes  # retrocompat
        session.pop('alterando_embarque', None)
        return jsonify({
            'sucesso': True,
            'total_lotes': len(lotes),
            'lotes': lotes,
            'redirect': url_for('cotacao.tela_cotacao'),
        })
    except Exception as e:
        logger.error(f"Erro ao cotar rota salva: {e}")
        return jsonify({'erro': str(e)}), 500
```

- [ ] **Step 4: Rodar — PASS**

Run: `pytest tests/carteira/test_api_cotar_rota.py -q`

- [ ] **Step 5: Commit**

```bash
git add app/carteira/routes/mapa_routes.py tests/carteira/test_api_cotar_rota.py
git commit -m "feat(roteirizacao): API cotar frete a partir de rota salva (F3)"
```

---

### Task 2: UI — cotar rota + origem configuravel + drag-and-drop

**Files:**
- Modify: `app/templates/carteira/mapa_pedidos.html`

**Interfaces:**
- Consumes: `/api/rota/<id>/cotar`, `/api/rota/otimizar` (origem), `/api/rota-clientes` (origem).
- Produces: UI funcional (smoke render server-side; smoke visual no browser = pendencia).

- [ ] **Step 1: Botao "Cotar" na lista de rotas salvas** — em `abrirRotasSalvas()`, adicionar por item um botao que chama `cotarRotaSalva(id)`; implementar `cotarRotaSalva(id)` = `POST /api/rota/<id>/cotar` -> `window.location.href = resp.redirect`.

- [ ] **Step 2: Input de origem** — no painel de parametros: `<input id="rotaOrigem" placeholder="Origem (vazio = CD Nacom)">`. Em `calcularRotaOtimizada()` e `atualizarCustoRota()`, incluir `origem: $('#rotaOrigem').val() || undefined` (so envia se preenchido) no payload.

- [ ] **Step 3: Drag-and-drop no painel** — em `atualizarListaClientes()`, marcar cada `.cliente-item` com `draggable="true"` + handlers; implementar `reordenarClientesDnD(from, to)` que move em `clientesData`, re-renderiza (`atualizarListaClientes`) e recalcula (`recalcularTotais`, `atualizarCustoRota`); a nova ordem vira a ordem da rota ao salvar.

- [ ] **Step 4: Smoke render**

Run: boot + `test_client().get('/carteira/mapa/visualizar?lotes[]=X')` == 200.

- [ ] **Step 5: Commit**

```bash
git add app/templates/carteira/mapa_pedidos.html
git commit -m "feat(roteirizacao): UI cotar rota salva + origem configuravel + drag-and-drop (F3)"
```

---

## Self-Review

- **Cobertura do escopo F3:** cotacao por rota salva (T1 API + T2 UI) ✓ · origem configuravel (T2) ✓ · drag-and-drop (T2) ✓.
- **Placeholders:** T1 com codigo completo; T2 e UI (passos descritivos + smoke, sem teste automatizado por ser template/DnD).
- **Consistencia:** `rota_cotar` usa o MESMO contrato de sessao de `cotar_frete_mapa`; `RotaSalva.lotes` reusado; origem ja aceita pelas APIs das Fases 1-2.
- **Encerra o pedido original:** "cotacao de frete por rota armazenada" era o ultimo item pendente da demanda inicial; drag-and-drop e origem eram extras sugeridos.
