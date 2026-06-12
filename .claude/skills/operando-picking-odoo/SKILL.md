---
name: operando-picking-odoo
description: >-
  Skill WRITE (átomo C2) para OPERAR PICKINGS no Odoo: cancelar (single ou
  batch fantasmas >7d), validar (button_validate com invariante G019/G020),
  devolver (stock.return.picking idempotente) e átomos inter-company v15a
  invocados em Python pela Skill 8. Usar quando o pedido é "cancela picking
  X", "cancela pickings fantasma da planilha", "re-valida picking Y",
  "devolve o picking Z (NF errada)". `--dry-run` é o DEFAULT no CLI; só
  efetiva com `--confirmar`. NAO usar para cirurgia/MLs órfãs ->
  operando-reservas-odoo. Matriz USAR/NAO-USAR completa no corpo.
allowed-tools: Read, Bash, Glob, Grep
---

# operando-picking-odoo (WRITE — átomo C2)

> **🆕 v19+ (2026-05-26)**: novo átomo `preencher_lotes_picking(picking_id, lotes_data, lote_default='MIGRAÇÃO', dry_run)` para pickings nativos via DFe→PO confirmada (compõe FLUXO L3 1.2.1/1.2.2 via Skill 7 ABRANGENTE). Atribui lote + qty em `stock.move.line`. 7 pytest mockados verdes em `tests/odoo/services/test_stock_picking_preencher_lotes.py`. Pattern minerado de `RecebimentoLfOdooService._preencher_lotes_picking` (L3982-4100+).

> **🛑 v19+ DEPRECATED**: `criar_picking_entrada_destino_manual` (Skill 5 v15a) marcada DEPRECATED — tampão arquitetural AP2 (§6.5 CLAUDE.md estoque). Caminho correto: criar DFe via Skill 7 `criar_dfe_a_partir_do_invoice_saida` → motor Odoo gera picking automaticamente. Função permanece como **museum vivo** com pytest preservados até v20+ canary remover.

Skill **mínimo viável** (C1 mineração ✅ · C2-C5 implementados para 3 átomos · C6-C10 conforme uso). Construída em 2026-05-24 a partir de demandas reais:
- **cancelar fantasma**: 854 pickings >7d cancelados em 2026-05-18 (script `16_cancelar_pickings_fantasmas`).
- **validar**: invariante G019/G020 já no service desde 2026-05-18 (resolve false-positive `button_validate` retornar OK com `state=assigned`).
- **devolver**: padrão fat_lf_cleanup.reverter_picking executado em 2026-05-20 (estorno de NFs com erro).
- **preencher_lotes_picking (v19+)**: pattern para pickings NATIVOS (gerados pelo Odoo via PO confirmada na escrituração de entrada). Atribui lote default (`MIGRAÇÃO` p/ inventário) ou mapping por produto.

Constituição: `app/odoo/estoque/CLAUDE.md`. Service: `app/odoo/estoque/scripts/picking.py` (StockPickingService — extende padrão pré-existente em `services/`).

## Quando usar / Quando NÃO usar

**Átomos inter-company v15a** (invocados pela Skill 8 `faturando-odoo`):
`criar_picking_inter_company` com D-OPS-3 tracking='none' fix ·
`validar_picking_inter_company` fluxo F5b completo com G018 peso/volumes ·
`criar_picking_entrada_destino_manual` ETAPA F com G023 company_id forçado e
idempotência via origin. Esses átomos NÃO TÊM CLI ad-hoc — são invocados em
Python pelo orchestrator Skill 8 (v15b+). Modo CLI permanece para
cancelar/validar/devolver.

**USAR QUANDO** o pedido é: "cancela picking X", "cancela pickings fantasma da
planilha", "re-valida picking Y (state assigned ficou pendurado)", "devolve o
picking Z (NF errada)", "estoque voltou pra Em Trânsito Industrialização — devolve".

**NÃO USAR PARA:**
- cirurgia/MLs órfãs/zerar reserved residual -> `operando-reservas-odoo`
- ajustar saldo de quant (não toca picking) -> `ajustando-quant-odoo`
- mover saldo entre lotes/locais -> `transferindo-interno-odoo`
- faturar inventario inter-company end-to-end (orquestrar A-F) -> `faturando-odoo`
  (Skill 8 v15+ — INVOCA os átomos v15a desta skill)
- cancelar/concluir MO de produção -> `operando-mo-odoo`
- só consultar pickings (não altera) -> `consultando-sql`

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

## Contratos — Átomos inter-company v15a (Python-only, sem CLI ad-hoc)

> Estes 3 átomos são **invocados em Python** pelo orchestrator Skill 8 `faturando-odoo` (v15b+). NÃO têm modo CLI dedicado (modo CLI permanece para `cancelar`/`validar`/`devolver`). O caller (Skill 8) controla dry-run via lógica externa (decisão de chamar ou não chamar o átomo).

### `criar_picking_inter_company` (ETAPA B F5a — codifica D-OPS-3)

```
objeto:        stock.picking de SAIDA inter-company (FB→LF, LF→FB, FB→CD, ...)
input:         company_origem_id, company_destino_id, location_origem_id,
               location_destino_id, linhas, picking_type_id, partner_id
               (OBRIGATORIO), origin (opcional), tracking_por_pid (opcional —
               pre-fetched p/ otim bulk)
output (dict): {picking_id, tracking_none_pids, linhas_planejadas, tempo_ms}
pré-condições: linhas nao-vazia (qty>0); company_origem != company_destino;
               partner_id != 0/None (fiscal_position resolver)
pós-condições: stock.picking criado com state='draft', incoterm + carrier
               default NACOM; lot_name/lot_id REMOVIDOS para produtos
               tracking='none' (D-OPS-3 fix)
gotchas-invariante: G004 (incoterm+carrier obrigatorios) · G021 (filter qty<=0) ·
               **D-OPS-3 (produto tracking='none' tem lot_name removido —
               Odoo CIEL IT nao aceita lote sem rastreio)**
demanda real:  Skill 8 F5a — substitui criar_transferencia + validacao manual
               de tracking que estava INLINE no script 09 L965 (bug D-OPS-3)
```

### `validar_picking_inter_company` (ETAPA B F5b — fluxo completo)

```
objeto:        stock.picking — fluxo F5b inteiro encapsulado
input:         picking_id, linhas_esperadas, aplicar_peso_volumes (default True),
               peso_unitario_fallback (default 0.001), volumes_fallback (default 1)
output (dict): {picking_id, state_apos_validate, mls_pendencias, g023_aplicado,
               peso_volumes, tempo_ms}
pré-condições: picking existe em state in (draft, confirmed, assigned)
pós-condições: picking.state='done' (G019 garante via re-leitura); pendencias
               de G021 reportadas; G018 peso/volumes aplicado em picking
sequencia:     1) confirmar_e_reservar  2) preencher_qty_done (lotes do ajuste)
               3) ajustar_qty_done_pelo_disponivel (G021 — pendencias)
               4) validar(linhas_esperadas=) — G023 consolidar + G019 re-state
               5) aplicar_peso_volumes_fallback (G018 v2 — opcional)
gotchas-invariante: G019/G020/G021/G023/G018 codificados (cascateia se G019
               raise)
demanda real:  Skill 8 F5b — substitui inventario_pipeline_service.f5b_validar
               _pickings + aplicar_peso_volumes_fallback_picking (script 09
               L1110-1124). NAO faz liberar_faturamento (F5c fica na Skill 8).
```

### `criar_picking_entrada_destino_manual` (ETAPA F G023)

```
objeto:        stock.picking de ENTRADA manual no destino (FB→LF, FB→CD)
input:         company_destino_id, location_origem_id (transito),
               location_destino_id (estoque destino), moves_data
               [{product_id, quantity, lot_dest_name}, ...], picking_type_id
               (entrada do destino), origin (OBRIGATORIO — idempotencia)
output (dict): {picking_id, status, state, n_moves, tempo_ms}
               status ∈ {CRIADO, IDEMPOTENT_DONE, IDEMPOTENT_OTHER}
pré-condições: moves_data nao vazio (qty>0); origin nao vazio
pós-condições: stock.picking criado com state='done' OU retorna picking
               existente com mesmo origin (idempotente); G023 company_id
               forcado em moves (XML-RPC nao herda); G011 lot_name + quantity
               re-escritos nas MLs; G019/G020 re-le state e raise se != done
gotchas-invariante: **G023 critico** (write company_id em moves apos create —
               XML-RPC nao herda da picking) · G011 (re-quantity + lot_name)
               · G019/G020 (re-le state) · idempotencia via origin exato
               (`origin = X` no domain)
demanda real:  Skill 8 ETAPA F — pickings 317306/317316 LF/IN/01733-01734
               validados em PROD 2026-05-19. Substitui implementacao INLINE
               no script 09 L1508-1688 (`_f_criar_entrada_destino_para_invoice`).
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
| `aplicar_peso_volumes_fallback(picking_id, ...)` | ✅ implementado (v15a — G018 v2) | F5b/F5c Skill 8 — l10n_br_peso_liquido + volumes via write em stock.picking. Caller controla entre `validar()` e `liberar_faturamento()`. |
| `criar_picking_inter_company(...)` | ✅ implementado (v15a — D-OPS-3 fix) | Skill 8 F5a — encapsula G004 (incoterm/carrier) + G021 (filter qty<=0) + **D-OPS-3 (tracking='none' remove lot_name/lot_id)**. SEM CLI ad-hoc — invocado em Python pelo orchestrator. |
| `validar_picking_inter_company(...)` | ✅ implementado (v15a) | Skill 8 F5b — sequencia: confirmar_e_reservar -> preencher_qty_done -> ajustar_qty_done_pelo_disponivel -> validar(G023+G019) -> aplicar_peso_volumes_fallback (G018). SEM CLI ad-hoc. |
| `criar_picking_entrada_destino_manual(...)` | ✅ implementado (v15a — ETAPA F) | Skill 8 ETAPA F — encapsula G023 critico (company_id forcado em moves apos create — XML-RPC nao herda) + G011 (lot_name + re-quantity) + G019/G020 + **idempotencia via origin exato**. SEM CLI ad-hoc. |
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

- **Fluxo 2.5.d — Skill 8 invoca átomos inter-company v15a** (orchestrator faturando-odoo, v15b+):
  1. Skill 8 chama `criar_picking_inter_company(...)` por chunk de ajustes (ETAPA B F5a — codifica D-OPS-3).
  2. Skill 8 chama `validar_picking_inter_company(picking_id, linhas_esperadas, aplicar_peso_volumes=True)` (ETAPA B F5b — fluxo completo).
  3. Skill 8 chama `liberar_faturamento(picking_id)` (F5c — fica fora do átomo `validar_picking_inter_company`).
  4. Após F5d (invoice gerada) + F5e (SEFAZ-OK), Skill 8 chama `criar_picking_entrada_destino_manual(...)` por invoice (ETAPA F — idempotente via origin).
  5. Caller (Skill 8) preserva sleep 5s entre pickings (G022 mitigation script 09 L1136-1138).

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

Skill **construída em 2026-05-24** + **estendida em v15a (2026-05-25)** com 3 átomos inter-company:
- C1: 4 scripts-fonte minerados integral (`16_cancelar_pickings_fantasmas`, `fat_lf_cleanup`, `substituir_lote_205030410_fb`, `fat_lf_05_executar_clean` etapas-chave) + 4 docs de gotchas (G011/G019/G020/G023).
- C2: service `app/odoo/estoque/scripts/picking.py` (capinado de `app/odoo/services/`) com shim em `services/` re-exportando. Métodos novos: `devolver()` + (v15a) `aplicar_peso_volumes_fallback` + `criar_picking_inter_company` + `validar_picking_inter_company` + `criar_picking_entrada_destino_manual`. **61 testes pytest verdes** (42 originais + 19 novos v15a — 2 cobrindo aplicar_peso_volumes + 6 criar_picking_inter_company [incluindo D-OPS-3 fix] + 4 validar_picking_inter_company + 7 criar_picking_entrada_destino_manual).
- C3: contrato de 6 átomos definido (cancelar, validar, devolver, criar_picking_inter_company, validar_picking_inter_company, criar_picking_entrada_destino_manual).
- C4: SKILL.md com receitas, fluxos 2.5.a/b/c/d, armadilhas, exemplos.
- C5: `scripts/operar_picking.py` (CLI 3 modos para cancelar/validar/devolver, --dry-run default, exit codes 0/1/2/4). Átomos v15a SEM CLI ad-hoc (invocados em Python pelo orchestrator Skill 8).
- C6: validação dry-run vs Odoo PROD em smoke v15a OK (6 cods v14a-ops — `103500105` PIMENTA tracking='none' detectado corretamente; lot_name removido das linhas normalizadas; criar_transferencia invocado com linhas pos-D-OPS-3 fix).
- C7-C10: cross-refs aplicados (subagente gestor-estoque-odoo + ROUTING_SKILLS + tool_skill_mapper + CLAUDE.md estoque + memoria skill5_picking_pattern).

Mapeamento script-fonte → átomo no `docs/inventario-2026-05/consolidacao/MAPA_SCRIPTS.md`. Resultado da validação em `_validados/operando-picking-odoo/VALIDACAO.md`.
