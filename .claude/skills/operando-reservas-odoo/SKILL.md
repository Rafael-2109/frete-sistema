---
name: operando-reservas-odoo
description: >-
  Skill WRITE (átomos C1/C2) para OPERAR RESERVAS no Odoo, 5 átomos: cirurgia
  (cancelar moves órfãos preservando picking), cancelamento de picking,
  unreserve, find_orphan_mls (READ) e zerar_reserved_residual. Usar quando o
  pedido é "limpa reserva órfã do picking X", "remove move.lines apontando
  para quant zerado", "picking quebrado pós-ajuste de inventário", "libera
  reservas mantendo picking". `--dry-run` é o DEFAULT (modos write); só
  efetiva com `--confirmar`. NAO usar para ajustar saldo de quant ->
  ajustando-quant-odoo. Matriz USAR/NAO-USAR completa no corpo.
allowed-tools: Read, Bash, Glob, Grep
---

# operando-reservas-odoo (WRITE — 5 átomos C1/C2)

Skill **mínimo viável** (C1 mineração ✅ · C2-C5 implementado para 5 átomos · C6-C10 conforme uso). Construída em 2026-05-23 a partir do caso real "6 pickings com 15 MLs órfãs pós-`--resetar-reserva` da skill 1". **Estendida em 2026-05-24 v7** com 2 átomos novos (`unreserve_picking` + `find_orphan_mls`) para fechar gap arquitetural "tratar reserva ATIVA pré-transferência" (caso 71 cods + fluxo 2.6).

Constituição: `app/odoo/estoque/CLAUDE.md`. Service: `app/odoo/estoque/scripts/reserva.py`.

## Quando usar / Quando NÃO usar

**5 átomos**: cirurgia (cancelar moves órfãos preservando picking) · cancelamento
(picking inteiro via `action_cancel`) · unreserve (`do_unreserve` mantendo picking —
NOVO v7) · find_orphan_mls (READ-only listar MLs zerados — NOVO v7) ·
zerar_reserved_residual (cleanup pós-unlink). Compõe **fluxo 2.6 — tratar reserva
ATIVA pré-Skill 2**.

**USAR QUANDO** o pedido é: "limpa reserva órfã do picking X", "cancela picking Y",
"remove move.lines apontando para quant zerado", "MLs órfãs no picking Z", "picking
quebrado pós-ajuste de inventário", "libera reservas mantendo picking" (NOVO v7),
"MLs órfãs por quants alvo" (NOVO v7).

**NÃO USAR PARA:**
- ajustar saldo de quant (não toca reservas) -> `ajustando-quant-odoo`
- cancelar MO de produção (mrp.production) -> `operando-mo-odoo`
- mover saldo entre lotes/locais -> `transferindo-interno-odoo`
- só consultar reservas/MLs (não altera) -> `consultando-sql` ou `consultando-quant-odoo`
- reservar (action_assign) -> Skill 5 `operando-picking-odoo`

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

## Contrato — Zerar reserved residual (átomo 3)

```
objeto:        stock.quant — zera reserved_quantity stale (positivo ou negativo)
input:         --zerar-residual --quant-ids <Q1,Q2,...> [--confirmar]
output (JSON): {status, quant_ids, valores_antes:{id:{qty,reserved}},
                 valores_depois:{id:{qty,reserved}}, quants_processados, tempo_ms}
pré-condições: quant_ids não-vazio; NÃO deve haver MLs ATIVAS (state=assigned/partial)
               apontando para os quants (Skill 9 find_orphan ou modo move-lines
               para verificar antes).
pós-condições: stock.quant.reserved_quantity = 0 para todos quant_ids.
gotchas-invariante: G027 — `reserved_quantity` interno SEMPRE vem de saída; zerar
                    residual stale e SEGURO apos unreserve/unlink. NUNCA usar
                    para zerar reserva legítima (MLs ativas) — usar
                    unreserve_picking ou cancelar_picking_inteiro primeiro.
modos:         --dry-run (default) -> --confirmar
status:        ZERAR_RESIDUAL_OK (CR1-M2 v7-fix; era CIRURGIA_OK) · DRY_RUN_OK ·
               FALHA_ODOO
```

## Contrato — Unreserve picking (átomo 4, NOVO v7)

```
objeto:        stock.picking — libera MLs SEM cancelar (do_unreserve nativo)
input:         --unreserve-picking --picking-id <id> [--confirmar]
output (JSON): {status, picking_id, picking_name, picking_state_antes,
                 picking_state_depois, n_mls_antes, n_mls_depois,
                 tempo_ms, [aviso se G_UNRESERVE_TRAVA]}
pré-condições: picking existe; state IN ['assigned', 'partially_available',
                 'confirmed', 'waiting']. State 'done'/'cancel' = FALHA.
                 Se n_mls_antes=0 = NOOP.
pós-condições: MLs do picking APAGADAS (qty_done virou 0); reserved_quantity
               dos quants relacionados RECALCULADO pelo Odoo; picking volta
               para confirmed/waiting/partially_available (ou TRAVA em assigned
               se Odoo re-reservar automaticamente — aviso emitido).
gotchas-invariante: G_UNRESERVE_TRAVA — picking pode CONTINUAR em assigned
                    se Odoo re-reservar automaticamente (depende de trigger).
                    Output emite "aviso" no campo correspondente.
modos:         --dry-run (default) -> --confirmar
status:        PICKING_UNRESERVED · DRY_RUN_OK · NOOP · FALHA_PICKING_NAO_EXISTE
               · FALHA_PICKING_STATE_INVALIDO · FALHA_ODOO
```

## Contrato — Find orphan MLs (átomo 5, NOVO v7, READ-only)

```
objeto:        stock.move.line — classifica MLs ÓRFÃS (quants com qty=0)
input:         --find-orphan --quant-ids <Q1,Q2,...> [--states <csv>]
                 (default states=assigned,partially_available)
output (JSON): {status='ORPHAN_MLS_LISTED', total_orfaos, mls_orfas: [...],
                 quants_zerados_com_mls: [...], quants_com_saldo: [...],
                 tempo_ms}
pré-condições: quant_ids não-vazio (vazio = retorna zerado sem RPC).
pós-condições: READ-only — sem mutação Odoo.
gotchas-invariante: G030 (cross-ref ML→quant via tupla — não usa quant_id direto
                    que é computed store:False). Internamente reaproveita Skill 9
                    `listar_move_lines_por_quant`. TOL=0.0001 para arredondamento.
modos:         sempre exec (READ-only, sem --dry-run)
status:        ORPHAN_MLS_LISTED · sem falhas (defensive)
```

## Tabela de decisão — 5 caminhos seguros para desreservar (fluxo 2.6)

Quando antes de uma Skill 2 (transferência) há reservas ativas bloqueando o quant origem, escolha 1 dos 5 caminhos:

| Caminho | Comando | Quando usar | Risco | Reversível? |
|---|---|---|---|---|
| **A. Cancelar picking inteiro** | Skill 5 `--modo cancelar` OU Skill 2.4 `--cancelar-picking` | Picking SEM MLs válidas além das bloqueantes (fantasma; INT sem origem/partner) | IRREVERSÍVEL. Consultar Fiscal se NF emitida. **NÃO USAR se picking tem MLs válidas de outros cods** (caso FB/OUT/01046 v8). | ❌ |
| **B. Devolver picking** | Skill 5 `--modo devolver` | Picking state=done que precisa estornar saldo | Cria NF devolução. Estorno fiscal pode ser necessário. | Parcial |
| **C. Desreservar mantendo picking** | Skill 2.4 `--unreserve-picking` (NOVO v7) | Operador quer liberar mas manter picking para re-reservar | **RISCO G_UNRESERVE_TRAVA**: picking pode TRAVAR. **NÃO USAR em picking MIX** — libera TODAS as MLs (incluindo válidas). | ✅ (re-reserva via Odoo) |
| **D. Não desreservar, usar OUTRO lote** | Skill 2 `--lote-origem <ALT>` OU `--para-indisponivel --lote <ALT>` | Existe lote livre com saldo suficiente | Mais seguro — não toca reserva. **Validado v8: 11 cods resolvidos via D.** | ✅ |
| **E. Cirurgia ML bloqueante (preserva picking)** | Skill 2.4 cirurgia + `--zerar-residual` + Skill 2 MODO C | Picking tem MIX MLs válidas + bloqueantes; quer preservar MLs válidas. **PREFERIDO sobre A neste caso** (validado v8 FB/OUT/01046 23 MLs). | Cirurgia segura. Deixa 3 moves residuais com qty=0 (cosmético; operador valida no Odoo UI). | Parcial (picking preservado, MLs bloqueantes removidas) |

**Regra de seleção (refinada v8 — prefira nesta ordem)**:
- **D primeiro** (sem risco fiscal, sem tocar picking).
- **E quando picking tem MIX** MLs válidas + bloqueantes — preserva o que importa.
- **A só se picking é 100% bloqueante/fantasma** (caso v7 FB/INT/08022).
- **B se state=done** com estorno necessário.
- **C como último recurso** (libera tudo + risco TRAVA).

**Premissa absoluta (NUNCA pular)**: antes de chamar Skill 2 transferência, rodar Skill 9 `--modo pickings` para identificar reservas. Se `reserved > 0` → fluxo 2.6. Documentado em `app/odoo/estoque/fluxos/2.6-tratar-reserva-bloqueia-transferencia.md`.

## Receitas (caso real -> args)

| Preciso de... | Atomo | Args |
|---------------|-------|------|
| Limpar 1 ML órfã preservando picking | cirurgia | `--picking-id P --ml-ids ML --moves-writes "M:qty" --confirmar` |
| Limpar 6 MLs órfãs em 1 picking | cirurgia | `--picking-id P --ml-ids ML1,ML2,... --moves-writes "M1:q1,M2:q2,..." --confirmar` |
| Cancelar picking sem MLs válidas | cancelamento | `--cancelar-picking --picking-id P --confirmar` |
| Cancelar picking com poucas MLs válidas | cancelamento | idem (operação/Fiscal decide) |
| Desreservar picking mantendo-o ativo (caminho C fluxo 2.6) | unreserve | `--unreserve-picking --picking-id P [--confirmar]` |
| Listar MLs órfãs por quants zerados (diagnóstico caminho E) | find_orphan | `--find-orphan --quant-ids Q1,Q2 [--states csv]` |
| Zerar reserved residual pós-cirurgia/unlink | zerar-residual | `--zerar-residual --quant-ids Q1,Q2 --confirmar` |

## Catálogo de átomos

| Átomo | Status | Notas |
|---|---|---|
| `cancelar_moves_orfaos(picking_id, ml_ids, moves_writes)` | ✅ | Cirurgia preservando picking |
| `cancelar_picking_inteiro(picking_id)` | ✅ | action_cancel cascade |
| `unreserve_picking(picking_id)` | ✅ **NOVO v7** | do_unreserve nativo + guard G_UNRESERVE_TRAVA |
| `find_orphan_mls(quant_ids)` | ✅ **NOVO v7** | READ-only — reaproveita Skill 9 cross-ref por tupla (G030) |
| `zerar_reserved_residual(quant_ids)` | ✅ | Cleanup stale APÓS unreserve/unlink (G027) |
| `unreserve_mo(mo_id, reassign=False)` | ⬜ previsto | quando precisar liberar reservas de componentes de MO |

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
- **G_UNRESERVE_TRAVA** (NOVO v7): após `unreserve_picking`, picking pode CONTINUAR em `state=assigned` se Odoo re-reservar automaticamente. Verificar `n_mls_depois==0` no output; se "aviso" emitido, reconsiderar caminho A (cancelar).
- **G030** (NOVO v7): `stock.move.line.quant_id` é `store: False` (computed UI-only "Pick From"). Filtros `quant_id in [...]` são IGNORADOS pelo Odoo. Skill 9 + Skill 2.4 `find_orphan_mls` fazem cross-ref via tupla (product, lot, location, company) automaticamente.
- **Caminho C é último recurso**: se quiser desreservar sem perder picking, prefira caminho D (outro lote) primeiro. Caminho C tem risco real de TRAVA confirmado pelo usuário 2026-05-24.
- **Cirurgia deixa moves residuais com qty=0** (NOVO v8 — lição FB/OUT/01046): após cirurgia (`unlink ML + product_uom_qty=0`), os 3 moves ficam vivos em state=assigned ate operador validar via Odoo UI (`button_validate` cancela automaticamente moves com qty=0). Cosmético — NÃO bloqueia operação. Se quiser limpar 100% manualmente, cancelar moves no Odoo UI (não tem CLI — `stock.move._action_cancel` é privado G025).
- **Caminho E é PREFERIDO sobre A quando picking tem MIX MLs válidas + bloqueantes** (NOVO v8): cirurgia preserva picking + suas MLs válidas (caso FB/OUT/01046: 23 MLs onde 3 eram bloqueantes e 20 eram devoluções legítimas — cancelar inteiro teria perdido as 20). Caminho A só se picking é 100% bloqueante.
- **Pattern "cirurgia → zerar_residual → MODO C"** (NOVO v8): combinação atômica de 3 chamadas que resolve o destravamento completo. Codificado no fluxo 2.6 caminho E.

## Exemplos

```bash
SK=.claude/skills/operando-reservas-odoo/scripts/operar_reserva.py

# 1) Cirurgia dry-run em FB/FB/EMB/11673 (1 ML órfã)
python "$SK" --picking-id 316701 --moves-writes "1075205:0.1986" --ml-ids 217654353

# 2) Efetivar cirurgia
python "$SK" --picking-id 316701 --moves-writes "1075205:0.1986" --ml-ids 217654353 --confirmar

# 3) Cancelar picking inteiro (FB/INT/07950 — só tinha 1 ML, virou órfã)
python "$SK" --cancelar-picking --picking-id 320076 --confirmar

# 4) NOVO v7: unreserve_picking — libera reservas SEM cancelar (caminho C fluxo 2.6)
python "$SK" --unreserve-picking --picking-id 320753              # dry-run
python "$SK" --unreserve-picking --picking-id 320753 --confirmar  # efetivar
# Output esperado: n_mls_depois=0, picking_state_depois=confirmed/waiting
# Se output emite "aviso" com G_UNRESERVE_TRAVA + state=assigned, reconsiderar caminho A.

# 5) NOVO v7: find_orphan_mls — READ-only, lista MLs apontando para quants zerados
python "$SK" --find-orphan --quant-ids 229937,258975
# Output: {total_orfaos, mls_orfas[...], quants_zerados_com_mls[...], quants_com_saldo[...]}
# Se total_orfaos > 0, usar caminho E (cirurgia) para limpar.

# 6) Zerar reserved residual (OBRIGATÓRIO após cirurgia E + ML afetando quant já com reserved=0)
python "$SK" --zerar-residual --quant-ids 258975,258988,258958 --confirmar
```

## Validação

A skill foi construída em 2026-05-23 a partir do caso real "6 pickings × 15 MLs órfãs pós-`--resetar-reserva` da skill 1". Mineração C1 baseada em 4 scripts-fonte (`remover_reservas_saida`, `cancelar_reservas_migracao`, `limpar_reservas_fantasma`, `auditoria/teste_unlink_moveline_fantasma`). Probes em produção identificaram que `stock.move._action_cancel` é private XML-RPC (workaround documentado). Ver `_validados/operando-reservas-odoo/VALIDACAO.md` para evidência do write real.
