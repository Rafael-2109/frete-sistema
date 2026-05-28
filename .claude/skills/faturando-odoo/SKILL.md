---
name: faturando-odoo
description: >-
  Skill WRITE ATOMICA L2 (v24+ AP6 refator) para 5 operacoes sobre `account.move`
  (NF SAIDA inter-company): validar_invoice_constants (pre-cond fiscal) +
  liberar_faturamento (dispara robo CIEL IT via XML-RPC) + polling_invoice
  (aguarda criacao) + validar_invoice_pos_robo (G029+G007+G034) + transmitir_sefaz
  (Playwright SEFAZ IRREVERSIVEL).

  Constituicao §6 Tabela 1: Skill 8 = SO SAIDA `account.move`; par da Skill 7
  `escriturando-odoo` (= SO ENTRADA DFe+account.move entrada). Quem une saida +
  entrada = FLUXO L3 1.3-transferencia-completa.md (⬜ a escrever v25+) ou
  orchestrator C3 `inventario_pipeline` (renomeado de `faturamento_pipeline.py`
  em v27+ S3; stub alias compat preservado).

  V24+ AT0MICA LIVE (2026-05-27): 5 atomos componiveis em
  `app/odoo/estoque/scripts/faturamento.py` (~750 LOC, 28 pytest verdes).
  Espelha pattern Skill 7 ABRANGENTE v19+ (7 atomos). Cada atomo dry-run-first
  + idempotente intra-Odoo + auto-seguro (G016/G019/G020/G029/G007/G034/D7/D8/
  D9/CRITICAL-1/MED C-1/MED C-2 codificados intra-atomo).

  Orchestrator C3 LEGACY `inventario_pipeline.py` (renomeado de
  `faturamento_pipeline.py` em v27+ S3 — stub alias preservado; ~5600 LOC,
  pipeline A-F + recovery + opt-in --usar-fluxo-l3-v19 + **opt-in
  --usar-skill8-atomica-v25 LIVE v27+ S1** delegando ETAPAs C+D aos atomos
  3, 4 e 5 da Skill 8 ATOMICA). Default OFF preserva 100% legacy = zero
  risco regressao. Canary REAL PROD do opt-in pendente proxima
  INDUSTRIALIZACAO_FB_LF natural (v26+ cleanup esvaziou candidatos).

  Usar atomos diretamente quando o pedido eh: "valida constants invoice X",
  "libera faturamento picking Y", "aguarda invoice do robo CIEL IT", "aplica
  G029+G007+G034 invoice Z", "transmite NF W via SEFAZ".

  Usar orchestrator quando o pedido eh: "executa onda completa de faturamento
  LF/CD/FB", "retoma faturamento travado em D apos crash", "smoke 1 ajuste
  end-to-end", "pre-flight cadastro fiscal antes de bulk".

  NAO USAR PARA:
  - Escrituracao ENTRADA (RecebimentoLf/DFe) -> Skill 7 escriturando-odoo
  - Picking generico (cancelar/validar/devolver fora pipeline) -> Skill 5
  - Transferencias internas pre-faturamento intra-empresa -> Skill 2
  - Recebimento de COMPRAS (DFe fornecedor 4 fases) -> gestor-recebimento
  - Cancelar NF SEFAZ-autorizada (processo formal 24h) -> NAO ha atomo
  - Lancar CTe / despesa extra -> integracao-odoo (LancamentoOdooService 16 etapas)

  `dry_run=True` eh o DEFAULT em cada atomo + no orchestrator CLI; atomo
  `transmitir_sefaz` em real-run exige `confirmar_sefaz=True` (2 nivel —
  IRREVERSIVEL).
allowed-tools: Read, Bash, Glob, Grep
---

# faturando-odoo (WRITE — Skill 8 ATÔMICA L2 v24+ + orchestrator C3 legacy)

Skill **ATÔMICA L2 LIVE v24+ (2026-05-27 AP6 refator)** com 5 átomos
componíveis sobre `account.move` + orchestrator C3 LEGACY **PIPELINE COMPLETO
A-F + RECOVERY + FLUXO L3 1.2.x LIVE v17.5+v18+v19+** (será migrado para usar
os 5 átomos via opt-in v25+).

Service ATÔMICA L2: `app/odoo/estoque/scripts/faturamento.py`
(FaturamentoInvoiceService, ~750 LOC, 28 pytest verdes — espelha pattern
Skill 7 ABRANGENTE v19+).
Orchestrator C3 LEGACY: `app/odoo/estoque/orchestrators/inventario_pipeline.py`
(renomeado de `faturamento_pipeline.py` em v27+ S3 — stub alias preservado;
FaturamentoPipelineExecutor, ~5600 LOC).
Service-fonte legado (COMPAT, NAO MEXER): `app/odoo/services/inventario_pipeline_service.py` (1346 LOC, minerado em §7.2 do planejamento).
Script-fonte macro (SUPERADO ao final v22+): `scripts/inventario_2026_05/09_executar_onda1_bulk.py` (1866 LOC, minerado em §7.3).

---

## 5 ÁTOMOS L2 (v24+ AP6 — espelha Skill 7 ABRANGENTE)

| # | Átomo | Pre-cond | Pos-cond | Idempotência |
|---|-------|----------|----------|--------------|
| 1 | `validar_invoice_constants(invoice_id, constants_esperadas, dry_run)` | account.move existe + campos suportados em CONSTANTS_CAMPOS_VALIDAVEIS | reporta divergencias (READ-only sempre) | n/a (READ-only) |
| 2 | `liberar_faturamento(picking_id, ajuste_ids, dry_run, confirmar)` | stock.picking state='done' (G019/G020) | action_liberar_faturamento disparado; robo CIEL IT criará invoice em 3-30min | Skill 5 LEGACY codifica (delegado a `StockPickingService.liberar_faturamento`) |
| 3 | `polling_invoice(picking_id, ajuste_ids, timeout_s, poll_interval_s, dry_run)` | picking ja com `liberar_faturamento` disparado | retorna invoice_id ou TIMEOUT | DELEGA `StockPickingService.aguardar_invoice_do_robo` (Skill 5 LEGACY) |
| 4 | `validar_invoice_pos_robo(invoice_id, ajuste_id_primeiro, perfil, dry_run, confirmar)` | account.move criada pelo robo CIEL IT | G029 + G007 + G034 aplicados via `_invoice_helpers` (perfil V1 'inventario-inter-company') | helpers idempotentes (checam estado pre-existente) |
| 5 | `transmitir_sefaz(invoice_id, ajuste_ids, max_tentativas, intervalo_retry, dry_run, confirmar_sefaz)` | account.move em F5d_INVOICE_GERADA + confirmar_sefaz=True | fase=F5e_SEFAZ_OK + chave_nfe propagada (D-OPS-2b) + status=EXECUTADO | D8.3 tripla (sem invoice_id / por invoice / por persistência) + CRITICAL-1 commit pós-SEFAZ |

**Gotchas codificados intra-átomo** (inviolaveis): G016 commit_resilient SSL drop · G019/G020 picking state='done' · G029 payment_provider_id=38 · G007 price_unit fallback · G034 DEV_* fiscal_position · D5 SNAPSHOT meta · D7 HARD_FAIL_CONFIG aborta batch · D8 idempotência tripla · D9 re-fetch via safe_session_get · CRITICAL-1 commit POS-Playwright falha = NAO conta sucesso · MED C-1 situacao_nf != 'autorizado' em erro_msg · MED C-2 cstat+xmotivo em falha.

**Composição típica** (1 ajuste end-to-end):

```python
from app.odoo.estoque.scripts.faturamento import FaturamentoInvoiceService
from app.odoo.estoque.scripts.picking import StockPickingService
from app.odoo.utils.connection import get_odoo_connection

odoo = get_odoo_connection()
picking_svc = StockPickingService(odoo=odoo)
svc = FaturamentoInvoiceService(odoo=odoo, picking_svc=picking_svc)

# 1. Validar pre-cond (opcional — orchestrator pode pular)
r1 = svc.validar_invoice_constants(
    invoice_id=716448,
    constants_esperadas={'fiscal_position_id': 25, 'l10n_br_tipo_pedido': 'industrializacao'},
)

# 2. Liberar faturamento (real-run exige confirmar=True)
r2 = svc.liberar_faturamento(
    picking_id=321600, ajuste_ids=[176013, 176014],
    ciclo='INVENTARIO_2026_05',
    dry_run=False, confirmar=True,
)

# 3. Polling do robo CIEL IT
r3 = svc.polling_invoice(
    picking_id=321600, ajuste_ids=[176013, 176014],
    timeout_s=1800, dry_run=False,
)
invoice_id = r3['invoice_id']

# 4. Aplicar G029+G007+G034
r4 = svc.validar_invoice_pos_robo(
    invoice_id=invoice_id, ajuste_id_primeiro=176013,
    ciclo='INVENTARIO_2026_05',
    dry_run=False, confirmar=True,
)

# 5. Transmitir SEFAZ (IRREVERSIVEL — exige confirmar_sefaz=True)
r5 = svc.transmitir_sefaz(
    invoice_id=invoice_id, ajuste_ids=[176013, 176014],
    ciclo='INVENTARIO_2026_05',
    dry_run=False, confirmar_sefaz=True,
)
# r5['chave_nfe'] = chave SEFAZ autorizada
```

**Status v24+**: 5 átomos LIVE + 28 pytest verdes. Orchestrator C3 LEGACY
ainda usa lógica inline (ETAPA C+D) em paralelo — refator profundo v25+ via
opt-in `--usar-skill8-atomica-v25` (canary primeiro, depois remove legacy).

---

## REGRAS CRITICAS

1. **`--dry-run` eh o DEFAULT.** Sem `--confirmar`, so calcula e mostra o plano.
2. **`--confirmar-sefaz` exigido para ETAPA D real-run** (IRREVERSIVEL — NF
   autorizada SEFAZ so cancela via processo formal 24h sem uso + declaracao).
3. **`--auto-confirma-direcao-nova` exigido para ETAPA F canary** DEV_FB_LF +
   TRANSFERIR_FB_CD (sem precedente PROD em v17.5; caminho B PALIATIVO).
4. **PRE-FLIGHT C5 obrigatorio** (sub-skill `auditando-cadastro-fiscal-odoo`
   `--perfil inventario`) — `--pular-pre-flight` so para pytest/smoke.
5. **Etapa = barreira de sincronizacao macro** (D11): `db.session.expire_all()`
   + re-load entre etapas; `db.engine.dispose()` profilatico antes/apos C+D.
6. **CR-H4 guard arquitetural**: ETAPA D bloqueada se ETAPA B falhou (anti-cascata).
7. **Sub-etapas D5/D7/D8/D9 codificadas** em ETAPA D (SNAPSHOT meta + HARD_FAIL_CONFIG
   aborta batch + idempotencia tripla F5e + safe_session_get pos-Playwright).
8. **NAO mexer no service externo `RecebimentoLfOdooService`** (4562 LOC, 37
   etapas — validados PROD; encapsulado pela Skill 7 atomo).
9. **NAO mexer no script `09_executar_onda1_bulk.py`** (regra v14a-ops — SUPERADO
   ao final do v22+ apos canary + bulk REAL PROD validados).

---

## MODOS DISPONIVEIS

### `--modo bulk` (default — pipeline A->F)
Executa etapas em sequencia, com barreira MACRO entre cada uma.
```
PRE-FLIGHT C5 -> A -> expire_all -> B -> expire_all -> C -> dispose -> D -> dispose -> E -> F
```
Aceita `--etapas A,B` para parar antes de C (smoke parcial). ETAPA D em
real-run exige `--confirmar-sefaz`. ETAPA F canary exige `--auto-confirma-direcao-nova`.

### `--modo pre-flight` (auditoria de cadastro fiscal)
Invoca sub-skill C5 `auditando-cadastro-fiscal-odoo` `--perfil inventario`
e retorna JSON sem entrar no pipeline. Use quando quiser checar cadastro
sem rodar nada.

### `--modo resume` (v18 — recovery iterativo)
Loop de `executar_pipeline_bulk(etapas=(apenas_etapa,))` ate' (a) pendentes==0
OU (b) detector_stagnation OU (c) max_iter atingido. Substitui scripts shell
`fat_lf_resume.sh` + `fat_lf_resume_entrada.sh`. Exige `--apenas-etapa B/C/D/E/F`.
Default `max_iter=18` + `detector_stagnation=True`. Recovery NAO re-roda
PRE-FLIGHT (custoso; ETAPAS B-F nao escrevem cadastro).

---

## Contrato — `FaturamentoPipelineExecutor.executar_pipeline_bulk` (entry-point principal)

```
objeto:        account.move (NF saida) + stock.picking (saida) + Playwright SEFAZ
               (compoe Skills 2 + 5 + 7 + servico Playwright)
input:         --ciclo NOME --etapas LISTA [--company-origem-id ID]
               [--cod-produto X] [--limite N] [--confirmar] [--confirmar-sefaz]
               [--auto-confirma-direcao-nova] [--pular-pre-flight]
output (JSON): {ciclo, etapas_solicitadas, pre_flight, etapas_executadas:
               {A: {...}, B: {...}, ...}, status, tempo_ms}
pre-condicoes: AjusteEstoqueInventario com status in (PROPOSTO, APROVADO)
               + acoes mapeadas em ACAO_PARA_DIRECAO
               PRE-FLIGHT C5 pode_faturar=True (ou --pular-pre-flight)
pos-condicoes: NF autorizada SEFAZ (chave_nfe gravada) + fase_pipeline avancada
               etapa a etapa + RecebimentoLf criado p/ ACOES_ENTRADA_FB
               + picking entrada manual destino criado p/ ACOES_ENTRADA_DESTINO_MANUAL
gotchas-invariante:
  - G011 timing CIEL IT (polling fire_and_poll)
  - G016 SSL drop (_commit_resilient + engine.dispose)
  - G018 weight=0 (l10n_br_peso_liquido fallback no atomo Skill 5)
  - G019/G020 picking state (validar() re-le state pos-button_validate)
  - G022 over-reservation (sleep 5s entre chunks ETAPA B)
  - G023 company_id forcado em moves (atomo Skill 5)
  - G034 fiscal_position DEV_* (corrigir_fiscal_setup F5d.7)
  - G035 barcode invalido (sub-skill C5 G035 pre-flight)
  - G037 (v18 REESCRITO Fase 0) picking ETAPA F criado MANUALMENTE sem PO precisa de `l10n_br_cfop_id` explicito (CAMINHO B PALIATIVO — refator v19+ remove). NAO se aplica ao fluxo normal account.move+PO+fiscal_position que continua informacional.
  - D-OPS-3 tracking='none' (atomo Skill 5 remove lot_name automaticamente)
  - D-OPS-5 produto sem lote (Skill 2 aceita_tracking_none=True)
  - HARD_FAIL_CONFIG_ERRORS aborta batch SEFAZ (D7)
modos:         dry-run default -> --confirmar (B/C/E/F) -> --confirmar-sefaz (D)
status:        EXECUTADO_OK | EXECUTADO_PARCIAL | DRY_RUN_OK | DRY_RUN_PARCIAL
               | BLOQUEADO_PRE_FLIGHT | FALHA_PRE_FLIGHT_CLI_AUSENTE
               | FALHA_PRE_FLIGHT_TIMEOUT | FALHA_USO
```

## Contrato — `FaturamentoPipelineExecutor.executar_pipeline_resume` (v18 — recovery)

```
objeto:        loop iterativo de executar_pipeline_bulk(etapas=(apenas_etapa,))
input:         --apenas-etapa B|C|D|E|F --max-iter 18 --timeout-iter 900
               [--sem-stagnation] [--confirmar] [--confirmar-sefaz] [demais flags do bulk]
output (JSON): {modo='resume', ciclo, apenas_etapa, max_iter, iteracoes_executadas,
               restantes_iniciais, restantes_por_iter: [{iter, restantes,
               status_bulk, tempo_ms}, ...], motivo_parada, ultima_invocacao_bulk,
               status, tempo_ms, erro?}
motivo_parada: TUDO_OK_INICIAL | TUDO_OK | STAGNATION | MAX_ITER | EXCECAO | FALHA_USO
pos-cond:     pendentes da etapa zerados (TUDO_OK) OU bloqueado (operador investiga)
```

---

## Receita 1: Canary 1 ajuste + Bulk onda + ETAPA F canary com flag

**Contexto v17.5+v18**: smoke end-to-end com 1 produto, depois bulk PROD,
e canary ETAPA F (caminho B PALIATIVO — refator v19+ extrair FLUXO L3 +
Skill 7 escriturando-odoo).

```bash
# 1. SMOKE dry-run 1 ajuste (pre-flight + A-F simulado)
source /home/rafaelnascimento/projetos/frete_sistema/.venv/bin/activate
set -a; . <(grep -E '^(DATABASE_URL|ODOO_)' \
  /home/rafaelnascimento/projetos/frete_sistema/.env); set +a

python -m app.odoo.estoque.orchestrators.inventario_pipeline \
  --ciclo INVENTARIO_2026_05 \
  --etapas A,B,C,D,E,F \
  --cod-produto 105000007 \
  --limite 1 \
  --pular-pre-flight  # smoke dispensa pre-flight C5

# Esperado: DRY_RUN_OK em ~1-2s; etapas_executadas mostra plano por etapa.

# 2. BULK real PROD onda completa (com pre-flight + 2 niveis confirmar)
python -m app.odoo.estoque.orchestrators.inventario_pipeline \
  --ciclo INVENTARIO_2026_05 \
  --company-origem-id 5 \
  --confirmar \
  --confirmar-sefaz \
  --auto-confirma-direcao-nova \
  --usuario operador_onda1

# Tempo estimado: A=segundos; B=minutos; C=15-30min (polling CIEL IT);
# D=5-10min/NF * N (Playwright SEFAZ); E=30-60min/invoice (G-RECLF-1);
# F=segundos/picking. Onda 100 ajustes: ~50-100h sequencial.

# 3. ETAPA F canary isolada (DEV_FB_LF + TRANSFERIR_FB_CD — PALIATIVO v17.5)
python -m app.odoo.estoque.orchestrators.inventario_pipeline \
  --ciclo INVENTARIO_2026_05 \
  --etapas F \
  --cod-produto 999999 \
  --confirmar \
  --auto-confirma-direcao-nova  # libera canary direcoes novas

# Esperado: picking manual criado via Skill 5 atomo
# `criar_picking_entrada_destino_manual` (CAMINHO B paliativo — caminho A
# correto fiscalmente seria via FLUXO L3 escriturar DFe que cria PO+picking
# nativo; refator v19+).
```

## Receita 2: Resume apos crash mid-ETAPA D (--modo resume --apenas-etapa D)

**Contexto v18**: Playwright SEFAZ travou (G016 SSL drop, robo CIEL IT lento,
crash mid-loop). Re-rodar ETAPA D em loop ate' todas NFs transmitidas OU
detector_stagnation parar (operador investiga).

```bash
# Loop ate 18 iter (default) ou TUDO_OK ou STAGNATION
python -m app.odoo.estoque.orchestrators.inventario_pipeline \
  --modo resume \
  --apenas-etapa D \
  --ciclo INVENTARIO_2026_05 \
  --max-iter 18 \
  --confirmar \
  --confirmar-sefaz

# Output JSON:
# {
#   "modo": "resume", "apenas_etapa": "D", "max_iter": 18,
#   "iteracoes_executadas": 5,
#   "restantes_iniciais": 50,
#   "restantes_por_iter": [
#     {"iter": 1, "restantes": 35, "status_bulk": "EXECUTADO_OK", "tempo_ms": 854312},
#     {"iter": 2, "restantes": 18, ...},
#     ...
#     {"iter": 5, "restantes": 0, ...}
#   ],
#   "motivo_parada": "TUDO_OK",
#   "ultima_invocacao_bulk": {...},
#   "status": "EXECUTADO_OK"
# }

# Exit code 0 = TUDO_OK; 1 = STAGNATION/MAX_ITER (operador investiga);
# 4 = DRY_RUN_OK.

# Variante: desligar stagnation detector (operador sabe que D tem timing
# irregular e quer mais chances)
python -m app.odoo.estoque.orchestrators.inventario_pipeline \
  --modo resume --apenas-etapa D --ciclo INVENTARIO_2026_05 \
  --sem-stagnation --max-iter 30 \
  --confirmar --confirmar-sefaz
```

## Receita 3: Resume mid-ETAPA E + F isoladas (RecebimentoLf + entrada manual)

**Contexto v18**: ETAPA E (Skill 7 RecebimentoLf X->FB) demora 30-60min/invoice
via robo CIEL IT (G-RECLF-1). Em onda 100 invoices = 50-100h sequencial.
Substitui `fat_lf_resume_entrada.sh` (E loop 30 iter + F loop 12 iter).

```bash
# ETAPA E: cria RecebimentoLf para PERDA_LF_FB / DEV_LF_FB / DEV_CD_LF / DEV_LF_CD.
# HIGH-3 RETOMA se status='processando' (anti-RecLf orfao por crash).
python -m app.odoo.estoque.orchestrators.inventario_pipeline \
  --modo resume --apenas-etapa E \
  --ciclo INVENTARIO_2026_05 \
  --max-iter 30 \
  --confirmar

# ETAPA F: picking entrada manual destino (G023) para INDUSTRIALIZACAO_FB_LF
# + canary DEV_FB_LF/TRANSFERIR_FB_CD com flag.
python -m app.odoo.estoque.orchestrators.inventario_pipeline \
  --modo resume --apenas-etapa F \
  --ciclo INVENTARIO_2026_05 \
  --max-iter 12 \
  --confirmar \
  --auto-confirma-direcao-nova  # opcional, libera canary

# Combinacao: rodar E ate' OK, depois F:
python -m app.odoo.estoque.orchestrators.inventario_pipeline \
  --modo resume --apenas-etapa E --ciclo INVENTARIO_2026_05 \
  --max-iter 30 --confirmar && \
python -m app.odoo.estoque.orchestrators.inventario_pipeline \
  --modo resume --apenas-etapa F --ciclo INVENTARIO_2026_05 \
  --max-iter 12 --confirmar --auto-confirma-direcao-nova
```

## Receita 5: FLUXO L3 1.2.x via `executar_fluxo_l3_1_2_x` (v19+ ABRANGENTE — caminho A ou B automatico)

**Contexto v19+**: substitui ETAPAS E+F legacy do `executar_pipeline_bulk`. Compoe
Skill 7 ABRANGENTE (7 atomos) + Skill 5 (`preencher_lotes_picking` + `validar`).
Decide caminho A vs B internamente via `buscar_dfe(chave_nfe_do_invoice_saida,
company_destino)`:

- **caminho A** (DFe ja veio via SEFAZ no destino): pula `criar_dfe_a_partir_do_invoice_saida`
  e segue direto para `escriturar_dfe → gerar_po → preencher_po → confirmar_po →
  preencher_lotes → validar → criar_invoice`. Tipico de PERDA_LF_FB,
  DEV_LF_FB, TRANSFERIR_CD_FB.
- **caminho B** (DFe ausente apos timeout): faz upload do XML autorizado da NF de
  SAIDA (`account.move.l10n_br_xml_aut_nfe`) para criar DFe no destino, dispara
  `action_processar_arquivo_manual`, depois segue passos identicos. Canonico para
  INDUSTRIALIZACAO_FB_LF (sentido reverso nao tem DFe SEFAZ automatico).

**Disparo direto (sessao v20+ canary REAL PROD)**:
```python
# Em PROD via Python (orquestrado por subagente gestor-estoque-odoo)
from app.odoo.estoque.orchestrators.inventario_pipeline import (
    FaturamentoPipelineExecutor,
)

executor = FaturamentoPipelineExecutor(db_session=db.session, odoo=odoo_conn)

# DRY-RUN primeiro (decide caminho + planeja todos passos)
plano = executor.executar_fluxo_l3_1_2_x(
    invoice_id_saida=607443,           # account.move da NF SAIDA SEFAZ-OK
    company_destino=5,                 # 1=FB, 4=CD, 5=LF
    l10n_br_tipo_pedido='serv-industrializacao',  # ou 'transf-filial'/'retorno'
    team_id=<TEAM>,                    # constants por company
    payment_term_id=<PT>,
    picking_type_id=<PT_ID>,
    payment_provider_id=38,            # G029
    lote_default='MIGRAÇÃO',
    poll_timeout_po_s=1800,
    poll_timeout_invoice_s=300,
    dry_run=True,                      # PRIMEIRO sempre dry-run
)
# plano['caminho'] ∈ {'A', 'B'}; plano['status'] = 'DRY_RUN_OK'
# plano['passos'] lista cada step + status + tempo_ms

# APOS REVISAO HUMANA EXPLICITA do plano:
real = executor.executar_fluxo_l3_1_2_x(
    invoice_id_saida=607443, company_destino=5, ...,
    dry_run=False,
)
# real['status'] = 'FLUXO_OK' ou 'FALHA_PASSO_<N>_<MOTIVO>'
# Posting da invoice (account.move.action_post) NAO faz parte — caller faz.
```

**Output keys**:
- `status`: `DRY_RUN_OK` | `FLUXO_OK` | `FALHA_PASSO_1_BUSCAR_DFE` |
  `FALHA_PASSO_2_CRIAR_DFE` | ... | `FALHA_PASSO_9_CRIAR_INVOICE`
- `caminho`: `'A'` | `'B'` | `'INDEFINIDO'`
- `dfe_id`, `po_id`, `picking_id`, `invoice_id`: ints (None em dry-run)
- `passos`: lista de `{passo, status, tempo_ms, erro}`
- `tempo_ms`, `erro`

**Idempotencia codificada**:
- Passo 1 (buscar_dfe) reusa DFe existente (nao cria duplicado)
- Passo 2 (criar_dfe) `IDEMPOTENT_EXISTE` quando DFe ja existe com mesma chave
- Passo 7 (preencher_lotes) `IDEMPOTENT_DONE` se picking ja em state='done'
- Passo 8 (validar) idem
- Passo 9 (criar_invoice) `IDEMPOTENT_EXISTE` se PO ja tem invoice

**Diferenca vs ETAPAS E+F legacy** (preservadas em paralelo ate canary v20+ OK):
| Aspecto | Legacy E+F (V1 STRICT) | FLUXO L3 1.2.x (v19+ ABRANGENTE) |
|---------|------------------------|----------------------------------|
| ETAPA E | Skill 7 atomo `criar_recebimento_orchestrado` (LF→FB only; raise NotImplementedError outras direcoes) | 7 atomos componiveis (qualquer direcao FB↔LF↔CD; dry-run-first) |
| ETAPA F | Skill 5 atomo `criar_picking_entrada_destino_manual` (CAMINHO B paliativo — bypassa motor Odoo, hardcoda CFOP via G037) | Caminho B usa `criar_dfe_a_partir_do_invoice_saida` + motor Odoo gera PO+picking nativo (CFOP derivado via fiscal_position) |
| Decisao A vs B | Manual (`--auto-confirma-direcao-nova` flag) | Automatico via `buscar_dfe` |
| Direcoes suportadas | LF→FB (E) + canary INDUSTR FB→LF / TRANSFERIR FB→CD (F com flag) | INDUSTRIALIZACAO_FB_LF, TRANSFERIR_CD_FB/FB_CD, PERDA_LF_FB, DEV_LF_FB/CD_LF/LF_CD/FB_LF (matriz inteira via constants) |
| Antipadrao | AP2 (orchestrator SAIDA cria picking de ENTRADA — viola fronteira) | AP2 reclassificado/resolvido v19+ (orchestrator delega via FLUXO L3) |

**Ativacao opt-in no `executar_pipeline_bulk` v20+** (S3 da sessao v20+): flag CLI
`--usar-fluxo-l3-v19` faz ETAPAS E+F do bulk invocarem `executar_fluxo_l3_1_2_x`
em vez do path legacy. Default `False` preserva 100% comportamento legacy =
zero risco regressao.

---

## Receita 4: Pre-flight isolado (--modo pre-flight, sub-skill C5 sem dispatch)

**Contexto**: Auditoria de cadastro fiscal antes de rodar pipeline. Operador
quer ver se ha bloqueios (NCM, barcode, weight) sem disparar SEFAZ.

```bash
python -m app.odoo.estoque.orchestrators.inventario_pipeline \
  --modo pre-flight \
  --ciclo INVENTARIO_2026_05

# Output JSON da sub-skill C5 (perfil 'inventario'):
# {
#   "status_global": "PRE_FLIGHT_WARN" | "PRE_FLIGHT_OK" | "PRE_FLIGHT_BLOQUEADO",
#   "pode_faturar": true | false,
#   "auditados": 158,
#   "bloqueios": {"ncm": [...], "barcode": [...], "weight": [...]},
#   "warnings": {...},
#   "tempo_ms": 987
# }

# Exit code 0 = PRE_FLIGHT_OK ou WARN; 1 = BLOQUEADO (corrigir cadastro antes).

# Variante: sub-skill C5 com auto-fix barcode (G035)
python .claude/skills/auditando-cadastro-fiscal-odoo/scripts/auditar_cadastro_inventario.py \
  --ciclo INVENTARIO_2026_05 \
  --auto-corrigir-barcode  # opcional, escreve product.barcode=False
```

---

## TRADE-OFFS V1 ACEITOS

| Trade-off | Razao | Mitigacao |
|-----------|-------|-----------|
| **ETAPA E SEQUENCIAL** | Decisao 10.7 v17 (Rafael 2026-05-25): `RecebimentoLfOdooService` NAO eh thread-safe (Redis state interno). | Recovery via `--modo resume --apenas-etapa E` + HIGH-3 retoma. Aceito 50-100h/onda. |
| **ETAPA D Playwright serial** | 1 browser global SSW; G016 SSL drop frequente. | `--modo resume --apenas-etapa D --max-iter 18` + idempotencia tripla F5e. |
| **PRE-FLIGHT C5 via subprocess** | Sub-skill C5 eh CLI separado (perfis multiplos: inventario, futuro venda-cliente). | Tradeoff: env=os.environ.copy() + sys.executable preserva venv. |
| **ETAPA F canary direcoes novas** (DEV_FB_LF + TRANSFERIR_FB_CD) | Sem precedente PROD em v17.5. PT 50 CD/IN/INTER descoberto via audit. | Flag `--auto-confirma-direcao-nova` bloqueia em real-run sem confirmacao explicita; dry-run sempre planeja todas. |
| **MIGRACAO -> INV-{cod}-{YYYYMMDD} lote na entrada manual** | Lote MIGRACAO eh agregador; entrada manual cria lote real por dia + cod. | Idempotente por dia; pickings de mesmo dia mesmo cod reusam lote. |
| **`--timeout-iter` NAO eh ENFORCADO em v18** (CR v18 F3) | Parametro existe no CLI + assinatura do `executar_pipeline_resume`, mas NAO eh propagado para `executar_pipeline_bulk` (que nao tem timeout). Operador que passa `--timeout-iter 300` esperando 5min/iter NAO ganha enforcement. | Operador deve usar `timeout NNN python -m ...` do shell Linux para enforcement real. Enforcement via threading pendente refator v19+. |
| **stdout mistura logs Flask + JSON** (CR v18 F4) | `app/__init__.py` + extensoes escrevem logs em stdout durante setup ("✅ Tipos PostgreSQL...", "✅ Modulo HORA registrado..."); JSON final tambem vai para stdout via `print(json.dumps(result))`. Aceitavel para operador humano (le terminal). CRITICO se Skill 8 for invocada via subprocess por outra skill (parser JSON quebra em logs pre-JSON). | Operador: `python -m ... 2>/dev/null \| tail -N \| jq` OU redirecionar arquivo direto. Para subprocess futuro: configurar logs em stderr OU adicionar `--quiet` flag (pendente v19+). |
| **CR-H4 guard ETAPA D NAO se aplica em --modo resume isolado** (CR v18 F2) | `executar_pipeline_bulk` tem CR-H4 que aborta ETAPA D se ETAPA B falhou. Mas `--modo resume --apenas-etapa D` chama bulk com `etapas=(D,)` — B nao esta no caminho, CR-H4 nao avalia. | OK em pratica: `executar_etapa_d` filtra `fase_pipeline=[F5d_INVOICE_GERADA, F5e_FALHA]`. Ajustes em fase pre-D (None/TRANSF/F5a/F5b/F5c) sao ignorados — recovery so processa ajustes ja com invoice. Operador deve rodar `--modo bulk --etapas A,B,C,D` antes de tentar resume D. |

---

## ANTIPADROES DETECTADOS — STATUS v19+ (rastreamento; constituicao §6.5 CLAUDE.md estoque eh fonte canonica)

> Documentado para que sessoes futuras nao reintroduzam. Status detalhado +
> causa-raiz + como evitar = `app/odoo/estoque/CLAUDE.md` §6.5.

### Antipadrao 1: Skill 7 V1 STRICT (raise NotImplementedError) ✅ RESOLVIDO v19+
- Atomo `EscrituracaoLfService.criar_recebimento_orchestrado` raise se cnpj!=LF
  OU company_recebedor!=FB. Limitava Skill 7 a 1 direcao.
- **RESOLUCAO v19+ (2026-05-26)**: 7 atomos ABRANGENTES criados em
  `app/odoo/estoque/scripts/escrituracao.py` (`buscar_dfe`,
  `criar_dfe_a_partir_do_invoice_saida`, `escriturar_dfe`, `gerar_po_from_dfe`,
  `preencher_po`, `confirmar_po`, `criar_invoice_from_po`). Cada atomo eh
  dry-run-first + versatil (qualquer direcao FB↔LF↔CD). Wrapper V1 STRICT
  permanece como museum vivo deprecado v20+ para preservar ETAPA E legacy.
  22 pytest mockados verdes.

### Antipadrao 2: ETAPA F orchestrator cria picking manual via Skill 5 ⚠️ RECLASSIFICADO v19+
- ETAPA F invoca `criar_picking_entrada_destino_manual` (Skill 5) que cria
  picking SEM PO + partner_id.
- **CAUSA RAIZ REAL (descoberta v19+)**: Skill 8 (`faturando-odoo`) = SAIDA.
  Criar picking de ENTRADA dentro de ETAPA F viola fronteira fiscal Skill 7/8.
  A explicacao anterior ("DFe demora paliativo") foi sintoma, nao causa.
- **RESOLUCAO PARCIAL v19+**: 2 folhas L3 escritas (1.2.1 + 1.2.2) + metodo
  `executar_fluxo_l3_1_2_x` no orchestrator (Receita 5 acima). Caminho B
  correto = upload XML SAIDA + motor Odoo gera picking nativo. Tampao Skill 5
  v15a `criar_picking_entrada_destino_manual` marcada DEPRECATED docblock
  (museum vivo ate canary v20+ remover). ETAPAS E+F legacy preservadas
  funcionais (nao quebrar baseline 555 pytest).
- **PENDENTE v20+**: opt-in `--usar-fluxo-l3-v19` (S3) faz bulk invocar
  `executar_fluxo_l3_1_2_x` em vez do path legacy. Apos canary REAL PROD
  validar: remove ETAPAS E+F legacy + remove `criar_picking_entrada_destino_manual`.

### Antipadrao 3 (relacionado): orchestrator chama skill atomo INLINE ✅ RESOLVIDO v18
- v17.5 ETAPA F chama Skill 5 atomo direto -> viola §6 "Fluxo >> Skill"
- v17.5 ETAPA E chama Skill 7 atomo direto -> viola §6
  (menos grave que v17 inline ~420 LOC; mas ainda violacao)
- **RESOLUCAO v18 (Fase 0)**: §6 CLAUDE.md reorganizado em 3 tabelas distintas
  (Skills L2 / Orchestrators C3 / Fluxos L3). §3.1 explicita "Orchestrator C3
  NAO eh skill". v19+ adiciona FLUXO L3 1.2.1/1.2.2 + metodo orchestrator
  `executar_fluxo_l3_1_2_x` seguindo pattern correto (orchestrator compoe via
  FLUXO, nao inline).

### Antipadrao 4: V1 STRICT pre-cond ANTES de dry-run check ✅ RESOLVIDO v19+
- Skill 7 raise NotImplementedError mesmo em `dry_run=True`. Operador nao
  conseguia planejar CD→FB hipotetico.
- **RESOLUCAO v19+**: 7 atomos novos da Skill 7 ABRANGENTE seguem dry-run-first
  — pre-cond LEVES (sintaticas) retornam `{status: 'FALHA', erro: '...'}`
  sem raise; pre-cond pesadas (que dependem de Odoo) APENAS no caminho write.
  Mesmo pattern em Skill 5 `preencher_lotes_picking`.

### Antipadrao 5: Criar gotcha sem ler docstrings de CONSTANTS ✅ RESOLVIDO v18

### Antipadrao 6: Confusao nomenclatura "Skill 8 = orchestrator C3" vs atomo L2 ⏳ PENDENTE v20+ (S4)
- Catalogo §6 Tabela 2 cataloga `faturando-odoo` como orchestrator C3 (~4400 LOC)
  + tem fachada SKILL.md fingindo ser skill L2. Definicao correta:
  - **Skill 8 ATOMICA L2** (`faturando-odoo` correto): 5 operacoes sobre
    `account.move` — validar constants + `action_liberar_faturamento` + polling +
    validar fatura vs constants + SEFAZ Playwright.
  - **`inventario_pipeline` C3** (renomeado de `faturamento_pipeline.py` em
    v27+ S3 — stub alias compat preservado): orchestrator pipeline A-F +
    recovery + dispatch fluxo L3 1.2.x + opt-in skill8 atomica v25+ S1.
- **REFATOR v20+ (S4 desta sessao)**: extrai metodo `executar_skill8_atomica`
  do orchestrator + atualiza §6 Tabela 1 (Skills L2) com nova entry + renomeia
  Tabela 2 entry para `inventario_pipeline`.

---

## CROSS-REFS

- Constituicao: `app/odoo/estoque/CLAUDE.md` §6 (catalogo Skill 8)
- Planejamento Skill 8 MACRO: `app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md`
  (sobrevive N sessoes; REGRA INVIOLAVEL 0 = ler INTEIRO antes de mexer)
- Roadmap migracao: `app/odoo/estoque/ROADMAP_SKILLS.md` HANDOFF v18
- Subagente: `.claude/agents/gestor-estoque-odoo.md` (atualizar com Skill 8)
- ROUTING_SKILLS: `.claude/references/ROUTING_SKILLS.md` (entry Skill 8)
- tool_skill_mapper: `app/agente/services/tool_skill_mapper.py`
- Skill 7 par (entrada): `.claude/skills/escriturando-odoo/SKILL.md`
- Sub-skill C5 PRE-FLIGHT: `.claude/skills/auditando-cadastro-fiscal-odoo/SKILL.md`
- Skill 5 atomos inter-company: `.claude/skills/operando-picking-odoo/SKILL.md`
- Skill 2 v2 ETAPA A: `.claude/skills/transferindo-interno-odoo/SKILL.md`
- Service-fonte legado (COMPAT): `app/odoo/services/inventario_pipeline_service.py`
- Script-fonte SUPERADO ao final: `scripts/inventario_2026_05/09_executar_onda1_bulk.py`
- Scripts shell substituidos pelo --modo resume: `scripts/inventario_2026_05/fat_lf_resume.sh`
  + `scripts/inventario_2026_05/fat_lf_resume_entrada.sh`
- Gotchas Odoo: `.claude/references/odoo/GOTCHAS.md` (referencia rapida) +
  `docs/inventario-2026-05/02-gotchas/` (G011, G016, G018, G019,
  G020, G022, G023, G034, G035, G036, G037 NOVO v18, D-OPS-3, D-OPS-5)
- IDs fixos: `.claude/references/odoo/IDS_FIXOS.md` (PT 19 LF/IN, PT 50 CD/IN/INTER,
  PT 53 FB/Exped/Industr)

---

## CHECKLIST DE EXPANSAO — V19+ ENTREGUE / V20+ PENDENTE

### ✅ ENTREGUE em v19+ (2026-05-26, commit 8670e08d)
- [x] Refatorar Skill 7 ABRANGENTE — 7 atomos extraidos via mineracao Explore
      do `RecebimentoLfOdooService` (NAO MEXER — service externo) sem tocar
      o codigo-fonte: `buscar_dfe`, `criar_dfe_a_partir_do_invoice_saida`,
      `escriturar_dfe`, `gerar_po_from_dfe`, `preencher_po`, `confirmar_po`,
      `criar_invoice_from_po`. 22 pytest mockados verdes.
- [x] Criar atomo Skill 5 `preencher_lotes_picking(picking_id, lotes_data, lote_default)`.
      7 pytest mockados verdes.
- [x] Criar FLUXO L3 `1.2.1-escriturar-dfe-industrializacao.md` (caminho A —
      DFe ja veio via SEFAZ).
- [x] Criar FLUXO L3 `1.2.2-criar-dfe-manual-transferencia.md` (caminho B —
      DFe via upload XML da SAIDA; substitui tampao Skill 5 v15a deprecado).
- [x] Metodo `FaturamentoPipelineExecutor.executar_fluxo_l3_1_2_x` no orchestrator
      (composicao dos atomos via fluxo L3; decide A vs B via `buscar_dfe`).
      4 pytest dispatch verdes.
- [x] `criar_picking_entrada_destino_manual` (Skill 5 v15a) marcada DEPRECATED
      docblock (museum vivo ate canary v20+).
- [x] Antipadroes AP1+AP3+AP4+AP5 resolvidos; AP2 reclassificado com causa
      real; AP6 NOVO (nomenclatura) documentado.

### ⏳ PENDENTE em v20+ (canary REAL PROD + opt-in + refator nomenclatura)
- [ ] Canary REAL PROD do FLUXO L3 1.2.x via subagente `gestor-estoque-odoo`
      em 1 caso INDUSTRIALIZACAO_FB_LF (caminho B — primeiro a validar).
- [ ] Opt-in CLI `--usar-fluxo-l3-v19` no `executar_pipeline_bulk`: quando
      flag=True, ETAPAS E+F invocam `executar_fluxo_l3_1_2_x` em vez do
      path legacy. Default=False preserva comportamento legacy (zero
      risco regressao). 2-3 pytest mockados dispatch.
- [ ] Refator AP6 (S4): extrair metodo `executar_skill8_atomica` do orchestrator
      (5 operacoes C+D sobre `account.move`) + atualizar §6 catalogo do
      CLAUDE.md estoque (Tabela 1 ganha Skill 8 ATOMICA L2; Tabela 2 renomeia
      orchestrator para `inventario_pipeline`).
- [ ] DeprecationWarning runtime em `criar_recebimento_orchestrado` (V1 STRICT
      wrapper) — fim de vida em v21+ ou v22+ apos mais 1 ciclo validacao.

### ⏳ PENDENTE em v21+ (galho 1.1 e 1.3 — refator nomenclatura AP6 destrava)
- [ ] Criar FLUXO L3 `1.1.x` (so faturamento — saida pura) compondo
      Skill 8 ATOMICA L2 + Skill 2 + Skill 5.
- [ ] Criar FLUXO L3 `1.3-transferencia-completa.md` (saida + entrada;
      compondo galho 1.1 + galho 1.2.x).
- [ ] Apos canary + bulk REAL PROD do fluxo L3 v19+: remover ETAPAS E+F
      legacy + remover `criar_picking_entrada_destino_manual` + remover
      wrapper V1 STRICT.

### ⏳ PENDENTE sem prazo definido
- [ ] Criar FLUXO L3 `1.5-lancar-frete-cte.md` (provar reuso atomos
      cross-modulo — fretes/CTe).
- [ ] Criar FLUXO L3 `1.6-lancar-despesa-extra.md`.
- [ ] Eventualmente: refatorar parcial `RecebimentoLfOdooService` (NAO MEXER
      regra v14a-fix) + `LancamentoOdooService` (NAO MEXER regra v19+) para
      virarem WRAPPERS dos atomos Skill 7 (inversao da relacao).
- [ ] CLI wrapper `.claude/skills/faturando-odoo/scripts/faturar.py`
      (entry-point Python wrapping orchestrator com helpers de smoke/canary/resume
      + JSON unico stdout — atualmente invocacao via `python -m
      app.odoo.estoque.orchestrators.inventario_pipeline`).
