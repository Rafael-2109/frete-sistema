<!-- doc:meta
tipo: how-to
camada: L3
sot_de: —
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# HORA — Pedido de Venda: editar item + Enter=Próximo + chassi autocomplete + regressões — Implementation Plan

> **Papel:** plano de implementação task-by-task das 4 frentes na tela unificada de Pedido de Venda das Lojas HORA — (A) editar item = só desconto/valor com a moto travada, (B) Enter avança campo, (C) chassi vira autocomplete, e (D) restauração das regressões CRÍTICAS+ALTAS da unificação anterior.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Na tela unificada de Pedido de Venda HORA: tornar a edição de uma moto restrita a desconto/valor (moto travada), fazer Enter avançar de campo, transformar o chassi em autocomplete, e restaurar os recursos/proteções CRÍTICOS+ALTOS perdidos na unificação anterior.

**Architecture:** Tudo em `app/hora/` — templates Jinja2 (`pedido_venda_novo.html`, `_componente_moto_desconto.html`, `_pedido_venda_scripts.html`), rotas (`vendas.py`, `autocomplete.py`) e service (`autocomplete_service.py`). Sem migrations. Worktree `feat/hora-pedido-venda-edicao` em `/home/rafaelnascimento/projetos/frete_sistema_hora_pv`.

**Tech Stack:** Flask 3.1 + SQLAlchemy 2.0 + Jinja2 + Bootstrap 5.3 + vanilla JS. Testes: pytest (`tests/hora/`). Spec: `docs/superpowers/specs/2026-06-03-hora-pedido-venda-edicao-autocomplete-design.md`.

## Indice

- [Convenções de execução](#convenções-de-execução)
- [Mapa de arquivos](#mapa-de-arquivos)
- [FASE 1 — Features (A+B+C)](#fase-1--features-abc)
- [FASE 2 — Regressões CRÍTICAS](#fase-2--regressões-críticas)
- [FASE 3 — Regressões ALTAS](#fase-3--regressões-altas)
- [Fechamento](#fechamento)

## Convenções de execução

- **Rodar tudo da raiz do worktree** `/home/rafaelnascimento/projetos/frete_sistema_hora_pv` (hooks PAD usam path relativo).
- **pytest**: ativar venv e passar `DATABASE_URL` da raiz (sem `.env` no worktree cai em SQLite). Comando padrão:
  `source /home/rafaelnascimento/projetos/frete_sistema/.venv/bin/activate && DATABASE_URL="$(grep -m1 '^DATABASE_URL=' /home/rafaelnascimento/projetos/frete_sistema/.env | cut -d= -f2-)" python -m pytest tests/hora/<arquivo> -v`
- **Recuperar o template antigo** (regressões): `git show 9a50b5af8^:app/templates/hora/venda_detalhe.html` (referências de linha do plano apontam para esse arquivo).
- **Commits frequentes**, um por task. Nunca usar `[skip render]`.
- Branch `feat/hora-pedido-venda-edicao` (não pushar até o usuário pedir).

## Mapa de arquivos

| Arquivo | Responsabilidade | Frentes |
|---------|------------------|---------|
| `app/hora/routes/vendas.py` | `vendas_item_editar` ignora `novo_chassi` | A |
| `app/hora/services/autocomplete_service.py` | `chassis()` + filtros `disponivel/modelo_id/cor` + campos extras | C |
| `app/hora/routes/autocomplete.py` | `autocomplete_chassi` repassa params | C |
| `app/templates/hora/tagplus/_componente_moto_desconto.html` | chassi vira `<input>` autocomplete; classes `.js-*` no desconto | A,C |
| `app/templates/hora/tagplus/_pedido_venda_scripts.html` | `wireDescontoSync` por-escopo; Enter; autocomplete-chassi JS; parcelas; frete multi-item; pagamentos | A,B,C,D |
| `app/templates/hora/tagplus/pedido_venda_novo.html` (modo edição) | collapse rico por item; restaurações D | A,D |
| `tests/hora/test_pedido_venda_editar_item.py` | testes Frente A (novo) | A |
| `tests/hora/test_autocomplete_chassi_disponivel.py` | testes Frente C (novo) | C |
| `app/hora/CLAUDE.md` | seção 19 documentando as mudanças | todas |

---

## FASE 1 — Features (A+B+C)

### Task 1: Backend — `vendas_item_editar` deixa de trocar a moto

**Files:**
- Modify: `app/hora/routes/vendas.py:584-612`
- Test: `tests/hora/test_pedido_venda_editar_item.py` (create)

- [ ] **Step 1: Escrever o teste que falha**

```python
# tests/hora/test_pedido_venda_editar_item.py
"""Frente A: editar item nunca troca a moto; so ajusta valor/desconto."""
from decimal import Decimal


def test_editar_item_ignora_novo_chassi(client_logado, venda_cotacao_2_itens):
    """POST com novo_chassi NAO troca o chassi do item (defesa em profundidade)."""
    venda = venda_cotacao_2_itens
    item = venda.itens[0]
    chassi_original = item.numero_chassi

    resp = client_logado.post(
        f'/hora/vendas/{venda.id}/itens/{item.id}/editar',
        data={
            'csrf_token': 'test',
            'novo_chassi': 'CHASSITROCADOXYZ',   # deve ser IGNORADO
            'valor_final': '9.999,00',
        },
        follow_redirects=False,
    )
    assert resp.status_code in (302, 303)

    from app.hora.models import HoraVendaItem
    item_atual = HoraVendaItem.query.get(item.id)
    assert item_atual.numero_chassi == chassi_original  # moto NAO trocou
    assert item_atual.preco_final == Decimal('9999.00')  # valor mudou
```

> Fixtures `client_logado` e `venda_cotacao_2_itens`: reusar/estender as de `tests/hora/test_pedido_workflow.py` (já criam venda COTACAO com itens, com CSRF desabilitado em config de teste). Se não existirem como fixtures compartilhadas, criar em `tests/hora/conftest.py` espelhando o setup de `test_pedido_workflow.py` (uuid nos chassis — ver memória `gotcha_testes_hora_residuo`).

- [ ] **Step 2: Rodar o teste e ver falhar**

Run: `... python -m pytest tests/hora/test_pedido_venda_editar_item.py -v`
Expected: FAIL — o item troca para `CHASSITROCADOXYZ` (rota ainda lê `novo_chassi`).

- [ ] **Step 3: Modificar a rota para ignorar `novo_chassi`**

Em `app/hora/routes/vendas.py`, na função `vendas_item_editar` (L584-612), remover a leitura de `novo_chassi` e passar `novo_chassi=None`:

```python
@hora_bp.route('/vendas/<int:venda_id>/itens/<int:item_id>/editar', methods=['POST'])
@require_hora_perm('vendas', 'editar')
def vendas_item_editar(venda_id: int, item_id: int):
    venda = HoraVenda.query.get_or_404(venda_id)
    if venda.loja_id and not usuario_tem_acesso_a_loja(venda.loja_id):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('hora.vendas_lista'))

    # Frente A (2026-06-03): editar item NUNCA troca a moto. Trocar = remover +
    # readicionar. A rota nao le mais `novo_chassi` (defesa em profundidade);
    # o service mantem a capacidade so para os testes de troca.
    valor_raw = (request.form.get('valor_final') or '').strip()
    novo_valor = None
    if valor_raw:
        try:
            novo_valor = _parse_decimal_form(valor_raw)
        except ValueError as exc:
            flash(f'Erro: {exc}', 'danger')
            return redirect(url_for('hora.vendas_detalhe', venda_id=venda.id))

    try:
        venda_service.editar_item_pedido(
            venda_id=venda.id, item_id=item_id,
            novo_chassi=None, novo_valor=novo_valor,
            usuario=_operador_atual(),
        )
        flash('Item atualizado.', 'success')
    except (ValueError, venda_service.ChassiIndisponivelError,
            venda_service.TransicaoInvalidaError) as exc:
        flash(f'Erro: {exc}', 'danger')
    return redirect(url_for('hora.vendas_detalhe', venda_id=venda.id))
```

- [ ] **Step 4: Rodar o teste e ver passar**

Run: `... python -m pytest tests/hora/test_pedido_venda_editar_item.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd /home/rafaelnascimento/projetos/frete_sistema_hora_pv
git add app/hora/routes/vendas.py tests/hora/test_pedido_venda_editar_item.py tests/hora/conftest.py
git commit -m "feat(hora): editar item nao troca a moto (so valor) — Frente A backend

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

### Task 2: Frontend — collapse de edição de item rico (desconto+valor, moto travada) + sincronia por-escopo

**Files:**
- Modify: `app/templates/hora/tagplus/_componente_moto_desconto.html` (adicionar classes `.js-desconto-pct/.js-desconto-rs/.js-valor` aos inputs de desconto)
- Modify: `app/templates/hora/tagplus/_pedido_venda_scripts.html` (extrair `wireDescontoSync`)
- Modify: `app/templates/hora/tagplus/pedido_venda_novo.html:378-395` (collapse rico por item)

- [ ] **Step 1: Adicionar classes utilitárias ao componente de desconto**

Em `_componente_moto_desconto.html`, acrescentar classes (sem remover os ids `f-*`):
- input desconto % (`id="f-desconto-pct"`): adicionar `js-desconto-pct`
- input desconto R$ (`id="f-desconto-rs"`): adicionar `js-desconto-rs`
- input valor (`id="f-valor"`): adicionar `js-valor`
- input preço tabela (`id="f-preco-tabela"`): adicionar `js-preco-tabela`

- [ ] **Step 2: Extrair `wireDescontoSync(rootEl, precoTabelaInicial)` no JS**

Em `_pedido_venda_scripts.html`, criar uma função reutilizável que opera por-escopo (querySelector dentro de `rootEl`), replicando a lógica de `recalcular(origem)` atual (preco null→mantém; pct/rs/valor clamp + arred2). Assinatura:

```javascript
// Sincroniza desconto% <-> desconto R$ <-> valor final dentro de um escopo.
// rootEl deve conter .js-desconto-pct, .js-desconto-rs, .js-valor.
// precoTabela: Number (preco de referencia) usado como ancora.
function wireDescontoSync(rootEl, precoTabela) {
  const elPct = rootEl.querySelector('.js-desconto-pct');
  const elRs  = rootEl.querySelector('.js-desconto-rs');
  const elVal = rootEl.querySelector('.js-valor');
  if (!elPct && !elRs && !elVal) return null;
  const state = { preco: precoTabela, lock: false };
  function recalc(origem) {
    if (state.lock) return;
    state.lock = true;
    try {
      const preco = state.preco;
      if (preco == null || preco <= 0) return;
      let pct = elPct ? parseBR(elPct.value) : NaN;
      let rs  = elRs ? parseBR(elRs.value) : NaN;
      let val = elVal ? parseBR(elVal.value) : NaN;
      if (origem === 'pct') {
        if (isNaN(pct)) pct = 0; pct = Math.max(0, Math.min(100, pct));
        rs = arred2(preco * pct / 100); val = arred2(preco - rs);
      } else if (origem === 'rs') {
        if (isNaN(rs)) rs = 0; rs = Math.max(0, Math.min(preco, rs));
        pct = preco > 0 ? arred2(rs / preco * 100) : 0; val = arred2(preco - rs);
      } else { // valor
        if (isNaN(val)) val = preco; val = Math.max(0, Math.min(preco, val));
        rs = arred2(preco - val); pct = preco > 0 ? arred2(rs / preco * 100) : 0;
      }
      if (elPct) setBR(elPct, arred2(pct));
      if (elRs)  setBR(elRs, rs);
      if (elVal) setBR(elVal, val);
    } finally { state.lock = false; }
  }
  if (elPct) elPct.addEventListener('change', () => recalc('pct'));
  if (elRs)  elRs.addEventListener('change', () => recalc('rs'));
  if (elVal) elVal.addEventListener('change', () => recalc('valor'));
  return { recalc, setPreco(p) { state.preco = p; } };
}
```

> `parseBR`, `setBR`, `arred2` já existem no topo de `_pedido_venda_scripts.html`. Manter a função global `recalcular` existente intacta para não quebrar o fluxo de criação nesta task (será o componente da criação migrado para `wireDescontoSync` na Task 5, junto com o autocomplete).

- [ ] **Step 3: Wire dos collapses de edição de item**

Ao final de `_pedido_venda_scripts.html`, adicionar (defensivo):

```javascript
// Frente A: cada collapse de edicao de item (#item-edit-<id>) tem sua propria
// sincronia de desconto, ancorada no preco de tabela do item (data-preco-tabela).
document.querySelectorAll('[data-item-edit-root]').forEach(function(root) {
  const preco = parseBR(root.dataset.precoTabela);
  wireDescontoSync(root, isNaN(preco) ? null : preco);
});
```

- [ ] **Step 4: Reescrever o collapse de edição de item no template**

Em `pedido_venda_novo.html`, substituir o bloco do collapse (L378-395) por (moto read-only + desconto + valor):

```html
{% if is_cotacao and pode_editar %}
<tr id="item-edit-{{ item.id }}" class="collapse">
  <td colspan="7" class="bg-body-tertiary">
    <form method="post" action="{{ url_for('hora.vendas_item_editar', venda_id=venda.id, item_id=item.id) }}"
          class="row g-2 align-items-end"
          data-item-edit-root data-preco-tabela="{{ item.preco_tabela_referencia or 0 }}">
      <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
      <div class="col-12 small text-muted mb-1">
        <i class="fas fa-lock"></i> Moto travada:
        <span class="chassi-mono">{{ item.numero_chassi }}</span> ·
        {{ item.moto.modelo.nome_modelo if item.moto and item.moto.modelo else '—' }} ·
        {{ item.moto.cor if item.moto else '—' }}
        <span class="ms-2">Para trocar a moto, remova o item e adicione outro.</span>
      </div>
      <div class="col-md-3">
        <label class="form-label small mb-1">Tabela ref.</label>
        <input type="text" class="form-control form-control-sm js-preco-tabela" readonly tabindex="-1"
               value="{{ item.preco_tabela_referencia|valor_br }}">
      </div>
      <div class="col-md-2">
        <label class="form-label small mb-1">Desconto (%)</label>
        <input type="text" class="form-control form-control-sm js-desconto-pct" inputmode="decimal"
               value="{{ item.desconto_percentual|numero_br(2) if item.desconto_percentual else '0,00' }}">
      </div>
      <div class="col-md-3">
        <label class="form-label small mb-1">Desconto (R$)</label>
        <input type="text" class="form-control form-control-sm js-desconto-rs" inputmode="decimal"
               value="{{ item.desconto_aplicado|numero_br(2) if item.desconto_aplicado else '0,00' }}">
      </div>
      <div class="col-md-2">
        <label class="form-label small mb-1">Valor final</label>
        <input type="text" name="valor_final" class="form-control form-control-sm fw-bold js-valor" inputmode="decimal"
               value="{{ item.preco_final|numero_br(2) }}">
      </div>
      <div class="col-md-2"><button type="submit" class="btn btn-sm btn-primary w-100">Salvar item</button></div>
    </form>
  </td>
</tr>
{% endif %}
```

> Só `valor_final` tem `name=` → é o único campo submetido (o backend deriva o desconto). `js-preco-tabela` é read-only (display). `data-preco-tabela` carrega o número cru para o JS.

- [ ] **Step 5: Validação visual (smoke + Playwright)**

Run (smoke render, sem 500):
`... python -c "from app import create_app; app=create_app(); c=app.test_client(); print('app ok')"`
Validação manual via Playwright (login bot `UI_VISUAL_EMAIL`/`UI_VISUAL_PASSWORD`): abrir um pedido COTACAO, expandir editar item, mudar % → R$ e valor sincronizam; salvar grava o valor; console sem erros.

- [ ] **Step 6: Commit**

```bash
git add app/templates/hora/tagplus/_componente_moto_desconto.html app/templates/hora/tagplus/_pedido_venda_scripts.html app/templates/hora/tagplus/pedido_venda_novo.html
git commit -m "feat(hora): edicao de item com desconto+valor sincronizados, moto travada — Frente A frontend

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

### Task 3: Backend — `autocomplete_service.chassis` com filtros disponivel/modelo/cor

**Files:**
- Modify: `app/hora/services/autocomplete_service.py:59-87`
- Test: `tests/hora/test_autocomplete_chassi_disponivel.py` (create)

- [ ] **Step 1: Escrever o teste que falha**

```python
# tests/hora/test_autocomplete_chassi_disponivel.py
"""Frente C: autocomplete de chassi com filtro de disponibilidade."""
from app.hora.services import autocomplete_service


def test_chassis_disponivel_exclui_vendidos(db_session, moto_em_estoque, moto_vendida):
    """disponivel=True retorna so chassis com ultimo evento em EVENTOS_EM_ESTOQUE."""
    res = autocomplete_service.chassis(
        q=moto_em_estoque.numero_chassi[:4],
        lojas_permitidas_ids=None, disponivel=True,
    )
    chassis = {r['chassi'] for r in res}
    assert moto_em_estoque.numero_chassi in chassis
    assert moto_vendida.numero_chassi not in chassis


def test_chassis_inclui_modelo_cor_no_json(db_session, moto_em_estoque):
    res = autocomplete_service.chassis(
        q=moto_em_estoque.numero_chassi[:4],
        lojas_permitidas_ids=None, disponivel=True,
    )
    assert res and 'modelo_id' in res[0] and 'cor' in res[0] and 'modelo' in res[0]
```

> Fixtures `moto_em_estoque` (último evento RECEBIDA/DISPONIVEL) e `moto_vendida` (último evento VENDIDA): criar em `tests/hora/conftest.py` via `registrar_evento` com chassis uuid.

- [ ] **Step 2: Rodar e ver falhar**

Run: `... python -m pytest tests/hora/test_autocomplete_chassi_disponivel.py -v`
Expected: FAIL — `chassis()` não aceita `disponivel`; JSON sem `modelo_id`.

- [ ] **Step 3: Estender `chassis()`**

Em `autocomplete_service.py`, alterar a assinatura e a query (reusar critério canônico do estoque_service):

```python
def chassis(q: str, lojas_permitidas_ids: Optional[List[int]] = None,
            limit: int = _DEFAULT_LIMIT, disponivel: bool = False,
            modelo_id: Optional[int] = None, cor: Optional[str] = None) -> List[dict]:
    """Busca chassis por substring (uppercase, ilike).

    disponivel=True restringe a chassis cujo ULTIMO evento esta em
    EVENTOS_EM_ESTOQUE (mesmo criterio de estoque_service). modelo_id/cor
    filtram opcionalmente. JSON inclui modelo_id/modelo/cor/loja_nome.
    """
    q_norm = (q or '').strip().upper()
    if len(q_norm) < _MIN_CHARS:
        return []

    base = (
        db.session.query(HoraMoto, HoraModelo)
        .join(HoraModelo, HoraMoto.modelo_id == HoraModelo.id)
        .filter(HoraMoto.numero_chassi.ilike(f'%{q_norm}%'))
    )
    if modelo_id:
        base = base.filter(HoraMoto.modelo_id == modelo_id)
    if cor:
        base = base.filter(HoraMoto.cor == cor.strip().upper())

    sub = _chassis_permitidos_subq(lojas_permitidas_ids)
    if sub is False:
        return []
    if sub is not None:
        base = base.filter(HoraMoto.numero_chassi.in_(sub))

    if disponivel:
        from sqlalchemy import and_
        from app.hora.services.estoque_service import (
            _subquery_ultimo_evento_id, EVENTOS_EM_ESTOQUE,
        )
        ult = _subquery_ultimo_evento_id()
        disp = (
            db.session.query(HoraMotoEvento.numero_chassi)
            .join(ult, and_(HoraMotoEvento.numero_chassi == ult.c.chassi,
                            HoraMotoEvento.id == ult.c.max_id))
            .filter(HoraMotoEvento.tipo.in_(EVENTOS_EM_ESTOQUE))
            .subquery()
        )
        base = base.filter(HoraMoto.numero_chassi.in_(disp))

    base = base.order_by(HoraMoto.numero_chassi).limit(limit)
    return [
        {
            'chassi': m.numero_chassi,
            'modelo_id': m.modelo_id,
            'modelo': modelo.nome_modelo,
            'cor': m.cor,
            'label': f'{m.numero_chassi} — {modelo.nome_modelo} ({m.cor})',
        }
        for m, modelo in base.all()
    ]
```

> `_subquery_ultimo_evento_id` e `EVENTOS_EM_ESTOQUE` existem em `estoque_service.py` (importar lazy para evitar ciclo). `loja_nome` é opcional — adicionar só se os testes/UX exigirem (mantém YAGNI).

- [ ] **Step 4: Rodar e ver passar**

Run: `... python -m pytest tests/hora/test_autocomplete_chassi_disponivel.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/hora/services/autocomplete_service.py tests/hora/test_autocomplete_chassi_disponivel.py tests/hora/conftest.py
git commit -m "feat(hora): autocomplete_service.chassis com filtro disponivel/modelo/cor — Frente C backend

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

### Task 4: Rota — `autocomplete_chassi` repassa os novos params

**Files:**
- Modify: `app/hora/routes/autocomplete.py:36-43`

- [ ] **Step 1: Atualizar a rota**

```python
@hora_bp.route('/autocomplete/chassi')
@require_hora_perm('estoque', 'ver')
def autocomplete_chassi():
    disponivel = (request.args.get('disponivel') or '0').strip() == '1'
    try:
        modelo_id = int(request.args.get('modelo_id') or 0) or None
    except ValueError:
        modelo_id = None
    cor = (request.args.get('cor') or '').strip().upper() or None
    return jsonify(autocomplete_service.chassis(
        q=request.args.get('q') or '',
        lojas_permitidas_ids=lojas_permitidas_ids(),
        limit=_limit_arg(),
        disponivel=disponivel, modelo_id=modelo_id, cor=cor,
    ))
```

- [ ] **Step 2: Smoke do endpoint**

Run: `... python -c "from app import create_app; app=create_app(); c=app.test_client(); print('rota ok')"`
(Teste funcional real exige login; coberto no Playwright da Task 5.)

- [ ] **Step 3: Commit**

```bash
git add app/hora/routes/autocomplete.py
git commit -m "feat(hora): rota autocomplete/chassi repassa disponivel/modelo_id/cor — Frente C rota

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

### Task 5: Frontend — chassi vira autocomplete + preenche modelo/cor/preço

**Files:**
- Modify: `app/templates/hora/tagplus/_componente_moto_desconto.html:18-24`
- Modify: `app/templates/hora/tagplus/_pedido_venda_scripts.html` (cascata → autocomplete)
- Modify: `pedido_venda_novo.html` (incluir `app/static/js/hora/autocomplete.js` se ainda não estiver no escopo da página)

- [ ] **Step 1: Trocar o `<select id="f-chassi">` por input autocomplete**

```html
<div class="col-md-4">
  <label class="form-label">Chassi <span class="text-danger">*</span></label>
  <input type="text" name="chassi" id="f-chassi" class="form-control chassi-mono"
         data-hora-autocomplete="chassi" data-hora-min-chars="2"
         data-hora-extra-params="disponivel=1" autocomplete="off" required>
  <small class="text-muted" id="chassi-status">Digite 2+ caracteres do chassi.</small>
</div>
```

- [ ] **Step 2: Garantir o JS do autocomplete carregado**

Verificar se `app/static/js/hora/autocomplete.js` é incluído em `hora/base.html` (ele auto-inicia no DOMContentLoaded). Se não estiver na página do pedido, adicionar `<script src="{{ url_for('static', filename='js/hora/autocomplete.js') }}"></script>` no bloco de scripts de `pedido_venda_novo.html`. (Confirmar via grep antes — `base.html` já registra `data-hora-autocomplete` em ~20 telas.)

- [ ] **Step 3: Adaptar o JS da cascata para o autocomplete**

Em `_pedido_venda_scripts.html`, na seção da cascata: o `#f-chassi` deixa de ser populado por `carregarChassis()`. Em vez disso:
- Quando `#f-modelo` ou `#f-cor` mudam: atualizar `f-chassi.dataset.horaExtraParams` para `disponivel=1` + (`modelo_id=<v>` se houver) + (`cor=<v>` se houver), limpar `f-chassi.value`, e re-inicializar o autocomplete via `window.HoraAutocomplete.init()` (re-attach é idempotente pelo guard `data-hora-autocomplete-inited`; para forçar re-leitura dos params, remover o atributo `data-hora-autocomplete-inited` antes de `init`).
- Quando o `#f-chassi` dispara `change` (item escolhido no dropdown): chamar a busca de preço (`atualizarPrecoTabela()` já existente, que usa modelo + forma) — e, se `#f-modelo`/`#f-cor` estiverem vazios, preenchê-los a partir do item escolhido. Para obter `modelo_id`/`cor` do chassi escolhido, usar `data-hora-target-key`/um pequeno fetch ao endpoint, OU ler do payload: estender o autocomplete genérico não é necessário — fazer um fetch leve a `/hora/autocomplete/chassi?q=<chassi>&disponivel=1&limit=1` e usar `modelo_id`/`cor` do primeiro resultado.

> Manter `carregarCores()` para popular o select de cor a partir do modelo (filtro). `carregarChassis()` pode ser removido (chassi não é mais select). Migrar o componente de criação para `wireDescontoSync` (Task 2) é opcional aqui se `recalcular` global continua funcionando; preferir migrar para evitar 2 caminhos — mas só se os testes/Playwright confirmarem paridade.

- [ ] **Step 4: Validação visual (Playwright)**

Login bot → Novo Pedido: escolher modelo → cor; digitar 2 chars no chassi → dropdown só com disponíveis daquele modelo/cor; escolher → preço de tabela carrega e desconto/valor sincronizam. Repetir em "Adicionar moto" na edição de um pedido COTACAO. Console sem erros.

- [ ] **Step 5: Commit**

```bash
git add app/templates/hora/tagplus/_componente_moto_desconto.html app/templates/hora/tagplus/_pedido_venda_scripts.html app/templates/hora/tagplus/pedido_venda_novo.html
git commit -m "feat(hora): chassi vira autocomplete (cascata modelo/cor como filtro) — Frente C frontend

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

### Task 6: Frente B — Enter avança campo (não submete)

**Files:**
- Modify: `app/templates/hora/tagplus/_pedido_venda_scripts.html` (novo bloco)

- [ ] **Step 1: Adicionar o handler global de Enter**

Ao final do IIFE de `_pedido_venda_scripts.html`:

```javascript
// Frente B: Enter avanca para o proximo campo em vez de submeter (telas novo+edicao).
// textarea mantem Enter (nova linha); botoes submit mantem (Enter no botao foca = clica).
(function() {
  const SEL = 'input:not([type=hidden]):not([type=submit]):not([type=button]), select';
  document.addEventListener('keydown', function(ev) {
    if (ev.key !== 'Enter') return;
    const el = ev.target;
    if (!el || !el.matches || !el.matches(SEL)) return;
    const form = el.closest('form');
    if (!form) return;
    ev.preventDefault();
    const focaveis = Array.from(form.querySelectorAll(
      'input:not([type=hidden]):not([disabled]), select:not([disabled]), textarea:not([disabled]), button:not([disabled])'
    )).filter(e => e.offsetParent !== null);
    const i = focaveis.indexOf(el);
    if (i >= 0 && i + 1 < focaveis.length) focaveis[i + 1].focus();
  });
})();
```

> Escopo: o handler só age em `input`/`select` (não `textarea`). Como o script é incluído em ambos os modos (criação + edição), cobre as duas telas. `offsetParent !== null` pula campos escondidos (ex.: collapses fechados, blocos de frete ocultos).

- [ ] **Step 2: Validação visual (Playwright)**

Novo Pedido: focar CPF, digitar, Enter → foca o próximo campo (Nome), o form NÃO é submetido. Em textarea (observações), Enter quebra linha. Botão "Salvar" continua submetendo por clique. Repetir na edição.

- [ ] **Step 3: Commit**

```bash
git add app/templates/hora/tagplus/_pedido_venda_scripts.html
git commit -m "feat(hora): Enter avanca para o proximo campo nas telas de pedido — Frente B

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

### Checkpoint Fase 1
Rodar a suíte HORA de regressão de pedido: `... python -m pytest tests/hora/test_pedido_workflow.py tests/hora/test_pedido_venda_editar_item.py tests/hora/test_autocomplete_chassi_disponivel.py -v`. Tudo verde. Pausa para review do usuário antes da Fase 2.

---

## FASE 2 — Regressões CRÍTICAS

> Todas no modo edição (`{% if venda %}`) de `pedido_venda_novo.html`. Recuperar markup de referência: `git show 9a50b5af8^:app/templates/hora/venda_detalhe.html`.

### Task 7: Restaurar seção "Peças do pedido"

**Files:** Modify `pedido_venda_novo.html` (após o card "Moto vendida", antes do card "Pagamento")

- [ ] **Step 1:** Recuperar o bloco do antigo (L857-933): `git show 9a50b5af8^:app/templates/hora/venda_detalhe.html | sed -n '857,933p'`.
- [ ] **Step 2:** Colar adaptado no modo edição: tabela `venda.itens_peca` (Código/Descrição/Qtd/Preço un./Desconto/Final), remoção via `hora.venda_remover_item_peca` com `confirm('Remover {{ ip.peca.codigo_interno }} do pedido?')`, adição via `hora.venda_adicionar_item_peca` com autocomplete `data-hora-autocomplete="peca"` (guard `is_cotacao and pode_editar`). Confirmar nomes de rota: `grep -n "def venda_adicionar_item_peca\|def venda_remover_item_peca" app/hora/routes/*.py`.
- [ ] **Step 3:** Smoke render de um pedido com peça (sem 500). Playwright: ver/add/remover peça.
- [ ] **Step 4:** Commit `feat(hora): restaura secao Pecas do pedido na edicao (regressao critica)`.

### Task 8: Restaurar botão "Reimportar do TagPlus"

**Files:** Modify `pedido_venda_novo.html` (barra de topo, perto de "NFe (TagPlus)")

- [ ] **Step 1:** Recuperar L51-67 do antigo. Guard `pode_criar and tem_emissao and venda.emissao_nfe.tagplus_nfe_id`, form POST `hora.tagplus_backfill_nfe_unica` com hidden `tagplus_nfe_id`, `confirm('Reimportar esta NF do TagPlus? Campos vazios serao preenchidos a partir da API; edicoes manuais sao preservadas.')`, `title` técnico. Confirmar rota: `grep -n "tagplus_backfill_nfe_unica" app/hora/routes/*.py`.
- [ ] **Step 2:** Smoke render de pedido FATURADO com emissão. 
- [ ] **Step 3:** Commit `feat(hora): restaura botao Reimportar do TagPlus na edicao (regressao critica)`.

### Task 9: Frete `disabled` (não `readonly`) quando não-CIF

**Files:** Modify `pedido_venda_novo.html:311-327` (modo edição)

- [ ] **Step 1:** No `<select name="modalidade_frete">` e nos inputs `valor_frete`/`tipo_frete_calc`, trocar `{% if ro_oper %}readonly{% endif %}` por `{% if ro_oper %}disabled{% endif %}` no `valor_frete` e garantir `disabled` (não readonly) também quando modalidade≠CIF. Justificativa: inputs `disabled` não são submetidos → preserva frete FOB legado (ver antigo L516-553).
- [ ] **Step 2:** Smoke + Playwright: editar header de um pedido FOB legado e salvar → `valor_frete` histórico preservado.
- [ ] **Step 3:** Commit `fix(hora): frete usa disabled (nao readonly) para preservar FOB legado (regressao critica)`.

### Task 10: Confirm do "Descartar (NF teste)" com aviso SEFAZ

**Files:** Modify `pedido_venda_novo.html:157`

- [ ] **Step 1:** Trocar `confirm('Descartar pedido #{{ venda.id }}?')` por `confirm('Descartar pedido #{{ venda.id }}? A NFe NAO sera cancelada na SEFAZ.')`.
- [ ] **Step 2:** Smoke render.
- [ ] **Step 3:** Commit `fix(hora): restaura aviso SEFAZ no confirm de descartar NF teste (regressao critica)`.

### Task 11: Aviso contextual de campos travados por status

**Files:** Modify `pedido_venda_novo.html` (após o botão "Salvar dados do pedido", L337-341)

- [ ] **Step 1:** Adicionar `<small class="text-muted d-block mt-1">` por status: FATURADO → "Pedido FATURADO — apenas observações são editáveis."; CONFIRMADO → "Pedido CONFIRMADO — cliente (nome/CPF) não pode mais ser alterado."; COTACAO → "Todos os campos editáveis." (NÃO mexer no guard `ro_oper`/`ro_cliente` — decisão #7).
- [ ] **Step 2:** Smoke render nos 3 status.
- [ ] **Step 3:** Commit `feat(hora): aviso contextual de campos editaveis por status (regressao critica)`.

### Checkpoint Fase 2
Smoke render dos 4 status sem 500. Pausa para review.

---

## FASE 3 — Regressões ALTAS

### Task 12: Restaurar KPIs (loja, chave 44d, data, valor, itens)
**Files:** Modify `pedido_venda_novo.html` (após a timeline)
- [ ] Recuperar L259-283 do antigo (row de `hora-kpi`). Colar no modo edição. Smoke render. Commit `feat(hora): restaura KPIs do pedido (chave acesso, data, valor) — regressao alta`.

### Task 13: Restaurar parcelamento + aviso intervalo<7d
**Files:** Modify `pedido_venda_novo.html` (card Frete/Observações) + `_pedido_venda_scripts.html`
- [ ] Recuperar L465-496 (campos `numero_parcelas`/`intervalo_parcelas_dias`) e o JS de aviso `<7 dias` (antigo L1001-1014). Guard: editáveis em COTACAO/CONFIRMADO (matriz `_CAMPOS_EDITAVEIS_HEADER`). A rota `vendas_editar` já lê ambos (`vendas.py:368-369`). Smoke + commit `feat(hora): restaura campos de parcelamento + aviso intervalo (regressao alta)`.

### Task 14: Auditoria com colunas Campo/De/Para
**Files:** Modify `pedido_venda_novo.html:504-518`
- [ ] Expandir a tabela de auditoria para colunas Quando/Quem/Ação/**Campo**/**De**/**Para**/Detalhe (`a.campo_alterado`, `a.valor_antes`, `a.valor_depois`). Confirmar nomes dos campos: `grep -n "campo_alterado\|valor_antes\|valor_depois" app/hora/models/*.py`. Smoke + commit.

### Task 15: Histórico de divergências (resolvidas)
**Files:** Modify `pedido_venda_novo.html`
- [ ] Recuperar L975-999 (`<details>` com `venda.divergencias` todas). Colar. Smoke + commit.

### Task 16: Frete CIF multi-item (data-item-* + alerta de margem)
**Files:** Modify `pedido_venda_novo.html` (linhas da tabela de itens) + `_pedido_venda_scripts.html`
- [ ] Adicionar `data-item-chassi`/`data-item-final`/`data-item-tabela` nos `<tr>` de item. Recuperar a função de preview de frete multi-item do antigo (L1082-1218) e portar para `_pedido_venda_scripts.html` operando sobre `tr[data-item-chassi]`. Playwright: alerta "abaixo da tabela" aparece. Commit.

### Task 17: Vendedor — fallback "(não habilitado)"
**Files:** Modify `pedido_venda_novo.html:244-250`
- [ ] Após o loop `vendedores_disponiveis`, se `venda.vendedor` não está na lista, adicionar `<option value="{{ venda.vendedor }}" selected>{{ venda.vendedor }} · (não habilitado)</option>` (recuperar lógica antiga L364-366). Smoke + commit.

### Task 18: Pagamentos — badge INCOMPLETO + total + Tipo + IDs do JS
**Files:** Modify `pedido_venda_novo.html` (card Pagamento, modo edição) + `_pedido_venda_scripts.html`
- [ ] **Step A:** Confirmar em runtime se o editor de edição tem JS (IDs `pag-edit-*` vs `pagamentos-container`/`pag-soma` que o script usa). `grep -n "pag-edit-container\|pag-edit-soma\|pagamentos-container\|pag-soma" app/templates/hora/tagplus/*.html`.
- [ ] **Step B:** Alinhar IDs (usar os do modo criação OU wire explícito do editor de edição) para soma em tempo real + AUT/ID dinâmico. Adicionar badge "INCOMPLETO" no card-header quando `is_incompleto`, linha "total formas vs pedido" e coluna "Tipo" na view de leitura (recuperar antigo L585-634). Playwright: somar formas atualiza total. Commit.

### Task 19: Guard de modalidade de frete legada
**Files:** Modify `pedido_venda_novo.html:310-314`
- [ ] Se `mf not in ('0','1')`, adicionar `<option value="{{ mf }}" selected disabled>{{ mf }} (legado, troque para CIF ou FOB)</option>` (recuperar antigo L509-513). Smoke + commit.

### Checkpoint Fase 3
Smoke render dos 4 status + pedido com peças + pedido FATURADO. Suíte `tests/hora/` verde.

---

## Fechamento

### Task 20: Documentação
**Files:** Modify `app/hora/CLAUDE.md` (nova seção 19) + `docs/superpowers/plans/INDEX.md`
- [ ] Adicionar seção "19. Pedido de Venda — editar item (moto travada), Enter, chassi autocomplete, restauração de regressões — 2026-06-03" no `app/hora/CLAUDE.md` resumindo as 4 frentes + ponteiros spec/plano.
- [ ] Registrar o plano em `docs/superpowers/plans/INDEX.md`.
- [ ] Commit `docs(hora): documenta edicao de item + autocomplete + regressoes (CLAUDE.md secao 19)`.

### Entrega
- Suíte `tests/hora/` verde; smoke render dos 4 status sem 500; Playwright das 3 frentes OK.
- NÃO pushar nem mergear sem o usuário pedir (branch `feat/hora-pedido-venda-edicao`).
- Ao finalizar, usar `superpowers:finishing-a-development-branch` para decidir merge/PR.
