<!-- doc:meta
tipo: how-to
camada: L3
sot_de: —
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-02
-->
# Big Bang Callsites List — Status Legados

> **Papel:** Big Bang Callsites List — Status Legados.

## Indice

- [Objetivo](#objetivo)
- [Resultado do grep exaustivo](#resultado-do-grep-exaustivo)
- [Refatoracoes necessarias](#refatoracoes-necessarias)
  - [A. Codigo de producao (refatorar)](#a-codigo-de-producao-refatorar)
  - [B. Templates Jinja2 (refatorar)](#b-templates-jinja2-refatorar)
  - [C. Aliases temporarios em __init__.py (remover)](#c-aliases-temporarios-em-__init__py-remover)
  - [D. Tests (refatorar)](#d-tests-refatorar)
  - [E. Preservar como historia](#e-preservar-como-historia)
- [Decisoes de mapeamento](#decisoes-de-mapeamento)
- [Validacao final](#validacao-final)
- [Commits](#commits)

**Data**: 2026-05-13
**Spec**: `docs/superpowers/specs/2026-05-12-motos-assai-carregamento-divergencia-design.md` §14.4 + A18
**Plano**: `docs/superpowers/plans/2026-05-12-motos-assai-fase1-fundacao.md` Tasks 19 e 20
**Branch**: `feature/motos-assai-implementacao`

---

## Objetivo

Erradicar todos os callsites de status legados de `AssaiPedidoVenda`:
- `EM_PRODUCAO` → REMOVIDO (agora pedido fica `ABERTO` ate primeira NF — R4.2)
- `SEPARANDO` → REMOVIDO (idem)
- `FATURADO_PARCIAL` → renomeado para `PARCIALMENTE_FATURADO`

Estado novo (4 valores apenas): `ABERTO`, `PARCIALMENTE_FATURADO`, `FATURADO`, `CANCELADO`.

A transicao agora e calculada automaticamente por `recalcular_status_pedido(pedido_id)`
em `app/motos_assai/services/pedido_status_service.py` (Task 17).

---

## Resultado do grep exaustivo

```
=== Python (motos_assai) ===
app/motos_assai/services/compra_service.py:6:- Após consolidação: pedidos passam a EM_PRODUCAO; PO em ABERTA
app/motos_assai/services/compra_service.py:25:    PEDIDO_STATUS_ABERTO, PEDIDO_STATUS_EM_PRODUCAO,
app/motos_assai/services/compra_service.py:122:        p.status = PEDIDO_STATUS_EM_PRODUCAO
app/motos_assai/services/separacao_service.py:24:    PEDIDO_STATUS_EM_PRODUCAO, PEDIDO_STATUS_SEPARANDO,
app/motos_assai/services/separacao_service.py:278:    # Pedido -> SEPARANDO
app/motos_assai/services/separacao_service.py:280:    if pedido and pedido.status == PEDIDO_STATUS_EM_PRODUCAO:
app/motos_assai/services/separacao_service.py:281:        pedido.status = PEDIDO_STATUS_SEPARANDO
app/motos_assai/services/separacao_service.py:441:    # o pedido como SEPARANDO mesmo apos cancelar todas as seps — status
app/motos_assai/services/separacao_service.py:455:        if pedido and pedido.status == PEDIDO_STATUS_SEPARANDO:
app/motos_assai/services/separacao_service.py:456:            pedido.status = PEDIDO_STATUS_EM_PRODUCAO
app/motos_assai/services/separacao_service.py:459:                'cancelar_separacao: pedido %s revertido SEPARANDO -> EM_PRODUCAO '
app/motos_assai/models/pedido.py:6:# Status legados (EM_PRODUCAO, SEPARANDO, FATURADO_PARCIAL) REMOVIDOS — Big Bang Task 19.
app/motos_assai/models/pedido.py:8:PEDIDO_STATUS_PARCIALMENTE_FATURADO = 'PARCIALMENTE_FATURADO'  # renomeado de FATURADO_PARCIAL
app/motos_assai/routes/pedidos.py:290:        statuses=['ABERTO', 'EM_PRODUCAO', 'SEPARANDO', 'FATURADO_PARCIAL', 'FATURADO', 'CANCELADO'],
app/motos_assai/models/__init__.py:30:PEDIDO_STATUS_EM_PRODUCAO = 'EM_PRODUCAO'  # DEPRECATED — sera mapeado pra ABERTO via Migration 21
app/motos_assai/models/__init__.py:31:PEDIDO_STATUS_SEPARANDO = 'SEPARANDO'  # DEPRECATED — idem
app/motos_assai/models/__init__.py:32:PEDIDO_STATUS_FATURADO_PARCIAL = PEDIDO_STATUS_PARCIALMENTE_FATURADO  # DEPRECATED — alias direto
app/motos_assai/models/__init__.py:116:    'PEDIDO_STATUS_EM_PRODUCAO', 'PEDIDO_STATUS_SEPARANDO',
app/motos_assai/models/__init__.py:117:    'PEDIDO_STATUS_FATURADO_PARCIAL',

=== Templates Jinja2 (motos_assai) ===
app/templates/motos_assai/separacao/nova.html:95:  Importe um Pedido VOE e marque como EM_PRODUCAO para começar.
app/templates/motos_assai/pedidos/lista.html:53:  ... 'SEPARANDO' ... 'EM_PRODUCAO' ...

=== JS (motos_assai) ===
(zero matches)

=== Cross-modulo (todo app/) ===
(zero matches — nenhum outro modulo importa status legados de motos_assai)

=== Tests motos_assai ===
tests/motos_assai/test_compra_service.py:11,60,74    PEDIDO_STATUS_EM_PRODUCAO
tests/motos_assai/test_separacao_service.py:9,31     PEDIDO_STATUS_EM_PRODUCAO
tests/motos_assai/test_nf_qpa_match.py:13,60         PEDIDO_STATUS_EM_PRODUCAO
tests/motos_assai/test_faturamento_service.py:15,37,105  PEDIDO_STATUS_EM_PRODUCAO

=== Migrations (preservar — referencia historica) ===
scripts/migrations/motos_assai_21_simplificar_status_pedido.py — backfill (mantem)
scripts/migrations/motos_assai_24_check_status_aceitar_novos.py — DDL CHECK (mantem)

=== Specs e Plans (mantem como referencia historica) ===
docs/superpowers/specs/2026-05-08-...
docs/superpowers/plans/2026-05-07-... (planos antigos, narrativa historica)
docs/superpowers/specs/2026-05-12-motos-assai-carregamento-divergencia-design.md (spec atual ja descreve a remocao)
```

---

## Refatoracoes necessarias

### A. Codigo de producao (refatorar)

| # | Arquivo | Linha(s) | Match | Acao |
|---|---|---|---|---|
| 1 | `app/motos_assai/services/compra_service.py` | 6 | docstring `Após consolidação: pedidos passam a EM_PRODUCAO` | TROCAR docstring: pedido fica `ABERTO` ate primeira NF (R4.2) |
| 2 | `app/motos_assai/services/compra_service.py` | 25 | `PEDIDO_STATUS_ABERTO, PEDIDO_STATUS_EM_PRODUCAO,` | REMOVER `PEDIDO_STATUS_EM_PRODUCAO` do import |
| 3 | `app/motos_assai/services/compra_service.py` | 122 | `p.status = PEDIDO_STATUS_EM_PRODUCAO` | REMOVER (R4.2 — pedido fica ABERTO ate primeira NF) |
| 4 | `app/motos_assai/services/separacao_service.py` | 24 | `PEDIDO_STATUS_EM_PRODUCAO, PEDIDO_STATUS_SEPARANDO,` | REMOVER do import |
| 5 | `app/motos_assai/services/separacao_service.py` | 278-281 | comentario + update `pedido.status = SEPARANDO` em registrar_chassi | REMOVER bloco inteiro (4 linhas) |
| 6 | `app/motos_assai/services/separacao_service.py` | 441,455-461 | reverter `SEPARANDO` em cancelar_separacao | REMOVER bloco inteiro (apenas atualiza comment para refletir nova realidade) |
| 7 | `app/motos_assai/routes/pedidos.py` | 290 | `statuses=['ABERTO', 'EM_PRODUCAO', 'SEPARANDO', 'FATURADO_PARCIAL', 'FATURADO', 'CANCELADO']` | TROCAR para `['ABERTO', 'PARCIALMENTE_FATURADO', 'FATURADO', 'CANCELADO']` |

### B. Templates Jinja2 (refatorar)

| # | Arquivo | Linha | Match | Acao |
|---|---|---|---|---|
| 8 | `app/templates/motos_assai/separacao/nova.html` | 95 | mensagem `Importe um Pedido VOE e marque como EM_PRODUCAO` | TROCAR para `Importe um Pedido VOE para começar.` (sem mencionar status legado) |
| 9 | `app/templates/motos_assai/pedidos/lista.html` | 53 | badges com `'SEPARANDO'`, `'EM_PRODUCAO'` | TROCAR badges: incluir `'PARCIALMENTE_FATURADO'` (warning), remover legados |

### C. Aliases temporarios em __init__.py (remover)

| # | Arquivo | Linha(s) | Match | Acao |
|---|---|---|---|---|
| 10 | `app/motos_assai/models/__init__.py` | 29-32 | aliases `PEDIDO_STATUS_EM_PRODUCAO`, `PEDIDO_STATUS_SEPARANDO`, `PEDIDO_STATUS_FATURADO_PARCIAL` | REMOVER 4 linhas (29-32) |
| 11 | `app/motos_assai/models/__init__.py` | 115-117 | __all__ entries | REMOVER 3 entries do __all__ |

### D. Tests (refatorar)

| # | Arquivo | Linhas | Match | Acao |
|---|---|---|---|---|
| 12 | `tests/motos_assai/test_compra_service.py` | 11,60,74 | `PEDIDO_STATUS_EM_PRODUCAO` (import + asserts + setup) | TROCAR para `PEDIDO_STATUS_ABERTO`. Test de "transicao para EM_PRODUCAO" agora valida que pedido permanece ABERTO. Test de "consolidar nao-aberto" usa outro estado nao-ABERTO (PARCIALMENTE_FATURADO ou CANCELADO) |
| 13 | `tests/motos_assai/test_separacao_service.py` | 9,31 | import + setup `status=PEDIDO_STATUS_EM_PRODUCAO` | TROCAR para `PEDIDO_STATUS_ABERTO` (pedido fica ABERTO durante separacao) |
| 14 | `tests/motos_assai/test_nf_qpa_match.py` | 13,60 | import + setup `status=PEDIDO_STATUS_EM_PRODUCAO` | TROCAR para `PEDIDO_STATUS_ABERTO` |
| 15 | `tests/motos_assai/test_faturamento_service.py` | 15,37,105 | import + setup `status=PEDIDO_STATUS_EM_PRODUCAO` | TROCAR para `PEDIDO_STATUS_ABERTO` |

### E. Preservar como historia

| Arquivo | Razao |
|---|---|
| `scripts/migrations/motos_assai_21_simplificar_status_pedido.py` | Migration de backfill — DEVE referenciar status legados para mapear |
| `scripts/migrations/motos_assai_24_check_status_aceitar_novos.py` | Migration de CHECK constraint — DEVE referenciar legados em CHECK transicional |
| `docs/superpowers/specs/2026-05-12-...` | Spec descreve os status legados para contexto historico |
| `docs/superpowers/plans/2026-05-07-*` | Planos antigos — narrativa historica |
| `app/motos_assai/models/pedido.py:6` | Comentario descritivo "Status legados [...] REMOVIDOS" — preserva memoria do projeto |

---

## Decisoes de mapeamento

Conforme spec §14.4:

- **`EM_PRODUCAO`** → REMOVER updates. Pedido permanece `ABERTO` apos consolidacao em PO.
  Comparacoes raras (= 'EM_PRODUCAO') nao existem em prod (zero callsites encontrados).
- **`SEPARANDO`** → REMOVER updates em registrar_chassi e em cancelar_separacao.
  Status do pedido fica `ABERTO` ate primeira NF FATURADA chegar.
- **`FATURADO_PARCIAL`** → renomear para `PARCIALMENTE_FATURADO` (ja feito em pedido.py).
  Ajustar todos callsites que usam string literal.

A nova transicao e CALCULADA por `recalcular_status_pedido(pedido_id)` chamado:
- Apos NF importada (BATEU) — ja invocado no fluxo Task 17
- Apos cancelamento de NF — ja invocado no fluxo Task 17
- Defensivamente em finalizar_carregamento (Plano 2) — A13

---

## Validacao final

Pos-refactor, re-rodar:

```bash
grep -rn "EM_PRODUCAO\|SEPARANDO\|FATURADO_PARCIAL" \
    app/motos_assai/ app/templates/motos_assai/ app/static/motos_assai/ \
    --include='*.py' --include='*.html' --include='*.js'
```

**Esperado** (zero matches em codigo executavel):
- `app/motos_assai/models/pedido.py:6` — comentario historico (`Status legados [...] REMOVIDOS`)
- `app/motos_assai/models/pedido.py:8` — comentario do alias `# renomeado de FATURADO_PARCIAL`

Demais matches devem desaparecer.

---

## Commits

Conforme plano (1D.1 a 1D.4 — quatro commits incrementais):

1. **1D.1** — `docs(motos-assai): pre-flight scan callsites legados (Big Bang Task 19)`
2. **1D.2** — `refactor(motos-assai): erradicar status legados em services/routes/templates`
3. **1D.3** — `refactor(motos-assai): remover aliases temporarios PEDIDO_STATUS_EM_PRODUCAO/SEPARANDO/FATURADO_PARCIAL`
4. **1D.4** — `test(motos-assai): atualizar suites para status simplificado (Big Bang)`
