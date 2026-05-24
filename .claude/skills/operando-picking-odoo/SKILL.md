---
name: operando-picking-odoo
description: >-
  Skill WRITE (átomo C2) para OPERAR PICKINGS no Odoo: cancelar (single ou batch
  fantasmas >7d), validar (button_validate com invariante G019/G020) ou devolver
  (criar stock.return.picking + validar, idempotente). Usar quando o pedido é
  "cancela picking X", "cancela pickings fantasma da planilha", "re-valida
  picking Y (state assigned ficou pendurado)", "devolve o picking Z (NF errada)",
  "estoque voltou pra Em Trânsito Industrialização — devolve".
  `--dry-run` é o DEFAULT; só efetiva com `--confirmar`.
  NÃO USAR PARA:
  - cirurgia/MLs órfãs/zerar reserved residual -> operando-reservas-odoo
  - ajustar saldo de quant (não toca picking) -> ajustando-quant-odoo
  - mover saldo entre lotes/locais -> transferindo-interno-odoo
  - criar picking inter-company para faturar -> faturando-odoo (futura —
    invariante G019/G020 já codificada neste service, ONDA 0.4 ✅ fechada
    2026-05-24 v3, destrava implementação da Skill 8)
  - cancelar MO de produção -> operando-mo-odoo (futura)
  - só consultar pickings (não altera) -> consultando-sql
allowed-tools: Read, Bash, Glob, Grep
---

# operando-picking-odoo (WRITE — átomo C2)

Skill **mínimo viável** (C1 mineração ✅ · C2-C5 implementados para 3 átomos · C6-C10 conforme uso). Construída em 2026-05-24 a partir de demandas reais:
- **cancelar fantasma**: 854 pickings >7d cancelados em 2026-05-18 (script `16_cancelar_pickings_fantasmas`).
- **validar**: invariante G019/G020 já no service desde 2026-05-18 (resolve false-positive `button_validate` retornar OK com `state=assigned`).
- **devolver**: padrão fat_lf_cleanup.reverter_picking executado em 2026-05-20 (estorno de NFs com erro).

Constituição: `app/odoo/estoque/CLAUDE.md`. Service: `app/odoo/estoque/scripts/picking.py` (StockPickingService — extende padrão pré-existente em `services/`).

---

## REGRAS CRÍTICAS

1. **`--dry-run` é o DEFAULT.** Sem `--confirmar`, só calcula e mostra o plano (exit 4).
2. **Verificar no Odoo** após efetivar — operação viva (G019/G020 protegem contra false-positive mas `quant` pós-validate só o usuário confirma).
3. **`cancelar` é IRREVERSÍVEL** no Odoo (precisa recriar manualmente se errar) — Skill 2.4 `operando-reservas-odoo` é alternativa cirúrgica quando só algumas MLs estão erradas.
4. **`devolver` é IDEMPOTENTE**: se `origin ilike "Devolução de NAME"` já existe, retorna esse id sem criar duplicado.
5. **`validar` com `linhas_esperadas=`** consolida MLs ANTES de `button_validate` (G023 — descarta reservas em lotes não esperados).

## Contrato — `cancelar` (átomo 1)

```
objeto:        stock.picking (cascateia para moves e MLs via action_cancel)
input:         --modo cancelar --picking-id <id> [--motivo "..."]
                 OU --modo cancelar --json <path> [--limite N] [--idade-min DIAS]
output (JSON): {status, picking_id, picking_state_antes, picking_state_depois,
                 motivo, tempo_ms}
                 (batch: {total, contagem_status, resultados:[...]})
pré-condições: picking existe; state NOT IN ['done', 'cancel']
                (se state='cancel': NOOP; se state='done': falha)
pós-condições: picking.state='cancel'; moves filhas state='cancel';
               MLs filhas removidas; quant.reserved_quantity recalculado
gotchas-invariante: action_cancel é nativo do Odoo (cascade automático);
                    se houve --resetar-reserva ANTES, chamar Skill 2.4
                    `zerar_reserved_residual` APÓS (reserved < 0 fantasma)
modos:         --dry-run (default, exit 4) -> --confirmar (exit 0)
status:        CANCELADO · DRY_RUN_OK · NOOP · FALHA_PICKING_NAO_EXISTE ·
               FALHA_STATE_DONE · FALHA_ODOO
```

## Contrato — `validar` (átomo 2)

```
objeto:        stock.picking.button_validate + G019/G020 invariante
input:         --modo validar --picking-id <id> [--linhas-esperadas JSON]
                 (--linhas-esperadas: lista [{product_id, quantity, lot_id?,
                  lot_name?}] — G023 consolida ANTES de button_validate)
output (JSON): {status, picking_id, state_antes, state_depois,
                 g023_ajustes, marshal_none, tempo_ms}
pré-condições: picking existe; state NOT IN ['done', 'cancel']
pós-condições: picking.state='done' (G019 garante via re-leitura).
                Se NÃO ficou 'done' → RuntimeError (false-positive G019).
gotchas-invariante: G019 (validar engole 'cannot marshal None' como sucesso) →
                    SEMPRE re-le state; G020 (liberar_faturamento sem pré-cond)
                    → este átomo NÃO chama liberar_faturamento (deixar p/ Skill 8);
                    G023 (consolidar_move_lines com linhas_esperadas)
modos:         --dry-run (default, exit 4) -> --confirmar (exit 0)
status:        VALIDADO · DRY_RUN_OK · FALSE_POSITIVE_G019 · FALHA_PICKING_NAO_EXISTE ·
               FALHA_STATE_INVALIDO · FALHA_ODOO
```

## Contrato — `devolver` (átomo 3)

```
objeto:        stock.return.picking (wizard) -> stock.picking novo
input:         --modo devolver --picking-id <id>
output (JSON): {status, picking_id_origem, picking_id_devolucao, state_devolucao,
                 reutilizado_idempotente, mls_qty_done_setadas, tempo_ms}
pré-condições: picking existe; state='done' (não dá pra devolver picking não-feito)
pós-condições: novo stock.picking criado com origin="Devolução de NAME";
                state='done'; saldo restaurado ao lote/loc original;
                idempotente (se já existe devolução por origin ilike, retorna esse id)
gotchas-invariante: stock.return.picking wizard exige write({}) com context
                    contendo active_id/model/ids p/ default_get popular
                    product_return_moves; G019 pattern aplicado no validate
                    do novo picking
modos:         --dry-run (default, exit 4) -> --confirmar (exit 0)
status:        DEVOLUCAO_CRIADA · DEVOLUCAO_REUTILIZADA (idempotente) ·
               DRY_RUN_OK · FALHA_PICKING_NAO_EXISTE · FALHA_STATE_NAO_DONE ·
               FALHA_CREATE_RETURNS · FALHA_ODOO
```

## Receitas (caso real -> args)

| Preciso de... | Modo | Args |
|---------------|------|------|
| Cancelar 1 picking fantasma | cancelar | `--modo cancelar --picking-id 316701 --confirmar` |
| Cancelar 854 pickings >7d da planilha | cancelar batch | `--modo cancelar --json /tmp/pickings.json --idade-min 7 --confirmar` |
| Re-validar picking em state=assigned | validar | `--modo validar --picking-id 316701 --confirmar` |
| Validar com lotes específicos (G023) | validar | `--modo validar --picking-id 316701 --linhas-esperadas '[{"product_id":1001,"quantity":5,"lot_name":"LOT_A"}]' --confirmar` |
| Devolver picking (NF errada) | devolver | `--modo devolver --picking-id 320063 --confirmar` |
| Verificar se devolução já existe | devolver dry-run | `--modo devolver --picking-id 320063` (idempotente — não cria duplicado) |

## Catálogo de átomos

| Átomo | Status | Demanda real |
|---|---|---|
| `cancelar(picking_id, motivo)` | ✅ implementado (StockPickingService.cancelar) | 854 cases 2026-05-18 (16_cancelar_pickings_fantasmas) |
| `validar(picking_id, linhas_esperadas)` | ✅ implementado (G019/G020/G023 invariantes) | Pipeline (9_bulk, fat_lf_05) + retomadas isoladas |
| `devolver(picking_id)` | ✅ implementado (StockPickingService.devolver — NOVO 2026-05-24) | fat_lf_cleanup.reverter_picking PROD 2026-05-20 |
| `criar_transferencia(...)` | ✅ implementado | Pipeline-only — sem CLI ad-hoc (usar via Python diretamente) |
| `consolidar_move_lines(picking_id, linhas_esperadas)` | ✅ implementado (G023) | Chamado INTERNAMENTE por `validar()` quando recebe `linhas_esperadas` |
| `alterar_lote_no_picking(...)` | ⬜ previsto | Caso `substituir_lote_205030410_fb` é FLUXO CROSS-SKILL (Skill 2.4 + 2 + reassign), não átomo. Implementar como folha de fluxo se houver 2+ casos. |
| `criar_picking_interno(...)` | ⬜ previsto | Sem demanda ad-hoc isolada — quem cria picking interno é pipeline (Skill 8). Implementar se aparecer caso fora-pipeline. |

## Composição em FLUXOS

- **Fluxo 2.5.a — cancelar picking fantasma batch** (16_cancelar_pickings_fantasmas):
  1. Identificar pickings >7d + origin antiga (script 15 FALHA_SEM_SALDO + investigação manual).
  2. Carregar JSON com `[{id, name, state, origin, create_date}, ...]`.
  3. `operar_picking.py --modo cancelar --json X --idade-min 7 --confirmar`.
  4. **Se** algum picking tinha sido pré-`--resetar-reserva` da Skill 1 → chamar Skill 2.4 `zerar_reserved_residual` nos `quant_ids` afetados (regra inviolável 9).

- **Fluxo 2.5.b — re-validar picking false-positive G019**:
  1. Identificar picking em `state=assigned` após ETAPA B (`f5b_validar_pickings` marcou F5b_VALIDADO mas Odoo manteve assigned).
  2. Diagnosticar causa (estoque negativo, wizard pendente, etc) via Odoo UI.
  3. Resolver causa (transferir saldo via Skill 2, criar saldo via Skill 1).
  4. `operar_picking.py --modo validar --picking-id X --confirmar`.
  5. Se ainda raise `state=assigned`, repete diagnóstico.

- **Fluxo 2.5.c — devolver picking (NF errada)** (fat_lf_cleanup pattern):
  1. NF foi emitida mas pré-SEFAZ (account.move.state=draft/posted sem cstat).
  2. `operar_picking.py --modo devolver --picking-id X --confirmar` → cria devolução do picking.
  3. Cancelar invoice via Odoo UI ou Skill financeiro (fora do escopo).
  4. Resetar fase_pipeline do ajuste local p/ reprocessamento.

## Armadilhas

- **`action_cancel` em picking `state=done` falha**. Usar `devolver` em vez de cancelar.
- **`button_validate` pode retornar `cannot marshal None`** (XML-RPC tenta serializar wizard de backorder). G019 trata: se marshal None + `state=done`, é sucesso; se marshal None + `state=assigned`, raise.
- **`skip_backorder=True` no context** evita criar backorder mas NÃO desativa wizards de estoque negativo — pode deixar picking em `assigned` (raise G019).
- **`stock.return.picking.write({}, context)`** é OBRIGATÓRIO antes de `create_returns` — o write vazio com context dispara `default_get` que popula `product_return_moves` (sem isso, devolução fica com 0 linhas).
- **`create_returns` retorna `dict` em alguns Odoo, `int` em outros** — código testa ambos e raise se nenhum.
- **G023 `linhas_esperadas`**: passar `quantity=0` ou negativa = ignorada (não vira chave); útil para "zerar tudo de um produto" passando lote inválido + qty=0 → loga warning mas não bloqueia.
- **`origin ilike "Devolução de NAME"`** depende de naming convention do Odoo CIEL IT — se mudar, idempotência quebra (devolução duplicada).
- **G011 `preencher_qty_done` é PRÉ-REQUISITO** de `validar()` em pickings criados via `criar_transferencia` — sem isso, qty_done=0 → button_validate falha com "Nao e possivel validar transferencia sem quantidades reservadas". A CLI da Skill 5 **NÃO** preenche qty_done (chamador faz isso antes — pipeline Skill 8).

## Exemplos

```bash
SK=.claude/skills/operando-picking-odoo/scripts/operar_picking.py

# 1) Dry-run: cancelar 1 picking fantasma
python "$SK" --modo cancelar --picking-id 316701

# 2) Efetivar cancelamento
python "$SK" --modo cancelar --picking-id 316701 --motivo "fantasma >7d" --confirmar

# 3) Cancelar batch (854 pickings) com filtro idade
python "$SK" --modo cancelar --json /tmp/pickings_reservadores_15.json --idade-min 7 --confirmar

# 4) Re-validar picking pendurado em assigned (G019)
python "$SK" --modo validar --picking-id 317342 --confirmar

# 5) Validar com lotes específicos (G023)
python "$SK" --modo validar --picking-id 317306 \
  --linhas-esperadas '[{"product_id":205460830,"quantity":35,"lot_name":"MI 027-098/26"}]' \
  --confirmar

# 6) Devolver picking (NF errada — fat_lf_cleanup pattern)
python "$SK" --modo devolver --picking-id 320063 --confirmar

# 7) Verificar se devolução já existe (idempotente)
python "$SK" --modo devolver --picking-id 320063
# → DEVOLUCAO_REUTILIZADA se já criada antes; DRY_RUN_OK se não.
```

## Validação

Skill **construída em 2026-05-24**:
- C1: 4 scripts-fonte minerados integral (`16_cancelar_pickings_fantasmas`, `fat_lf_cleanup`, `substituir_lote_205030410_fb`, `fat_lf_05_executar_clean` etapas-chave) + 4 docs de gotchas (G011/G019/G020/G023).
- C2: service `app/odoo/estoque/scripts/picking.py` (capinado de `app/odoo/services/`) com shim em `services/` re-exportando. Método novo `devolver()` adicionado. **42 testes pytest verdes** (19 originais + 16 novos cobrindo G023/ajustar_qty_done/validar-com-linhas/G011/G019/G020 + 7 cobrindo `devolver`).
- C3: contrato de 3 átomos definido (cancelar, validar, devolver).
- C4: SKILL.md com receitas, fluxos 2.5.a/b/c, armadilhas, exemplos.
- C5: `scripts/operar_picking.py` (CLI 3 modos, --dry-run default, exit codes 0/1/2/4).
- C6: validação dry-run vs Odoo PROD em 1-2 casos pendente.
- C7-C10: cross-refs + arquivamento `_validados/operando-picking-odoo/` + atualizar docs G019/G020 + ROADMAP.

Mapeamento script-fonte → átomo no `docs/inventario-2026-05/consolidacao/MAPA_SCRIPTS.md`. Resultado da validação em `_validados/operando-picking-odoo/VALIDACAO.md`.
