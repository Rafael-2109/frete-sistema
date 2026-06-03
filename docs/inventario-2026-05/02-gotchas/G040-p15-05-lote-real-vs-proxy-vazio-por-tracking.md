<!-- doc:meta
tipo: reference
camada: L3
sot_de: —
hub: docs/inventario-2026-05/02-gotchas/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# G040 — `P-15/05` é `stock.lot` REAL (não proxy-vazio) em produto `tracking='lot'`

> **Papel:** G040 — `P-15/05` é `stock.lot` REAL (não proxy-vazio) em produto `tracking='lot'`.

**Severidade**: HIGH (evaporação silenciosa de saldo em transferência interna)
**Status**: ✅ CORRIGIDO 2026-05-29 (decisão "Opção B" do Rafael — invariante codificada no átomo Skill 2)
**Detecção/prevenção**: ✅ invariante codificada em `resolver_lote_origem/destino` (`transfer.py`) — consulta `product.tracking` por produto. Coberta por pytest.
**Escopo**: Skill 2 `transferindo-interno-odoo` (`resolver_lote_origem`, `resolver_lote_destino`) + todos os callers: `transferir_loc_e_lote` (MODO D), `transferir_para_indisponivel`, e o orchestrator `pre_etapa_executor` (Skill 6, ajuste positivo puro).

## Sintoma

Transferência interna (MODO D `transferir_loc_e_lote`) com `nome_lote_destino='P-15/05'` em produto rastreado por lote (`tracking='lot'`):

1. O átomo retornava `status='EXECUTADO'`.
2. MAS a verificação no Odoo mostrava que **o saldo saiu da origem (`{emp}/Indisponível/MIGRAÇÃO`) e NÃO entrou no destino** (`{emp}/Estoque` ficava `qty=0`).
3. O saldo simplesmente **evaporava**.

Incidente real: 2026-05-28, os **17 MOVER** do bloco B do inventário (Indisp/MIGRAÇÃO → Estoque/P-15/05) — todos com saldo evaporado, exigindo rollback (+1.720,36 un restauradas) e reexecução via 2× Skill 1.

## Causa raiz

`resolver_lote_destino` (e `resolver_lote_origem`) tratavam o literal `'P-15/05'` como **proxy de "quant sem lote"** (`lot_id=None`):

```python
# ANTES (bug):
if nome_lote is None or (isinstance(nome_lote, str) and nome_lote.strip() in ('', 'P-15/05')):
    return None, 'P-15/05(sem-lote)', None   # <-- P-15/05 sempre vira lot_id=None
```

Para um produto `tracking='lot'`, criar um quant **SEM lote** (`lot_id=False`) é inválido no Odoo — o quant é **zerado** (o saldo não se mantém). Por isso o crédito no destino evaporava, enquanto o débito na origem (lote real MIGRAÇÃO) era efetivado: resultado líquido = perda de saldo.

### A inconsistência entre skills (o que tornou o bug sutil)

O nome `P-15/05` tem **duas semânticas em uso simultâneo** no projeto:

| Contexto | Significado de `P-15/05` | Onde |
|----------|--------------------------|------|
| Matching de planilha de inventário (D012/D013) | proxy de "linha sem lote" (`lot_id=False`) | `pre_etapa.py:129` `LOTE_DEFAULT_SEM_NOME` |
| Saldo real no Odoo atual | `stock.lot` **REAL** (299 lotes, um por produto) | criados pela Skill 1 `ajustar_quant --criar-se-faltar --lote 'P-15/05'` |

A **Skill 1** (`ajustar_quant`) sempre criou o `stock.lot` REAL "P-15/05" (`lote_acao=created`). A **Skill 2** (`transfer`) tratava o mesmo nome como vazio. Mesmo nome, comportamento OPOSTO entre as duas skills — origem do bug.

## Correção (Opção B — 2026-05-29)

A semântica de `P-15/05` passa a depender do `tracking` do produto (decisão do negócio, validada pelo Rafael):

| `tracking` | `P-15/05` resolve para |
|------------|------------------------|
| `'none'` | proxy de quant sem lote (`lot_id=None`) — comportamento legado preservado |
| `'lot'` / `'serial'` | `stock.lot` **REAL** (busca/cria via `lot_svc`) |

- `None` e `''` (string vazia) continuam **sempre** sem lote (sinal explícito; não leem tracking).
- Helper `_tracking_produto(product_id)` lê `product.product.tracking` 1x com cache local (evita N reads em loops). Default defensivo `'none'` se o read vier vazio.
- Parâmetro opcional `tracking=` em `resolver_lote_origem/destino` permite o caller fornecer o tracking e evitar o read.
- O `nome_canonico` retornado distingue os casos: `'P-15/05(sem-lote)'` (proxy) vs `'P-15/05'` (lote real). O `pre_etapa_executor` usa esse rótulo (em vez do nome de input) para decidir o `DRY_RUN_OK_LOTE_A_CRIAR` — assim o dry-run da pré-etapa reflete fielmente o `--confirmar` (cria lote real para produto rastreado).

## Como evitar / lição atemporal

- **Nunca crie saldo sem lote (`lot_id=False`) para produto `tracking != 'none'`** — o Odoo zera o quant.
- Quando um identificador textual (`P-15/05`, etc.) tem semântica diferente entre contextos (matching/leitura vs destino/escrita), **resolva por uma dimensão objetiva do dado** (aqui: `product.tracking`) em vez de uma lista hardcoded de "nomes proxy".
- Inconsistência entre 2 skills sobre o MESMO identificador (`P-15/05` real na Skill 1, vazio na Skill 2) = sinal de armadilha. Auditar todas as skills que tocam o identificador.

## Referências

- Fix: `app/odoo/estoque/scripts/transfer.py` (`_tracking_produto`, `resolver_lote_origem`, `resolver_lote_destino`) + `app/odoo/estoque/orchestrators/pre_etapa_executor.py` (`_executar_positivo_puro`, condição `DRY_RUN_OK_LOTE_A_CRIAR` por `nome_canonico`).
- Testes: `tests/odoo/services/test_stock_internal_transfer_service.py` (`test_resolver_lote_*_p15_tracking_*`) + `tests/odoo/services/test_pre_etapa_executor_orchestrator.py` (`test_executar_positivo_puro_dry_run_p15_lote_real_a_criar`).
- Workaround histórico do incidente (17 MOVER via 2× Skill 1): `/tmp/subagent-findings/gestor-estoque-EXEC2-2026-05-29.md` §P2.
- Relacionado: G031 (`stock.lot` é por produto) + G036 (lote literal vs operador `=`).
