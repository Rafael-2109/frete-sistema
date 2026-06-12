---
name: operando-mo-odoo
description: >-
  Skill WRITE+READ (átomo C2 + modos READ §6.b) para operar Ordens de
  Produção (mrp.production) no Odoo, em 4 modos: listar (READ, com
  classificação SEGURO/RESERVA_FANTASMA/FURO_REAL), detalhar (READ),
  cancelar (WRITE, single ou batch, guard G-MO-01 bloqueia FURO_REAL) e
  concluir (WRITE V7, single-only — Produzir Tudo + Validar via
  button_mark_done com guards G-MO-05/G-MO-06 anti-producao-fantasma). Usar
  quando o pedido é "lista MOs antigas", "detalhe da MO X", "cancela MO X",
  "cancela MOs zumbi", "conclui/produz a MO X", "Produzir Tudo e validar".
  `--dry-run` é o DEFAULT; `--confirmar` executa. NAO usar para cancelar
  PICKING -> operando-picking-odoo. Matriz USAR/NAO-USAR completa no corpo.
allowed-tools: Read, Bash, Glob, Grep
---

# operando-mo-odoo (WRITE + READ — átomo C2 + §6.b)

Skill com 4 modos. Construída em 2026-05-24 v5; **estendida em 2026-05-27 v6** com modos READ + guard G-MO-01 refinado; **estendida em 2026-06-12 V7** com modo `concluir`:

- **Cancelamento periódico de MOs antigas/zumbi** em FB e CD (caso real 2026-05-20: 120 MOs zumbi 2024-2025; caso 2026-05-27: 342 MOs pré-2026-05-15 canceladas — 314 limpas + 28 reserva-fantasma).
- **Guard G-MO-01 v6 (2026-05-27)**: distingue `done` (consumo CONTÁBIL = furo real) de `reservado` (assigned/waiting/picked = reserva fantasma). Bloqueia apenas FURO_REAL. Origem: 29 MOs classificadas como FURO em 2026-05-27, auditoria revelou 100% FALSO-POSITIVO (todos os moves em `assigned`/`waiting`, nenhum em `done`).. Ver `docs/inventario-2026-05/02-gotchas/G-MO-05-falso-positivo-reserva-fantasma.md`.
- **Modos READ (§6.b CLAUDE.md)**: `listar` (com classificação) + `detalhar` (raws+finished+MLs+consumo). Pattern compartilhado: skills WRITE expõem `--modo listar/detalhar` do seu objeto principal (sem trocar de skill).
- **Audit pré/pós opcional** (`--with-audit`): snapshot completo de MO + raws/finished + MLs + quants origem antes e depois do `action_cancel`, com diff estruturado.
- **Idempotência action_cancel**: validada AO VIVO 2026-05-24 em MO já cancelada (retorna `True` sem erro, state continua 'cancel').
- **Modo `concluir` (V7 2026-06-12)**: Produzir Tudo + Validar (`button_mark_done`) com sequência minerada do piloto industrialização FB-LF (validada PROD 2026-06-01). Guards G-MO-05 (`picked=True` em MLs+moves ANTES do done + POS-CHECK — sem isso o wizard de consumo CANCELA os raws = produção fantasma a custo zero, caso real MOs 20235/36/38/39) e G-MO-06 (raw sem move.line pós-`action_assign` bloqueia). SINGLE-ONLY: escrita contábil IRREVERSÍVEL (MO done não é cancelável). Demanda real: MO LF/MO/03556 (sessão 2026-06-10, agente só soube guiar manualmente).

Constituição: `app/odoo/estoque/CLAUDE.md` (§6.b para modos READ). Service: `app/odoo/estoque/scripts/mo.py` (StockMOService); shim em `app/odoo/services/stock_mo_service.py`.

## Quando usar / Quando NÃO usar

**Modos**: (1) **listar** (READ) — lista MOs por critério (data/states/empresas)
com classificação SEGURO/RESERVA_FANTASMA/FURO_REAL; (2) **detalhar** (READ) —
MO completa (raws+finished+MLs+consumo); (3) **cancelar** (WRITE) —
`action_cancel` single ou batch com guard G-MO-01 v6 (bloqueia apenas FURO_REAL =
consumo done > 0; reserva fantasma passa); (4) **concluir** (WRITE V7,
single-only) — Produzir Tudo + Validar via `button_mark_done` com guards
G-MO-05/G-MO-06. Opt-in `--with-audit` captura snapshot pré/pós + diff.

**USAR QUANDO** o pedido é: "lista MOs antigas", "detalhe da MO X", "cancela MO X",
"cancela MOs zumbi", "limpa MOs draft/confirmed sem consumo done",
"conclui/produz a MO X", "Produzir Tudo e validar a MO", "finaliza a producao".

**NÃO USAR PARA:**
- cancelar MO COM consumo done > 0 (gera furo real) -> use `mrp.unbuild` via
  cross-skill (ver memória local Claude Code [[reaproveitar-semiacabado-orfao-mo-cancelada]])
- criar MO nova -> sem demanda real isolada (pipeline cria via Odoo)
- alterar MO (mover componente, ajustar qty) -> fluxo cross-skill
  (Skill 2 transfer + write em stock.move; ver memória local Claude Code
  [[mo_componente_local_consumo]])
- concluir MO em BATCH -> não suportado por design (escrita contábil
  irreversível; concluir é single-only `--mo-id`)
- produção PARCIAL (qty < product_qty) -> fora do V7 (comportamento de
  backorder não validado ao vivo); concluir é Produzir Tudo
- cancelar PICKING (não é MO) -> `operando-picking-odoo`
- cirurgia/MLs órfãs -> `operando-reservas-odoo`

---

## REGRAS CRÍTICAS

1. **`--dry-run` é o DEFAULT** (modo cancelar). Sem `--confirmar`, só calcula e mostra o plano (exit 4).
2. **Modos READ (`listar`, `detalhar`) bloqueiam `--confirmar`** (CLI retorna exit 2). Convenção §6.b CLAUDE.md: skills mistas READ/WRITE distinguem por `--modo`.
3. **G-MO-01 v6 (2026-05-27) — particionado**:
   - `done > TOL` (consumo CONTÁBIL efetivado) → `FALHA_FURO_CONTABIL_REAL`. Default seguro INVIOLÁVEL.
   - `reservado > TOL` e `done = 0` (apenas reserva fantasma) → **PASSA** com `OK_RESERVA_FANTASMA` (action_cancel libera reservas sem furo).
   - `done = 0` e `reservado = 0` → `OK` (limpo).
   - CLI **NÃO expõe** `--forcar-consumo` (parâmetro do service mantido apenas para auditoria/pipelines internos; raramente necessário com o guard v6).
4. **Para MO com `done > 0` (e precisa reverter)**: usar `mrp.unbuild` via fluxo cross-skill — devolve componentes aos lotes originais (ver [[reaproveitar-semiacabado-orfao-mo-cancelada]] (memória local Claude Code) §3).
5. **`action_cancel` é IDEMPOTENTE** em MO state='cancel' (retorna True sem erro, state continua 'cancel') — atomo retorna `NOOP` sem chamar Odoo novamente.
6. **`action_cancel` NÃO funciona** em MO state='done' (não tem como reverter sem unbuild) — atomo retorna `FALHA_STATE_NAO_CANCELAVEL`.
7. **Cancelamento libera automaticamente** as reservas dos componentes (Odoo cascade). Se sobrar quant.reserved residual stale → chamar Skill 2.4 `zerar_reserved_residual` (regra inviolável 9 — pattern do orquestrador).
8. **Audit pré/pós (`--with-audit`)**: default **ON em single** (`--mo-id`), **OFF em batch** (custa +1-2s/MO). Captura snapshot completo de MO+raws+finished+MLs+quants_origem antes e depois, com diff estruturado. Use para single mode ou batches pequenos onde rastreabilidade é mais importante que throughput.
9. **Concluir é IRREVERSÍVEL e single-only (V7)**: `button_mark_done` gera consumo contábil (SVL + account.move); MO done NÃO é cancelável e `mrp.unbuild` reverte só o físico re-adicionando a BoM inteira. Por isso: sem batch, dry-run primeiro SEMPRE, e o POS-CHECK G-MO-05 é a rede final (raw cancelado pós-done = `FALHA_PRODUCAO_FANTASMA` — parar e investigar, NÃO repetir).
10. **Lote produzido nunca é inventado**: produto com tracking lot/serial sem `lot_producing_id` exige `--lote` explícito (busca com operador `in` + filtro `company_id` — gotchas stock.lot); sem ele, `FALHA_LOTE_PRODUZIDO_AUSENTE`.

## Contratos

### `listar` (READ — §6.b)

```
objeto:        mrp.production
input:         --modo listar
                  [--create-de YYYY-MM-DD] [--create-ate YYYY-MM-DD]
                  [--states draft,confirmed,progress,to_close]
                  [--empresas 1,3,4,5]
                  [--limite N]
                  (BLOQUEIA --confirmar)
output (JSON): {modo: 'listar', criterio, total, classificacao:{SEGURO|RESERVA_FANTASMA|FURO_REAL: N},
                itens:[{id, name, state, company_id, company_name, create_date,
                       classificacao, consumo:{done, reservado, total}}],
                tempo_ms}
WRITE:         NUNCA
exit codes:    0 (sucesso) · 2 (uso invalido)
```

### `detalhar` (READ — §6.b)

```
objeto:        mrp.production (+ stock.move raws/finished + stock.move.line)
input:         --modo detalhar --mo-id <id>
                  (BLOQUEIA --confirmar)
output (JSON): {modo: 'detalhar', id, name, state, company_id, company_name,
                product_id, product_name, product_qty, qty_produced,
                reservation_state, classificacao, consumo:{done, reservado, total},
                details:{date_start, date_deadline, date_finished, origin, bom_id,
                         raws:[{id, product, state, planejado, quantity, picked,
                                location, location_dest, move_lines:[{id, state,
                                quantity, picked, location, lot}]}],
                         finished:[<idem raws>]},
                tempo_ms}
WRITE:         NUNCA
exit codes:    0 · 2 (uso invalido)
```

### `cancelar` (WRITE — átomo C2)

```
objeto:        mrp.production (cascateia para stock.move + stock.move.line via action_cancel)
input:         --modo cancelar --mo-id <id> [--motivo "..."] [--with-audit] [--confirmar]    (single)
                 OU --modo cancelar --mo-ids 17449,18108 [--motivo "..."] [--with-audit] [--confirmar]  (batch explicito)
                 OU --modo cancelar (batch por criterio)
                    [--create-de YYYY-MM-DD] [--create-ate YYYY-MM-DD]
                    [--states draft,confirmed,progress,to_close]
                    [--empresas 1,4,5]
                    [--consumo zero|qualquer]   (default zero = filtra furo REAL)
                    [--limite N]
                    [--with-audit]   (default OFF em batch)
output (JSON): single  : {modo, tipo:'single', dry_run, with_audit, status,
                          mo_id, name, state_antes, state_apos,
                          consumo:{done, reservado, total}, consumo_total (compat),
                          warning_reserva_fantasma?, motivo, tempo_ms, acao, erro?,
                          audit?:{pre, pos, diff}}  -- audit so se with_audit=True
               batch   : {modo, tipo:'batch', dry_run, with_audit, criterio,
                          total_pre_filtro, total_candidatas,
                          total_filtradas_por_consumo, contagem_status,
                          resultados:[<single>...], tempo_total_ms}
pré-condições: MO existe; state IN (draft, confirmed, progress, to_close)
               (se state='cancel': NOOP; se state='done': falha)
               consumo done <= 0.0001 (G-MO-01 v6 — bloqueia furo real)
pós-condições: MO.state='cancel'; moves filhas state='cancel';
               MLs filhas removidas; quant.reserved_quantity recalculado
               (Odoo cascade automático)
gotchas-invariante:
  G-MO-01 v6: done > 0 = FURO CONTABIL REAL -> FALHA_FURO_CONTABIL_REAL
              (default seguro; sugere mrp.unbuild via cross-skill).
              done = 0 e reservado > 0 = RESERVA FANTASMA -> OK_RESERVA_FANTASMA
              (action_cancel libera reservas sem furo).
              Refinado em 2026-05-27 a partir do incidente das 29 MOs
              falso-positivo. Ver `docs/inventario-2026-05/02-gotchas/G-MO-05-falso-positivo-reserva-fantasma.md`.
  G-MO-02 manual_consumption nao reserva via action_assign -> NAO relevante
          para cancelar (action_cancel ignora reservas/picked).
  G-MO-03 componente em local errado -> NAO relevante para cancelar.
  G-MO-04 picked=True em to_close/done -> herdado de Skill 2.4 G026
          (action_cancel e seguro com picked).
  G019-like: SEMPRE re-le state pos action_cancel; raise nao e raise
             (retorna FALHA_STATE_INESPERADO).
modos:         --dry-run (default, exit 4) -> --confirmar (exit 0)
status:        EXECUTADO · NOOP · OK_RESERVA_FANTASMA ·
               DRY_RUN_OK · DRY_RUN_NOOP · DRY_RUN_OK_RESERVA_FANTASMA ·
               FALHA_FURO_CONTABIL_REAL · DRY_RUN_FALHA_FURO_CONTABIL_REAL ·
               FALHA_STATE_NAO_CANCELAVEL · DRY_RUN_FALHA_STATE_NAO_CANCELAVEL ·
               FALHA_STATE_INESPERADO · FALHA
               (alias deprecated FALHA_FURO_CONTABIL ainda reconhecido)
```

### `concluir` (WRITE — átomo C2, V7 2026-06-12, SINGLE-ONLY)

```
objeto:        mrp.production (cascateia para stock.move/stock.move.line via
               action_assign + button_mark_done; stock.lot apenas para
               resolver/criar lot_producing_id)
input:         --modo concluir --mo-id <id> [--lote "099/26"] [--motivo "..."]
                  [--with-audit] [--confirmar]
               (batch NAO suportado: --mo-ids/--create-de/--create-ate -> exit 2)
output (JSON): {modo: 'concluir', tipo:'single', dry_run, with_audit, status,
                mo_id, name, state_antes, state_apos, company_id, product_id,
                product_qty, tracking, plano? (dry-run), warnings?,
                raws_apontados?, raws_sem_ml?, raws_cancelados?,
                raws_consumidos?, lote?, wizard_consumo_confirmado?,
                motivo, tempo_ms, acao, erro?, audit?:{pre, pos, diff}}
pré-condições: MO existe; state IN (confirmed, progress, to_close)
               (done: NOOP; cancel/draft: FALHA — draft orienta action_confirm);
               tracking lot/serial exige lot_producing_id OU --lote;
               TODOS os raws com move.line apos action_assign (G-MO-06)
pós-condições: MO.state='done'; raws state='done' com quantity>0 (consumo
               contabil real — SVL + account.move); finished move done no
               location_dest; qty_producing = product_qty (Produzir Tudo)
gotchas-invariante:
  G-MO-05 (ex-G-ENT-10 piloto industrializacao, validado PROD 2026-06-01):
          action_assign cria ML com picked=False; wizard mrp.consumption.warning
          dispara button_mark_done(skip_consumption=True) que com picked=False
          CANCELA os raws -> producao fantasma (SVL value=0). Fix codificado:
          picked=True em MLs+moves ANTES do done + POS-CHECK pos-done.
  G-MO-06: raw sem move.line pos-assign (manual_consumption G-MO-02 OU saldo
          fora do location_src G-MO-03) -> FALHA_COMPONENTE_SEM_RESERVA
          (concluir cancelaria o raw = consumo parcial silencioso).
  Context multi-company derivado de mo.company_id em TODAS as chamadas
          (licao D-V30-1: action_* com company do USUARIO opera errado).
  Wizard mrp.consumption.warning tratado (create + action_confirm); unico
          artefato tolerado e 'cannot marshal None' (helper canonico T1.5).
  G019-like: re-le state pos mark_done; != 'done' -> FALHA_STATE_INESPERADO.
modos:         --dry-run (default, exit 4) -> --confirmar (exit 0)
status:        EXECUTADO · NOOP · DRY_RUN_OK · DRY_RUN_NOOP ·
               FALHA_STATE_NAO_CONCLUIVEL · DRY_RUN_FALHA_STATE_NAO_CONCLUIVEL ·
               FALHA_COMPONENTE_SEM_RESERVA ·
               FALHA_LOTE_PRODUZIDO_AUSENTE · DRY_RUN_FALHA_LOTE_PRODUZIDO_AUSENTE ·
               FALHA_PRODUCAO_FANTASMA · FALHA_STATE_INESPERADO · FALHA
```

## Receitas (caso real → args)

### Workflow recomendado: listar → detalhar → cancelar

| Preciso de... | Modo | Args |
|---------------|------|------|
| **Listar candidatas + classificar** (READ) | listar | `--modo listar --create-ate 2025-06-01 --empresas 1,4,5` |
| **Detalhar 1 MO suspeita** (raws+MLs+consumo) | detalhar | `--modo detalhar --mo-id 17449` |
| **Cancelar 1 MO específica** (audit default ON) | single | `--modo cancelar --mo-id 19713 --motivo "zumbi 2025" --confirmar` |
| **Cancelar 1 MO SEM audit** (canary rápido) | single | `--modo cancelar --mo-id 19713 --confirmar` (audit default mas pode adicionar `--with-audit` explicito) |
| **Cancelar lista explícita de IDs** | batch | `--modo cancelar --mo-ids 17449,18108,19704 --motivo "..." --confirmar` |
| **Cancelar lista com audit completo** | batch | `--modo cancelar --mo-ids 17449,18108 --confirmar --with-audit` |
| **Cancelar zumbi FB 2024-2025 sem furo** | batch | `--modo cancelar --create-de 2024-01-01 --create-ate 2026-01-01 --empresas 1 --states draft,confirmed,progress,to_close --consumo zero --confirmar` |
| **Cancelar MOs antigas FB/CD em massa** | batch | `--modo cancelar --create-ate 2025-06-01 --empresas 1,4 --consumo zero --confirmar` |
| **Canary (1 MO antes de batch)** | batch | `--modo cancelar --create-ate 2025-06-01 --empresas 1 --consumo zero --limite 1 --confirmar` |
| **Dry-run prévio** (ver quantas seriam canceladas) | batch dry | `--modo cancelar --create-ate 2025-06-01 --empresas 1` (sem `--confirmar`) |
| **Tentar cancelar MO com furo real** → bloqueia | single | `--modo cancelar --mo-id 19850` (done>0 → FALHA_FURO_CONTABIL_REAL) |
| **MO com reserva fantasma** (não bloqueia) | single | `--modo cancelar --mo-id 19780 --confirmar` (reservado>0, done=0 → OK_RESERVA_FANTASMA) |
| **Concluir MO (Produzir Tudo + Validar)** — dry-run primeiro | concluir | `--modo concluir --mo-id 20606` (plano: raws, lote, qty) |
| **Concluir efetivando** (lote já na MO) | concluir | `--modo concluir --mo-id 20606 --motivo "pedido Rafael" --confirmar` |
| **Concluir informando lote produzido** (tracking sem lot na MO) | concluir | `--modo concluir --mo-id 20606 --lote "099/26" --confirmar` |
| **Concluir MO já done** (idempotente) | concluir | `--modo concluir --mo-id 20606 --confirmar` → NOOP |

## Catálogo de átomos

### Operações (WRITE)

| Átomo | Status | Demanda real |
|---|---|---|
| `cancelar_mo(mo_id, motivo, forcar_consumo, consumo_total, dry_run)` | ✅ implementado | Caso real 2026-05-20 (120 MOs zumbi) + 2026-05-27 (342 MOs) |
| `cancelar_mo_com_audit(mo_id, ...)` | ✅ implementado (v6 2026-05-27) | Auditoria estruturada pré/pós para single mode + batches pequenos |
| `cancelar_mos_em_massa(criterio, max_n, motivo, dry_run)` | ✅ implementado | Pattern de `cancelar_mos.py` + `14_cancelar_mos_antigas_fb.py` |
| `medir_consumo_mo(mo_ids)` | ✅ implementado v6 (retorna dict {done, reservado, total}) | Guard G-MO-01 v6 particionado |
| `medir_consumo_mo_legacy(mo_ids)` | ✅ implementado (compat float) | Callers que ainda dependem do formato antigo (deprecar gradualmente) |
| `concluir_mo(mo_id, nome_lote, motivo, dry_run)` | ✅ implementado (V7 2026-06-12) | MO LF/MO/03556 (2026-06-10) + piloto industrialização FB-LF (2026-06-01, e2e_mo_lf_criar.py) |
| `concluir_mo_com_audit(mo_id, ...)` | ✅ implementado (V7) | Auditoria pré/pós (default ON em single) |
| `criar_mo(...)` | ⬜ NÃO previsto | Sem demanda real isolada (pipeline cria via Odoo) |
| `alterar_mo(...)` | ⬜ NÃO previsto | Caso real PROD existe MAS é fluxo cross-skill. Implementar como FOLHA de fluxo (3.2.x), NÃO como átomo. |
| `mrp_unbuild(mo_id, ...)` | ⬜ NÃO previsto | Fluxo cross-skill — caso real existe (reverter MO done) mas não é átomo isolado da Skill 4. |

### Leituras (READ — §6.b adicionado v6 2026-05-27)

| Átomo | Status | Demanda real |
|---|---|---|
| `listar_mos(criterio)` | ✅ implementado | Caso 2026-05-27 (343 MOs candidatas filtradas + classificadas) |
| `detalhar_mo(mo_id)` | ✅ implementado | Caso 2026-05-27 (2 MOs detalhadas antes de cancelar) |
| `_snapshot_mo(mo_id)` | ✅ implementado (helper interno do audit) | Pré-cond do diff pré/pós |
| `_diff_snapshots(pre, pos)` | ✅ implementado (helper estático) | Diff estruturado do `--with-audit` |

## Composição em FLUXOS

- **Fluxo 3.1.a — cancelar MO única (zumbi reportada)**:
  1. Identificar MO via Skill 9 (`consultando-quant-odoo` + investigação manual mrp.production).
  2. Confirmar state IN (draft/confirmed/progress/to_close) E consumo_total = 0.
  3. `operar_mo.py --modo cancelar --mo-id X --motivo "..." --confirmar`.
  4. Verificar no Odoo UI: MO state='cancel', moves filhas state='cancel', componentes liberados.
  5. **Se** havia reservas pré-cancel + alguma ML órfã sobrar → Skill 2.4 `zerar_reserved_residual` nos quant_ids afetados (regra inviolável 9).

- **Fluxo 3.1.b — batch zumbi antigas** (pattern 2026-05-20, 120 MOs):
  1. Definir critério (ex.: empresas=[1,4], create_ate='2025-06-01', states ativos, consumo=zero).
  2. Dry-run: `operar_mo.py --modo cancelar [filtros]` → vê quantas seriam canceladas + filtro de consumo.
  3. Revisar lista de MOs (log JSON dry-run); confirmar que não há MOs ativas conhecidas (excluir via `--empresas` ou outro filtro).
  4. Canary: rodar com `--limite 1 --confirmar` em 1 MO; verificar resultado direto no Odoo.
  5. Batch completo: `operar_mo.py --modo cancelar [filtros] --confirmar`.
  6. Verificar no Odoo UI: critério retorna 0 candidatas após batch (idempotente).

- **Fluxo 3.1.c — MO com consumo (NÃO COBERTO por esta skill)**:
  - DELEGAR para fluxo cross-skill `mrp.unbuild` (sem skill ainda). Ver memória [[reaproveitar-semiacabado-orfao-mo-cancelada]] (memória local Claude Code) para procedimento manual XML-RPC: criar `mrp.unbuild` com `mo_id` definido → `action_unbuild` → componentes voltam aos lotes originais automaticamente.

- **Fluxo 3.2 — concluir MO (Produzir Tudo + Validar)** (folha L3 `app/odoo/estoque/fluxos/3.2-concluir-mo.md`):
  1. `--modo detalhar --mo-id X` — conferir raws/reservas/lote ANTES.
  2. `--modo concluir --mo-id X [--lote ...]` (dry-run) — validar plano (qty, lote, raws_sem_ml_atual).
  3. Se raw sem reserva persistir no real (G-MO-06): tratar componente primeiro (transferência interna p/ location_src — ver [[mo_componente_local_consumo]]) e repetir.
  4. `--confirmar` — IRREVERSÍVEL.
  5. Verificar no Odoo: MO done, raws done com quantity>0, SVL com value≠0, saldo do acabado no location_dest.

## Armadilhas

- **`action_cancel` em MO state='cancel' retorna True** (idempotente). Validado AO VIVO 2026-05-24 (FB/OP/BALDE/00009 id=4192). Service trata como `NOOP` sem chamar Odoo novamente (economiza RPC).
- **`action_cancel` em MO state='done' não funciona**. Service retorna `FALHA_STATE_NAO_CANCELAVEL` sem chamar Odoo — mensagem sugere `mrp.unbuild` via fluxo cross-skill.
- **`stock.move.action_cancel` NÃO existe** via XML-RPC (`_action_cancel` é privado). Cancelar MO via `mrp.production.action_cancel` é o caminho correto (cascade automático para moves + MLs).
- **`qty_produced` é o produto acabado finalizado, NÃO componentes consumidos.** Validado AO VIVO 2026-05-24 (MOs com qty_produced=0 e consumo_total>0 são comuns). Para guard G-MO-01, medimos `stock.move.quantity` (raw materials != cancel), não `qty_produced`.
- **Tolerância TOL_CONSUMO=0.0001** (mesma dos scripts-fonte). Consumos abaixo são tratados como zero (rounding errors do Odoo: 6 decimais).
- **Cuidado com MOs em state='progress'**: cancelar MO em produção ATIVA é perigoso (operador no chão de fábrica pode estar apontando). Default `--states draft,confirmed,progress,to_close` inclui progress por consistência com scripts-fonte, MAS recomenda-se filtrar para `confirmed,draft` em batches grandes (zumbis antigas raramente estão em progress real — geralmente são órfãs do MRP).
- **MOs de SEMI-ACABADO multi-nível**: cancelar MO de acabado pode deixar MO de semi órfã (caso real [[reaproveitar-semiacabado-orfao-mo-cancelada]] (memória local Claude Code)). Esta skill NÃO trata isso — operador valida manualmente após cancel; se semi gerou estoque órfão, abrir caso de unbuild ou consumo via outra MO.
- **picked=True em to_close/done**: action_cancel é seguro nesse cenário (não mexe em quants existentes — só marca state='cancel'). G-MO-04 herdado de Skill 2.4 G026.
- **(concluir) Wizard `mrp.consumption.warning`**: `button_mark_done` pode retornar o wizard (rounding 6dp BoM vs 4dp estoque). O átomo o confirma automaticamente (`create` + `action_confirm`) — COM `picked=True` já aplicado o wizard CONSOME; sem picked, CANCELARIA os raws (G-MO-05).
- **(concluir) `cannot marshal None`**: `button_mark_done` via XML-RPC pode retornar None (artefato de marshalling) — único erro tolerado (helper canônico `is_cannot_marshal_none`); qualquer outra exceção vira FALHA.
- **(concluir) Componente `manual_consumption` (salmoura, azeitona...)**: não reserva via `action_assign` (G-MO-02) — G-MO-06 bloqueia. Tratar o apontamento manual no Odoo (ou transferir saldo p/ o location_src) antes de concluir.
- **(concluir) MO em `progress`**: operador no chão de fábrica pode estar apontando — o dry-run emite warning; confirmar com a produção antes do `--confirmar`.
- **(concluir) Alinhamento demanda→reservado FICA FORA do átomo** (decisão 2026-06-12): o e2e do piloto alinhava `product_uom_qty` ao reservado para rounding, mas generalizado isso MASCARA falta real de componente. MO com partial real falha no G-MO-06 — correto.

## Exemplos

```bash
SK=.claude/skills/operando-mo-odoo/scripts/operar_mo.py

# === MODOS READ (sem WRITE — bloqueiam --confirmar) ===

# 1) Listar MOs candidatas com classificacao SEGURO/RESERVA_FANTASMA/FURO_REAL
python "$SK" --modo listar --create-ate 2025-06-01 --empresas 1,3,4,5

# 2) Listar limitado (top 5 mais antigas)
python "$SK" --modo listar --create-ate 2025-06-01 --empresas 1 --limite 5

# 3) Detalhar 1 MO (raws+finished+MLs+consumo)
python "$SK" --modo detalhar --mo-id 17449

# === MODO CANCELAR (WRITE) ===

# 4) Dry-run: cancelar 1 MO especifica (audit default ON em single)
python "$SK" --modo cancelar --mo-id 19713

# 5) Efetivar cancelamento de 1 MO com audit pre/pos
python "$SK" --modo cancelar --mo-id 19713 --motivo "zumbi 2025" --confirmar

# 6) Cancelar lista explicita de IDs com audit completo
python "$SK" --modo cancelar --mo-ids 17449,18108,19704 --confirmar --with-audit

# 7) Dry-run batch: quantas MOs FB ativas pre-2025-06 sem furo real?
python "$SK" --modo cancelar \
  --create-ate 2025-06-01 --empresas 1 --consumo zero

# 8) Canary: cancelar 1 MO do batch (testar real)
python "$SK" --modo cancelar \
  --create-ate 2025-06-01 --empresas 1 --consumo zero \
  --limite 1 --confirmar

# 9) Batch completo (cuidado!)
python "$SK" --modo cancelar \
  --create-ate 2025-06-01 --empresas 1 --consumo zero \
  --motivo "limpeza zumbi 2024-2025" --confirmar

# 10) Tentar cancelar MO COM consumo done > 0 (esperado: FALHA_FURO_CONTABIL_REAL)
python "$SK" --modo cancelar --mo-id 19850

# 11) MO com reserva fantasma (esperado: OK_RESERVA_FANTASMA, nao bloqueia)
python "$SK" --modo cancelar --mo-id 19780 --confirmar

# 12) Idempotencia: cancelar MO ja cancelada (esperado: NOOP)
python "$SK" --modo cancelar --mo-id 4192 --confirmar

# === MODO CONCLUIR (WRITE V7 — single-only, IRREVERSIVEL) ===

# 13) Dry-run: plano de conclusao (raws, lote, qty — exit 4)
python "$SK" --modo concluir --mo-id 20606

# 14) Efetivar (lote ja na MO): Produzir Tudo + Validar
python "$SK" --modo concluir --mo-id 20606 --motivo "producao confirmada" --confirmar

# 15) Efetivar informando lote produzido (tracking lot sem lot_producing_id)
python "$SK" --modo concluir --mo-id 20606 --lote "099/26" --confirmar

# 16) Idempotencia: concluir MO ja done (esperado: NOOP)
python "$SK" --modo concluir --mo-id 20606 --confirmar
```

## Validação

**V1 (2026-05-24 v5)** — construção inicial:
- C1: 2 scripts-fonte minerados integral (`cancelar_mos.py` + `14_cancelar_mos_antigas_fb.py`). Investigação AO VIVO via `/tmp/investigar_mos_skill4.py` (10.000 MOs FB / 17 CD / 3367 LF; estrutura mrp.production validada; idempotência action_cancel confirmada em FB/OP/BALDE/00009).
- C2: service `app/odoo/estoque/scripts/mo.py` (NOVO — sem service legado) com shim em `services/stock_mo_service.py`. 29 testes pytest verdes.
- C3-C7: contrato, SKILL.md, CLI, validação dry-run vs Odoo PROD (4 casos), cross-refs + arquivamento.

**V6 (2026-05-27)** — extensão com modos READ + guard refinado:
- **Trigger**: caso real 343 MOs zumbi pré-2026-05-15 (FB=335, SC=0, CD=2, LF=6); 29 classificadas como FURO pelo guard antigo MAS auditoria revelou 100% FALSO-POSITIVO (nenhuma com move state='done'). Ver `docs/inventario-2026-05/02-gotchas/G-MO-05-falso-positivo-reserva-fantasma.md`.
- **Mudanças no service** (`app/odoo/estoque/scripts/mo.py`):
  - `medir_consumo_mo` retorna `{mo_id: {done, reservado, total}}` particionando por state (`done` vs `assigned|waiting|partially_available|confirmed`).
  - `medir_consumo_mo_legacy` adicionado para callers que ainda dependem do formato float.
  - Guard G-MO-01 v6: bloqueia apenas `done > TOL`; `reservado > TOL` e `done = 0` passa como `OK_RESERVA_FANTASMA`.
  - Novos métodos READ: `listar_mos(criterio)`, `detalhar_mo(mo_id)`.
  - Novo método de audit: `cancelar_mo_com_audit(mo_id, ...)`, com helpers `_snapshot_mo` + `_diff_snapshots`.
  - Status renomeados: `FALHA_FURO_CONTABIL` → `FALHA_FURO_CONTABIL_REAL` (alias antigo mantido em `_FALHAS` da CLI para compat).
- **Mudanças na CLI** (`scripts/operar_mo.py`):
  - `--modo {listar, detalhar, cancelar}` (era só `cancelar`).
  - `--mo-ids` (CSV) para batch explícito (alternativa aos filtros).
  - `--with-audit` (default ON em single, OFF em batch).
  - Bloqueio anti-WRITE: `--modo listar/detalhar + --confirmar` → exit 2.
- **Testes pytest**: **42 verdes** (29 refatorados + 13 novos cobrindo guard refinado, listar, detalhar, snapshot, diff, audit dry-run, audit real).
- **Validação AO VIVO 2026-05-27**:
  - Cancel batch das 314 limpas (FB=307, CD=2, LF=5): 100% EXECUTADO, 9min20s, 0 erros.
  - Cancel das 28 com reserva fantasma (via `/tmp/cancelar_mo_nativo.py` PRE-skill-v6, mesmo `action_cancel` nativo): 28/28 state=cancel; 13.610,765 un de reserva liberadas em 22 quants; 201 MLs unlinkadas; 107s; 0 anomalias.
  - Modo `listar` validado em PROD: 5 itens, classificou corretamente SEGURO=4, RESERVA_FANTASMA=1.

**V7 (2026-06-12)** — modo `concluir` (Produzir Tudo + Validar):
- **Trigger**: MO LF/MO/03556 (sessão 2026-06-10 — usuário queria Produzir Tudo + Validar e o agente só soube guiar manualmente; rejeição IMP-2026-06-10-001 do D8 #36 elevada a necessidade pelo Rafael em 2026-06-12).
- **Fonte minerada**: `docs/industrializacao-fb-lf/scripts/e2e_mo_lf_criar.py` (sequência validada em PROD 2026-06-01 no piloto industrialização FB-LF; gotcha picked=True ex-G-ENT-10 → codificado como G-MO-05).
- **Service**: `concluir_mo` + `concluir_mo_com_audit` + helpers `_ctx_company`/`_ler_raws_concluir`/`_resolver_lot_producing`; constante `STATES_CONCLUIVEIS`; context multi-company em todas as chamadas (lição D-V30-1).
- **Decisões de escopo (Rafael 2026-06-12)**: single-only; Produzir Tudo apenas (parcial fora — backorder não validado); raw sem reserva BLOQUEIA (G-MO-06); draft falha pedindo `action_confirm` prévio; `--lote` obrigatório quando tracking sem lot (nunca inventado); alinhamento demanda→reservado FORA do átomo.
- **Auditoria P8**: `button_mark_done` adicionado a `METODOS_WRITE_AUDITADOS` (`app/utils/odoo_audit_helpers.py`).
- **Testes pytest**: **57 verdes** (42 v6 + 15 novos V7 — dry-run plano, NOOP, states, lote ausente/busca/criação, G-MO-06, picked+context, wizard, marshal None, exceção real, state inesperado, produção fantasma, audit).
- **Smokes PROD 2026-06-12 (dry-run/READ)**: MO 20606 done → `DRY_RUN_NOOP` exit 4; MO 19762 (FB/OP/SALMOURA/05825, confirmed, tracking lot, lote 135/26) → `DRY_RUN_OK` com plano completo + warning G-MO-06 (3 raws sem ML no estado atual). **Canary `--confirmar` PENDENTE** — aguarda demanda natural de conclusão (a MO 03556 já foi concluída manualmente).

Mapeamento script-fonte → átomo: `docs/inventario-2026-05/consolidacao/MAPA_SCRIPTS.md`.

Constituição do pattern READ em skills WRITE: `app/odoo/estoque/CLAUDE.md` §6.b.
