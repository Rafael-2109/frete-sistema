<!-- doc:meta
tipo: reference
camada: L3
sot_de: —
hub: docs/inventario-2026-05/02-gotchas/INDEX.md
superseded_by: —
atualizado: 2026-06-12
-->
# INV-021 — ETAPA A reporta resultado prematuro (race condition A↔B)

> **Papel:** INV-021 — ETAPA A reporta resultado prematuro (race condition A↔B).

> **Nota:** Renomeado de G021 em 2026-06-12 (T1.3) — colisao com a serie G0xx do dominio estoque `app/odoo/estoque/`.

**Status**: 🔴 ABERTO
**Severidade**: HIGH
**Sessão descoberto**: 2026-05-18 sessão 3 (tarde, batch 50 prods LF)

## Sintoma

ETAPA A (`StockInternalTransferService.transferir_quantidade_para_lote`)
retorna sucesso/falha para o Python ANTES de o Odoo finalizar o
`stock.move.line state=done` do `action_apply_inventory`. ETAPA B inicia
imediatamente após, consulta `stock.quant` e vê saldo OBSOLETO (pré-A).

Resultado: ETAPA B aloca qty maior do que realmente disponível, cria
move_lines reservando saldo inexistente. `action_assign` aceita (soft
reservation), mas `button_validate` rejeita com `Fault 2: "stock negativo
não é permitido"`.

## Evidência

Caso reproduzido (produto 104000003 ACUCAR, picking 317402):

| Tempo (BRT) | Evento |
|---|---|
| 13:25:31 | ETAPA A começou |
| 13:25:45 | ETAPA A reportou "concluida 14s OK=0 SKIP=39 FALHA=102" |
| 13:25:47 | ETAPA B criou picking 317402 (alocou 250 do lote 2025,2527/24) |
| 13:25:48 | `button_validate` falhou: stock negativo |
| **13:26:21** | **Odoo registrou `state=done` da operação A** (lote 2025,2527/24 -102.7120 -> Em Trânsito Ajuste) |
| 13:26:22 | Lote 1260207 recebeu 102.7120 (finalização A) |

**ETAPA A reportou OK=0 mas o ajuste 161380 ficou TRANSF_OK + EXECUTADO no DB local** — a transferência teve sucesso silencioso ~30s depois do retorno.

## Causa raiz hipotetizada

`stock.quant.action_apply_inventory` no Odoo CIEL IT executa hooks que
levam ~30s para finalizar. O retorno XML-RPC vem antes do commit completo
do movimento `state=done`. Provavelmente queue interna do Odoo (hooks,
constraints, computes).

## Workarounds possíveis

- **Sleep 60s entre ETAPA A e B** — garante flush. Trade-off: +60s
  no tempo total.
- **Re-validar quants ao iniciar ETAPA B** — adicionar polling até
  `quantity` ficar estável por N segundos antes de criar pickings.
- **Rodar ETAPA A e B em batches separados** — `--ate-etapa=A` primeiro,
  depois `--apenas-etapa=B`. Operador valida via UI Odoo entre os dois.
- **Logger checkar state=done dos quants antes de retornar** —
  modificar `StockInternalTransferService` para esperar
  `stock.move.line state=done` antes de retornar.

## Não é problema de location

A location (LF/Estoque=42) está correta. O problema é temporal: saldo
mostrado pelo `stock.quant` reflete um estado pré-A enquanto a A está
in-flight no Odoo.

## Decisão para próxima sessão LF

Antes de rodar batches grandes:
1. Rodar `--apenas-etapa=A` primeiro (`--confirmar`)
2. **Aguardar 2-5 min** para Odoo flush
3. Verificar `stock.quant` para o produto manualmente
4. Depois rodar `--apenas-etapa=B,C,D,E,F`

OU implementar workaround code-level (re-validar quants em ETAPA B).

## Ref

- `app/odoo/services/stock_internal_transfer_service.py` (alvo do fix)
- `scripts/inventario_2026_05/09_executar_onda1_bulk.py:413+` (ETAPA A)
- `docs/inventario-2026-05/02-gotchas/G022-etapa-b-sem-revalidar-saldo.md` (complementar)
- Log: `/tmp/bulk_lf_batch_20260518_132517.log`
