---
name: operando-reservas-odoo
description: >-
  Skill WRITE (átomo C1/C2) para OPERAR RESERVAS no Odoo: cirurgia (cancelar
  moves órfãos preservando picking) ou cancelamento (picking inteiro via
  action_cancel). Usar quando o pedido é "limpa reserva órfã do picking X",
  "cancela picking Y", "remove move.lines apontando para quant zerado",
  "MLs órfãs no picking Z", "picking quebrado pós-ajuste de inventário".
  `--dry-run` é o DEFAULT; só efetiva com `--confirmar`.
  NÃO USAR PARA:
  - ajustar saldo de quant (não toca reservas) -> ajustando-quant-odoo
  - cancelar MO de produção (mrp.production) -> operando-mo-odoo (futura skill)
  - mover saldo entre lotes/locais -> transferindo-interno-odoo (futura)
  - só consultar reservas/MLs (não altera) -> consultando-sql
allowed-tools: Read, Bash, Glob, Grep
---

# operando-reservas-odoo (WRITE — átomos C1/C2)

Skill **mínimo viável** (C1 mineração ✅ · C2-C5 implementado para 2 átomos · C6-C10 conforme uso). Construída em 2026-05-23 a partir do caso real "6 pickings com 15 MLs órfãs pós-`--resetar-reserva` da skill 1".

Constituição: `app/odoo/estoque/CLAUDE.md`. Service: `app/odoo/estoque/scripts/reserva.py`.

---

## REGRAS CRÍTICAS
1. **`--dry-run` é o DEFAULT.** Sem `--confirmar`, só calcula e mostra o plano (exit 4).
2. **Verificar no Odoo** após efetivar — operação viva.
3. **NÃO usar este átomo para zerar `reserved_quantity` direto sem antes liberar a ML/picking** — gera estado fantasma (MLs órfãs).
4. **Cirurgia preserva** o picking; **cancelamento** descarta. Saber qual é o intento ANTES de invocar.

## Contrato — Cirurgia (átomo 1)

```
objeto:        stock.move + stock.move.line (cirurgia em 1+ moves de um picking)
input:         --picking-id <id> --ml-ids <ml1,ml2,...> --moves-writes "m1:qty1,m2:qty2,..." [--confirmar]
                 (--moves-writes: dict {move_id: novo_product_uom_qty}; use 0
                  para zerar move com 1 ML órfã, ou soma das MLs OK que sobram
                  para moves multi-ML mistos)
output (JSON): {status, picking_id, picking_state_antes, picking_state_depois,
                 ml_ids_unlinked, moves_ajustados, moves_estado, tempo_ms}
pré-condições: picking existe; state NOT IN ['done', 'cancel']
pós-condições: MLs com ml_ids removidas; moves com move_ids têm product_uom_qty
               ajustado conforme moves_writes; picking mantém state (Odoo pode
               mover para partially_available)
gotchas-invariante: stock.move._action_cancel é PRIVADO no XML-RPC → workaround
                    é unlink ML + write product_uom_qty
modos:         --dry-run (default, exit 4) -> --confirmar (exit 0)
status:        CIRURGIA_OK · DRY_RUN_OK · FALHA_PICKING_NAO_EXISTE ·
               FALHA_PICKING_STATE_INVALIDO · FALHA_ODOO
```

## Contrato — Cancelamento inteiro (átomo 2)

```
objeto:        stock.picking inteiro (cascateia para moves e MLs)
input:         --picking-id <id> [--confirmar]
output (JSON): {status, picking_id, picking_state_antes, picking_state_depois,
                 moves_count_antes, tempo_ms}
pré-condições: picking existe; state NOT IN ['done', 'cancel']
                (se state='cancel': NOOP; se state='done': falha)
pós-condições: picking.state='cancel'; moves filhas state='cancel';
               MLs filhas removidas/cancel; quant.reserved_quantity recalculado
gotchas-invariante: action_cancel é nativo do Odoo (cascade automático)
modos:         --dry-run (default) -> --confirmar
status:        PICKING_CANCELADO · DRY_RUN_OK · NOOP · FALHA_*
```

## Receitas (caso real -> args)

| Preciso de... | Atomo | Args |
|---------------|-------|------|
| Limpar 1 ML órfã preservando picking | cirurgia | `--picking-id P --move-ids M --ml-ids ML --confirmar` |
| Limpar 6 MLs órfãs em 1 picking | cirurgia | `--picking-id P --move-ids M1,M2,... --ml-ids ML1,ML2,... --confirmar` |
| Cancelar picking sem MLs válidas | cancelamento | `--cancelar-picking --picking-id P --confirmar` |
| Cancelar picking com poucas MLs válidas | cancelamento | idem (operação/Fiscal decide) |

## Catálogo de átomos (alguns implementados, outros previstos)

| Átomo | Status | Quando implementar |
|---|---|---|
| `cancelar_moves_orfaos(picking_id, ml_ids, moves_writes)` | ✅ implementado | — |
| `cancelar_picking_inteiro(picking_id)` | ✅ implementado | — |
| `zerar_reserved_residual(quant_ids)` | ✅ implementado | cleanup stale APÓS unreserve/unlink (descoberta 2026-05-23: unlink ML gera `reserved_quantity` NEGATIVO se quant já estava zerado) |
| `unreserve_picking(picking_id)` | ⬜ previsto | quando precisar liberar sem cancelar (preserva moves) |
| `unreserve_mo(mo_id, reassign=False)` | ⬜ previsto | quando precisar liberar reservas de componentes de MO |
| `find_orphan_mls(quant_ids)` | ⬜ previsto | identificar MLs órfãs por quant_id (helper read) |

## Composição em FLUXOS

- **Pós-`--resetar-reserva` da skill 1**: a skill 1 zera `quant.reserved_quantity` mas não toca `stock.move.line` → MLs órfãs. Esta skill 2.4 resolve em 3 passos:
  1. **Cirurgia** (`cancelar_moves_orfaos`) ou **Cancelamento** (`cancelar_picking_inteiro`) — remove as MLs órfãs e ajusta moves parent.
  2. **EFEITO COLATERAL DESCOBERTO (2026-05-23):** o unlink da ML faz Odoo recalcular `reserved_quantity = reserved_anterior − ml.quantity`. Se o quant já estava com `reserved=0` (pós-resetar-reserva), o resultado fica **NEGATIVO** — estado fantasma.
  3. **`zerar_reserved_residual(quant_ids)`** — limpa o residual negativo. **OBRIGATÓRIO chamar após qualquer operação que mexa em MLs apontando para quants já com reserved=0**.

## Armadilhas

- **`stock.move._action_cancel` é PRIVADO** no XML-RPC (validado 2026-05-23 contra odoo-17-ee-nacomgoya-prd). Workaround: `ml.unlink() + move.write({product_uom_qty: 0})`. Documentado como G025.
- **`reserved_uom_qty` NÃO existe** em Odoo 16/17 (G024). Usar `quantity` ou `qty_done`.
- **`picking.state='done'` é IMUTÁVEL** — não tentar reverter. Validação à priori na skill.
- **Cirurgia pode deixar `move.state='confirmed'` ou `waiting`** (Odoo pode tentar re-assign) — se isso for problema, usar cancelamento inteiro.
- **`stock.picking.do_unreserve` libera TODAS as MLs do picking** — não usar para cirurgia em picking com MLs válidas.

## Exemplos

```bash
SK=.claude/skills/operando-reservas-odoo/scripts/operar_reserva.py

# 1) Dry-run: cirurgia em FB/FB/EMB/11673 (1 ML órfã)
python "$SK" --picking-id 316701 --move-ids 1075205 --ml-ids 217654353

# 2) Efetivar
python "$SK" --picking-id 316701 --move-ids 1075205 --ml-ids 217654353 --confirmar

# 3) Cancelar picking inteiro (FB/INT/07950 — só tinha 1 ML, virou órfã)
python "$SK" --cancelar-picking --picking-id 320076 --confirmar
```

## Validação

A skill foi construída em 2026-05-23 a partir do caso real "6 pickings × 15 MLs órfãs pós-`--resetar-reserva` da skill 1". Mineração C1 baseada em 4 scripts-fonte (`remover_reservas_saida`, `cancelar_reservas_migracao`, `limpar_reservas_fantasma`, `auditoria/teste_unlink_moveline_fantasma`). Probes em produção identificaram que `stock.move._action_cancel` é private XML-RPC (workaround documentado). Ver `_validados/operando-reservas-odoo/VALIDACAO.md` para evidência do write real.
