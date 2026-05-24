# VALIDACAO — skill `operando-reservas-odoo`

Skill nascida em 2026-05-23 para resolver o efeito colateral do `--resetar-reserva` da skill 1 (`ajustando-quant-odoo`).

**Status:** ✅ C1 (mineração 4 scripts-fonte) + C2-C5 (3 átomos implementados) + **write real validado em produção** (6 operações em 6 pickings + 15 quants limpos).

**Constituição:** [`app/odoo/estoque/CLAUDE.md`](../../../../app/odoo/estoque/CLAUDE.md) · **Service:** [`app/odoo/estoque/scripts/reserva.py`](../../../../app/odoo/estoque/scripts/reserva.py) · **Skill:** [`.claude/skills/operando-reservas-odoo/`](../../../../.claude/skills/operando-reservas-odoo/SKILL.md)

---

## C1 — Mineração (4 scripts-fonte lidos integral, 2026-05-23)

| Script-fonte | LOC | O que mineramos |
|---|---|---|
| `remover_reservas_saida.py` | 247 | Base 4 companies. 3 fases: pickings.do_unreserve + MOs.do_unreserve + cleanup `reserved_quantity` direto. Batch 50 com fallback. Filtra MOs ativas (NÃO mexe done/to_close). |
| `cancelar_reservas_migracao.py` | 295 | Cirurgia por CSV. Busca MLs com `qty_done=0` que reservam quant pulado. `do_unreserve` para pickings, `unlink` direto para MLs de MO sem picking. |
| `limpar_reservas_fantasma.py` | 202 | Específico Pré-Produção FB/LF (locations 4068/4066/4067/27458/30718/48/20140/53/54). Fallback de métodos: `do_unreserve`/`button_unreserve`/`action_unreserve`. Reassign após unreserve em MOs ativas. |
| `auditoria/teste_unlink_moveline_fantasma.py` | 99 | Canary 1 ML. Validou que `stock.move.line.unlink` funciona em MLs de MOs done. |

**Probes em produção (2026-05-23, odoo-17-ee-nacomgoya-prd):**
- ❌ `stock.move._action_cancel` — privado XML-RPC (`<Fault 4: Private methods cannot be called>`)
- ❌ `stock.move.action_cancel`, `button_cancel`, `do_unreserve` — não existem
- ✅ `stock.picking.action_cancel` — existe, cancela picking + cascade
- ✅ `stock.picking.do_unreserve` — existe
- ❌ `stock.picking.action_unreserve` — não existe (não confundir com action_assign)
- ✅ `stock.move.line.unlink` — funciona
- ✅ `stock.move.write({'product_uom_qty': X})` — funciona (campo NÃO é readonly)
- ✅ `stock.quant.write({'reserved_quantity': 0})` — funciona (campo NÃO é readonly em Odoo 17)
- ❌ `reserved_uom_qty` — não existe em Odoo 16/17 (G024)

---

## C2-C5 — Átomos implementados

| Átomo | Granularidade | Primitiva Odoo |
|---|---|---|
| `cancelar_moves_orfaos(picking_id, ml_ids, moves_writes)` | cirurgia | unlink MLs + write product_uom_qty |
| `cancelar_picking_inteiro(picking_id)` | picking inteiro | stock.picking.action_cancel |
| `zerar_reserved_residual(quant_ids)` | cleanup | stock.quant.write({'reserved_quantity': 0}) |

---

## C6 — Evidência de write real em produção (2026-05-23)

### Caso de validação

Os 15 FALHA_RESERVADO da skill 1 (sessão anterior — `log_2.1_ajuste_planilha_RESETAR_RESERVA_*.json`) deixaram 15 MLs órfãs em 6 pickings:

| Picking | MLs total antes | Órfãs | Estratégia escolhida |
|---|---|---|---|
| FB/FB/EMB/11673 | 10 | 1 | Cirurgia (move com 2 MLs mistas — ajustar para soma das OK = 0.1986) |
| FB/INT/07950 | 1 | 1 | Cancelar picking inteiro (sem MLs válidas) |
| FB/INT/08022 | 6 | 2 | Cirurgia (2 moves 1:1) |
| FB/INT/08030 | 24 | 1 | Cirurgia (1 move 1:1) |
| FB/OUT/01046 | 29 | 6 | Cirurgia (6 moves 1:1 + 1 move já sem ML em state=waiting → zerado também) |
| FB/OUT/01053 | 5 | 4 | Cancelar picking inteiro (decisão do usuário — só 1 ML válida restaria) |

### Execução (2026-05-23 22:02 UTC)

| # | Picking | Operação | Status | tempo |
|---|---|---|---|---|
| 1 | FB/FB/EMB/11673 | cirurgia | ✓ CIRURGIA_OK | 1334ms |
| 2 | FB/INT/07950 | cancelar | ✓ PICKING_CANCELADO (state→cancel) | 270ms |
| 3 | FB/INT/08022 | cirurgia | ✓ CIRURGIA_OK | 374ms |
| 4 | FB/INT/08030 | cirurgia | ✓ CIRURGIA_OK | 547ms |
| 5 | FB/OUT/01046 | cirurgia | ✓ CIRURGIA_OK | 782ms |
| 6 | FB/OUT/01053 | cancelar | ✓ PICKING_CANCELADO (state→cancel) | 249ms |

**Duração total: 3,6s.** Log: `log_2.4_operar_reservas_20260523_220239.json`.

### Estado pós-operação dos pickings

| Picking | State final | Moves | MLs (antes→depois) |
|---|---|---|---|
| FB/FB/EMB/11673 | assigned ✅ | 9 | 10 → 9 |
| FB/INT/07950 | cancel ✅ | 1 | 1 → 0 |
| FB/INT/08022 | assigned ✅ | 6 | 6 → 4 |
| FB/INT/08030 | assigned ✅ | 24 | 24 → 23 |
| FB/OUT/01046 | assigned ✅ | 30 | 29 → 23 |
| FB/OUT/01053 | cancel ✅ | 5 | 5 → 0 |

### Efeito colateral descoberto + correção

**Problema:** após unlink das MLs + write `product_uom_qty=0` nos moves, o Odoo recalculou `reserved_quantity` dos 15 quants antes zerados para valores NEGATIVOS:

```
quant=258975 reserved=-40.7319  (cod 104000037)
quant=258988 reserved= -1.4611  (cod 104000056)
...
quant=261592 reserved=-108.0000 (cod 4899024)
```

**Causa:** Odoo aplica `reserved_quantity_novo = reserved_quantity_atual − ml.quantity` ao fazer unlink de ML. Como o `reserved_quantity` já era 0 (pós-`--resetar-reserva`), ficou negativo.

**Correção:** implementação on-demand do átomo previsto `zerar_reserved_residual(quant_ids)` (segue padrão da FASE 3 do `remover_reservas_saida.py`): `stock.quant.write([ids], {'reserved_quantity': 0})`.

**Aplicação:** 15 quants em 62ms. Log: `log_2.4_zerar_reserved_residual_20260523_220404.json`.

**Estado final dos 15 quants:**
```
quant=258975 cod=104000037 qty=0.0000 reserved=0.0000 ✅
quant=258988 cod=104000056 qty=0.0000 reserved=0.0000 ✅
... (todos os 15)
quant=261592 cod=4899024 qty=0.0000 reserved=0.0000 ✅
```

---

## GOTCHA registrar (skill 1 + skill 2.4)

> **Quando aplicar `--resetar-reserva` na skill `ajustando-quant-odoo` E DEPOIS limpar as MLs órfãs via skill 2.4, é OBRIGATÓRIO chamar `zerar_reserved_residual` ao final.** O unlink da ML faz Odoo subtrair `ml.quantity` do `reserved_quantity` atual; como o quant já estava com `reserved=0`, fica negativo (estado fantasma).
>
> **Fluxo correto pós-`--resetar-reserva`:**
> 1. Cirurgia (`cancelar_moves_orfaos`) ou Cancelamento (`cancelar_picking_inteiro`) das MLs órfãs.
> 2. **OBRIGATÓRIO:** `zerar_reserved_residual(quant_ids)` para limpar o residual negativo.
> 3. Verificar `quant.reserved_quantity == 0` em todos.

---

## Status C7-C10 (concluídos em 2026-05-23 pós-sessão)

- **C7 ✅** — ROUTING_SKILLS.md (Skills Odoo 12 entries) + tool_skill_mapper.py (`Estoque Odoo (Write)/Odoo`) + subagente `gestor-estoque-odoo` (skills: lista). Galho `2.4` da árvore do subagente atualizado com link para folha.
- **C8 ✅** — folha [`fluxos/2.4-cancelar-reserva-orfa.md`](../../../app/odoo/estoque/fluxos/2.4-cancelar-reserva-orfa.md).
- **C9 ✅** — 3 scripts movidos via `git mv` para `_validados/operando-reservas-odoo/`: `remover_reservas_saida.py`, `cancelar_reservas_migracao.py`, `limpar_reservas_fantasma.py`. sys.path corrigido `parents[2]→parents[4]` em cada (museum vivo).
- **C10 ✅** — MAPA_SCRIPTS.md §"scripts/reserva.py" linkado para `_validados/`; ROADMAP_SKILLS.md SKILL 3 status 🟡 mín viável.

## Pós code-review (2026-05-23)

Code-reviewer descobriu duas falhas que foram corrigidas:
- **CR1#4** — SKILL.md descrevia `--move-ids` no contrato, mas a CLI aceita `--moves-writes` (dict `move_id:novo_qty`). Contrato alinhado com CLI: `input: --picking-id <id> --ml-ids <ml1,...> --moves-writes "m1:qty1,m2:qty2,..." [--confirmar]`.
- **CR1#5** — Átomo `zerar_reserved_residual` existia no service mas não tinha CLI. **Corrigido:** CLI agora aceita 3 modos exclusivos: cirurgia · cancelar-picking · zerar-residual. Permite chamada `python operar_reserva.py --zerar-residual --quant-ids ... --confirmar` como passo 3 obrigatório do fluxo 2.4.

## Implementar átomos previstos restantes quando aparecer caso real

- `unreserve_picking` (preserva picking, libera reservas — alternativa não-destrutiva à cirurgia)
- `unreserve_mo(reassign=False)` (libera reservas de componentes de MO; reassign opcional)
- `find_orphan_mls(quant_ids)` (helper read — pertence à skill 9 `consultando-quant-odoo`?)
