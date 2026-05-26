# PLANEJAMENTO — Skill 8 `faturando-odoo` (MACRO C3 SEFAZ)

**Criado:** 2026-05-25 v13 | **Audiencia:** Claude Code + agente web (orquestrador-Odoo) | **Sobrevive:** N sessoes

> **PROPOSITO:** documento vivo de planejamento que persiste o ESCOPO + CHECKPOINTS + DECISOES + PROGRESSO da capinagem da Skill 8 (`faturando-odoo`) — a MACRO C3 mais perigosa do roadmap (NF inter-company → robo CIEL IT → SEFAZ irreversivel). Atualizar a CADA sessao que toque esta skill.

> **REGRA INVIOLAVEL 0 (fundadora deste arquivo):** ANTES de qualquer modificacao em codigo da Skill 8, LER este arquivo INTEIRO + atualizar o checkpoint ativo. Sem isso, risco de regressao e perda de contexto entre sessoes e' inaceitavel para SEFAZ irreversivel.

---

## 0. CABECALHO DE ESTADO (atualizar a cada sessao)

| Campo | Valor |
|-------|-------|
| **Status global** | 🟡 ORCHESTRATOR + ETAPAS A/B/C + G014 LIVE v16 (C6/C7/C8/C9/**C10/C10.2/C10.3** + 9 fixes 2 reviewers paralelos; ETAPAS D/E/F stubs v17) |
| **Sessao atual** | v16 (2026-05-25) — **C10 ETAPA C F5d + C10.2 ETAPA A real + C10.3 G014 pre-check + 9 fixes 2 reviewers paralelos**: (1) `_invoice_helpers.py` NOVO ~430 LOC com 3 helpers F5d.5/.6/.7 (G029 payment_provider, G034 fiscal_setup DEV_*, G007 price_zero) com perfil V1 'inventario-inter-company' (outros perfis raise NotImplementedError — Rafael v16 evita inline contaminando logica generica). (2) ETAPA C real (`_executar_etapa_c` substitui stub NOT_IMPLEMENTED_v15b): polling 1800s/40s + SNAPSHOT meta + safe_session_get + sub-etapas .5/.6/.7 try/except + fase F5d_INVOICE_GERADA + invoice_id_odoo + external_id_operacao (F12 v15c pattern). (3) ETAPA A real (substitui guard NotImplementedError por Skill 2 v2 `transferir_quantidade_para_lote_v2`, filtra ACOES_LOTE = {RENOMEAR_LOTE, TRANSFERIR_LOTE} — escopo disjunto de ACOES_PICKING). (4) G014 pre-check (`_g014_pre_check_lotes_vencidos`) detecta lotes vencidos com saldo livre + migra via Skill 2 v2 para lote novo `INV-{cod}-{YYYYMMDD}` ANTES de criar picking. **2 reviewers paralelos: 9 findings (4 CRIT+5 HIGH) — TODOS aplicados**: R1F1 (CRIT 95) validar perfil pre-polling + R2F1 (CRIT 92) guard situacao_nf em `garantir_payment_provider` fallback + R2F2 (CRIT 88) incluir 'enviado' nos guards + R1F4 (HIGH 82) substituir `datetime.utcnow()` (banido) por `agora_utc_naive` + R2F3 (HIGH 85) guard situacao_nf em `corrigir_price_zero` + R2F4 (HIGH 80) `garantir_fiscal_setup` retorna True com SKIP_GUARD_SITUACAO_NF + R2F5 (HIGH 83) DEV_FB_LF SKIP_NAO_MAPEADO auditavel + R1F2 (HIGH 88) G014 partial failure marca cod falha + R1F3 (HIGH 85) commit_resilient False -> continue. **483 pytest verdes** (+11 v16: 5 ETAPA C + 4 ETAPA A + 4 G014). Smoke PROD: cod 105000007 detecta 4 pickings F5c_LIBERADO (317346/317516/317517/317518) em ETAPA C dry-run 766ms. MIN seguranca SEFAZ ALCANCADO (F1 idempotencia + R2F1/F2/F3 guards situacao_nf garantem que re-execucoes NAO invalidam chaves autorizadas/enviadas). |
| **Sessoes estimadas** | 4-5 sessoes restantes (v17 → v20+) — F5e/E/F + recovery + canary + bulk PROD |
| **Baseline pytest atual** | 483 verdes (tests/odoo/ — v16 em 15.51s; 472 baseline v15c + 11 v16) |
| **Baseline pytest pos-v20 esperado** | ≥490 verdes (+~25 testes restantes Skill 8 F5d/F5e/E/F + recovery) |
| **Branch** | `feat/estoque-odoo` (worktree `/home/rafaelnascimento/projetos/frete_sistema_estoque_odoo`) |
| **Service-fonte** | `app/odoo/services/inventario_pipeline_service.py` (1.346 LOC) — minerado v13 §7.2 (D1-D9) |
| **Script-fonte macro** | `scripts/inventario_2026_05/09_executar_onda1_bulk.py` (1866 LOC) — minerado v14a §7.3 (D10-D18 + compensatorio + G014) |
| **Service externo** | `app/recebimento/services/recebimento_lf_odoo_service.py` (4562 LOC, 37 etapas em 7 fases) — minerado v14a-fix §7.4 (G-RECLF-1 a G-RECLF-11) — **NAO MEXER** |
| **Pattern de reuso** | `app/odoo/estoque/orchestrators/pre_etapa_executor.py` (Skill 6 v9, 907 LOC) |
| **Destino do orchestrator** | `app/odoo/estoque/orchestrators/faturamento_pipeline.py` (a criar v15b) |
| **Sub-skill C5 service** | `app/odoo/estoque/scripts/cadastro_fiscal_audit.py` (~430 LOC) — capinado v14b a partir de `validar_cadastro_fiscal` no script 09 + gtin_validator.py + queries D-OPS-2 |
| **Decisoes ABERTAS** | 1 (paralelismo ETAPA E — G-RECLF-1, decidir em v17) — 6 RESOLVIDAS em v13 + R1 INTACTA + ETAPA F via Skill 5 v14a-fix + G035 V1 RESOLVIDO em v14b |
| **Checkpoints concluidos** | 6 de 24 (C1 ✅ pre-mortem + C2 ✅ mineracao service + C3 ✅ mineracao script v14a + C4 ✅ escopo + C5 ✅ sub-skill auditando-cadastro-fiscal-odoo v14b + **C6.5 ✅ Skill 5 estendida com 3 atomos inter-company v15a**) |
| **Skills NOVAS criadas pela Skill 8** | (1) `auditando-cadastro-fiscal-odoo` ✅ V1 inventario LIVE (v14b); (2) **3 atomos NOVOS na Skill 5** `operando-picking-odoo` ✅ LIVE (v15a) — `criar_picking_inter_company` codifica D-OPS-3 · `validar_picking_inter_company` fluxo F5b + G018 · `criar_picking_entrada_destino_manual` ETAPA F G023 + idempotencia origin |
| **Fixes a Skill 2 (helper)** | **D-OPS-5 ✅ FIXADO em v14b** — `_listar_quants_origem` aceita `aceita_tracking_none=True` default + atomo `transferir_para_indisponivel` valida `product.tracking` quando `lot_id_origem=None`; 9 pytest novos; canary PROD em cod 208000043 sem lote validado em ~1.5s + reversão |
| **Pattern arquitetural FINAL** | **Etapa = barreira de sincronizacao** (MACRO: A→expire_all+re-load→B→...→F com `db.engine.dispose()` profilatico antes/apos C+D + serializa Playwright F5e vs step_23 RecebimentoLfOdoo G-RECLF-9). Mitiga DetachedInstanceError + SSL drop. **Sub-nuance MICRO ETAPA B** (D16): pipeline por picking com sleep 5s (G022 mitigation) — NAO paraleliza N pickings entre si. **ETAPA F via Skill 5** (Fluxo>>Skills mantido). **PRE-FLIGHT via sub-skill C5** (Skill 8 v15+ chama subprocess `auditar_cadastro_inventario.py --ciclo X --perfil inventario`). |
| **Demanda real associada** | Casos em todas as direcoes (Rafael v13) — a estruturar nas sessoes posteriores |

---

## 1. VISAO MACRO

### 1.1 O que e' a Skill 8

Orquestrador C3 que executa o pipeline completo de **faturamento inter-company de inventario** (Onda 1 LF, Onda 2 FB/CD, etc.). Compoe:
- **Skill 5** (`operando-picking-odoo`) — criar/validar pickings
- **Skill 1** (`ajustando-quant-odoo`) — ajustes pontuais residuais
- **Skill 2** (`transferindo-interno-odoo`) — transferencias internas pre-faturamento (Etapa A)
- **Robo CIEL IT** (XML-RPC) — cria invoice account.move a partir do picking validado
- **Playwright SEFAZ** — transmite NF-e (irreversivel)

Resulta em: NFs autorizadas pela SEFAZ + saldo de estoque ajustado em ambas as filiais + RecebimentoLf criado para PERDA/DEV LF→FB + entrada manual para INDUSTR FB→{LF,CD} (G023).

### 1.2 Por que e' a MACRO mais perigosa

| Dimensao | Risco |
|----------|-------|
| **SEFAZ irreversivel** | NF autorizada com chave 35 digitos so' pode ser cancelada via processo formal (24h, sem uso, declaracao). Erro = problema fiscal real. |
| **Robo CIEL IT externo** | Modulo XML-RPC de terceiros (`l10n_br_ciel_it_account`) — timing imprevisivel (3-5min madrugada, 5-10min manha, >2h pico). Sem SLA. |
| **Playwright SEFAZ** | Loop serial 1 browser, 5-10min/NF, susceptivel a SSL drop (G016) + crash mid-loop. |
| **Estado distribuido** | DB local (AjusteEstoqueInventario.fase_pipeline) + Odoo (stock.picking.state + account.move.state + l10n_br_situacao_nf) + RecebimentoLf — desincronia gera bloqueio. |
| **6 etapas sequenciais com dependencia** | A→B→C→D→E→F. Falha em D bloqueia E/F. Recovery exige idempotencia rigorosa. |
| **Volume** | Ondas tipicas: 100-700 ajustes/batch. Erro em qty=0 ou price=0 rejeita todo o lote (G007). |

### 1.3 Material existente (inventario)

**Service**: `inventario_pipeline_service.py` (1.346 LOC) — implementa F5a-F5e:
- F5a `criar_pickings` (L581)
- F5b `validar_pickings` (L774)
- F5c `liberar_faturamento` (L882)
- F5d `aguardar_invoices` (L945) com sub-etapas F5d.5 (payment_provider), F5d.6 (price zero), F5d.7 (fiscal setup DEV)
- F5e `transmitir_sefaz` (L1116)
- Helpers: `_commit_with_retry` (L165, G016), `_garantir_payment_provider` (L204, G029), `_garantir_fiscal_setup` (L293, G034), `_corrigir_price_zero_em_invoice` (L401, G007), `_registrar_op` (L523, auditoria)
- 29 pytest verdes em `tests/odoo/services/test_inventario_pipeline_service.py`

**Script-fonte macro**: `09_executar_onda1_bulk.py` (~1.850 LOC) — 6 etapas A-F:
- **A** `etapa_a_transferencias_lote` (L501) — internas pre-faturamento (DELEGAVEL Skill 2)
- **B** `etapa_b_pickings` (L624) — chama F5a/F5b/F5c
- **C** `etapa_c_aguardar_invoices` (L1156) — chama F5d
- **D** `etapa_d_sefaz` (L1197) — chama F5e (IRREVERSIVEL)
- **E** `etapa_e_entrada_fb` (L1239) — cria RecebimentoLf X→FB
- **F** (inline) — picking entrada manual FB→{LF,CD} (G023)

**Scripts ad-hoc relacionados** (15 vivos em `scripts/inventario_2026_05/`):
- `09_executar_onda1_bulk.py` (macro)
- `09c_executar_onda2_fb_cd.py` (Onda 2)
- `fat_lf_00_preflight.py` (read-only, 4 perguntas decisivas)
- `fat_lf_01_stock_audit.py` (audit estoque LF pre-fat)
- `fat_lf_02_carregar.py` (load Excel → DB)
- `fat_lf_03_prestage.py` (valida cadastro fiscal: NCM, weight, barcode)
- `fat_lf_04_executar.py` (executor antigo)
- `fat_lf_05_executar_clean.py` (executor atual, usado pelos resume scripts)
- `fat_lf_06_consolidar_validos.py` (consolida pos-execucao)
- `fat_lf_cleanup.py` (cleanup orfaos)
- `fat_lf_diag.py` (diag estado)
- `fat_lf_inspect_invoice.py` (inspect invoices CIEL IT)
- `fat_lf_resume.sh` (recovery B→D loop)
- `fat_lf_resume_entrada.sh` (recovery E + F loop)
- `debug_sefaz_608607.py` (debug NF rejeitada)

**Constantes ja centralizadas** (`app/odoo/constants/`):
- `MATRIZ_INTERCOMPANY` (operacoes_fiscais.py) — 8 acoes_decididas + CFOPs
- `PICKING_TYPE_POR_DIRECAO` + `LOCATION_DESTINO_*` (picking_types.py)
- `COMPANY_LOCATIONS` (locations.py) — FB=8, CD=32, LF=42
- `PAYMENT_PROVIDER_SEM_PAGAMENTO=38`, `CARRIER_NACOM=996`, `INCOTERM_CIF=6` (ids_diversos.py)
- `CODIGO_PARA_COMPANY_ID = {'FB': 1, 'CD': 4, 'LF': 5}`
- `COMPANY_PARTNER_ID` (CD=34 = partner_id, distinto de company_id=4)
- ⚠️ **NAO centralizados ainda:** journals fiscais (VND=847, SARET=1002, RRET=987) — so' em comentarios

### 1.4 Material existente (galho 1.x dos fluxos)

- `app/odoo/estoque/fluxos/README.md` lista galho 1.1 (so' faturamento) e galho 1.3 (transf completa = faturando ⨾ escriturando) com status ⬜ (a escrever).
- **Nenhuma folha `1.1*.md` ou `1.3*.md` criada ainda.**

---

## 2. ESCOPO (decisao do Rafael v13 — "estruturar bem, depois rodar casos reais")

### 2.1 Estrategia escolhida

**Pipeline COMPLETO A-F** capinado em N sessoes (~6-8 sessoes), com checkpoints persistentes. Estruturar TUDO antes de tocar caso real PROD. Razao: Skill 8 nao admite mudanca incremental incompleta (estado de rabo entre sessoes bloqueia recovery).

### 2.2 Entra no escopo (FAZ parte da Skill 8)

| Categoria | Itens |
|-----------|-------|
| **Etapas pipeline** | F5a, F5b, F5c, F5d (com sub-etapas .5/.6/.7), F5e |
| **Etapas adjacentes** | E (RecebimentoLf X→FB), F (entrada manual FB→{LF,CD} G023) |
| **Recovery** | Loop com idempotencia por `fase_pipeline` + timeout/iteracao + stagnation detector |
| **SSL/timeout** | G016 commit_with_retry + re-fetch ajuste + TCP keepalive |
| **Auditoria** | `OperacaoOdooAuditoria.registrar` por etapa+ajuste+uuid8 |
| **Paralelizacao** | `ThreadPoolExecutor + Semaphore(max_concurrent=5)` (preservar do service atual) |
| **Pre-flight inventario** | INVOCA a sub-skill `auditando-cadastro-fiscal-odoo --perfil inventario` ANTES do bulk (sem implementar diretamente) |
| **Modos CLI** | `--canary` / `--bulk` / `--resume` / `--etapa A\|B\|C\|D\|E\|F` (NAO inclui `--pre-flight` — esta na sub-skill) |
| **Folha de fluxo** | `app/odoo/estoque/fluxos/1.1-faturamento-completo.md` + `1.3-transferencia-completa.md` |
| **SKILL.md** | Com 5+ receitas (canary, bulk, resume, recovery NF travada, integracao com pre-flight) |
| **Tests** | Pytest `tests/odoo/services/test_faturamento_pipeline_orchestrator.py` (>20 testes) |

### 2.3 Sai do escopo (DELEGADO)

| Categoria | Para onde |
|-----------|-----------|
| **Etapa A** (transferencias internas pre-faturamento) | Skill 2 `transferindo-interno-odoo` ✅ |
| **Picking generico** (cancelar, validar, devolver fora do pipeline) | Skill 5 `operando-picking-odoo` ✅ |
| **Reservas / cirurgia ML orfa** | Skill 2.4 `operando-reservas-odoo` 🟡 |
| **Ajustes positivos puros** (etapa de planejamento) | Skill 6 `planejando-pre-etapa-odoo` 🟡 |
| **Pre-flight (G017 NCM + G035 barcode + G018 weight) + futuros perfis** | **Sub-skill nova `auditando-cadastro-fiscal-odoo`** (DECISAO 10.5 v13 — Rafael) ⬜ |
| **Recebimento de COMPRAS** (DFe fornecedor, NAO inventario) | gestor-recebimento (subagente) |
| **Reconciliacao financeira** (CNAB, extrato) | auditor-financeiro (subagente) |
| **Centralizacao de journals** (847/1002/987) | Tarefa ortogonal — pode entrar em C6 ou ficar para Skill 7 (escriturando) |

### 2.4 NAO-objetivos

- Refatorar Skill 5 para absorver F5a/F5b — pattern atual paralelo no service e' eficiente; over-refactoring quebraria.
- Implementar transmissao SEFAZ via API REST (Playwright e' o padrao validado).
- Substituir robo CIEL IT (modulo externo de terceiros — fora do escopo).
- Cancelar NFs SEFAZ-autorizadas (processo formal fora da Skill 8).

---

## 3. DECOMPOSICAO EM ETAPAS A-F (diagrama)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ PIPELINE COMPLETO Skill 8 — faturando-odoo                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  [PRE-FLIGHT] ──> validar G017 NCM + G035 barcode + G018 weight             │
│      |              em produtos da onda (BLOCKING se houver problema)       │
│      v                                                                      │
│  ┌─────────────┐                                                            │
│  │  ETAPA A    │  Skill 2 (DELEGADO)                                        │
│  │  transf int │  - Transferencias internas pre-faturamento                 │
│  │  (intra-co) │  - Ex: consolidar MIGRACAO → lote canonico antes do bulk  │
│  └─────────────┘                                                            │
│      v                                                                      │
│  ┌─────────────┐  ThreadPool max_concurrent=5                               │
│  │  ETAPA B    │  - F5a criar_pickings (paralelo)                           │
│  │  pickings   │  - F5b validar_pickings (paralelo, agrupa por picking_id) │
│  │             │  - F5c liberar_faturamento (paralelo, dispara robo)        │
│  └─────────────┘                                                            │
│      v                                                                      │
│  ┌─────────────┐  Polling SEQUENCIAL longo (1800s default)                  │
│  │  ETAPA C    │  - F5d aguardar_invoices                                   │
│  │  invoices   │    * sub-F5d.5: _garantir_payment_provider (G029)          │
│  │             │    * sub-F5d.6: _corrigir_price_zero (G007)                │
│  │             │    * sub-F5d.7: _garantir_fiscal_setup (G034 DEV_*)        │
│  └─────────────┘  G016: commit_with_retry antes do loop + re-fetch          │
│      v                                                                      │
│  ┌─────────────┐  IRREVERSIVEL — confirmacao explicita                      │
│  │  ETAPA D    │  - F5e transmitir_sefaz (Playwright serial, 1 browser)    │
│  │  SEFAZ      │  G016: commit_with_retry antes de cada NF + re-fetch      │
│  │             │  Idempotente: ja' F5e_SEFAZ_OK ? skip                      │
│  └─────────────┘                                                            │
│      v                                                                      │
│  ┌─────────────┐  Por acao_decidida                                         │
│  │  ETAPA E    │  - PERDA_LF_FB / DEV_LF_FB / DEV_CD_LF / DEV_LF_CD:        │
│  │  entrada FB │    cria RecebimentoLf X→FB (robo CIEL IT entrada)         │
│  │  X→FB       │  - INDUSTRIALIZACAO_FB_LF / TRANSFERIR_*: nao se aplica   │
│  └─────────────┘  Idempotente: RecebimentoLf.odoo_lf_invoice_id            │
│      v                                                                      │
│  ┌─────────────┐  G023 — robo CIEL IT NAO cria entrada destino             │
│  │  ETAPA F    │  - INDUSTRIALIZACAO_FB_LF: picking entrada manual         │
│  │  entrada    │    DELEGADO Skill 5 atomo NOVO v14a-fix:                  │
│  │  manual     │    `criar_picking_entrada_destino_manual` (G011+G023+    │
│  │  FB→{LF,CD} │    G019/G020 codificados intra-atomo, idempotencia        │
│  │             │    via origin). Marca fase='F5f_ENTRADA_OK' apos OK       │
│  └─────────────┘                                                            │
│      v                                                                      │
│  [AUDITORIA]  ──> OperacaoOdooAuditoria.registrar por ajuste+etapa+uuid8   │
│      |                                                                      │
│      v                                                                      │
│  [CONSOLIDACAO] ──> consolidar_validos + cleanup orfaos                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.1 Tabela de estado por etapa (`fase_pipeline` em `AjusteEstoqueInventario`)

| Etapa | fase_pipeline final | Bloqueio se nao OK |
|-------|---------------------|---------------------|
| Pre-flight | n/a (NAO escreve) | bulk nao inicia |
| A | (escreve na Skill 2) | B nao executa se quant nao reservado |
| B (F5a) | `F5a_PICKING_OK` | C nao inicia |
| B (F5b) | `F5b_VALIDADO` | C nao inicia |
| B (F5c) | `F5c_LIBERADO` | C nao acha invoice |
| C (F5d) | `F5d_INVOICE_GERADA` | D nao transmite |
| D (F5e) | `F5e_SEFAZ_OK` (chave_nfe gravada) | E nao processa |
| E | (cria `RecebimentoLf`) | inventario LF nao reflete entrada |
| F | `F5f_ENTRADA_OK` | inventario destino nao reflete |

### 3.2 Direcoes de pipeline (`acao_decidida` em `AjusteEstoqueInventario`)

| Acao | CFOP saida | CFOP entrada | Pre-flight | F5d sub-etapa | E? | F? |
|------|-----------|--------------|-----------|---------------|----|----|
| `TRANSFERIR_CD_FB` | 5152 | 1152 | NCM+weight+barcode | F5d.5 | NAO | NAO (entrada CIEL IT) |
| `TRANSFERIR_FB_CD` | 5152 | 1152 | idem | F5d.5 | NAO | NAO |
| `INDUSTRIALIZACAO_FB_LF` | 5901 | 1901 | idem | F5d.5 | NAO | **SIM** (G023) |
| `PERDA_LF_FB` | 5903 | 1903 | idem | F5d.5 | **SIM** | NAO |
| `DEV_FB_LF` | 5949 | 1949 | idem | F5d.5+.7 (G034) | NAO | NAO |
| `DEV_LF_FB` | 5949 | 1949 | idem | F5d.5+.7 (G034) | **SIM** | NAO |
| `DEV_CD_LF` | 5949 | 1949 | idem | F5d.5+.7 (G034) | **SIM** | NAO |
| `DEV_LF_CD` | 5949 | 1949 | idem | F5d.5+.7 (G034) | **SIM** | NAO |

---

## 4. PRE-FLIGHT (DELEGADO a sub-skill `auditando-cadastro-fiscal-odoo`)

### 4.0 Decisao v13: pre-flight COMO SKILL SEPARADA

**Razao do Rafael (v13 2026-05-25):** podem haver no futuro **faturamentos para cliente** (vendas comerciais, nao so' inventario inter-company) cujo pre-flight tera regras DIFERENTES (ex: certificado A1, validacao de inscricao estadual do destinatario, tabela de precos, FCI, etc.). Ter o pre-flight INVENTARIO como entry-point da Skill 8 amarraria as duas coisas e bloquearia reuso futuro.

**Decisao:** criar sub-skill nova `auditando-cadastro-fiscal-odoo` com **perfis multiplos** (`--perfil inventario`, futuro `--perfil venda-cliente`, etc.). Skill 8 **INVOCA** a sub-skill com perfil correto ANTES do bulk; nao implementa pre-flight diretamente.

### 4.1 Contrato da sub-skill `auditando-cadastro-fiscal-odoo` (v0 — refinar em C5/C6)

```
## Contrato
- objeto:        product.product + l10n_br_ciel_it_account.ncm
- input:         --perfil PERFIL (inventario | venda-cliente | ...)
                 --produto-ids LISTA  OU  --ciclo NOME (le AjusteEstoqueInventario)
                 --auto-corrigir-barcode (opcional, default False — G035)
- output:        relatorio JSON estruturado com:
                   * por produto: ncm_ok, barcode_ok, weight_ok, gaps por gotcha
                   * resumo: pode_faturar (bool), bloqueios por categoria
                   * acoes_aplicadas (lista de corrections automaticas)
- pré-condições: nenhuma (READ-only por default; WRITE so' com --auto-corrigir)
- pós-condições: NENHUM ajuste de inventario tocado; opcional WRITE em product.barcode
- gotchas-invariante: G017 (NCM CIEL IT custom), G035 (barcode→cEAN), G018 (weight bloqueia F5c)
- modos:         --dry-run (default, NAO escreve nada) → --confirmar (escreve barcode=False onde necessario)
```

### 4.2 Perfis previstos (estende quando demanda surgir)

| Perfil | Validacoes | Demanda |
|--------|-----------|---------|
| `inventario` (V1) | G017 NCM + G035 barcode + G018 weight | Skill 8 v1 (esta sessao em diante) |
| `venda-cliente` (futuro) | inventario + certificado A1 + IE destinatario + tabela_preco + FCI | quando Rafael indicar |
| `compras-importacao` (futuro hipotetico) | NCM + barcode + dados aduaneiros | sem demanda atual |

**Atomo extensivel:** estrutura segue pattern "DSL de validacoes por perfil" — cada perfil = lista de checks. Adicionar perfil = adicionar entrada no dict de perfis + N funcoes de check. Nao requer alterar entry-point.

### 4.3 Validacoes V1 (perfil `inventario`)

#### G017 — NCM cadastro

- **Risco:** `product.l10n_br_ncm_id=False` gera `<NCM>False</NCM>` no XML → SEFAZ cstat=225.
- **Detecao:** query `product.product` com `l10n_br_ncm_id=False` para produtos da onda.
- **Correcao:** cadastrar NCM via `l10n_br_ciel_it_account.ncm` (campo `codigo_ncm`, NAO `code` — quirk CIEL IT). Default sub-skill: NAO auto-corrige (operador cadastra manual).
- **Fonte existente:** funcao `validar_cadastro_fiscal` em `09_executar_onda1_bulk.py:139-211`.

#### G035 — barcode invalido

- **Risco:** `product.barcode` populado com `default_code` (ex: 9 digitos sem check digit GTIN-13) gera `<cEAN>` invalido → SEFAZ cstat=225.
- **Detecao:** validar GTIN dos produtos da onda (existe `gtin_validator.py` em algum lugar de `scripts/` — confirmar caminho em C2/C5).
- **Correcao:** `odoo.write('product.product', [ids], {'barcode': False})`. Opcional auto-corrigir via flag `--auto-corrigir-barcode` (default False).

#### G018 — weight=0

- **Risco:** `product.weight=0` bloqueia `action_liberar_faturamento` (F5c) silenciosamente.
- **Detecao:** query `product.product.weight=0` para produtos da onda.
- **Correcao:** **NAO** alterar `product.weight` (CIEL IT hook nao persiste — quirk). Sub-skill apenas REPORTA. O fix (`stock.picking.l10n_br_peso_liquido` manual apos F5b) e' codificado DENTRO da Skill 8 F5b/F5c.

### 4.4 Output da sub-skill (formato estruturado)

| Campo | Valor |
|-------|-------|
| `status_global` | `PRE_FLIGHT_OK` / `PRE_FLIGHT_BLOQUEADO` |
| `pode_faturar` | bool |
| `bloqueios` | dict por categoria: `ncm_faltando` (lista produtos), `barcode_invalido` (lista produtos), `weight_zero` (lista — warning so) |
| `acoes_aplicadas` | lista (se `--auto-corrigir-barcode`): `[{'produto_id': X, 'campo': 'barcode', 'valor_antes': '...', 'valor_depois': False}]` |
| `relatorio_path` | caminho do CSV/JSON salvo |

### 4.5 Integracao Skill 8 ↔ sub-skill

- Skill 8 modo `--bulk` ou `--canary` chama subprocess da sub-skill com `--perfil inventario --ciclo <NOME>`.
- Se `pode_faturar=False`: aborta com mensagem clara apontando bloqueios.
- Se `pode_faturar=True`: prossegue para etapa A→B→C→D→E→F.
- Operador pode rodar sub-skill ISOLADAMENTE (sem Skill 8) para auditoria/cleanup de cadastro.

### 4.6 Status da sub-skill

| Item | Status | Quando |
|------|--------|--------|
| Decisao tomada | ✅ | v13 (Rafael 2026-05-25) |
| Contrato V0 | ✅ | esta secao §4 |
| Implementacao service | ✅ | v14b — `app/odoo/estoque/scripts/cadastro_fiscal_audit.py` (~430 LOC) |
| Wrapper CLI | ✅ | v14b — `.claude/skills/auditando-cadastro-fiscal-odoo/scripts/auditar_cadastro_inventario.py` |
| Testes pytest | ✅ | v14b — 14 verdes em `tests/odoo/services/test_cadastro_fiscal_audit.py` |
| SKILL.md | ✅ | v14b — `.claude/skills/auditando-cadastro-fiscal-odoo/SKILL.md` |
| Integracao com Skill 8 | ⬜ | v15b (C6 orchestrator base invoca sub-skill via subprocess `--ciclo X --perfil inventario`) |
| Cross-refs (subagente, ROUTING_SKILLS, tool_skill_mapper) | ✅ | v14b — `.claude/agents/gestor-estoque-odoo.md` + `.claude/references/ROUTING_SKILLS.md` + `app/agente/services/tool_skill_mapper.py` + `app/odoo/estoque/CLAUDE.md` |
| Smoke PROD V1 | ✅ | v14b — 6 cods v14a-ops em 987ms; detectou 2 G014 + 1 D-OPS-3 (esperados) |
| Cobertura V1 perfil inventario | ✅ | G017 NCM + G018 weight + G035 barcode (+ auto-fix) + G014 lote vencido + D-OPS-2 duplicacao + D-OPS-3 tracking='none' |

---

## 5. SSL/TIMEOUT/RECOVERY (G016 + scripts resume)

### 5.1 G016 — SSL crash em loops longos (CRITICO)

**Sintoma**: `psycopg2.OperationalError: SSL connection has been closed unexpectedly` apos NF transmitida com sucesso no Odoo, mas `UPDATE ajuste_estoque_inventario SET fase_pipeline='F5e_SEFAZ_OK' ...` falha → DB local desincroniza.

**Causa raiz**: PgBouncer SSL timeout durante operacoes que demoram >5min (F5d polling 1800s; F5e Playwright 5-10min/NF).

**Fix codificado**: Combinacao A+B+C no service atual:
- **A — commit antes**: `_commit_with_retry()` ANTES de operacoes longas (F5d while loop, F5e cada NF)
- **B — retry + re-fetch**: `_commit_with_retry()` (L165) try/except OperationalError, rollback+close+retry. Apos operacao: `db.session.get(AjusteEstoqueInventario, ajuste_id)` para re-fetch
- **C — TCP keepalive**: `config.py:115-118` (keepalives=1, idle=30s, interval=10s, count=5)

**Acao Skill 8:** preservar 100% no novo orchestrator. Documentar como invariante codificada (NAO depender de memoria do agente).

### 5.2 Pattern recovery (scripts `fat_lf_resume*`)

**`fat_lf_resume.sh`** (loop B→D):
```bash
prev=99999
for i in $(seq 1 18); do
  timeout 900 python fat_lf_05_executar_clean.py --confirmar --confirmar-sefaz --apenas-etapa D
  rem=$(contar)  # count(F5c_LIBERADO + F5d_INVOICE_GERADA)
  [ "$rem" = "0" ] && break
  if [ "$rem" = "$prev" ]; then
    # stagnation: rodar C separadamente
    timeout 900 python ... --apenas-etapa C
  fi
  prev=$rem
done
```

**`fat_lf_resume_entrada.sh`** (loop E + F):
- Fase E: ate 30 iteracoes, timeout 600s
- Fase F: ate 12 iteracoes, timeout 600s
- Detecao de stagnation similar

**Acao Skill 8:** capinar como **modo CLI `--resume`** do `faturar_pipeline.py`:
- Args: `--ciclo NOME --apenas-etapa B|C|D|E|F --max-iter N --timeout-por-iter S --detector-stagnation`
- Output JSON estruturado (regra v7) com `iteracoes_executadas`, `restantes_por_fase`, `motivo_parada` (TUDO_OK / STAGNATION / MAX_ITER)
- Idempotencia: pula ajustes com `fase_pipeline` em estado final (regra v7)

### 5.3 Quirks de timing CIEL IT (G011)

| Janela | Timing tipico/invoice | Bloqueador |
|--------|----------------------|------------|
| Madrugada (00h-06h) | 3-5min | raro |
| Manha (08h-12h) | 5-10min | medio (concorrencia outros usuarios CIEL IT) |
| Pico (12h-18h) | >2h ate sem criar | comum (rejeitar bulk se janela ruim) |

**Acao Skill 8:** documentar em SKILL.md armadilha + sugerir janela. Adicionar argumento `--janela-permitida` que checa horario e aborta se for pico (com flag `--ignorar-janela` para override).

### 5.4 Quirks que engolem erros

- **`button_validate`** (F5b): pode retornar sem erro mas picking permanecer em `state='assigned'`. Solucao: re-fetch `stock.picking.state` ANTES de prosseguir. **Codificar no atomo.**
- **`action_liberar_faturamento`** (F5c): aceita picking nao-done sem erro, mas robo NUNCA cria invoice. Solucao: pre-validar `picking.state='done'` antes de chamar.

---

## 6. PATTERN SKILL 6 v9 — REUSO E ADAPTACOES

### 6.1 O que REUSAR de `pre_etapa_executor.py`

| Pattern | Onde no Skill 6 | Como adaptar em Skill 8 |
|---------|-----------------|-------------------------|
| `--dry-run` default | entry-point `executar_onda_pre_etapa` | identico |
| Lazy import `OperacaoOdooAuditoria` | `_registrar_auditoria` (L156) | identico |
| Contadores thread-safe `_dry` vs reais | `_novos_contadores` (L71) | adicionar contadores `f5d_invoices_geradas_dry`, `f5e_sefaz_ok_dry`, etc. |
| `ThreadPoolExecutor + Semaphore` | `_executar_paralelo` (L733) | **preservar pattern do service atual** (Semaphore=5 por F5a/F5b/F5c) |
| Re-fetch ajuste pos-operacao longa | implicito | combinar com G016 _commit_with_retry |
| JSON output estruturado | `executar_onda_pre_etapa` retorna dict | adaptar com `etapas_executadas` + `fase_pipeline_distribuicao` |
| Status `EXECUTADO_AUTO_CORRIGIDO` distincao | `_avaliar_sucesso_v2` (L358) | analogo: `F5_BULK_OK`, `F5_BULK_PARCIAL`, `F5_BULK_FALHA` |

### 6.2 O que ADAPTAR (Skill 8 e' diferente)

| Diferenca | Razao |
|-----------|-------|
| **Etapas SEQUENCIAIS com BARREIRA de sincronizacao** (B→C→D→E→F) | **DECISAO 10.3 (Rafael v13) + CONFIRMADA v14a R1**: fazer TUDO por etapa. Mecanismo do script (main L1771-1860): `expire_all() + carregar_ajustes()` re-load entre etapas + `db.engine.dispose()` profilatico antes/apos C+D. Cada etapa = barreira (aguarda 100% completar antes de iniciar a proxima) |
| Paralelismo INTRA-etapa (B com Semaphore=5) | **REFINADO v14a sub-nuance D16**: ETAPA B no script faz pipeline POR PICKING (criar→validar→liberar→sleep 5s→proximo) — NAO paraleliza N pickings entre si (G022 over-reservation mitigation). Service `f5b_validar_pickings(ajustes_chunk)` paraleliza ajustes DENTRO de 1 picking via Semaphore=5; mas o script chama com 1 chunk de cada vez. **PRESERVAR pattern intra-B no Skill 8 orchestrator v15** |
| **NAO interleaving de ajustes entre etapas** | NAO rodar B→C→D em pipeline por ajuste (ajuste 1 vai B→C; ajuste 2 vai B→C; ...). Em vez: TODOS em B, depois TODOS em C, etc. Isso e' chave para reduzir SSL drop window. **MAS** dentro de B, sim pipeline por picking (sub-nuance acima) |
| Polling F5d sequencial longo | nao paralelizar — Odoo CIEL IT rejeita concorrente. **D10 v14a**: chamar `db.engine.dispose()` ANTES e APOS (profilatico, alem do `_commit_with_retry` interno) |
| F5e SEQUENCIAL (1 browser Playwright) | preservar — Playwright nao concorre. **D10 v14a**: idem dispose antes/apos |
| Recovery loop fora do orchestrator (script shell?) | DECISAO: capinar como `--resume` modo CLI no proprio entry-point Python. **D12 v14a**: preservar `--apenas-etapa` + `--ate-etapa` para recovery operacional |
| **F5a/F5b refatorados para atomos Skill 5** | **DECISAO 10.6 (Rafael v13)**: principio inviolavel "se mexe com picking, devera ser atraves da Skill 5". F5a vira `criar_picking_inter_company` na Skill 5; F5b vira `validar_picking_inter_company` na Skill 5. Skill 8 ORQUESTRA sequencia. **D16 v14a**: atomo Skill 5 deve preservar sleep 5s entre pickings ou orchestrator Skill 8 invoca com pausa |
| **D14 v14a — `_commit_resilient` MAIS FORTE que `_commit_with_retry`** | Script faz `engine.dispose()` proativo quando detecta SSL na string do erro; service so' rollback+close+retry. **APLICAR versao MAIS FORTE no orchestrator Skill 8** (consolidar helper em `app/odoo/estoque/scripts/_commit_helpers.py` ou similar) |
| **D17 v14a — `ACAO_PARA_CFOP_ENTRADA` (5xxx→1xxx)** | Constante inline no script (L1300-1305). **Skill 8 deve centralizar** em `app/odoo/constants/operacoes_fiscais.py` (mesmo arquivo das outras matrizes fiscais) |
| **D11 v14a — `expire_all() + carregar_ajustes()` entre etapas** | Pattern explicito no script para invalidar ORM cache stale. **APLICAR no orchestrator Skill 8** entre cada etapa A→B→C→D→E→F |
| **D18 v14a — Default `dry_run=True` + `--confirmar`** | Pattern reuso Skill 6 v9. Skill 8 CLI deve seguir + segundo nivel `--confirmar-sefaz` para ETAPA D (irreversivel SEFAZ) |

### 6.3 Destino do orchestrator

**Caminho**: `app/odoo/estoque/orchestrators/faturamento_pipeline.py`

**Estrutura prevista**:
- ~1.000-1.200 LOC (maior que Skill 6 v9 — 6 etapas vs 1)
- Helpers privados: `_resolver_picking_type`, `_resolver_partner_id`, `_garantir_peso_liquido_picking` (G018 in-atom)
- Funcoes publicas:
  - `executar_pre_flight(ciclo, company_id, auto_corrigir_barcode=False, ...)` — sub-modo
  - `executar_pipeline_bulk(ciclo, etapas=['B','C','D','E','F'], confirmar=False, confirmar_sefaz=False, max_workers=5, ...)` — entry-point principal
  - `executar_pipeline_resume(ciclo, max_iter=18, timeout_iter=900, ...)` — recovery
  - `executar_canary(ciclo, ajuste_id, confirmar_sefaz=False)` — canary 1-ajuste
  - `consolidar_validos(ciclo)` — pos-execucao
- Auditoria `OperacaoOdooAuditoria.registrar(pipeline_etapa='F5{a/b/c/d/e}_{action}', ...)`

**Wrapper CLI**: `.claude/skills/faturando-odoo/scripts/faturar_pipeline.py`
- Modos: `--canary` / `--bulk` / `--resume` / `--consolidar` (NAO `--pre-flight` — esta na sub-skill `auditando-cadastro-fiscal-odoo`)
- Args: `--ciclo NOME` / `--company-id ID` / `--etapas LISTA` / `--confirmar-sefaz` / `--max-workers N` / `--max-iter N` / `--timeout-iter S` / `--limite N` / `--ajuste-id ID` / `--pular-pre-flight` (default False, exige pre-flight OK)
- Exit codes: 0 (OK) / 1 (falha negocial) / 2 (uso) / 4 (DRY_RUN_OK)

**Sub-skill `auditando-cadastro-fiscal-odoo`** (a criar em v14 — C5 redefinido):
- Caminho: `.claude/skills/auditando-cadastro-fiscal-odoo/SKILL.md`
- Service base: `app/odoo/estoque/scripts/cadastro_fiscal_audit.py` (a criar — extrair logica de `09_executar_onda1_bulk.py:139-211` + `gtin_validator.py`)
- Modos: `--perfil inventario` (V1) / futuros `--perfil venda-cliente` etc.
- Wrapper CLI: `.claude/skills/auditando-cadastro-fiscal-odoo/scripts/auditar_cadastro.py`

---

## 7. CHECKPOINTS NUMERADOS (granulares — atualizar status a cada sessao)

### Legenda status

- ⬜ pendente
- 🟡 em andamento
- ✅ concluido com artefato concreto
- ⏸️ pausado (motivo registrado)
- ❌ bloqueado (acao necessaria)

### Lista de checkpoints

| # | Checkpoint | Entregavel | Criterio de aceite | Sessao prevista | Status | Notas |
|---|-----------|-----------|-------------------|-----------------|--------|-------|
| **C1** | Pre-mortem completo (§7.1) | secao §7.1 atualizada com 4 dimensoes x 6 etapas | Tabela de riscos com mitigacao codificavel | v13 | 🟡 | esta sessao |
| **C2** | Mineracao detalhada `inventario_pipeline_service.py` | mapa metodos+linhas+helpers, conferir com cabecalho | Doc inline neste arquivo (§7.2) com referencia file:line | ~~v14~~ **v13 mid** | ✅ | mapa completo + **9 descobertas-chave** D1-D9 documentadas |
| **C3** | Mineracao `09_executar_onda1_bulk.py` (etapas A/B/C/D/E/F + main) | mapa etapas+funcoes+chamadas, conferir | Doc inline (§7.3) com referencia file:line | ~~v14~~ **v14a** | ✅ | Tabela §7.3 com 11 funcoes + 9 descobertas D10-D18 + dependencias externas; R1 RESPONDIDO (10.3 INTACTA) |
| **C4** | Confirmar escopo completo (a/b/c) com Rafael | decisoes §10.1, §10.2 fechadas | Rafael confirmou via AskUserQuestion | v13 | ✅ | "estruturar bem, depois rodar casos reais" |
| **C5** | **Criar sub-skill `auditando-cadastro-fiscal-odoo` (perfil inventario V1)** | `app/odoo/estoque/scripts/cadastro_fiscal_audit.py` (service ~430 LOC) + `.claude/skills/auditando-cadastro-fiscal-odoo/{SKILL.md,scripts/auditar_cadastro_inventario.py}` (CLI) + cross-refs (subagente + ROUTING_SKILLS + tool_skill_mapper + CLAUDE.md estoque) | smoke dry-run em onda real OK; >5 pytest verdes; --perfil inventario funcional | ~~v14~~ **v14b** | ✅ | **CONCLUIDO v14b** — service ~430 LOC capinado de `validar_cadastro_fiscal` (script 09) + `gtin_validator.py` + queries D-OPS-2 em AjusteEstoqueInventario; 14 pytest verdes; smoke PROD 6 cods em 987ms detectou 2 G014 + 1 D-OPS-3 (esperados); cobertura G017+G018+G035+G014+D-OPS-2+D-OPS-3 |
| **C6** | Capinar orchestrator base (skeleton) | `app/odoo/estoque/orchestrators/faturamento_pipeline.py` com entry-points, helpers (_commit_resilient/_carregar_ajustes/_pre_flight_via_subskill_c5/_resolver_picking_metadata/_agrupar_por_direcao/_agrupar_em_chunks), classe `FaturamentoPipelineExecutor` + CLI argparser + main() com app_context | pytest smoke import OK + 30 pytest verdes + smoke dry-run PROD OK | v15b | ✅ | **COMPLETO v15b 2026-05-25** — ~1300 LOC; constants `ACAO_PARA_DIRECAO`+`ACOES_PICKING`+`MAX_CODS_POR_PICKING=30`+`SLEEP_ENTRE_CHUNKS=5.0`+`ETAPAS_VALIDAS=(A,B,C,D,E,F)`; helpers D11/D14/D15/D16/D18 codificados; PRE-FLIGHT C5 subprocess; pre/pos-fixes pos code-review (CR-C1+C2+H1+H2+H4+M1+M3) |
| **C6.5** | **NOVO v13 + EXPANDIDO v14a-fix — Estender Skill 5 com 3 atomos** (DECISAO 10.6) | `app/odoo/estoque/scripts/picking.py` ganha `criar_picking_inter_company` + `validar_picking_inter_company` + **`criar_picking_entrada_destino_manual` (NOVO v14a-fix — ETAPA F G023)**; SKILL.md `operando-picking-odoo` estendida; pytest >8 verdes novos (3 atomos × ~3 cenarios) | dry-run PROD OK em 2 pickings reais (1 inter-company + 1 entrada destino manual); idempotencia via origin validada | v15a | ✅ | **COMPLETO v15a (2026-05-25)** — 3 atomos LIVE com 19 pytest verdes (61 total stock_picking_service); constants ETAPA F centralizadas em `app/odoo/constants/picking_types.py`; smoke PROD com 6 cods v14a-ops validou D-OPS-3 detection (`103500105` PIMENTA tracking='none' detectado corretamente, `lot_name` removido das linhas); 435 baseline Odoo |
| **C7** | Capinar F5a no orchestrator (chamando atomo Skill 5 estendido) | metodo `_processar_chunk_etapa_b` chama `criar_picking_inter_company` (Skill 5 v15a) com chunks <=30 cods + G022 sleep 5s entre chunks + tracker `chunk_executado` global (CR-H1) + G-ETB-COMPENSATORIO preservando acao_decidida origem (CR-H2) | smoke dry-run PROD OK; pytest cobre invocacao mocada + acao invalida + chunk vazio | v15b | ✅ | **COMPLETO v15b 2026-05-25** — invocacao via `picking_svc.criar_picking_inter_company(...)`; metadata resolvido via `_resolver_picking_metadata` (acao->picking_type+partner+locations); origin idempotente `INV-{ciclo}-SAIDA-{tipo_op[:8].upper()}-{ajuste_id:06d}`; CR-C2 corrigiu agrupamento (`acao_decidida` em vez de `(co, tipo_op)`) |
| **C8** | Capinar F5b no orchestrator (chamando atomo Skill 5 estendido) | metodo `_processar_chunk_etapa_b` chama `validar_picking_inter_company` (Skill 5 v15a) APOS F5a; passa `linhas_esperadas` com lot_name + G018 v2 codificado intra-atomo | smoke dry-run PROD OK; pytest cobre fluxo F5a->F5b->F5c sequencial em chunk | v15b | ✅ | **COMPLETO v15b 2026-05-25** — invocacao via `picking_svc.validar_picking_inter_company(picking_id, linhas_esperadas=..., aplicar_peso_volumes=True)`; pendencias G021 capturadas + alimentam G-ETB-COMPENSATORIO em PERDA_LF_FB |
| **C9** | Capinar F5c (liberar faturamento) | metodo `_processar_chunk_etapa_b` chama `picking_svc.liberar_faturamento(picking_id)` apos F5b OK | smoke dry-run PROD OK; pytest cobre fluxo F5c em real run | v15b (EXPANDIDO no escopo de v15b) | ✅ | **COMPLETO v15b 2026-05-25** — atomo legacy `liberar_faturamento` valida pre-cond state='done' (G019/G020 fechada v3); fase `F5c_LIBERADO` + auditoria registrada |
| **C10** | Capinar F5d (aguardar invoices) + G016 SSL + G007+G034+G029 | metodo `executar_etapa_c` no orchestrator com sub-etapas .5/.6/.7 via `_invoice_helpers.py` + commit_resilient + safe_session_get + ETAPA A real (Skill 2 v2) + G014 pre-check on-the-fly | 14 pytest verdes; dry-run PROD validado (cod 105000007 detecta 4 pickings F5c_LIBERADO em 766ms) | v16 | ✅ | **COMPLETO v16 2026-05-25** — C10+C10.2+C10.3 entregues + 9 fixes 2 reviewers paralelos. `_invoice_helpers.py` NOVO ~430 LOC perfil V1 'inventario-inter-company' (futuros perfis raise NotImplementedError). MIN seguranca SEFAZ alcancado (guards R2F1/F2/F3). |
| **C11** | Capinar F5e (transmitir SEFAZ) + G016 SSL | metodo `_executar_f5e` Playwright serial + commit_with_retry + idempotencia F5e_SEFAZ_OK | 5+ pytest verdes (mockando Playwright); dry-run sem confirmar-sefaz OK | v16-v17 | ⬜ | |
| **C12** | Capinar etapa E (RecebimentoLf X→FB) | metodo `_executar_etapa_e` + idempotencia odoo_lf_invoice_id | 4+ pytest verdes; dry-run OK | v17 | ⬜ | |
| **C13** | Capinar etapa F (entrada manual FB→{LF,CD}) — INVOCA atomo Skill 5 NOVO `criar_picking_entrada_destino_manual` (G023 fix codificado intra-atomo, alinha "Fluxo>>Skills") | metodo `_executar_etapa_f` no orchestrator que itera por invoice_id chamando atomo Skill 5 + agg moves_data + origin idempotente | 4+ pytest verdes; dry-run OK | v17 | ⬜ | **EXPANDIDO v14a-fix**: ETAPA F nao implementa picking inline — DELEGA para Skill 5 |
| **C14** | Capinar recovery (`--resume` modo CLI) | entry-point `executar_pipeline_resume` + detector stagnation + max_iter | 3+ pytest verdes (mockando ondas); smoke shell script substitutivo OK | v18 | ⬜ | |
| **C15** | SKILL.md com 5+ receitas | `.claude/skills/faturando-odoo/SKILL.md` + frontmatter description rica | description triga em "fature a onda X", "transmita SEFAZ", "resume da onda Y" via tool_skill_mapper | v18 | ⬜ | |
| **C16** | Pytest baseline ≥420 verdes | suite completa passando | `pytest tests/odoo/ -q` OK | v18 | ⬜ | meta +27 testes Skill 8 |
| **C17** | Smokes dry-run vs PROD | 5+ smokes documentados em log JSON | logs `/tmp/log_skill8_*.json` salvos + analisados | v18 | ⬜ | |
| **C18** | Folha de fluxo 1.1 + 1.3 + README dos fluxos | `app/odoo/estoque/fluxos/1.1-faturamento-completo.md` + `1.3-transferencia-completa.md` + README atualizado | links de subagente apontam para folhas | v19 | ⬜ | |
| **C19** | Cross-refs completas | subagente `gestor-estoque-odoo` + ROUTING_SKILLS + tool_skill_mapper + CLAUDE.md raiz + CLAUDE.md estoque + MAPA_SCRIPTS | grep `faturando-odoo` retorna ≥6 hits coerentes | v19 | ⬜ | |
| **C20** | Canary REAL PROD (1 ajuste) | execucao `--canary` com `--confirmar-sefaz` em 1 ajuste real | NF autorizada SEFAZ + DB sincronizado + auditoria registrada | v19-v20 | ⬜ | escolha do caso com Rafael |
| **C21** | Bulk REAL PROD (onda inteira) | execucao `--bulk` em onda escolhida + monitorar SSL/timing | ≥95% F5e_SEFAZ_OK + recovery valido para 5% restantes | v20+ | ⬜ | depende C20 |
| **C22** | Code-review paralelo (feature-dev:code-reviewer) | findings priorizados + fixes aplicados | 0 HIGH severity remaining | v20 | ⬜ | |
| **C23** | Commit consolidado + arquivar 09_* SUPERADOS | git mv 09_executar_onda1_bulk.py + 09c + fat_lf_* → `_validados/faturando-odoo/` + VALIDACAO.md | sys.path corrigido nos arquivados (parents[2]→parents[4]); smoke import museum vivo OK | v20+ | ⬜ | |

### 7.1 Pre-mortem por etapa (C1 — preencher nesta sessao v13)

#### Dimensao 1: Bugs reais que podem aparecer em PROD

| Etapa | Bug possivel | Sintoma | Mitigacao |
|-------|--------------|---------|-----------|
| Pre-flight | Falso negativo (produto OK mas detector marca KO) | bulk nao inicia | smoke 3 produtos validados manualmente antes de cada bulk |
| F5a | Race em paralelo: 2 threads criam picking duplicado para mesma chave (ajuste_id) | violacao constraint UK | lock por ajuste_id (DB advisory lock ou sets in-memory thread-safe) |
| F5a | `partner_id` resolver retorna False (G004) | picking criado sem destinatario, robo CIEL IT nao processa | pre-validar partner_id na resolucao + abortar ajuste especifico |
| F5b | `button_validate` retorna sem erro mas state continua `assigned` (quirk) | F5c chama sobre picking nao-done, robo silencioso | re-fetch state ANTES de F5c (codificar invariante) |
| F5b | G018 `peso_liquido` zerado mesmo apos write | F5c bloqueia silenciosamente | escrever direto em `stock.picking.l10n_br_peso_liquido` (NAO em product) + re-checar |
| F5b | Race em paralelo: `move_line` qty_done sobrescrito por outra thread (G011) | quantidade errada na invoice | agrupar por picking_id (codificado no service atual — preservar) |
| F5c | `action_liberar_faturamento` em picking nao-done (silencioso) | invoice nunca criada | invariante: pre-validar state='done' (regra G019/G020-like) |
| F5d | SSL crash no polling 1800s (G016) | DB desincroniza com Odoo | _commit_with_retry codificado + re-fetch (preservar do service) |
| F5d | Robo CIEL IT em pico >2h sem criar invoice (G011) | timeout do polling + bulk parcial | janela permitida + warn |
| F5d.6 | price_unit=0 em algumas linhas (G007) mas NAO em todas | partial fix | corrigir TODAS linhas com price=0 (codificado em service) |
| F5d.7 | G034 reset_to_draft falha se ja' SEFAZ-autorizado (state guard) | NF errada autorizada | guard `l10n_br_situacao_nf in ('autorizado', 'excecao_autorizado')` codificado (preservar) |
| F5e | SSL crash em Playwright loop (G016) | NF SEFAZ-OK mas DB nao registra | _commit_with_retry antes de cada NF + re-fetch (preservar) |
| F5e | Playwright crash mid-loop (browser zombie) | bulk para no meio | recovery via `--resume` retoma do ultimo ajuste sem chave_nfe |
| F5e | Browser session expirou Odoo UI | login falha em meio do loop | recovery retoma + lifetime de sessao monitorado |
| E | RecebimentoLf duplicado (idempotencia falha) | constraint UK violation | check `odoo_lf_invoice_id` antes de criar (codificado em `etapa_e_entrada_fb` — preservar) |
| E | Robo CIEL IT entrada hang (>10min) | timeout iter, recovery retoma | timeout=600s no resume script + retry |
| F | G023: `company_id` NAO forcado em moves | "Empresas incompativeis" no picking | forcar `company_id` apos `create('stock.picking', ...)` (codificar invariante) |
| F | `picking_type_id=19` nao encontrado na company | erro de uso | validar pre-criacao |

#### Dimensao 2: Erros de uso (operador / agente)

| Erro | Sintoma | Mitigacao |
|------|---------|-----------|
| Rodar `--bulk --confirmar-sefaz` direto sem `--canary` antes | risco de NF errada em 100+ ajustes | regra inviolavel: canary OBRIGATORIO antes de bulk (codificar `--bulk` rejeita sem `--canary-feito-em CICLO`) |
| Rodar `--pre-flight --auto-corrigir-barcode` em onda errada | barcode limpo em produtos fora do escopo | regra: `--auto-corrigir-barcode` exige `--limite N` + lista explicita |
| Rodar 2 instancias simultaneas do mesmo `--ciclo` | duplicacao + race | guard via pgrep -f + advisory lock por ciclo |
| Esquecer etapa F apos D (INDUSTR FB→LF) | inventario destino nao reflete | `--bulk` default executa B→C→D→E→F; etapa explicita exige flag |
| Re-rodar `--bulk` sobre onda ja' OK | desperdicio de tempo | idempotencia por fase_pipeline final (codificado) |

#### Dimensao 3: Riscos operacionais (impacto fisico/contabil)

| Risco | Impacto | Mitigacao |
|-------|---------|-----------|
| NF autorizada SEFAZ com qty errada | problema fiscal real (cancelar 24h) | pre-flight + canary + double-check qty no XML antes de transmitir |
| Saldo de estoque movido SEM NF correspondente | divergencia ETB | idempotencia por etapa + auditoria + reconciliacao pos-bulk |
| RecebimentoLf criado para invoice cancelada | inventario inflado | check `account.move.state='posted'` AND `l10n_br_situacao_nf='autorizado'` antes de E |
| Picking de entrada manual (F) cria saldo duplicado | inventario inflado | check `RecebimentoLf` ja' existe AND tipo correspondente |

#### Dimensao 4: Riscos tecnicos (manutenibilidade)

| Risco | Mitigacao |
|-------|-----------|
| Pattern Skill 6 v9 nao se adapta bem (etapas sequenciais vs paralelo) | adaptar com cuidado em C6; documentar trade-offs |
| Refatoracao quebra 29 pytest existentes | preservar interfaces publicas do service; novos tests testam orchestrator |
| Mock Playwright dificil em pytest | usar `unittest.mock.patch('transmitir_nfe_via_playwright')` |
| Mock robo CIEL IT (cria invoice) dificil | mockar `odoo.search('account.move', ...)` apos sleep N |
| Centralizar journals (847/1002/987) exige rodar pre-flight em todo o codigo legacy | tarefa ortogonal — adiar para Skill 7 ou pos-v20 |

### 7.2 Mineracao service-fonte `inventario_pipeline_service.py` (C2 ✅ COMPLETA v13 mid)

#### Mapa detalhado metodo → linhas → side-effects → deps

| Metodo | Linhas | Side-effects | Deps Odoo | Deps DB | Notas |
|--------|--------|--------------|-----------|---------|-------|
| `resolver_location_destino` | 66-107 | (READ-only — resolver) | constants `LOCATION_DESTINO_*` | - | Resolve stock.location.id por (tipo_op, company_origem). G023: dest precisa ser virtual (company_id=False) |
| `__init__` | 109-119 | inicializa odoo conn + Semaphore | `get_odoo_connection()` | - | Args: `max_concurrent=5`, `max_workers=10` |
| Class constants `PAYMENT_PROVIDER_SEM_PAGAMENTO` | 125 | - | `ids_diversos` | - | G029 — id=38 SEM PAGAMENTO |
| Class constants `FISCAL_SETUP_POR_ACAO` | 143-159 | - | - | - | G034 — 3 acoes DEV mapeadas (LF_FB sem precedente) |
| `_commit_with_retry` | 165-202 | DB commit + rollback + close | - | session | **G016 Opcao B** — try OperationalError + rollback+close+retry (max 2) |
| `_garantir_payment_provider` | 204-291 | read+write account.move (com reset_to_draft+post fallback) | account.move | OperacaoOdooAuditoria | **G029 F5d.5** — idempotente; fallback se write em posted falhar |
| `_garantir_fiscal_setup` | 293-399 | read+write account.move + reset_to_draft+post | account.move | OperacaoOdooAuditoria | **G034 F5d.7** — guard pre-state autorizado bloqueia; nao altera journal pos-post |
| `_corrigir_price_zero_em_invoice` | 401-506 | read account.move.line + reset_to_draft + write + post | account.move, product.product, account.move.line | OperacaoOdooAuditoria | **G007 F5d.6** — fallback standard_price ou 0.01; retorna count corrigidas |
| `_resolver_picking_type` | 508-521 | - (lookup) | constants `PICKING_TYPE_POR_DIRECAO` | - | ValueError se sem mapeamento |
| `_registrar_op` | 523-575 | insert | - | OperacaoOdooAuditoria | external_id unique INV-{ciclo}-A{id:06d}-{fase}-{uuid8} |
| `f5a_criar_pickings` | 581-754 | create stock.picking + write moves | stock.picking, stock.move, product.product | AjusteEstoqueInventario (UPDATE picking_id_odoo + fase_pipeline) | **PARALELO** Semaphore=5; SNAPSHOT antes threads; idempotente via picking_id_existente; usa `picking_svc.criar_transferencia` |
| `_agrupar_por_picking` | 760-772 | - (utility) | - | - | Suporta N ajustes/picking (1 picking pode ter N produtos) |
| `f5b_validar_pickings` | 774-876 | confirmar_e_reservar + preencher_qty_done + ajustar_qty_done + validar | stock.picking, stock.move.line | AjusteEstoqueInventario (UPDATE fase_pipeline) | **PARALELO** Semaphore=5; agrupado por pid; **bug L19/L20/L21 fix**: preencher_qty_done ENTRE action_assign e ajustar; G023: `linhas_esperadas` para `validar()` |
| `f5c_liberar_faturamento` | 882-939 | action_liberar_faturamento | stock.picking | AjusteEstoqueInventario (UPDATE fase_pipeline) | **PARALELO** Semaphore=5; agrupado por pid; dispara robo CIEL IT |
| `f5d_aguardar_invoices` | 945-1102 | polling search account.move + sub-etapas .5/.6/.7 | account.move | AjusteEstoqueInventario (UPDATE fase_pipeline + invoice_id_odoo) | **POLLING LONGO** 1800s/40s; SNAPSHOT meta antes; `db.session.get` re-fetch pos-resolved; G016 commit antes+depois |
| `f5e_transmitir_sefaz` | 1116-1346 | Playwright transmit + write account.move | account.move | AjusteEstoqueInventario (UPDATE fase_pipeline + chave_nfe + status) | **SERIAL** 1 browser; idempotencia TRIPLA; HARD_FAIL_CONFIG abort batch; G016 commit antes+depois cada NF; re-fetch via db.session.get |

#### Descobertas-chave (padroes a PRESERVAR no orchestrator Skill 8)

**D1 — Pattern SNAPSHOT antes de threads** (F5a L599-616):
```python
snapshots = [{'id': a.id, 'acao_decidida': a.acao_decidida, ...} for a in ajustes]
def _odoo_io(snap): ...  # threads SO fazem Odoo I/O, sem tocar DB local
# DB writes na main thread (apos as_completed)
```
**Razao**: evita problemas de pool de conexao + savepoint isolado em tests + SQLAlchemy `DetachedInstanceError`. **APLICAR em F5b/F5c quando estender Skill 5 (C6.5).**

**D2 — Agrupamento por picking** (`_agrupar_por_picking` L760-772):
1 picking pode ter N ajustes (N produtos no mesmo picking inter-company). Pattern: dict `{picking_id: [ajustes...]}`. **Marca fase em TODOS os ajustes do mesmo picking.** Preservar em qualquer etapa que opera por picking.

**D3 — Bug L19/L20/L21 fix em F5b** (L795-799 docstring):
Sem `preencher_qty_done` ENTRE `action_assign` e `ajustar_qty_done_pelo_disponivel`, move_lines ficam com qty_done=0 → cascateia em peso_liquido=0 (L20) e volumes=0 (L21) → F5c falha em `action_liberar_faturamento`. **Sequencia codificada e' inviolavel.** Codificar em `validar_picking_inter_company` da Skill 5 (C6.5).

**D4 — G023 `linhas_esperadas` em F5b validate** (L837-840):
Passar `linhas_esperadas` para `validar()` consolida move_lines antes de `button_validate` — descarta reservas em lotes nao planejados pos-renomeacao via ETAPA A. Importante quando ETAPA A renomeia lotes MIGRACAO → lote canonico.

**D5 — Pattern SNAPSHOT meta antes de polling longo** (F5d L972-975):
```python
ajustes_meta_por_pid = {
    pid: [{'id': a.id, 'ciclo': a.ciclo} for a in lista]
    for pid, lista in ajustes_por_pid.items()
}
```
**Razao G016**: sessao pode expirar em SSL idle timeout durante esperas de 30min. Apos resolved, faz `db.session.get(AjusteEstoqueInventario, meta['id'])` para re-fetch. **APLICAR em qualquer etapa com loop >5min.**

**D6 — Sub-etapas F5d.5/.6/.7 em try/except** (F5d L1031-1066):
- F5d.5: `_garantir_payment_provider` (G029) — falha vira warning
- F5d.6: `_corrigir_price_zero_em_invoice` (G007) — falha vira warning
- F5d.7: `_garantir_fiscal_setup` (G034 DEV_*) — falha vira warning
**Falha individual NAO derruba o ajuste** — pode tentar transmissao SEFAZ mesmo assim. Pattern arquitetural: sub-etapas idempotentes que melhoram sucesso da F5e mas nao bloqueiam.

**D7 — `HARD_FAIL_CONFIG_ERRORS` em F5e** (L1110-1114):
```python
HARD_FAIL_CONFIG_ERRORS = {
    'playwright_indisponivel',
    'odoo_password_ausente',
    'odoo_username_ausente',
}
```
Estes 3 erros + `tentativas == 0` **ABORTA o batch inteiro** via `raise RuntimeError`. Operador precisa intervir manualmente. **Preservar lista no orchestrator.**

**D8 — Idempotencia TRIPLA em F5e**:
1. Por ajuste: `if not inv_id` → SKIP (sem invoice_id_odoo do F5d)
2. Por invoice no batch: `if inv_id in invoices_processadas` — 1 invoice = 1 transmissao SEFAZ
3. Por persistencia: `if aj.fase_pipeline == 'F5e_SEFAZ_OK' or aj.status == 'EXECUTADO'`
**Crucial para recovery** — `--resume` re-roda F5e sem re-transmitir o que ja' foi enviado.

**D9 — Pattern `db.session.get` re-fetch + `_commit_with_retry`** (F5e L1230-1237, L1326-1332):
Apos Playwright (5-10min), sessao pode estar morta. Re-fetch via `db.session.get(AjusteEstoqueInventario, ajuste_id_local)`. Se retornar `None` (ajuste deletado), log error + continue. **Sempre apos operacao longa: re-fetch + commit_with_retry.**

#### Achados secundarios

- **`MED C-1`** (L1269-1275): `situacao_nf != 'autorizado'` mas `sucesso=True` (caso `excecao_autorizado`) — registrar em `aj.erro_msg` para audit fiscal, NAO marca como falha.
- **`MED C-2`** (L1294-1302): persistir `cstat`+`xmotivo` de `ultimo_estado` na falha SEFAZ — campo mais acionavel.
- **`MED B-2`** (L1155-1168): skip silencioso virou WARNING — sinal de F5d timeout (sem invoice_id_odoo).
- `transmitir_nfe_via_playwright` esta em `app.recebimento.services.playwright_nfe_transmissao` — modulo externo a esta skill (reutilizar como esta).
- `picking_svc` injetado via construtor (default `StockPickingService(odoo=self.odoo)`) — facil mockar em testes.

#### Dependencias externas confirmadas

| Dependencia | Tipo | Onde |
|-------------|------|------|
| `StockPickingService` | service legado | `app.odoo.services.stock_picking_service` (provavelmente SHIM para `app/odoo/estoque/scripts/picking.py`) |
| `transmitir_nfe_via_playwright` | funcao Playwright | `app.recebimento.services.playwright_nfe_transmissao` — **NAO mexer**, reutilizar como esta |
| `OperacaoOdooAuditoria.registrar` | helper de auditoria | `app.odoo.models.OperacaoOdooAuditoria` — schema fixo (external_id unique) |
| `AjusteEstoqueInventario` | model SQLAlchemy | `app.odoo.models.AjusteEstoqueInventario` — UPDATE de `picking_id_odoo`, `fase_pipeline`, `invoice_id_odoo`, `chave_nfe`, `status`, `erro_msg` |
| `MATRIZ_INTERCOMPANY`, `PICKING_TYPE_POR_DIRECAO`, `COMPANY_LOCATIONS`, `COMPANY_PARTNER_ID`, `ids_diversos` | constants | `app.odoo.constants` |

### 7.3 Mineracao script-fonte `09_executar_onda1_bulk.py` (C3 ✅ COMPLETA v14a)

#### Estrutura geral (1866 LOC, 6 etapas A→F)

| Bloco | Linhas | Conteudo |
|-------|--------|----------|
| Imports + constants | L1-150 | `CICLO='INVENTARIO_2026_05'`, `ACOES_PICKING` (8 acoes NF), `ACOES_LOTE` ({RENOMEAR_LOTE, TRANSFERIR_LOTE}), `ACOES_ENTRADA_DESTINO_MANUAL` ({INDUSTRIALIZACAO_FB_LF} — so' validado), `PICKING_TYPE_ENTRADA_DESTINO_MANUAL` ({5:19}), `LOCATION_ORIGEM_ENTRADA_INDUSTR=26489`, `ETAPAS_VALIDAS=('A','B','C','D','E','F')` |
| Helpers | L151-415 | `banner`, `_commit_resilient` (G016 D14), `resolver_product_id`, **`validar_cadastro_fiscal`** (G017 NCM strict + G018 weight=0 warn — **FONTE para sub-skill `auditando-cadastro-fiscal-odoo` C5 v14b**), `corrigir_weight_zero` (apenas detecta), `aplicar_peso_volumes_fallback_picking` (G018 v2 ENTRE F5b/F5c — `l10n_br_peso_liquido` writable em stock.picking) |
| Carregamento | L416-494 | `carregar_ajustes` (DB local + filtros onda/status/cod), `imprimir_resumo_ajustes` |
| ETAPA A | L498-613 | `etapa_a_transferencias_lote` — DELEGADO para Skill 2 (StockInternalTransferService) |
| ETAPA B | L617-1149 | `etapa_b_pickings` (532 LOC monolitica) — chama `picking_svc.criar_transferencia` (F5a) + `pipeline_svc.f5b/f5c` |
| ETAPA C | L1156-1190 | `etapa_c_aguardar_invoices` (35 LOC) — DELEGADO para `pipeline_svc.f5d_aguardar_invoices` |
| ETAPA D | L1197-1232 | `etapa_d_sefaz` (36 LOC) — DELEGADO para `pipeline_svc.f5e_transmitir_sefaz` |
| ETAPA E | L1239-1421 | `etapa_e_entrada_fb` (183 LOC) — DELEGADO para `RecebimentoLfOdooService.processar_recebimento` |
| ETAPA F | L1428-1688 | `etapa_f_entrada_destino_manual` (entry L1428-1505) + `_f_criar_entrada_destino_para_invoice` (helper L1508-1688) — implementacao DIRETA XML-RPC (cria picking + G023 company_id forcado + G011 lot_name + G019/G020 re-le state) |
| main() | L1695-1862 | argparser + orchestracao A→B→C→D→E→F |

#### Mapa detalhado funcao → linhas → side-effects → deps

| Funcao | Linhas | Side-effects | Deps Odoo | Deps DB | Notas |
|--------|--------|--------------|-----------|---------|-------|
| `_commit_resilient` | 158-210 | DB commit + rollback + close + **engine.dispose()** se SSL | - | session | **D14**: MAIS FORTE que `_commit_with_retry` do service — faz `engine.dispose()` proativo quando detecta SSL (não só rollback+close). Backoff exponencial 2s, 4s. |
| `validar_cadastro_fiscal` | 228-294 | (READ-only) | product.product | - | **G017 NCM strict raise + G018 weight=0 warn**. `modo` = strict\|warn\|skip. **Fonte para C5 v14b**. |
| `corrigir_weight_zero` | 297-343 | (READ-only despite name) | product.product | - | **G018 v2**: write NAO persiste em CIEL IT (hook reseta). Funcao so' detecta e loga. Fix REAL e' em `aplicar_peso_volumes_fallback_picking`. |
| `aplicar_peso_volumes_fallback_picking` | 346-413 | write stock.picking | stock.picking | - | **G018 v2 fix codificado**: escreve `l10n_br_peso_liquido`/`l10n_br_peso_bruto`/`l10n_br_volumes` (writable em picking). Chamado ENTRE F5b e F5c. |
| `carregar_ajustes` | 416-469 | (READ-only) | - | AjusteEstoqueInventario | Filtros: ciclo + company_id + status_filtro + onda (PERDA/INDUS/DEV/RENOMEAR) + cod_produto. `limite_produtos` limita N produtos distintos. |
| `etapa_a_transferencias_lote` | 501-613 | DB UPDATE fase_pipeline | (via Skill 2 atomo) | AjusteEstoqueInventario | **D13 + D15**: SEQUENCIAL (max_workers arg legacy/no-op — comentario L555 "XML-RPC nao thread-safe Request-sent"). Pre-snapshot D1 (L533-545). Idempotente via `TRANSF_OK`. **DELEGAVEL 100% para Skill 2**. |
| `etapa_b_pickings` | 624-1149 | create stock.picking + write moves + insert AjusteEstoqueInventario (compensatorio) | stock.quant, stock.lot, product.product, stock.picking, stock.move | AjusteEstoqueInventario | **D16**: `time.sleep(5)` entre chunks (G022 mitigation over-reservation). Pre-validacao fiscal G017 (L719-732, strict-aborta-etapa). Loop POR GRUPO (company_origem, tipo_op) SERIAL, dentro POR CHUNK SERIAL. Cada chunk: F5a → F5b → G018 fallback → F5c sequencial. **G014 PROTECTION**: lote vencido → transferir para lote novo on-the-fly. **G023**: respeitar lote_origem dos ajustes (nao FIFO automatico) + resolver sem-lote via FIFO descontando alocado. **Compensatorio**: se qty_restante > 0 e' PERDA_LF_FB → cria novo `AjusteEstoqueInventario('INDUSTRIALIZACAO_FB_LF', lote_destino='MIGRACAO', status='PROPOSTO')` para ondas futuras. |
| `etapa_c_aguardar_invoices` | 1156-1190 | (delegado a service) | (via service) | AjusteEstoqueInventario (via service) | Filtra `picking_id_odoo + F5c_LIBERADO + sem invoice_id_odoo`. Chama `pipeline_svc.f5d_aguardar_invoices` (D5/D6 do service §7.2). |
| `etapa_d_sefaz` | 1197-1232 | (delegado a service) | (via service) | AjusteEstoqueInventario (via service) | Filtra `invoice_id_odoo + F5d_INVOICE_GERADA`. Reduz para invoices distintas (D8 do service). Chama `pipeline_svc.f5e_transmitir_sefaz` (D7+D8+D9 do service §7.2). |
| `etapa_e_entrada_fb` | 1239-1421 | insert RecebimentoLf + RecebimentoLfLote; depois processa via service externo | account.move (READ) | AjusteEstoqueInventario, RecebimentoLf, RecebimentoLfLote | Filtra `ACOES_ENTRADA_FB = {PERDA_LF_FB, TRANSFERIR_CD_FB, DEV_LF_FB, DEV_CD_LF}` (sentido X→FB). Agrupa por invoice_id (1 NF = 1 RecebimentoLf). **D17**: `ACAO_PARA_CFOP_ENTRADA` mapeia 5xxx→1xxx (PERDA 5903→1903, TRANSFERIR 5152→1152, DEV 5949→1949). Idempotente via `RecebimentoLf.odoo_lf_invoice_id`. Re-fetch ajustes da invoice (anti-DetachedInstanceError D9). Chama `RecebimentoLfOdooService.processar_recebimento` (service externo modulo recebimento, sincrono). |
| `etapa_f_entrada_destino_manual` | 1428-1505 | (delegado a `_f_criar_entrada_destino_para_invoice`) | - | AjusteEstoqueInventario (via helper) | Filtra `ACOES_ENTRADA_DESTINO_MANUAL = {INDUSTRIALIZACAO_FB_LF}` (so' validado). Agrupa por invoice_id (1 NF = 1 picking entrada). |
| `_f_criar_entrada_destino_para_invoice` | 1508-1688 | create stock.picking + write stock.move (company_id) + write stock.move.line + action_confirm + action_assign + button_validate | account.move (READ), stock.picking, stock.move, stock.move.line | AjusteEstoqueInventario (UPDATE fase_pipeline) | **Origin**: `INV-{CICLO}-ENTRADA-{LABEL}-NF{invoice_id}` (idempotencia via origin). Lote MIGRACAO/vazio vira `INV-{cod}-{YYYYMMDD}` (consistente com pickings validados 317306/317316). **G023 critico (L1637-1640)**: forca `company_id` em moves apos create (XML-RPC nao herda). **G011 (L1646-1665)**: preencher `lot_name` + re-escrever `quantity` em move_lines. **G019/G020 (L1670-1676)**: re-le state e raise se != done. |

#### Pattern de orchestracao em main() (L1771-1860)

```python
if 'A' in etapas:
    etapa_a_transferencias_lote(odoo, ajustes, ...)
    db.session.expire_all()          # invalida ORM cache da sessao
    ajustes = carregar_ajustes(...)  # re-load do DB com fase_pipeline atualizada

if 'B' in etapas:
    etapa_b_pickings(odoo, ajustes, ...)
    db.session.expire_all(); ajustes = carregar_ajustes(...)

if 'C' in etapas:
    db.engine.dispose()              # G016 PROFILATICO antes de polling 1800s
    etapa_c_aguardar_invoices(odoo, ajustes, ...)
    db.engine.dispose()              # G016 PROFILATICO apos
    db.session.expire_all(); ajustes = carregar_ajustes(...)

if 'D' in etapas:
    db.engine.dispose()              # G016 PROFILATICO antes de Playwright 5-10min/NF
    etapa_d_sefaz(odoo, ajustes, ...)
    db.engine.dispose()
    db.session.expire_all(); ajustes = carregar_ajustes(...)

if 'E' in etapas:
    etapa_e_entrada_fb(odoo, ajustes, ...)
    db.session.expire_all(); ajustes = carregar_ajustes(...)

if 'F' in etapas:
    etapa_f_entrada_destino_manual(odoo, ajustes, ...)
    # NAO recarrega (e' ultima etapa)
```

**CONCLUSAO R1 ✅**: pattern do script **CONFIRMA decisao 10.3** (etapa = barreira de sincronizacao) em NIVEL MACRO (entre etapas A/B/C/D/E/F). Mecanismo: cada `if 'X' in etapas` aguarda etapa concluir → `expire_all()` + `carregar_ajustes()` (re-load com fase atualizada) → so' depois a proxima inicia. Etapas longas (C/D) ainda ganham `db.engine.dispose()` ANTES e APOS (G016 profilatico).

**Sub-nuance NIVEL MICRO em ETAPA B**: pipeline POR PICKING (criar→validar→liberar→sleep 5s→proximo) — NAO paraleliza N pickings entre si (G022 mitigation D16). Service `f5b_validar_pickings(ajustes_chunk)` PARALELIZA ajustes DENTRO de 1 picking (Semaphore=5), mas o script chama com 1 chunk de cada vez. **IMPLICACAO Skill 8 orchestrator v15**: preservar pattern intra-B (NAO criar N pickings em paralelo).

#### Descobertas-chave NOVAS D10-D18 (alem das D1-D9 do service §7.2)

**D10 — `db.engine.dispose()` PROFILATICO antes E apos ETAPAS C+D** (L1799-1813 / L1822-1844)
- Forca recriar conexoes DB que podem estar idle/SSL morto.
- Mais agressivo que `_commit_with_retry` do service (que age durante etapa).
- **APLICAR em Skill 8 orchestrator**: chamar antes/depois de F5d (polling 1800s) e F5e (Playwright 5-10min/NF).

**D11 — `db.session.expire_all() + carregar_ajustes()` ENTRE etapas** (L1777-1782 e similares)
- Invalida TODOS ORM objects da sessao e re-carrega do DB.
- Razao: etapas anteriores commitaram `fase_pipeline` atualizada; objetos stale na sessao poderiam ter dados antigos.
- **APLICAR em Skill 8 orchestrator**: re-carregar lista de ajustes entre cada etapa.

**D12 — `--apenas-etapa` + `--ate-etapa` para recovery operacional** (L1704-1707)
- Permite rodar etapas isoladas (`--apenas-etapa=C` para retomar polling) OU pipeline parcial (`--ate-etapa=B` para parar antes de SEFAZ).
- **CRITICO no Skill 8 CLI**: preservar como `--apenas-etapa` + `--ate-etapa` ou equivalente `--etapas LISTA`.

**D13 — ETAPA A e SEQUENCIAL** (loop principal L583 `for idx, snap in enumerate(snapshots, 1)`)
- `max_workers` arg existe mas e' legacy/no-op no loop principal.
- Comentario L555: `"SEQUENCIAL — conexao XML-RPC nao e thread-safe (Request-sent)"`.
- **IMPLICACAO Skill 8**: ETAPA A no orchestrator pode SER sequencial. Como sera' DELEGADA via Skill 2 (cada chamada e' processo separado = sem race), pode-se considerar paralelizacao via subprocess.

**D14 — `_commit_resilient` (script L158-210) MAIS FORTE que `_commit_with_retry` (service L165)**
- Script: detecta SSL via substring match em err.lower() + faz `engine.dispose()` proativo apos rollback+close.
- Service: so' rollback+close+retry (sem engine.dispose).
- **APLICAR em Skill 8 orchestrator**: usar versao MAIS FORTE (`_commit_resilient`-like) em commits criticos pos-Playwright/polling longo.

**D15 — ETAPA A 100% DELEGAVEL para Skill 2 `transferindo-interno-odoo`** (confirma §2.3)
- Usa apenas `StockInternalTransferService.transferir_quantidade_para_lote` (atomo Skill 2 ja existente).
- Skill 8 orchestrator NAO reimplementa — invoca Skill 2 via service direto (NAO subprocess CLI, pois e' chamado dentro do mesmo Python).

**D16 — `time.sleep(5)` entre chunks ETAPA B** (L1136-1138, comentario "G022 mitigation")
- Reduz over-reservation por reservas orfas em lote velho pos-renomeacao (ETAPA A pendentes).
- Tambem da' tempo de PgBouncer SSL/keepalive renovar conexao.
- **APLICAR em Skill 8 orchestrator**: preservar sleep entre criacao de pickings (mesmo no novo atomo Skill 5 `criar_picking_inter_company` C6.5).

**D17 — `ACAO_PARA_CFOP_ENTRADA` mapeia CFOP saida (5xxx) → CFOP entrada (1xxx)** (L1300-1305)
- PERDA_LF_FB: saida 5903 → entrada 1903
- TRANSFERIR_CD_FB: saida 5152 → entrada 1152
- DEV_LF_FB / DEV_CD_LF: saida 5949 → entrada 1949
- **Razao**: o Odoo da FB so' tem `fiscal_position` cadastrada para CFOPs de entrada (1xxx). Gravar 5xxx no `RecebimentoLfLote.cfop` causa "CFOP nao cadastrado".
- **APLICAR em Skill 8 orchestrator ETAPA E**: preservar mapa.

**D18 — Default `dry_run=True` + `--confirmar` para escrever** (L1708-1709)
- Pattern reuso v9 (Skill 6).
- `--confirmar-sefaz` adicional exige `--confirmar` para ETAPA D (irreversivel).
- **APLICAR em Skill 8 CLI**: mesmo pattern + 2 nivel de confirmacao para SEFAZ.

#### Dependencias externas confirmadas

| Dependencia | Onde | Notas |
|-------------|------|-------|
| `StockInternalTransferService` | `app.odoo.services.stock_internal_transfer_service` | DELEGADO Skill 2 (capinado v10-v12 — agora `app/odoo/estoque/scripts/transfer.py`) |
| `StockLotService` | `app.odoo.services.stock_lot_service` | Utility — resolve lote por nome |
| `StockPickingService` | `app.odoo.services.stock_picking_service` | DELEGADO Skill 5 (`app/odoo/estoque/scripts/picking.py`) — invocado em F5a via `criar_transferencia` (C6.5 v15 cria `criar_picking_inter_company`) |
| `InventarioPipelineService` | `app.odoo.services.inventario_pipeline_service` | Service-fonte ja' minerado §7.2 — F5b/F5c/F5d/F5e |
| `RecebimentoLfOdooService` | `app.recebimento.services.recebimento_lf_odoo_service` | Service EXTERNO modulo recebimento. ETAPA E o invoca SINCRONO via `processar_recebimento(rec.id, usuario_nome=...)`. **NAO mexer** — reuso como esta'. |
| `AjusteEstoqueInventario` | `app.odoo.models` | Model DB local — UPDATE `fase_pipeline`, `picking_id_odoo`, `invoice_id_odoo`, `chave_nfe`, `erro_msg`, `custo_medio` |
| `RecebimentoLf`, `RecebimentoLfLote` | `app.recebimento.models` | DB local — agg por (pid, lote_dest, cfop) com qty |
| `COMPANY_LOCATIONS`, `COMPANY_PARTNER_ID`, `ACAO_PARA_DIRECAO`, `PICKING_TYPE_POR_DIRECAO` | `app.odoo.constants` | Ja' centralizado |
| `ACAO_PARA_CFOP_ENTRADA` (inline L1300-1305) | script | **NAO centralizado** — Skill 8 deve centralizar em `app/odoo/constants/operacoes_fiscais.py` |
| `ACOES_ENTRADA_FB` (inline L1261-1263) | script | **NAO centralizado** — Skill 8 deve centralizar |
| `ACOES_ENTRADA_DESTINO_MANUAL`, `PICKING_TYPE_ENTRADA_DESTINO_MANUAL`, `COMPANY_LABEL_ENTRADA`, `LOCATION_ORIGEM_ENTRADA_INDUSTR` (L126-146) | script | **NAO centralizado** — Skill 8 deve centralizar |

#### Resposta R1 (revalidar 10.3)

✅ **R1 CONFIRMA decisao 10.3** (etapa = barreira) em NIVEL MACRO.
🟡 **Sub-nuance** documentada: dentro de ETAPA B, pipeline por picking com `sleep 5s` (G022). Decisao 10.3 INTACTA. **NAO requer AskUserQuestion adicional**.

**Recomendacao para §6.2 + v15 orchestrator**:
- Macro: etapa = barreira (todos pickings → expire_all → re-load → todas validacoes → expire_all → ...)
- Micro ETAPA B: pipeline por picking (criar 1 → validar 1 → liberar 1 → sleep 5s → criar 2 → ...)
- Micro outras etapas: ja' sequencial natural (C polling longo, D Playwright serial, E/F idempotente por invoice_id)

#### Gotchas DESTACADOS adicionais (v14a-fix)

**G-ETB-COMPENSATORIO (ETAPA B L994-1031) — regra de negocio CRITICA**:
- Quando `qty_restante > 0` (demand > disponivel) em PERDA_LF_FB, script cria NOVO `AjusteEstoqueInventario` com:
  - `acao_decidida='INDUSTRIALIZACAO_FB_LF'`
  - `lote_destino='MIGRAÇÃO'`
  - `status='PROPOSTO'`
  - `origem_ajuste_id=ajustes_produto[0].id`
  - `erro_msg='[COMPENSATORIO_FALTA_ESTOQUE] Compensatorio origem_ajuste=...'`
- **So' aplicavel quando** `tipo_op='perda' AND company_origem=5 (LF)`.
- **Skill 8 orchestrator deve preservar esse comportamento** (caso contrario operador fica com ajuste sem rastro de "porque nao executou totalmente").
- **PRESERVAR em v15b (C7)** quando capinar F5a no orchestrator: replicar logica + commit + atualizar plano_de_acao se necessario.

**G-ETB-G014 (ETAPA B L795-917) — lote vencido on-the-fly via Skill 2**:
- Detecta `quants_vencidos` (lote `expiration_date < HOJE`) que tem saldo livre.
- Se `livre_validos < demand_total` e `livre_vencidos > 0`:
  - Calcula `qty_a_migrar = min(demand_total - livre_validos, livre_vencidos)`.
  - Cria lote novo on-the-fly: `nome_lote_novo = f'INV-{cod}-{HOJE.strftime("%Y%m%d")}'` com `EXP_NOVO_LOTE = HOJE + 365 dias`.
  - Chama `StockInternalTransferService.transferir_quantidade_para_lote` (atomo Skill 2 ja existente — `transferir_quantidade_para_lote_v2`?) para mover qty vencida → lote novo.
  - Re-consulta quants apos transferencia + refaz split validos/vencidos.
- **Skill 8 orchestrator deve preservar esse comportamento em v15b (C7)** — fluxo Skill 2 dentro de C7 (criar picking) ANTES de criar moves do picking.
- **GOTCHA HIDDEN**: a chamada `transferir_quantidade_para_lote` PROVAVELMENTE NAO usa o atomo Skill 2 v2 com guard `delta_esperado` (Skill 2 atual). Verificar se script usa versao v1 ou v2 — se v1, atualizar para v2 no orchestrator Skill 8.

---

## 7.4 Mineracao service externo `RecebimentoLfOdooService` (v14a-fix — READ-ONLY, NAO MEXER)

### 7.4.1 Por que existe esta secao

A ETAPA E do orchestrator Skill 8 chama `RecebimentoLfOdooService().processar_recebimento(rec.id)` — service GIGANTE (4562 LOC, 37 sub-etapas em 7 fases) que NAO sera' minerado em detalhe (DELEGADO — reuso como esta'). Esta secao documenta o **INTERFACE + GOTCHAS** que afetam a Skill 8.

**REGRA INVIOLAVEL**: **NUNCA MEXER** em `app/recebimento/services/recebimento_lf_odoo_service.py`. Skill 8 INVOCA via interface publica (`processar_recebimento` ou `processar_transfer_only`).

### 7.4.2 Arquitetura do service (do docstring L1-77)

**Pattern**: Checkpoint por Etapa + Fire and Poll
- Cada etapa: (1) Guard `if etapa_atual >= N` skip; (2) Idempotencia (le Odoo); (3) Execute (write/fire+poll); (4) Checkpoint (`etapa_atual=N + IDs locais`)
- **Fire and Poll** (etapas 4, 7, 8, 12, 13, 16): dispara com `FIRE_TIMEOUT=120s`, se timeout OK (continua no Odoo), poll a cada `POLL_INTERVAL=10s` ate `MAX_POLL_TIME=1800s` (30min)
- **Resiliencia**: anti-DetachedInstanceError (re-busca recebimento por step), `_checkpoint` SSL-safe com `engine.dispose()` + exponential backoff
- **Recovery**: `_recover_state_from_odoo` le Odoo (PO/picking/invoice state) para ajustar `etapa_atual` em retomada

### 7.4.3 Mapa das 7 fases (steps 0 a 37)

| Fase | Steps | Conteudo | Tempo tipico |
|------|-------|----------|--------------|
| **1 — Preparacao DFe FB** | 1, 2, 3 | Buscar DFe + avancar status + configurar (data_entrada, tipo_pedido) | < 1min |
| **2 — Gerar PO FB** | 4, 5, 6, 7, 8 | action_gerar_po_dfe [fire_and_poll] + extrair PO + configurar + confirmar [fire_and_poll] + aprovar [fire_and_poll] | 3-15min |
| **3 — Picking FB** | 9, 10, 11, 12 | Buscar picking + preencher lotes (CFOP!=1902 manual) + aprovar QC + validar [fire_and_poll] | 2-10min |
| **4 — Fatura FB** | 13, 14, 15, 16 | Criar invoice [fire_and_poll] + extrair + configurar + post [fire_and_poll] | 3-15min |
| **5 — Finalizacao FB** | 17, 18 | Atualizar status local + criar MovimentacaoEstoque | < 1min |
| **6 — Transfer FB→CD (saida)** | 19, 20, 21, 22, 23 | Filtrar acabados + criar picking saida FB + validar + liberar + transmitir NFe Playwright | 5-30min (Playwright + SEFAZ) |
| **7 — Recebimento CD via DFe** | 24-37 | Upload DFe CD + gerar PO CD + processar picking CD + criar invoice CD + finalizar | 10-30min |
| **TOTAL POR INVOICE** | - | - | **30-60min**, ate' 90min sob carga |

**FASE 6+7 PODE FALHAR** sem derrubar FASE 1-5: `_safe_update(transfer_status='erro', ...)` e nao re-raise. Recebimento FB ja' esta OK; Rafael pode rodar `processar_transfer_only(rec.id)` depois.

### 7.4.4 Mapa entry-points + helpers criticos

| Funcao | Linhas | Side-effects | Notas |
|--------|--------|--------------|-------|
| `processar_recebimento(recebimento_id, usuario_nome=None)` | 148-280 | Pipeline completo 38 steps + write `RecebimentoLf` extensivo | **Entry-point chamado pela ETAPA E do orchestrator Skill 8**. Sincrono. Pode raisar Exception apos FB OK se FASE 6+7 falhar. |
| `processar_transfer_only(recebimento_id)` | 282-364 | Pipeline FASE 6+7 (steps 19-37) | Retry isolado pos-FB-OK. Skill 8 NAO usa diretamente (chama processar_recebimento que faz tudo). |
| `_get_recebimento()` | 370-383 | (READ) | Re-busca via `db.session.get(RecebimentoLf, id)` com fallback rollback (anti-DetachedInstanceError). |
| `_safe_update(tentativas_increment=False, **fields)` | 385-429 | DB commit com retry 3x + `engine.dispose()` + exponential backoff (0.5s,1s,2s) | **G-RECLF-4**: versao MAIS FORTE que `_commit_with_retry` (lista de erros recoveraveis mais ampla: ssl/decryption/bad record/not bound/DetachedInstanceError). |
| `_checkpoint(etapa, fase=None, msg='', **extra_fields)` | 439-528 | DB commit + Redis polling update + log | Calcula fase automaticamente: 1-3→1, 4-8→2, 9-12→3, 13-16→4, 17-18→5, 19-23→6, 24-37→7. SSL-safe com 3 retries. |
| `_write_and_verify(odoo, model, record_id, values, step_name, critical_fields=None)` | 530-590 | write + read-back | Verifica campos criticos (raise ValueError se divergir). Normaliza Odoo `False`→`None` e many2one `[id, name]`→`id`. |
| `_recover_state_from_odoo(odoo)` | 592-832 | DB read + UPDATE `etapa_atual` + `odoo_*_id/name` | Le Odoo para PO/Picking/Invoice/Transfer states; ajusta `etapa_atual` baseado em `po.state`/`picking.state`/`invoice.state`. Roda apenas se `etapa_atual > 0`. |

### 7.4.5 Constants HARDCODED no service (potencial conflito com Skill 8)

| Constant | Valor | Onde tambem aparece | Risco |
|----------|-------|---------------------|-------|
| `COMPANY_FB` | 1 | `app/odoo/constants/locations.py` `CODIGO_PARA_COMPANY_ID['FB']` | OK (consistente) |
| `COMPANY_LF` | 5 | idem | OK |
| `COMPANY_CD` | 4 | idem | OK |
| `TEAM_ID` | 119 | inline | Skill 8 NAO usa team_id (so' RecebimentoLf) — sem conflito |
| `PAYMENT_PROVIDER_ID` (FB) | 92 | inline | Skill 8 usa `PAYMENT_PROVIDER_SEM_PAGAMENTO=38` (G029) — **DIFERENTE** mas OK (RecebimentoLf usa "Transferencia Bancaria" para entrada FB; Skill 8 usa "Sem Pagamento" para inter-company inventario) |
| `PAYMENT_PROVIDER_ID_CD` | 30 | inline | idem — diferente proposito |
| `PAYMENT_TERM_A_VISTA` | 2791 | inline | Skill 8 nao define payment_term em invoice (vem do POs) — sem conflito |
| `PAYMENT_TERM_CD` | 2800 | inline | idem |
| `PICKING_TYPE_FB` | 1 | `app/odoo/constants/picking_types.py` `PICKING_TYPE_POR_DIRECAO` | Verificar se entra na MATRIZ Skill 8 |
| `PICKING_TYPE_OUT_FB` | 51 | inline | Skill 8 nao usa (RecebimentoLf cria picking de saida proprio) |
| `PICKING_TYPE_IN_CD` | 13 | inline | Skill 8 nao usa |
| `PARTNER_CD_IN_FB` | 34 | `app/odoo/constants/operacoes_fiscais.py` `COMPANY_PARTNER_ID[4]=34` | OK (consistente) |
| `LOCATION_FB_ESTOQUE` | 8 | `COMPANY_LOCATIONS[1]=8` | OK |
| `LOCATION_CD_ESTOQUE` | 32 | `COMPANY_LOCATIONS[4]=32` | OK |
| `LOCATION_CLIENTES` | 5 | nao centralizado | Skill 8 nao usa |
| `CARRIER_ID_FB` | 996 | `ids_diversos.py` `CARRIER_NACOM=996` | OK |
| `CNPJ_FB` | '61.724.241/0001-78' | inline | Skill 8 usa partner_id, nao CNPJ direto |
| `FIRE_TIMEOUT`, `POLL_INTERVAL`, `MAX_POLL_TIME` | 120, 10, 1800 | inline | Skill 8 ETAPA E timeout deve respeitar 1800s (30min/invoice) |
| `PLAYWRIGHT_MAX_TENTATIVAS`, `PLAYWRIGHT_INTERVALO_RETRY` | 15, 120 | inline | **Sobreposto com F5e do service inventario_pipeline_service** que tambem usa Playwright SEFAZ. **GOTCHA G-RECLF-9**: se ETAPA D do orchestrator Skill 8 esta rodando E ETAPA E dispara `_step_23_transmitir_nfe_transferencia` do RecebimentoLfOdooService ao mesmo tempo → 2 instancias Playwright concorrentes podem dar conflito SEFAZ |

### 7.4.6 Gotchas CRITICOS para Skill 8 ETAPA E (11 itens G-RECLF-1 a G-RECLF-11)

| # | Gotcha | Impacto Skill 8 | Mitigacao no orchestrator v17 |
|---|--------|-----------------|------------------------------|
| **G-RECLF-1** | 30-60min por invoice (37 etapas + fire_and_poll 6x). Onda 100 invoices = 50-100 horas. | Bulk ETAPA E NAO E' SINCRONO viavel para grandes ondas | **OPCAO A**: assincrono via RQ worker (job por invoice); ETAPA E so' enfileira + monitora. **OPCAO B**: paralelizar invoice_ids distintos (cada `processar_recebimento` em thread/processo separado) — mas RecebimentoLfOdooService PROVAVELMENTE nao e' thread-safe (Redis state). **DECIDIR em v17.** |
| **G-RECLF-2** | FASE 6+7 (steps 19-37) pode falhar sem derrubar FASE 1-5 (FB OK) | Skill 8 ETAPA E deve aceitar `transfer_status='erro'` como sucesso parcial (FB OK suficiente para inventario) | Checar `rec.status='processado' AND rec.transfer_status IN ('concluido', 'erro')` apos cada processar_recebimento |
| **G-RECLF-3** | Recovery automatico via `_recover_state_from_odoo` reduz necessidade de re-disparar | Skill 8 NAO precisa re-chamar se ja' `rec.status='processado'` (idempotencia ja' codificada em ETAPA E) | Pre-check: `if existente AND existente.status == 'processado': skip` (ja' codificado em ETAPA E L1335-1338) |
| **G-RECLF-4** | `_safe_update`/`_checkpoint` versao MAIS FORTE que `_commit_with_retry` (D14) — `engine.dispose()` + 0.5/1/2s backoff + lista ampla de erros | **D14 NAO E' SUFICIENTE** para Skill 8 sozinho — esta versao do RecebimentoLfOdoo tem padroes mais agressivos. Considerar consolidar AMBOS em util compartilhada | Usar versao MAIS FORTE em todo o orchestrator Skill 8 (alias `commit_resilient_strong`) |
| **G-RECLF-5** | Service usa `commit_with_retry(db.session)` de `app.utils.database_retry` em `_recover_state_from_odoo` (L825) | Utility ja' existe e e' reusada — Skill 8 deve preferi-la em vez de re-implementar | Importar `from app.utils.database_retry import commit_with_retry` no orchestrator Skill 8 |
| **G-RECLF-6** | PAYMENT_PROVIDER_ID hardcoded (FB=92, CD=30) — diferente do que Skill 8 usa (38 SEM PAGAMENTO) | NAO CONFLITA (propositos diferentes), mas se Skill 8 centralizar journals (D17) deve cuidar para nao tocar nesses | Documentar em comentario do D17 centralizado: "NAO migrar PAYMENT_PROVIDER_ID=92/30 — sao do RecebimentoLfOdooService, proposito diferente" |
| **G-RECLF-7** | PICKING_TYPE_OUT_FB=51 (Expedicao Entre Filiais) e PICKING_TYPE_IN_CD=13 — diferentes da MATRIZ Skill 8 | Skill 8 cria picking de SAIDA de inventario (PICKING_TYPE_POR_DIRECAO matrices); RecebimentoLfOdoo cria picking saida FB para transferir → CD apos invoice posted | **Sem conflito**, mas confirmar em v17 que MATRIZ_INTERCOMPANY nao colide quando ETAPA E roda em paralelo com mesmo invoice |
| **G-RECLF-8** | PARTNER_CD_IN_FB=34 — mesmo CD partner_id que Skill 8 (consistente) | OK | - |
| **G-RECLF-9** | Playwright SEFAZ no `_step_23` (transmite NFe transferencia FB→CD) — **mesma infra Playwright** que F5e do service inventario_pipeline | **RISCO ALTO**: se ETAPA D do orchestrator Skill 8 dispara F5e (SEFAZ) E em PARALELO a ETAPA E processa step_23 do RecebimentoLfOdoo (que tambem SEFAZ) → 2 instancias Playwright concorrentes. SEFAZ pode rejeitar; sessao Odoo UI pode expirar | **MITIGACAO**: serializar ETAPA D vs ETAPA E (etapa-barreira ja' faz isso!). Nunca rodar D e E concorrentemente. Garantir ETAPA E so' inicia depois de D 100% concluir. **JA' coberto pelo pattern macro etapa = barreira (decisao 10.3)** ✓ |
| **G-RECLF-10** | `processar_transfer_only` exige `rec.status == 'processado'` (FB OK) | Skill 8 NAO usa diretamente; se ETAPA E falhar com FB OK mas FASE 6+7 erro, Rafael pode chamar manual | Documentar em SKILL.md recovery: "para retry FASE 6+7: `RecebimentoLfOdooService().processar_transfer_only(rec_id)`" |
| **G-RECLF-11** | Reset etapa para 18 se `etapa_atual >= 19 AND transfer_status in ('erro', 'pendente', 'processando')` (L320) | Idempotencia para retry FASE 6+7 | OK — Skill 8 nao precisa replicar |

### 7.4.7 Dependencias adicionais

- `app.utils.database_retry.commit_with_retry` — utility de commit SSL-safe (mais simples que `_safe_update`). Skill 8 deve usar.
- `app.utils.timezone.agora_utc_naive` — helper de timezone naive (regra projeto).
- `redis.Redis` — para `_atualizar_redis` (polling tela de status). **Skill 8 NAO precisa**.
- `app.recebimento.models.RecebimentoLf` — model DB local. Skill 8 ETAPA E cria registro + invoca service.

### 7.4.8 Conclusao para Skill 8

1. **NAO MEXER no service** (4562 LOC validados em PROD durante meses).
2. **ETAPA E do orchestrator Skill 8 deve INVOCAR `processar_recebimento(rec_id)`** como ja' faz o script `09_executar_onda1_bulk.py` (L1413).
3. **Aceitar `transfer_status='erro'` como sucesso parcial** (FASE 6+7 podem falhar sem derrubar FB).
4. **Idempotencia ja' codificada**: pre-check `existente AND status='processado'` antes de re-chamar.
5. **Decidir paralelismo em v17** (G-RECLF-1): assincrono via RQ vs paralelo invoice_ids vs sequencial.
6. **Serializar ETAPA D vs ETAPA E** (G-RECLF-9 — Playwright concorrente). **JA' coberto pelo etapa = barreira (decisao 10.3)** ✓.
7. **Consolidar commit_with_retry** com versao MAIS FORTE (G-RECLF-4 + D14): usar util compartilhada `app.utils.database_retry.commit_with_retry` ou criar `app/odoo/estoque/scripts/_commit_helpers.py`.

---

## 7.5 DIFICULDADES OPERACIONAIS DESCOBERTAS (teste real 6 cods 2026-05-25 v14a-ops)

> **Origem**: Rafael solicitou teste real de faturamento LF→FB + transferencia para Indisp/MIGRACAO de 6 cods (102020600, 4829046, 4879046, 103500105, 4849003, 4759598). Operacao COMPLETA em 22min (script 09 ~10min + Skill 5 cancelamento + Skill 2 distribuir + workaround). **5/6 cods OK na 1a rodada**, 1 cod (103500105 tracking='none') exigiu workaround. **Resultado: 654.385 un movidas LF/Estoque → SEFAZ → FB/Indisp/MIGRACAO + 41.56 un do 103500105 via workaround.** Esta secao registra as **dificuldades reais** descobertas que a Skill 8 (v15+) deve eliminar.

### 7.5.1 DIFICULDADE 1 — CICLO hardcoded no script 09 (L112)

**Sintoma**: `CICLO = 'INVENTARIO_2026_05'` hardcoded em `09_executar_onda1_bulk.py:112` impede ciclos isolados de teste. Forcou mover 6 ajustes antigos para `status='REPROCESSADO_v14a'` (varchar(20) — limite curto!) e meus 6 novos do ciclo `TESTE_v14a_FAT_LF_FB_6CODS` para `INVENTARIO_2026_05`.

**Impacto Skill 8 v15+**: orchestrator NAO pode ter ciclo hardcoded. Aceitar `--ciclo NOME` como argumento OBRIGATORIO. Pre-flight de duplicacao (DIFICULDADE 2) elimina necessidade de "fundir" ciclos.

**Side-finding**: `ajuste_estoque_inventario.status` e' `varchar(20)` — nomes como 'CANCELADO_v14a_compensatorio' (28 chars) sao rejeitados. Limite curto demais para status descritivos. **Migration futura**: aumentar para `varchar(40)` ou `varchar(60)`.

### 7.5.2 DIFICULDADE 2 — Falta pre-flight de DUPLICACAO + propagacao falso F5e_SEFAZ_OK

**Sintoma**: descobri que os 6 cods JA estavam em pipeline ativo do `INVENTARIO_2026_05`:
- 2 EXECUTADO/F5e_SEFAZ_OK (NF 629363 RETNA/00035 cancelada + pickings com return done = saldo voltou)
- 4 PROPOSTO/F5c_LIBERADO (pickings done sem invoice, robo CIEL IT nunca criou)

Script 09 NAO detectou essa duplicacao. Permitiu criar novos pickings/NFs sem aviso (so o filtro `fase_pipeline not in (F5a..F5e)` impede re-criacao do mesmo cod no mesmo pipeline).

**Falso positivo F5e_SEFAZ_OK** (DERIVADA crítica de DIFICULDADE 2 + 3): ajuste 172261 (103500105 PERDA) foi marcado `EXECUTADO/F5e_SEFAZ_OK` mesmo NAO estando na linha da NF 709837 (que so' contem 102020600). Razao: `inventario_pipeline_service.py:f5e_transmitir_sefaz` propaga `chave_nfe` para TODOS ajustes do mesmo `invoice_id_odoo` (linha 1245 — `F5e ajuste X replicado de invoice Y`), sem verificar se o ajuste tem linha real na invoice. Compensatórios (criados por bug L965) ficam falsamente "autorizados".

**Impacto Skill 8 v15+**:
- **Pre-flight obrigatorio em C5** (sub-skill `auditando-cadastro-fiscal-odoo` perfil `inventario`): validar `NAO ha ajuste do mesmo cod/company em fase F5a..F5e_SEFAZ_OK no mesmo ciclo`. Se houver, abortar com mensagem clara (operador decide: cancelar/aguardar/forcar).
- **Fix F5e propagacao**: em vez de replicar chave para TODOS ajustes do invoice, replicar so' para ajustes que TEM linha real na invoice. Cross-ref via `account.move.line.product_id` ↔ `aj.cod_produto`. Compensatórios ficam em fase `F5e_SKIP_COMPENSATORIO` (novo status).

### 7.5.3 DIFICULDADE 3 — Bug tracking='none' em ETAPA B (L965)

**Sintoma**: cod 103500105 (PIMENTA JALAPENO, tracking='none') tinha 41.56 un em LF/Estoque (sem lot_id, conforme tracking=none). Ajuste original tinha `lote_origem=None`, foi para `ajustes_sem_lote` (L932). Loop FIFO em `quants_validos` (L962) tem:
```python
for q in quants_validos:
    if qty_a_distribuir <= 0.001: break
    if not q.get('lot_id'):
        continue   # <-- BUG: pula quants sem lot_id
    ...
```
Quants sem lot_id sao PULADOS — mas e' exatamente onde tracking='none' guarda saldo. Resultado: script gera `qty_restante=41.56 sem estoque para resolver` (warning L988-991) + cria compensatorio `INDUSTRIALIZACAO_FB_LF PROPOSTO` (L1009-1025) que viraria saldo positivo na LF — sentido inverso e SEM SENTIDO operacional para tracking=none.

**Workaround v14a-ops**: criar ajuste com `lote_origem='SEMLOTE'` (string nao-vazia dummy) — forca entrada em `ajustes_com_lote` (L944) que cria linha com `lot_name='SEMLOTE'`. Odoo aceita `lot_name` em move para produto tracking='none' (ignora — nao cria stock.lot). Validado em PROD: 103500105 41.56 un faturado via NF nova.

**Impacto Skill 8 v15+**:
- **Fix no atomo Skill 5 `criar_picking_inter_company`** (C6.5 v15a): no helper que monta `linhas` para o move, detectar `produto.tracking == 'none'` e:
  - SE `aj.lote_origem` vazio → criar move SEM lot_name (apropriado para tracking=none)
  - SE `aj.lote_origem` preenchido → ignorar (tracking=none nao usa lote)
- **NAO portar o bug L965** para o novo atomo. Quants sem lot_id de produto tracking='none' devem ser ACEITOS no FIFO `quants_validos`.

### 7.5.4 DIFICULDADE 4 — Picking automatico pos-RecLF (FB/INT/08056) SEM MO

**Sintoma**: ETAPA E (RecebimentoLfOdooService) processou 2 invoices com sucesso. Apos, os 4 cods DEV (4759598, 4829046, 4849003, 4879046) apareceram em FB/Estoque com `reserved_quantity == quantity` (saldo 100% reservado). Investigacao revelou picking `FB/INT/08056` (id 321341):
- state=`assigned`, type=`FB: Transferencias Internas`
- src=FB/Estoque → dst=Estoque Virtual/Producao
- `origin=False`, `raw_material_production_id=False`, `production_id=False`, `group_id=False`
- Criado **automaticamente pelo Odoo** apos o robo CIEL IT processar invoice da entrada FB

E' um picking SOLTO (sem MO associada) que reservaria saldo para transferir para Producao. Sem cancelar, **Skill 2 falha** (Modo C tenta reduzir quant reservado).

**Workaround v14a-ops**: Skill 5 modo `cancelar` em FB/INT/08056 (cancelou em 1s, liberou reserva). Skill 2 prosseguiu sem problema.

**Impacto Skill 8 v15+**:
- **Pos-ETAPA E hook**: orchestrator deve **detectar pickings automaticos pos-RecLF com origin=False + reservando saldo recem-recebido** e cancela-los proativamente. Cross-ref: para cada `picking_id` resultante do RecebimentoLfOdooService.step_09 (buscar_picking) que esteja em state=done, listar `stock.picking` que **reservam quants criados por aquele picking** com `origin=False` e cancelar (Skill 5).
- Alternativa: detectar via heuristica (`origin=False AND src=FB/Estoque AND dst=Estoque Virtual/Producao AND group_id=False`).

### 7.5.5 Resumo das 4 dificuldades + side-findings

| # | Dificuldade | Severidade | Mitigacao Skill 8 v15+ |
|---|-------------|------------|------------------------|
| **D-OPS-1** | CICLO hardcoded | Media | `--ciclo NOME` arg obrigatorio |
| **D-OPS-1b** | `ajuste_estoque_inventario.status` varchar(20) | Baixa | Migration: varchar(40+) |
| **D-OPS-2** | Falta pre-flight de duplicacao | Alta | C5 sub-skill faz pre-flight; aborta se cod em pipeline ativo |
| **D-OPS-2b** | F5e propaga chave para ajustes sem linha real (falso positivo) | Alta (auditoria) | Fix em `f5e_transmitir_sefaz`: replicar so' para ajustes com linha na invoice |
| **D-OPS-3** | Bug L965 tracking='none' no script 09 | Alta | Novo atomo Skill 5 detecta tracking='none' + aceita quants sem lot_id |
| **D-OPS-4** | Picking automatico pos-RecLF SEM MO | Media | Pos-hook ETAPA E detecta+cancela pickings com `origin=False` reservando saldo recem-recebido |
| **D-OPS-5** | Skill 2 `_listar_quants_origem` tambem filtra `lot_id != False` (L1145+1147) | Alta | Adicionar `aceita_tracking_none=True` default; modo C precisa lidar com `lot_id_origem=None` |

### 7.5.6 Validacao do workaround D-OPS-3 em PROD (16:43-16:51 — 8min)

- ✅ Compensatorio 172264 cancelado (status='CANCEL_v14a_BUG')
- ✅ Novo ajuste 172265 criado (PERDA_LF_FB, lote_origem='SEMLOTE')
- ✅ Script 09 ETAPA B-E COMPLETO em ~5min:
  - Picking 321351 criado (1 ajuste, 1 linha, **0 compensatorios** — workaround funcionou!)
  - Invoice 709989 criada CIEL IT
  - NF RETNA/2026/00090 SEFAZ-OK (chave 35260518467441000163550010000132451007099890)
  - RecLF 68 criado (DFe=43417, PO=C2619538, Picking=FB/IN/13325, Invoice 709995 posted)
- ✅ **Side-finding D-OPS-5**: Skill 2 `transferindo-interno-odoo` **TAMBEM tem o bug** L1145+1147 (`domain.append(['lot_id', '!=', False])`) — mesmo padrao de exclusao de quants sem lot_id. FALHA_SEM_QUANT para tracking='none'.
- ✅ **Workaround aplicado**: 2 Skill 1 calls em vez de Skill 2:
  - PASSO 1: `ajustar_quant --quant-id 264041 --valor-absoluto 0 --confirmar` (FB/Estoque 41.56 → 0)
  - PASSO 2: `ajustar_quant --quant-id 255309 --delta 41.56 --confirmar` (FB/Indisp/MIGRAÇÃO 881.34 → 922.9)
- ✅ Validacao FINAL: cod 103500105 100% em FB/Indisponivel/MIGRAÇÃO (922.9 un)

### 7.5.7 DIFICULDADE 5 — Skill 2 tambem filtra quants sem lot_id (D-OPS-5 NOVA v14a-ops)

**Sintoma**: Skill 2 `distribuir_para_indisponivel` (helper alto-nivel) chama `_listar_quants_origem` que aplica `domain.append(['lot_id', '!=', False])` em `app/odoo/estoque/scripts/transfer.py:1145+1147`. Para produto tracking='none' (sem lot_id), retorna `quants_disponiveis=0` → `FALHA_SEM_QUANT`.

**Workaround v14a-ops**: 2 calls Skill 1 (`ajustar_quant`) em vez de Skill 2. Funcional mas viola principio "1 chamada de alto-nivel".

**Impacto Skill 8 v15+ + Skill 2 atual**:
- **Fix em Skill 2 `_listar_quants_origem`** (NOVA tarefa para Rafael decidir): adicionar parametro `aceita_tracking_none=True` (default) que NAO aplica filtro `['lot_id', '!=', False]`. Modo C `distribuir_para_indisponivel` precisa lidar com isso especialmente — `lot_id_origem=False` na chamada de `ajustar_quant`.
- Atualizar memoria `[[skill2_distribuir_indisp_pattern]]` com esse caso.

### 7.5.8 Resumo executivo (workflow v14a-ops 16:00-16:51, 51min)

| Etapa | Tempo | Resultado |
|-------|-------|-----------|
| Pre-flight 6 cods | ~1min | OK (G017+G018+saldo); G035 detectou 2 barcodes invalidos |
| Mover ciclo (UPDATE DB local) | ~30s | 6 antigos→REPROCESSADO_v14a; 6 novos→INVENTARIO_2026_05 |
| G035 fix + criar AjusteEstoqueInventario | ~5s | 2 barcodes limpos + 6 ajustes APROVADOS |
| Script 09 ETAPAS A→E (5 cods, 1 compensatorio) | ~10min | 2 pickings + 2 invoices + 2 NFs SEFAZ-OK + 2 RecLF OK |
| Cancelar FB/INT/08056 (libera reserva) | ~1s | state=assigned→cancel |
| Skill 2 distribuir 5 cods | ~10s | 5/5 EXECUTADO_TOTAL, 654.385 un |
| Workaround 103500105 (cancelar comp + criar novo ajuste + script 09 + Skill 1 x2) | ~10min | NF RETNA/2026/00090 SEFAZ-OK + 41.56 un consolidados em FB/Indisp/MIGRAÇÃO |
| **TOTAL** | **51min** | **6/6 cods 100% OK, 695.945 un consolidadas em FB/Indisp/MIGRAÇÃO + 3 NFs SEFAZ autorizadas** |

**5 dificuldades reais identificadas** (D-OPS-1, -2, -3, -4, -5) — Skill 8 v15+ deve eliminar todas.

---

## 8. RISCOS ARQUITETURAIS E MITIGACAO

### 8.1 PRE-MORTEM v13 (decisoes tomadas nesta sessao — leitura OBRIGATORIA em v14)

> Imaginando 6 meses adiante: "por que a Skill 8 nao foi entregue como planejei nesta sessao v13?"

#### Riscos arquiteturais (decisoes RESOLVIDAS v13)

| # | Risco | Prob | Impacto | Mitigacao |
|---|-------|------|---------|-----------|
| **R1** | **"Etapa = barreira" pode NAO ser o padrao do script atual** (decidido 10.3 ANTES de minerar `09_executar_onda1_bulk.py`). Service paraleliza intra-etapa, mas script pode encadear A→B→C→D→E→F por ajuste em vez de aguardar 100% completar cada etapa. | Alta | Alto | **C3 v14 PRIMEIRO**: confirmar pattern real do script ANTES de codar orchestrator v15. Se contradisser 10.3, re-validar com Rafael |
| **R2** | **Refatoracao F5a/F5b para Skill 5 pode QUEBRAR a Skill 5 madura** (42 pytest verdes). Adicionar `criar_picking_inter_company` encapsulando G004/G023/partner/company/carrier/incoterm vira "atomo Frankenstein" — viola atomicidade | Media-Alta | Alto | C6.5 deve ter pytest >10 verdes ANTES de C7/C8; canary obrigatorio em picking real |
| **R3** | **Sub-skill `auditando-cadastro-fiscal-odoo` viola "skills nascem de demanda real"** (feedback Rafael). Capinar com perfil V1 + estrutura para perfis futuros NAO existentes ainda. Demanda atual: 1 perfil so' | Alta | Medio | V14 C5: implementar perfil V1 INLINE; estrutura de perfis SO' quando 2o perfil chegar |
| **R4** | **Decisao 10.5 desfaz simplicidade**: pre-flight como entry-point Skill 8 = 1 comando; sub-skill separada = 2 comandos + cross-refs + subprocess + risco divergencia | Media | Medio | Documentar TRADE-OFF no SKILL.md: "ganha reuso futuro; perde simplicidade atual" |
| **R5** | **D2 "agrupamento por picking" mascara erros parciais**: 1 picking com 5 ajustes onde so 1 tem qty errada marca TODOS como F5b_FALHA. Operador pensa que problema e' global | Media | Medio | Refatoracao C8: marcar falha INDIVIDUAL no ajuste problematico + warning no picking grupo (nao FALHA cega) |

#### Riscos de execucao (proximas sessoes v14-v20)

| # | Risco | Prob | Impacto | Mitigacao |
|---|-------|------|---------|-----------|
| **R6** | **C3 mineracao 1850 LOC consome 80% do contexto de v14**, sem sobrar para C5 | Alta | Medio | Dividir v14: **v14a so C3 + decisao R1** (~80k tokens); **v14b so C5** (sessao fresca) |
| **R7** | **C6.5 + C7/C8 no mesmo v15 = sobrecarga**. Estender Skill 5 (2 atomos + 10 pytest + dry-run) + implementar 2 etapas orchestrator e' >1 sessao | Alta | Medio | Dividir v15: **v15a so C6.5** (Skill 5 estendida + canary); **v15b C6/C7/C8** (orchestrator + F5a/F5b) |
| **R8** | **Mock Playwright em pytest e' fragil**. F5e tem ~250 LOC + 3 caminhos erro + idempotencia tripla. Mock simplista mascara bug real | Media | Alto (NF errada PROD) | C11 v17: `unittest.mock.patch` com 5+ cenarios (sucesso, falha CSTAT, HARD_FAIL, timeout, sessao expirou) + canary OBRIGATORIO |
| **R9** | **G016 `_commit_with_retry` mascara problema real**: se SSL drop e' frequente, codigo fica em retry sem corrigir causa raiz (PgBouncer config, keepalive errado) | Baixa | Medio | Adicionar telemetria: log + Sentry quando retry > 1 (sinal sistemico) |
| **R10** | **Canary C20 revela quirk nao previsto** (robo CIEL IT mudou, CFOP novo, etc.) que invalida design v15-v18 | Media | Alto | C20 OBRIGATORIO com 1 ajuste so + revisao Rafael ANTES de C21 bulk |

#### Riscos de processo (sustentabilidade)

| # | Risco | Prob | Impacto | Mitigacao |
|---|-------|------|---------|-----------|
| **R11** | **PLANEJAMENTO crescera a ~1500 LOC** com edits parciais entre sessoes. Inconsistencia entre §3 + §7.2 + §10 | Alta | Medio | Cada sessao DEVE atualizar §0 + §12 + checkpoint; code-review focado em consistencia ao fim de v18 |
| **R12** | **Cronograma 8 sessoes era OTIMISTA**. Com R6+R7+sub-skill+possivel re-validacao 10.3 → 10-12 sessoes | Alta | Medio | Documentar §11: "cronograma orientativo, decisoes em cada sessao podem expandir" |
| **R13** | **Eu (agente) releio PLANEJAMENTO mas IGNORO padroes D1-D9**. Memoria nao persiste — preciso seguir literal | Alta | Alto | Cada sessao v14+ checklist "§7.2 D1-D9 aplicados?" antes de commit |
| **R14** | **Rafael muda de ideia em alguma decisao** (ex: 10.6 reverter se Skill 5 ficar complexa) | Media | Baixo | §10 marca decisoes com data + razao; revisao explicita no inicio de cada sessao |
| **R15** | **Sub-skill `auditando-cadastro-fiscal-odoo` nunca tem perfil 2**. Estrutura de perfis = trabalho que nao compensa | Media | Baixo | Aceitar V1 minima + simples; expandir perfis SO' com demanda real |

#### Descobertas esperadas em v14+ (que podem mudar o plano)

| Descoberta | Impacto se confirmada |
|------------|-----------------------|
| Script `09_executar_onda1_bulk.py` faz **pipeline por ajuste** (nao etapa-barreira) | **Decisao 10.3 precisa re-validar com Rafael ANTES de v15** |
| `gtin_validator.py` esta em `app/odoo/utils/` ou `app/recebimento/services/`, nao `scripts/` | Atualizar §4 e §9 (pendencias) |
| Pre-flight V1 e' 200 LOC simples — estrutura de perfis multiplos overkill | Confirmar R3 + simplificar §4 |
| F5c (`liberar_faturamento`) tambem pode ir para Skill 5 (operacao em picking) | Estender 10.6 — F5c vira atomo `liberar_faturamento_picking` na Skill 5 |
| `picking_svc.preencher_qty_done` precisa ser exposto na Skill 5 atual ou criar atomo composto na Skill 5 | C6.5 — analisar interface da Skill 5 atual antes de adicionar |

### 8.2 Riscos arquiteturais gerais (mantidos da versao v13 inicial)



| Risco | Probabilidade | Impacto | Mitigacao |
|-------|---------------|---------|-----------|
| **Capinar tudo de uma vez quebra demanda real** | Alta | Alto | capinar por etapa (C7-C13 sequencial); validar pytest a cada etapa; canary obrigatorio antes de bulk |
| **Estado de rabo entre sessoes** (commit parcial em C9 mas C10 nao iniciado) | Alta | Medio | regra inviolavel 0 deste arquivo + atualizar checkpoint a CADA sessao + commit isolado por checkpoint |
| **Race condition em paralelismo** (F5a/F5b/F5c) | Media | Alto | preservar Semaphore=5 do service; agrupamento por picking_id; testes com `concurrent.futures.ThreadPoolExecutor` em pytest |
| **SSL drop mid-loop perde sincronizacao** | Alta (em F5d/F5e) | Alto | _commit_with_retry codificado (G016 A+B+C) + re-fetch + tests de SSL drop |
| **Playwright crash mid-loop** | Media | Medio | recovery via `--resume` + idempotencia por chave_nfe + browser timeout |
| **Robo CIEL IT lento (>2h)** | Alta (pico) | Medio | janela permitida + warn + recovery |
| **NF SEFAZ-autorizada com erro** | Baixa (com pre-flight) | Critico (irreversivel 24h) | pre-flight + canary obrigatorio + double-check XML antes de transmitir |
| **G023 falta `company_id` em moves** | Baixa | Alto | invariante codificado: forcar apos create() |
| **Centralizar journals quebra outros services** | Media | Medio | tarefa ortogonal — adiar para pos-v20 |

---

## 9. PENDENCIAS E ACTION ITEMS VIVOS (atualizar a cada sessao)

| Item | Origem | Status | Acao | Sessao prevista |
|------|--------|--------|------|-----------------|
| ~~Confirmar caminho exato do `gtin_validator.py` (G035)~~ | C5 | ✅ v14a | **NAO NECESSARIO** — script `09_executar_onda1_bulk.py:228-294` tem `validar_cadastro_fiscal` inline cobrindo G017 NCM strict + G018 weight=0 warn. **G035 (barcode invalido)** NAO esta' coberto no script — provavelmente esta' em outro lugar OU nao foi automatizado ainda. Confirmar em C5 v14b se incluir G035 no V1 ou adiar. | v14a / decisao em v14b |
| ~~Confirmar onde fica `validar_cadastro_fiscal` (G017 fonte)~~ | C5 | ✅ v14a | LOCALIZADO: `09_executar_onda1_bulk.py:228-294` | v14a |
| ~~Decidir: pre-flight como sub-skill nova ou entry-point Skill 8?~~ | §10.5 | ✅ v13 | sub-skill nova (RESOLVIDO §10.5) | v13 |
| ~~Decidir: centralizar journals 847/1002/987 nesta skill ou depois?~~ | §10.4 | ✅ v13 | adiar para Skill 7 (RESOLVIDO §10.4) | v13 |
| Centralizar `ACAO_PARA_CFOP_ENTRADA` (5xxx→1xxx) em `app/odoo/constants/operacoes_fiscais.py` | C3 v14a D17 | ⬜ | criar constante + import em Skill 8 + fluxos futuros | v15b ou v17 |
| ~~Centralizar `ACOES_ENTRADA_DESTINO_MANUAL`, `PICKING_TYPE_ENTRADA_DESTINO_MANUAL`, `COMPANY_LABEL_ENTRADA`, `LOCATION_ORIGEM_ENTRADA_INDUSTR` em `app/odoo/constants/`~~ | C3 v14a §7.3 | ✅ v15a | **CENTRALIZADAS em `app/odoo/constants/picking_types.py`** (decisao v15a — junto com PICKING_TYPE_POR_DIRECAO existente; nao em operacoes_fiscais.py para nao misturar fluxos picking com matriz fiscal). `LOCATION_ORIGEM_ENTRADA_INDUSTR = LOCATION_DESTINO_TRANSITO_INDUSTR` (alias semantico). `ACOES_ENTRADA_FB` ainda pendente (entry-side; ETAPA E nao implementada) | v15a |
| Decidir em C5 v14b: implementar G035 (barcode invalido — `<cEAN>` invalido SEFAZ cstat=225) ou adiar? | C3 v14a §9 | ⬜ | AskUserQuestion em v14b | v14b |
| Decidir em C5 v14b: V1 INLINE simples (pre-mortem R3) ou ja' estruturar perfis multiplos? | §10.5 + R3 v13 | ⬜ | implementacao V1 INLINE; estrutura perfis SO' quando 2o perfil chegar | v14b |
| Consolidar helper `_commit_resilient` (versao MAIS FORTE D14 + G-RECLF-4) em util compartilhada | C3 v14a D14 + v14a-fix G-RECLF-4 | ⬜ | usar existente `app.utils.database_retry.commit_with_retry` OU criar `app/odoo/estoque/scripts/_commit_helpers.py` consolidando AMBOS padroes (script `_commit_resilient` + service `_commit_with_retry` + RecebimentoLfOdoo `_safe_update`/`_checkpoint`) | v15b ou v16 |
| **DECISAO PENDENTE v17: paralelismo ETAPA E** | v14a-fix G-RECLF-1 | ⬜ | 30-60min POR INVOICE (37 etapas RecebimentoLfOdoo); bulk 100 invoices = 50-100h sincrono. OPCAO A: assincrono via RQ worker; OPCAO B: paralelo invoice_ids distintos (verificar thread-safety RecebimentoLfOdoo — provavelmente NAO); OPCAO C: sequencial + aceitar tempo + recovery `--apenas-etapa=E --resume`. AskUserQuestion em v17 | v17 |
| ~~Centralizar constants ETAPA F ANTES de v17 (atomo Skill 5 ETAPA F precisa)~~ | v14a-fix L1 | ✅ v15a | **RESOLVIDO** — centralizadas em `app/odoo/constants/picking_types.py` (decisao v15a: junto com PICKING_TYPE_POR_DIRECAO em vez de `operacoes_fiscais.py` para nao misturar fluxos picking com matriz fiscal). Imports aplicados via `from app.odoo.constants.picking_types import ...`. | v15a |
| Confirmar se `transferir_quantidade_para_lote` chamada por G014 (script L867-877) usa atomo v1 ou v2 (Skill 2 atual) | v14a-fix G-ETB-G014 | ⬜ | grep + Read; se v1, atualizar para v2 no orchestrator Skill 8 C7 | v15b (C7) |
| Picking 317346 pendente (caso FB/SAI/IND/01559 do v8) | memoria | ⬜ | verificar se invoice apareceu apos 1 semana; usar como canary C20? | v19-v20 |
| Casos reais de Rafael "em todas as direcoes" | resposta v13 | ⬜ | catalogar (planilha?) antes do canary C20 | v19 |

---

## 10. DECISOES A TOMAR (com Rafael — atualizar quando decidido)

### 10.1 ✅ Escopo da Skill 8 (RESOLVIDO v13)
- **Decisao**: Pipeline COMPLETO A-F capinado em N sessoes (~6-8 sessoes).
- **Razao Rafael**: "estruturar bem, depois rodar casos reais"; Skill 8 nao admite incompleto entre sessoes.

### 10.2 ✅ Demanda real (RESOLVIDO v13)
- **Decisao**: Estruturar antes; casos reais agendados para apos C18.
- **Razao Rafael**: "tenho casos em todas as direcoes; primeiro estruturar".

### 10.3 ✅ Pattern paralelismo (RESOLVIDO v13 + REVALIDADO v14a — INTACTA)
- **Decisao**: (a) **Preservar Semaphore=5 do service atual** — paraleliza DENTRO de cada etapa; sequencializa ENTRE etapas (barreira de sincronizacao).
- **Razao Rafael v13 2026-05-25**: "fazer tudo por etapa — todos os pickings, todas as validacoes, todas emissoes de fatura, etc.". Razao concreta: DetachedInstanceError e SSL connection timeout sao agravados por loops longos com state DB compartilhado. Etapas curtas e atomicas reduzem janela de exposicao.
- **REVALIDACAO v14a (R1) — pattern do script CONFIRMA decisao em NIVEL MACRO**:
  - main() L1771-1860: cada `if 'X' in etapas` → executa etapa → `db.session.expire_all()` + `carregar_ajustes()` (re-load do DB) → so' depois a proxima.
  - ETAPAS C+D ganham `db.engine.dispose()` ANTES e APOS (G016 profilatico — D10).
  - **NAO houve interleaving de ajustes entre etapas no script** — comprovado.
- **REVALIDACAO v14a (R1) — sub-nuance MICRO ETAPA B descoberta**:
  - Script faz pipeline POR PICKING dentro de B (criar 1 → validar 1 → liberar 1 → sleep 5s → criar 2 → ...) — NAO paraleliza N pickings entre si.
  - Razao codificada (G022 mitigation D16): pickings concorrentes geram over-reservation em lotes velhos pos-renomeacao de ETAPA A. Sleep 5s tambem da' tempo ao PgBouncer renovar SSL.
  - Service `f5b_validar_pickings(ajustes_chunk)` paraleliza ajustes DENTRO de 1 picking via Semaphore=5; mas o script chama com 1 chunk de cada vez.
  - **IMPLICACAO para v15 (orchestrator Skill 8 base + F5a/F5b)**: PRESERVAR pattern intra-B (sleep 5s entre pickings).
- **Pattern arquitetural** (consolidando v13+v14a):
  - **NIVEL MACRO entre etapas**: A → (expire+reload) → B → (expire+reload) → C → (dispose+expire+reload) → D → (dispose+expire+reload) → E → (expire+reload) → F.
  - **NIVEL MICRO ETAPA B**: pipeline por picking (criar→validar→liberar→sleep 5s→proximo). Service intra-picking paraleliza ajustes via Semaphore=5.
  - **NIVEL MICRO ETAPA A**: SEQUENCIAL (D13 — XML-RPC nao thread-safe). Possivel paralelizar via Skill 2 subprocess (cada processo = sem race).
  - **NIVEL MICRO ETAPAS C/D/E/F**: ja' sequencial natural (polling longo, Playwright serial, agregacao por invoice_id).
- **Mitigacoes** de DetachedInstanceError + SSL drop:
  - G016 codificado: `_commit_with_retry` antes de cada operacao longa + re-fetch via `db.session.get(AjusteEstoqueInventario, ajuste_id)` apos.
  - **D14 v14a**: `_commit_resilient` do script faz tambem `engine.dispose()` proativo (versao MAIS FORTE — APLICAR no Skill 8).
  - **D10 v14a**: `db.engine.dispose()` profilatico ANTES e APOS C+D (alem do retry interno do service).
  - **D11 v14a**: `expire_all() + carregar_ajustes()` entre etapas (re-load com fase atualizada).
  - Etapas longas (F5d 1800s, F5e Playwright 5-10min/NF) tem re-fetch explicito.
  - TCP keepalive em `config.py:115-118` (ja' configurado).
- **Smoke obrigatorio em pytest**: simular SSL drop mid-etapa via mock + verificar re-fetch correto + verificar `engine.dispose()` chamado profilaticamente antes de C/D.

### 10.4 ✅ Centralizar journals (847/1002/987) (RESOLVIDO v13)
- **Decisao**: (b) **Adiar para Skill 7 escriturando** que tambem precisa.
- **Razao Rafael v13**: adiar (recomendacao aceita).
- **Implicacao operacional**:
  - Skill 8 v1: usa inline com comentarios `# journal_id=847 (VND)` quando necessario.
  - Quando Skill 7 capinar, criar `app/odoo/constants/journals.py` ENTAO + tarefa de migracao para Skill 8 (~1 PR doc-only).
  - Sem bloqueador imediato — pattern atual do service ja' funciona.

### 10.5 ✅ Pre-flight como sub-skill OU entry-point (RESOLVIDO v13)
- **Decisao**: (a) **Sub-skill nova `auditando-cadastro-fiscal-odoo`** (orquestrada pela Skill 8).
- **Razao Rafael v13 2026-05-25**: podem haver no futuro **faturamentos para cliente** (vendas comerciais, nao so' inventario inter-company) cujo pre-flight tera regras DIFERENTES (certificado A1, IE destinatario, tabela preco, FCI). Ter pre-flight INVENTARIO como entry-point da Skill 8 amarra as duas coisas e bloqueia reuso futuro.
- **Implicacao operacional**:
  - C5 redefinido: criar sub-skill nova em v14 (era "integrar pre-flight em Skill 8")
  - Sub-skill tem perfis multiplos (`--perfil inventario` V1; futuros `--perfil venda-cliente` etc.)
  - Skill 8 INVOCA via subprocess (delegacao limpa)
  - Operador pode rodar sub-skill ISOLADAMENTE (sem Skill 8) para auditoria de cadastro
  - +1 sessao no cronograma global (7-9 sessoes em vez de 6-8)
- **Cross-refs a atualizar quando criar (C5 v14)**:
  - subagente `gestor-estoque-odoo` (adicionar `auditando-cadastro-fiscal-odoo` ao skills lista)
  - `ROUTING_SKILLS.md` (incluir nova skill, +1 invocavel)
  - `tool_skill_mapper.py` (mapear `'auditando-cadastro-fiscal-odoo': 'Estoque Odoo (Audit)'` ou similar)
  - `CLAUDE.md` raiz (Skills WRITE + Skills READ — defaultly READ-only)
  - `app/odoo/estoque/CLAUDE.md` §6 catalogo (Skills READ ancillary — passa de 1 para 2: `consultando-quant-odoo` + `auditando-cadastro-fiscal-odoo`)

### 10.6 ✅ Refatorar F5a/F5b + ETAPA F para reusar Skill 5 (RESOLVIDO v13 + EXPANDIDO v14a-fix)
- **Decisao v13**: (c) **REFATORAR COMPLETAMENTE** — F5a vira atomo novo na Skill 5 `criar_picking_inter_company`; F5b vira atomo novo `validar_picking_inter_company`.
- **Expansao v14a-fix (Rafael)**: ETAPA F (entrada destino manual G023, script L1428-1688) faz `odoo.create('stock.picking') + write company_id + write lot_name + action_confirm/assign/button_validate + G019/G020 check` INLINE no orchestrator — VIOLA "se mexe com picking, deve ser via Skill 5". **3o atomo Skill 5 NOVO**: `criar_picking_entrada_destino_manual`.
- **Razao Rafael v13 2026-05-25**: principio arquitetural inviolavel — "Se mexe com picking, devera ser atraves da Skill 5". "Devemos seguir o principio da atomicidade e funcao especifica". "Fluxo >> Skills (esta registrado, apenas SIGA)".
- **Implicacao arquitetural**:
  - **Skill 5 estendida** com 3 atomos novos para inter-company:
    - `criar_picking_inter_company(args) -> picking_id` (F5a) — encapsula G004 partner_id + G023 company_id forcado em moves + carrier + incoterm
    - `validar_picking_inter_company(picking_id, qty_done_map, peso_liquido_map) -> bool` (F5b) — encapsula G011 qty_done + G018 peso_liquido + G019/G020 idempotencia
    - **`criar_picking_entrada_destino_manual(invoice_id, picking_type_id, location_origem, location_destino, company_destino, moves_data, origin) -> picking_id`** (ETAPA F — NOVO v14a-fix) — encapsula:
      - `odoo.create('stock.picking', picking_data)` + `company_id=company_destino` em moves (G023 fix CRITICO)
      - `action_confirm` + `action_assign`
      - G011: preencher `lot_name` nos move_lines + re-escrever `quantity` (auto-vazio apos action_assign)
      - `button_validate` + G019/G020 re-le state e raise se != done
      - Idempotencia via `origin` (formato `INV-{CICLO}-ENTRADA-{LABEL}-NF{invoice_id}`)
  - **F5c `liberar_faturamento`** pode ir tambem para Skill 5 ou ficar na Skill 8 (decidir em v15a — mas inclinacao para Skill 5: e' operacao em picking).
  - **F5d/F5e** permanecem na Skill 8 (operam em `account.move`, nao picking).
- **Atualizacao do cronograma**:
  - v14 inclui PLANEJAR extensao da Skill 5 (especificar 3 atomos novos no SKILL.md existente)
  - v15a EXECUTA: estende Skill 5 com 3 atomos (~1.5 dia — +50% pelo atomo F)
  - v15b implementa orchestrator Skill 8 que usa atomos
  - Possivel +1 sessao se atomos novos exigirem mais cuidado (pytest >8 verdes + dry-run PROD)
- **Risco mitigado**: refatoracao FRESCA (capinando de inventario_pipeline_service.py + script L1428-1688) reduz risco — nao mexe em codigo legacy de Skill 5, apenas ADICIONA atomos.
- **Cross-refs a atualizar quando criar atomos novos (em v15a)**:
  - `app/odoo/estoque/scripts/picking.py` (adicionar 3 funcoes top-level)
  - `.claude/skills/operando-picking-odoo/SKILL.md` (estender contrato com 3 novos atomos)
  - testes pytest em `tests/odoo/services/test_stock_picking_service.py` (adicionar >8 verdes — 3 atomos x ~3 cenarios cada)
  - subagente `gestor-estoque-odoo` (atualizar listagem Skill 5 com novos atomos)
  - VALIDACAO_FINAL_SESSAO.md §17+ (nova entrada documentando extensao)
  - memoria `[[skill5_picking_pattern]]` (atualizar com inter-company + entrada destino manual)

---

## 11. CRONOGRAMA ESTIMADO

| Sessao | Foco | Checkpoints | Risco |
|--------|------|-------------|-------|
| **v13** | Planejamento + estruturacao + 6 decisoes RESOLVIDAS + C2 mineracao service | C1, C2, C4 | Baixo (sem codigo) |
| **v14a (esta)** | C3 mineracao script + revalidar R1 (10.3 INTACTA) | **C3** | Baixo (sem codigo) |
| **v14b (proxima)** | Criar sub-skill `auditando-cadastro-fiscal-odoo` perfil inventario V1 | **C5** | Baixo-Medio (cria service novo) |
| **v15a** | Estender Skill 5 com atomos inter-company (`criar_picking_inter_company` + `validar_picking_inter_company`) | **C6.5** | Medio (mexe skill madura — pytest >5 verdes + canary obrigatorio) |
| **v15b** | Orchestrator base + F5a + F5b (chamam atomos novos Skill 5; invoca sub-skill C5 no bulk) | C6, C7, C8 | Medio-Alto |
| **v16** | F5c + F5d (com G016+G007+G034+G029) + D10 dispose profilatico + D14 commit_resilient forte | C9, C10 | Medio (SSL pattern critico) |
| **v17** | F5e + etapas E/F (D17 ACAO_PARA_CFOP_ENTRADA centralizado) | C11, C12, C13 | Alto (SEFAZ Playwright, G023 company_id forcado em moves) |
| **v18** | Recovery (`--resume`, `--apenas-etapa`, `--ate-etapa` D12) + SKILL.md + tests + smokes | C14, C15, C16, C17 | Medio |
| **v19** | Folhas fluxos 1.1+1.3 + cross-refs + Canary REAL PROD (1 ajuste) | C18, C19, C20 | Alto (PRIMEIRA NF real) |
| **v20+** | Bulk REAL PROD + code-review + commit final + arquivar 09_* SUPERADOS | C21, C22, C23 | Alto (volume real) |

**Total estimado: 9-10 sessoes** (sub-skill C5 em v14b separada; Skill 5 estendida em v15a separada). Pode estender se canary C20 revelar gaps nao previstos. Pre-mortem R6+R7 (v13) preserva contexto via divisao de sessoes longas.

---

## 12. TRILHA DE AUDITORIA (sessoes — adicionar entry a cada)

### Sessao v13 (2026-05-25)
- ✅ Setup worktree + venv + ENV + pytest baseline 393 verdes
- ✅ Verificacao main (sem avanco desde a937748b)
- ✅ Leitura HANDOFF v9-v12 + VALIDACAO §13-§15 + gestor-estoque-odoo invariantes + memoria skill2_distribuir_indisp_pattern
- ✅ AskUserQuestion: foco A (Skill 8) escolhido
- ✅ Levantamento contexto Skill 8 (subagente Explore: service 1.346 LOC + script 1.850 LOC + 15 scripts ad-hoc + constants + gotchas + memorias + pattern Skill 6 v9 + folhas 1.x ausentes)
- ✅ AskUserQuestion: estruturacao com checkpoints persistentes escolhida
- ✅ Mapeamento SSL/timeout: G016 codificado (commit_with_retry+re-fetch+TCP keepalive) + recovery scripts fat_lf_resume*.sh (timeout 900 + idempotencia fase_pipeline + stagnation detector)
- ✅ **C1 — Pre-mortem completo** registrado (§7.1, 4 dimensoes x todas etapas)
- ✅ **C4 — Escopo confirmado**: pipeline COMPLETO A-F em N sessoes
- 🟡 Documento PLANEJAMENTO_SKILL8_FATURANDO.md criado (esta versao)
- ✅ Commit `63d817d5`: docs(estoque) v13 — planejamento Skill 8 + ROADMAP HANDOFF + CLAUDE.md atualizado
- ✅ **AskUserQuestion v13 mid**: avancar A+B+C nesta sessao (~70k tokens)
- ✅ **Decisao 10.5 RESOLVIDA** (mid-sessao v13): pre-flight como **sub-skill nova `auditando-cadastro-fiscal-odoo`** (Rafael: razao = futuros faturamentos para cliente terao pre-flight diferente; agnostica com perfis multiplos)
- ✅ **Refatoracoes §2.2/§2.3/§4/§6.3/§7C5/§10.5/§11** aplicadas:
  - §2.2: pre-flight saiu de "Entra na Skill 8", virou invocacao via subprocess
  - §2.3: pre-flight delegado para sub-skill nova
  - §4: reescrita inteira como "DELEGADO" + contrato V0 da sub-skill + perfis multiplos
  - §6.3: orchestrator nao tem `--pre-flight`, mas tem `--pular-pre-flight` opcional
  - §7 C5: redefinido para criar a sub-skill (em vez de integrar pre-flight em Skill 8)
  - §10.5: RESOLVIDA com razao + cross-refs a atualizar em C5
  - §11: v14 inclui criacao da sub-skill (cabe sem expandir cronograma global)
- ✅ **AskUserQuestion v13 B**: 3 decisoes adicionais resolvidas:
  - **10.3 paralelismo**: PRESERVAR Semaphore=5 + ETAPA = BARREIRA DE SINCRONIZACAO (mitiga DetachedInstanceError + SSL drop conforme Rafael)
  - **10.4 journals**: ADIAR para Skill 7 escriturando
  - **10.6 F5a/F5b**: REFATORAR COMPLETAMENTE — atomos novos na Skill 5 (`criar_picking_inter_company` + `validar_picking_inter_company`) seguindo principio "Fluxo >> Skills"
- ✅ **Refatoracoes adicionais aplicadas** (apos B):
  - §6.2: pattern de etapa-barreira documentado + F5a/F5b via Skill 5
  - §7: novo checkpoint **C6.5** (estender Skill 5 com atomos inter-company); C7/C8 reescritos para chamar atomos Skill 5
  - §10.3/§10.4/§10.6: RESOLVIDAS com razao + implicacoes operacionais + cross-refs
  - §11: v15 expandido com C6.5
  - §0: 6 decisoes RESOLVIDAS; pattern arquitetural FINAL declarado
- ✅ **C2 — Mineracao detalhada `inventario_pipeline_service.py` COMPLETA** (mid-sessao):
  - Tabela §7.2 com 14 metodos+linhas+side-effects+deps (cabecalho L1-L575 + F5a L581-754 + F5b L774-876 + F5c L882-939 + F5d L945-1102 + F5e L1116-1346)
  - **9 descobertas-chave D1-D9** documentadas como padroes a PRESERVAR no orchestrator:
    - D1: SNAPSHOT antes de threads (evita DetachedInstanceError)
    - D2: agrupamento por picking (N ajustes/picking)
    - D3: bug L19/L20/L21 fix (preencher_qty_done sequencia)
    - D4: G023 `linhas_esperadas` em validate
    - D5: SNAPSHOT meta + `db.session.get` re-fetch em polling longo
    - D6: sub-etapas F5d.5/.6/.7 em try/except (falha individual nao derruba)
    - D7: `HARD_FAIL_CONFIG_ERRORS` aborta batch
    - D8: idempotencia TRIPLA em F5e (sem inv_id, batch, persistencia)
    - D9: `db.session.get` re-fetch + `_commit_with_retry` apos Playwright
  - Achados secundarios MED-B-2 / MED-C-1 / MED-C-2 + dependencias externas listadas
- ⬜ Resto dos checkpoints pendentes para v14+ (mineracao C3 do script 09_* + sub-skill C5)

### Sessao v14a (2026-05-25) — C3 mineracao script + revalidar R1
- ✅ Setup worktree + venv + ENV; verificacao main avancou 11 commits (SPED V36, weekly, fix tabelas, SDK 0.2.87, D8) — sem conflito esperado com `app/odoo/estoque/`, sem rebase.
- ✅ Pytest baseline confirmado: **393 verdes em 15.87s** (tests/odoo/).
- ✅ Leituras obrigatorias: CLAUDE.md estoque + PLANEJAMENTO_SKILL8 INTEIRO (especialmente §7.2 D1-D9 + §8.1 pre-mortem 15 riscos) + ROADMAP_SKILLS HANDOFF v13 + gestor-estoque-odoo invariantes.
- ✅ AskUserQuestion: foco v14a so (C3 + revalidar R1) escolhido — preserva contexto para v14b fresca (pre-mortem R6).
- ✅ **C3 mineracao script `09_executar_onda1_bulk.py` (1866 LOC) COMPLETA**:
  - Estrutura geral §7.3 (11 blocos + tabela com 11 funcoes+linhas+side-effects+deps).
  - Pattern macro confirmado em `main()` L1771-1860: cada `if 'X' in etapas` → executa → `db.session.expire_all() + carregar_ajustes()` → so' depois proxima. C+D ganham `db.engine.dispose()` ANTES e APOS (G016 profilatico).
  - **9 descobertas-chave NOVAS D10-D18** documentadas como padroes a PRESERVAR no orchestrator Skill 8:
    - D10: `db.engine.dispose()` PROFILATICO antes/apos C+D
    - D11: `expire_all() + carregar_ajustes()` entre etapas
    - D12: `--apenas-etapa` + `--ate-etapa` para recovery operacional
    - D13: ETAPA A SEQUENCIAL (max_workers arg legacy/no-op — XML-RPC nao thread-safe Request-sent)
    - D14: `_commit_resilient` (script) MAIS FORTE que `_commit_with_retry` (service) — faz `engine.dispose()` se SSL
    - D15: ETAPA A 100% DELEGAVEL para Skill 2 `transferindo-interno-odoo`
    - D16: `time.sleep(5)` entre chunks ETAPA B (G022 over-reservation mitigation)
    - D17: `ACAO_PARA_CFOP_ENTRADA` mapeia 5xxx→1xxx (PERDA 5903→1903, TRANSFERIR 5152→1152, DEV 5949→1949)
    - D18: default `dry_run=True` + `--confirmar` + `--confirmar-sefaz` (2 niveis)
  - Constantes inline a CENTRALIZAR pela Skill 8 em `app/odoo/constants/operacoes_fiscais.py`:
    - `ACAO_PARA_CFOP_ENTRADA` (L1300-1305 script)
    - `ACOES_ENTRADA_FB`, `ACOES_ENTRADA_DESTINO_MANUAL`, `PICKING_TYPE_ENTRADA_DESTINO_MANUAL`, `COMPANY_LABEL_ENTRADA`, `LOCATION_ORIGEM_ENTRADA_INDUSTR` (L126-146)
  - Dependencias externas listadas: StockInternalTransferService (Skill 2), StockPickingService (Skill 5), InventarioPipelineService (service §7.2), RecebimentoLfOdooService (modulo externo recebimento).
  - `validar_cadastro_fiscal` (L228-294) identificado como **fonte para sub-skill `auditando-cadastro-fiscal-odoo` (C5 v14b)** — G017 NCM strict + G018 weight=0 warn. **NAO precisa de gtin_validator.py separado** — script ja' tem logica G017 inline, e G018 e' detect-only (fix real e' em `aplicar_peso_volumes_fallback_picking` ENTRE F5b/F5c, nao no produto).
- ✅ **R1 REVALIDADO — decisao 10.3 INTACTA**:
  - ✅ Macro: pattern do script CONFIRMA "etapa = barreira" (mecanismo explicito via `expire_all+reload+dispose`).
  - 🟡 Micro ETAPA B: descoberta de sub-nuance (pipeline por picking com sleep 5s G022). Documentada em §6.2 + §7.3 + §10.3. **NAO requer AskUserQuestion adicional** — decisao 10.3 intacta + sub-nuance preservada no orchestrator v15.
- ✅ Refatoracoes §0/§6.2/§7-tabela-C3/§10.3/§11 aplicadas:
  - §0: status global atualizado (C3 ✅, 4 de 24), pattern arquitetural FINAL atualizado com sub-nuance ETAPA B.
  - §6.2: tabela "O que ADAPTAR" expandida com D10-D18 + sub-nuance ETAPA B.
  - §7 tabela: C3 marcado ✅ com referencia §7.3 + 9 descobertas + R1 RESPONDIDO.
  - §10.3: REVALIDADO v14a — secao expandida com macro/micro pattern + mitigacoes D10/D11/D14.
  - §11: cronograma redividido v14a/v14b/v15a/v15b (preserva pre-mortem R6+R7).
  - §7.3 NOVA: 11 funcoes+linhas+side-effects+deps + 9 descobertas D10-D18 + dependencias externas + conclusao R1.
- 🟢 **Sem mudancas em codigo nesta sessao** (so docs/planejamento).
- 🟢 **Pytest baseline mantido: 393 verdes**.

### Sessao v14a-fix (2026-05-25) — Mineracao RecebimentoLfOdoo + ETAPA F via Skill 5 + gotchas destacados
- ✅ Rafael pediu auditoria das 2 perguntas: (1) Fluxo>>Skills mantido? (2) Gotchas cobertos incluindo RecebimentoLF?
- ✅ Auto-auditoria honesta identificou **4 lacunas** reais:
  - L1: ETAPA F faz picking inline no orchestrator (viola Fluxo>>Skills)
  - L2: RecebimentoLfOdooService (4562 LOC, 37 etapas) NAO foi minerado (anotado "DELEGADO, reuso como esta'")
  - L3: Gotcha compensatorio ETAPA B L994-1031 (regra de negocio importante) nao destacado
  - L4: G014 PROTECTION ETAPA B L795-917 (lote vencido on-the-fly via Skill 2) nao detalhado
- ✅ AskUserQuestion: opcao (a) Corrigir AGORA + NAO MEXER no RecebimentoLfOdooService escolhida
- ✅ **L2 RESOLVIDO — Mineracao §7.4 NOVA de RecebimentoLfOdoo (4562 LOC READ-only)**:
  - Header docstring completo: 37 etapas em 7 fases (FB DFe→PO→Picking→Invoice→Finalizacao→Transfer FB→CD→Recebimento CD)
  - Pattern: Checkpoint por Etapa + Fire and Poll (FIRE_TIMEOUT=120s + POLL=10s + MAX=1800s = 30min)
  - Helpers criticos lidos: `_get_recebimento` (anti-DetachedInstanceError), `_safe_update`/`_checkpoint` (SSL-safe com `engine.dispose()` + exponential backoff 0.5/1/2s + 3 retries), `_write_and_verify` (write + read-back), `_recover_state_from_odoo` (ajusta etapa_atual baseado em po/picking/invoice state)
  - **Tempo total estimado: 30-60min POR INVOICE** (FB 30min + transfer FB→CD 30min)
  - **11 gotchas G-RECLF-1 a G-RECLF-11 documentados**, destacando:
    - G-RECLF-1: 30-60min por invoice — bulk ETAPA E NAO viavel sincrono (decidir paralelismo em v17)
    - G-RECLF-2: FASE 6+7 pode falhar sem derrubar FB — Skill 8 deve aceitar `transfer_status='erro'` como sucesso parcial
    - G-RECLF-4: `_safe_update`/`_checkpoint` versao MAIS FORTE que `_commit_with_retry` (D14) — consolidar
    - G-RECLF-9: Playwright SEFAZ no step_23 sobreposto com F5e — **JA' MITIGADO pelo etapa-barreira (decisao 10.3)** ✓
  - Constants HARDCODED mapeadas + verificadas (PAYMENT_PROVIDER FB=92, CD=30 DIFERENTE de 38 da Skill 8 — sem conflito)
  - Conclusao §7.4.8: ETAPA E do orchestrator INVOCA `processar_recebimento(rec_id)` (como faz o script L1413), idempotente, aceita parcial, decide paralelismo em v17
- ✅ **L1 RESOLVIDO — ETAPA F via 3o atomo Skill 5 (`criar_picking_entrada_destino_manual`)**:
  - §10.6 EXPANDIDO: 3 atomos em vez de 2 (`criar_picking_inter_company` + `validar_picking_inter_company` + **NOVO** `criar_picking_entrada_destino_manual`)
  - §3 diagrama: ETAPA F agora marca "DELEGADO Skill 5 atomo NOVO v14a-fix"
  - §7 tabela C6.5: expandido para 3 atomos (pytest >8 verdes em vez de >5)
  - §7 tabela C13: expandido — orchestrator INVOCA atomo Skill 5 em vez de implementar picking inline
- ✅ **L3+L4 RESOLVIDO — Gotchas DESTACADOS em §7.3**:
  - G-ETB-COMPENSATORIO: regra de negocio quando `qty_restante > 0` em PERDA_LF_FB (cria novo AjusteEstoqueInventario PROPOSTO para ondas futuras)
  - G-ETB-G014: lote vencido on-the-fly via `StockInternalTransferService.transferir_quantidade_para_lote` (mover qty vencida → lote novo `INV-{cod}-{HOJE}`). **GOTCHA HIDDEN**: verificar se script usa atomo v1 ou v2 — se v1, atualizar para v2 no orchestrator
- ✅ §0 atualizado: 3 mineracoes completas (service + script + RecebimentoLfOdoo), 1 decisao ABERTA (paralelismo G-RECLF-1 v17), pattern arquitetural mencionando ETAPA F via Skill 5
- ✅ §10.6 expandido com 3o atomo Skill 5 + cronograma C6.5 ~1.5 dia (+50%)
- 🟢 **Sem mudancas em codigo neste fix** (so docs/planejamento; RecebimentoLfOdoo INTOCADO conforme Rafael)
- 🟢 **Pytest baseline mantido: 393 verdes**.

### Sessao v14a-ops (2026-05-25 — 16:00→16:51, 51min) — TESTE REAL LF→FB 6 cods em PROD
- ✅ Rafael solicitou teste real: faturar 6 cods de LF para FB + transferir para FB/Indisp/MIGRAÇÃO
  - 102020600 AZEITONAS PRETAS TRITURADA — 1.385 un (tipo 1)
  - 4829046 MOLHO DE PIMENTA ST ISABEL — 2 un (tipo 4)
  - 4879046 MOLHO SHOYU ST ISABEL — 23 un (tipo 4)
  - 103500105 PIMENTA JALAPENO VERMELHA — 41.56 un (tipo 1, tracking='none')
  - 4849003 MOSTARDA GL ST ISABEL — 128 un (tipo 4)
  - 4759598 OLEO SOJA SENHORA DO VISO — 500 un (tipo 4)
- ✅ Decisao Rafael: usar scripts existentes (NAO Skill 8 — ela e' planejada, nao implementada) + mapear dificuldades reais
- ✅ Pre-flight READ-only OK: G017+G018 todos OK; G035 detectou 2 barcodes invalidos (4829046, 4849003); saldos LF suficientes
- ✅ Acao fiscal aplicada per fat_lf_02_carregar pattern: tipo 1/2/3=PERDA_LF_FB; tipo 4/6=DEV_LF_FB
- ✅ Estado descoberto: 6 cods ja em pipeline antigo INVENTARIO_2026_05 (2 EXECUTADO/F5e_SEFAZ_OK NF cancelada + 4 PROPOSTO/F5c_LIBERADO sem invoice; todos pickings antigos com return done = saldo voltou para LF/Estoque)
- ✅ Workaround: status='REPROCESSADO_v14a' nos 6 antigos para excluir do filtro do script 09 + mover meus 6 novos para INVENTARIO_2026_05
- ✅ Script 09 ETAPAS A→E executado em ~10min:
  - 2 pickings criados (321332 PERDA com 102020600 1.385un, 321333 DEV com 4 cods 653un)
  - 2 invoices CIEL IT criadas (709837 PERDA + 709835 DEV)
  - 2 NFs SEFAZ-OK (chaves 35260518467441000163550010000132411007098371 + ...132421007098352)
  - 2 RecLF processados (66 e 67) com invoices FB posted (709846, 709863)
- ✅ Cancelado picking automatico FB/INT/08056 (criado pos-RecLF, reservava saldo para Estoque Virtual/Produção sem MO)
- ✅ Skill 2 `distribuir_para_indisponivel` para 5 cods (102020600 + 4 DEV): 5/5 EXECUTADO_TOTAL, 654.385 un, fallback Modo B (lote ja MIGRAÇÃO)
- ⚠️ **Bug descoberto** L965 script 09: 103500105 (tracking='none') NAO foi faturado — virou compensatorio INDUSTRIALIZACAO_FB_LF PROPOSTO
- ✅ Workaround 103500105 (~10min):
  - Compensatorio 172264 cancelado (status='CANCEL_v14a_BUG' — varchar(20) limite!)
  - Novo ajuste 172265 com lote_origem='SEMLOTE' (dummy nao-vazio forca entrada em ajustes_com_lote L944)
  - Script 09 com filtro 103500105: NF RETNA/2026/00090 SEFAZ-OK + RecLF 68 OK em ~5min
  - **Bug DESCOBERTO em Skill 2** (`_listar_quants_origem` L1145+1147): mesmo padrao de filtro `lot_id != False`. FALHA_SEM_QUANT para tracking='none'.
  - Workaround Skill 2: 2 calls Skill 1 `ajustar_quant` (zerar FB/Estoque sem lote + delta+ em FB/Indisp/MIGRAÇÃO com lote)
- ✅ **Estado FINAL PROD validado**: TODOS 6 cods em FB/Indisp/MIGRAÇÃO:
  - 102020600: 8.0 | 4829046: 7.0 | 4879046: 23.0 | 103500105: 922.9 | 4849003: 128.0 | 4759598: 502.0
  - **Total ajustado: 695.945 un consolidadas em FB/Indisp/MIGRAÇÃO**
- ✅ **§7.5 NOVA** criada com 5 dificuldades operacionais reais (D-OPS-1..D-OPS-5) + side-findings + workflow timeline
- ✅ **§0 atualizado** com status `🟡 PLANEJADO COMPLETO + 3 MINERACOES + TESTE REAL 6 CODS 100% PROD`
- 🟢 **3 NFs SEFAZ autorizadas** + 0 falhas operacionais (com workarounds)
- 🟢 **Pytest baseline mantido: 393 verdes**

### Sessao v14b (2026-05-25) — FIX Skill 2 D-OPS-5 + CRIAR sub-skill `auditando-cadastro-fiscal-odoo` V1
- ✅ **PRIORIDADE 1 — Fix Skill 2 D-OPS-5 RESOLVIDO**:
  - `_listar_quants_origem` (transfer.py L1104-1180) adicionou parametro `aceita_tracking_none: bool = True` default. Quando True (novo default), NAO aplica filtro `['lot_id', '!=', False]` no domain do search_read. Permite incluir quants sem lote (produto tracking='none').
  - `transferir_para_indisponivel` (Modo C atomico L780+): relaxou tipo `lot_id_origem: Optional[int]`. Adicionou validacao: se `lot_id_origem is None`, faz 1 read em `product.tracking`. Se != 'none', raise ValueError clara ("anomalia: quant orfao sem lote em produto rastreavel"). Se == 'none', prossegue (ajustar_quant ja aceita lot_id=None).
  - `distribuir_para_indisponivel` (helper alto-nivel L1224+): adicionou parametro `aceita_tracking_none: bool = True` default + propaga para `_listar_quants_origem`.
  - **Campo novo no retorno**: `tracking_origem` (None quando lot_id passado; 'none' quando lot_id=None e tracking validado).
  - **9 pytest novos verdes** (6 no test_stock_internal_transfer_service + 3 no test_distribuir_para_indisponivel)
  - **Canary PROD validado**: cod 208000043 QUADRO DE MADEIRA NADIR (1 un sem lote em FB/Estoque) movido via Skill 2 modo C para FB/Indisp/MIGRAÇÃO. dry-run + --confirmar + reversão Skill 1 ×2 OK. Estado PROD restaurado.

- ✅ **PRIORIDADE 2 — Sub-skill `auditando-cadastro-fiscal-odoo` perfil V1 'inventario' CRIADA**:
  - Service `app/odoo/estoque/scripts/cadastro_fiscal_audit.py` (~430 LOC) — `CadastroFiscalAuditService` com 3 entry-points de resolucao (produto_ids | cods | ciclo) + 4 checks (G017+G018+D-OPS-3, G035, G014, D-OPS-2) + entry-point unificado `auditar_perfil_inventario` retornando status_global + bloqueios/warnings/acoes_aplicadas + tempo_ms.
  - SKILL.md `.claude/skills/auditando-cadastro-fiscal-odoo/SKILL.md` com contrato + receitas + exit codes + trade-offs.
  - CLI `auditar_cadastro_inventario.py` com 3 modos input mutuamente exclusivos + flags --auto-corrigir-barcode + --no-pipeline-check + --no-lote-vencido-check + --confirmar.
  - **14 pytest novos verdes** em `tests/odoo/services/test_cadastro_fiscal_audit.py`.
  - **Smoke PROD v14a-ops 6 cods em 987ms**: detectou 2 G014 (lotes 0711/24 venceram em 2026-05-08 para cods 4829046 + 4879046) + 1 D-OPS-3 (cod 103500105 PIMENTA JALAPENO tracking='none' — esperado!) + 0 bloqueios. Status PRE_FLIGHT_WARN + pode_faturar=true.
  - **G035 incluido no V1** (decisao Rafael v14b — Rafael pediu "G035 + outros gotchas como NCM, lote vencido") — incluidos G014 + D-OPS-2/3 alem de G017/G018/G035.
  - **Cross-refs aplicados**: `app/odoo/estoque/CLAUDE.md` §6 (nova tabela sub-skills PRE-FLIGHT), `.claude/references/ROUTING_SKILLS.md` (header count + tabela skills + decision tree §8 + lista skills Odoo), `app/agente/services/tool_skill_mapper.py` (entry 'Pre-Flight Cadastro Fiscal Odoo'), `.claude/agents/gestor-estoque-odoo.md` (skills frontmatter + header status).

- ✅ **PRIORIDADE 3 — D-OPS-3 (bug L965 script 09) DECISAO**: (a) NAO mexer no script (alinha regra Rafael "use scripts existentes apenas"). Sub-skill V1 flagga produto tracking='none' como INFO (apos fix Skill 2 v14b, deixou de ser WARN). v15a Skill 5 atomo `criar_picking_inter_company` codifica fix permanente.
- ✅ **§0 atualizado** com status `🟡 + SUB-SKILL C5 + FIX SKILL 2 D-OPS-5 EM v14b` + baseline `416 verdes`
- ✅ **§4.6 status sub-skill atualizado** (todos ✅ exceto C6 v15b integracao com Skill 8)
- ✅ **§7 C5 ✅ marcado COMPLETO** com criterios de aceite atingidos
- 🟢 **Pytest baseline novo: 416 verdes** (393 + 9 D-OPS-5 + 14 sub-skill C5)
- 🟢 **Sub-skill C5 desbloqueia integracao Skill 8 v15b** (orchestrator base chama subprocess sub-skill pre-faturamento)
- 🟢 **Fix Skill 2 D-OPS-5 desbloqueia atomo Skill 5 inter-company v15a** (3o atomo `criar_picking_inter_company` pode reusar pattern tracking='none' validado em transfer.py)
- 🟢 **NAO mexeu** no RecebimentoLfOdooService (regra Rafael v14a-fix) NEM no script 09 (regra Rafael v14a-ops)

### Sessao v15b (2026-05-25) — **C6 + C7 + C8 + F5c ✅** Orchestrator base Skill 8 LIVE

- ✅ Setup worktree + venv + ENV; rebase de main (11 commits — SDK 0.2.87, SPED V36, references, weekly, fix tabelas Sentry) sem conflito (zero overlap com `app/odoo/estoque/`).
- ✅ Pytest baseline pos-rebase: **435 verdes em 15.03s** (paridade v15a).
- ✅ AskUserQuestion v15b: opcoes "C6+C7+C8 juntos" (sem fasear) + "Rebase agora" escolhidas.
- ✅ Leituras obrigatorias (regra inviolavel 0): PLANEJAMENTO §0+§3+§6+§7.2+§7.3+§10.6+§12 INTEIRO + memorias `[[skill5_picking_pattern]]` (v15a 3 atomos) + `[[skill6_planejar_pre_etapa_pattern]]` (orchestrator C3 pattern v9) + `[[sub-skill-c5-pattern]]` (PRE-FLIGHT subprocess) + `pre_etapa_executor.py` template (907 LOC) + `picking.py` atomos novos (1378 LOC).
- ✅ **CRIADO `app/odoo/estoque/orchestrators/faturamento_pipeline.py`** (~1300 LOC):
  - **Constants modulo**: `ACAO_PARA_DIRECAO` (8 acoes -> tipo_op/co/cd), `ACOES_PICKING` (frozenset), `MAX_CODS_POR_PICKING=30`, `SLEEP_ENTRE_CHUNKS=5.0`, `ETAPAS_VALIDAS=(A,B,C,D,E,F)`, fases F5a/F5b/F5c OK/FALHA.
  - **Helpers**:
    - `_commit_resilient` (D14): MAIS FORTE que `_commit_with_retry` — backoff exponencial 2s/4s/8s + `engine.dispose()` proativo quando substring 'ssl' em err.lower().
    - `_registrar_auditoria`: lazy import `OperacaoOdooAuditoria` (CR-Pattern Skill 6 v9); external_id `INV-{ciclo}-A{id:06d}-{fase}-{uuid8}`.
    - `_pre_flight_via_subskill_c5`: subprocess `sys.executable` + `env=os.environ.copy()` + cwd=project_root + timeout=120s. Parsea JSON do stdout. Trade-offs R22 mitigados (path absoluto + env preservado + timeout actionable).
    - `_resolver_picking_metadata` (acao -> picking_type+partner+locations) via ACAO_PARA_DIRECAO + get_picking_type + COMPANY_PARTNER_ID + COMPANY_LOCATIONS + LOCATION_DESTINO_POR_DIRECAO.
    - `_carregar_ajustes` (D11 + CR-C1): `expire_all()` + filtro `status_filter` default `['PROPOSTO','APROVADO']` (CR-C1 CRITICAL — exclui CANCELADO/EXECUTADO/FALHA) + `acoes` filter + `fases_pipeline` + `cod_produto` + `limite`. CR-M1: intersecao acoes vazia retorna `[]`.
    - `_agrupar_em_chunks`: max 30 cods por chunk; mesmo cod sempre no mesmo chunk.
    - `_agrupar_por_direcao` (CR-C2 CRITICAL): agrupa por `acao_decidida` (NAO `(co, tipo_op)`) — preserva (co, cd) unico no chunk = partner_id correto. Era inconsistente para `DEV_LF_FB` (cd=1) vs `DEV_LF_CD` (cd=4) que compartilham (5, 'dev-industrializacao').
  - **Classe `FaturamentoPipelineExecutor`**:
    - `__init__`: injetavel `odoo` + `picking_svc` (StockPickingService).
    - `pre_flight`: wrapper publico do helper.
    - `executar_etapa_a` (D15 DELEGADO Skill 2): v15b stub `DRY_RUN_OK_ETAPA_A_NOOP` / `EXECUTADO_ETAPA_A_NOOP` — marca todos `fase_pipeline='TRANSF_OK'`. v16 expandir com analise de quants + invocacao Skill 2 inline.
    - `executar_etapa_b` (C7+C8+F5c): agrupa por `acao_decidida` -> chunks -> pipeline POR CHUNK (F5a -> F5b -> F5c) com G022 sleep 5s entre chunks (CR-H1 tracker global cobre transicoes entre grupos).
    - `_processar_chunk_etapa_b`: invoca atomos Skill 5 v15a em sequencia + auditoria + commit_resilient apos cada sub-etapa. G-ETB-COMPENSATORIO em PERDA_LF_FB (CR-H2 preserva acao_decidida do origem em vez de hardcode INDUSTRIALIZACAO_FB_LF).
    - `_resolver_pids_em_batch`: 1 read batch product.product por `default_code`.
    - `_criar_compensatorios_g_etb`: cria `AjusteEstoqueInventario` PROPOSTO com `acao_decidida` igual ao origem para ondas futuras.
    - `executar_etapa_c/d/e/f`: stubs `NOT_IMPLEMENTED_v15b` com roadmap v16/v17. ETAPA D exige `confirmar_sefaz=True` (CR-H4 + CR-M3 codificados).
    - `executar_pipeline_bulk` (entry-point macro): PRE-FLIGHT C5 -> A -> expire+reload -> B -> ... -> F. CR-H4: `ETAPAS_ABORT_SE_ANTERIOR_FALHOU=(D,)` bloqueia ETAPA D se B falhou. CR-M3: `BLOQUEADO_*` conta como falha em status agregado.
  - **CLI** `python -m app.odoo.estoque.orchestrators.faturamento_pipeline`:
    - Modos `bulk` (default) | `pre-flight`
    - Args `--ciclo` `--etapas A,B,C,D,E,F` `--company-origem-id` `--cod-produto` `--limite` `--confirmar` `--confirmar-sefaz` `--pular-pre-flight` `--usuario`
    - Cria Flask `app_context()` no `main()` (D11 — `db.session.expire_all()` precisa).
    - Exit codes alinhados Skill 6 v9: 0=OK, 1=falha negocial, 2=uso, 4=DRY_RUN_OK.
- ✅ **30 PYTEST NOVOS VERDES** em `tests/odoo/services/test_faturamento_pipeline_orchestrator.py`:
  - 25 baseline + 5 NOVOS pos code-review (status_filter / etapa D bloqueia / BLOQUEADO_SEFAZ status falha / compensatorio preserva acao / intersecao vazia retorna []).
- ✅ **BASELINE PYTEST ODOO**: 435 → **465 verdes em 14.85s** (+30 v15b).
- ✅ **SMOKE DRY-RUN PROD** em cod 210639522 (INDUSTRIALIZACAO_FB_LF, status=PROPOSTO, fase=None):
  - `python -m app.odoo.estoque.orchestrators.faturamento_pipeline --ciclo INVENTARIO_2026_05 --etapas A,B --cod-produto 210639522 --limite 1 --pular-pre-flight`
  - **status=DRY_RUN_OK em 1623ms**
  - ETAPA A status `DRY_RUN_OK_ETAPA_A_NOOP` (1 ajuste 789ms).
  - ETAPA B status `DRY_RUN_OK_ETAPA_B` (1 picking planejado):
    - origin: `INV-INVENTARIO_2026_05-SAIDA-INDUSTRI-171489` (idempotente)
    - tipo_op=industrializacao, co=1 (FB) -> cd=5 (LF)
    - picking_type_id=53 (FB Expedicao Industrializacao) ✓
    - partner_id=35 (LF) ✓
    - location_origem=8 (FB/Estoque) ✓
    - location_destino=26489 (Em Transito Industrializacao) ✓
    - qty_total=6000.0
  - Pos-fixes CR-C2: `grupos_direcao={"INDUSTRIALIZACAO_FB_LF": 1}` (chave por acao_decidida) ✓
- ✅ **CODE-REVIEW PARALELO** (feature-dev:code-reviewer) — 9 findings com confidence >= 70:
  - 2 CRITICAL (C1=92 status filter / C2=85 agrupamento incorreto)
  - 4 HIGH (H1=83 sleep boundary / H2=80 compensatorio acao / H3=80 ETAPA A untested / H4=82 abort guard D)
  - 3 MEDIUM (M1=85 intersecao vazia / M2=72 teste IDs hardcoded / M3=78 BLOQUEADO_SEFAZ status)
  - **Aplicados 7/9**: C1+C2+H1+H2+H4+M1+M3 (TODOs registrados para H3+M2 — proxima sessao).
- ✅ Cross-refs aplicados: `CLAUDE.md estoque` (status global + tabela §6) + `ROADMAP_SKILLS.md` HANDOFF + PLANEJAMENTO §0 + §7 (C6/C7/C8 ✅) + §12 (esta trilha).
- ✅ **NAO MEXEU** no script 09 (regra Rafael v14a-ops) nem RecebimentoLfOdooService (regra v14a-fix) nem InventarioPipelineService legacy.
- 🟢 **C6+C7+C8+F5c destravam v16** (ETAPA C — F5d aguardar invoices + sub-etapas .5/.6/.7).
- 🟢 Pattern arquitetural v15a validado em producao: atomos Skill 5 invocados via Python (NAO subprocess CLI) + barreira sincronizacao + auditoria + dry-run default.

### Sessao v15a (2026-05-25) — C6.5 ✅ Estender Skill 5 com 3 atomos inter-company

- ✅ Setup worktree + venv + ENV; main avancou 11 commits (SPED V36, weekly, fix tabelas, SDK 0.2.87, D8) — sem conflito esperado em `app/odoo/estoque/`, sem rebase.
- ✅ Pytest baseline confirmado: **416 verdes em 14.34s** (tests/odoo/) — paridade com v14b.
- ✅ Leituras obrigatorias: memorias `[[skill5_picking_pattern]]` + `[[sub-skill-c5-pattern]]` + `[[skill2_distribuir_indisp_pattern]]` + PLANEJAMENTO §3 + §7.3 D10-D18 + §7.5 D-OPS-3 + §10.6 EXPANDIDO + service-fonte ETAPA B (L617-1149) e ETAPA F (L1428-1688) do script 09.
- ✅ AskUserQuestion: opcao "3 atomos juntos nesta sessao" escolhida — sem fasear.
- ✅ **CENTRALIZADAS CONSTANTS ETAPA F** em `app/odoo/constants/picking_types.py` (resolve R19/pendencia §9):
  - `ACOES_ENTRADA_DESTINO_MANUAL: FrozenSet[str]` (set imutavel — antes `Set` inline em 09_*)
  - `PICKING_TYPE_ENTRADA_DESTINO_MANUAL: Dict[int, int]` (LF=19; CD/FB pendentes — descobrir audit)
  - `COMPANY_LABEL_ENTRADA: Dict[int, str]` (FB/CD/LF — usado em origin)
  - `LOCATION_ORIGEM_ENTRADA_INDUSTR = LOCATION_DESTINO_TRANSITO_INDUSTR` (alias semantico — mesma 26489, perspectivas diferentes)
- ✅ **3 ATOMOS NOVOS** em `app/odoo/estoque/scripts/picking.py` (StockPickingService) + 1 helper publico `aplicar_peso_volumes_fallback`:
  - `criar_picking_inter_company(...)` (~220 LOC novas) — encapsula `criar_transferencia` com pre-flight D-OPS-3 (read tracking em batch + remove lot_name/lot_id de produtos tracking='none'); pre-cond: company_origem!=company_destino + partner_id obrigatorio + linhas qty>0. Aceita `tracking_por_pid` pre-fetched p/ otim bulk. Retorna dict com `picking_id`, `tracking_none_pids`, `linhas_planejadas`, `tempo_ms`.
  - `validar_picking_inter_company(picking_id, linhas_esperadas, aplicar_peso_volumes=True, ...)` (~150 LOC) — fluxo F5b completo (D3): confirmar_e_reservar → preencher_qty_done → ajustar_qty_done_pelo_disponivel (G021) → validar(linhas_esperadas=) (G023 consolidar + G019 re-state) → aplicar_peso_volumes_fallback (G018 v2). NAO faz liberar_faturamento (F5c fica na Skill 8 orchestrator). Retorna dict com state_apos_validate, mls_pendencias, peso_volumes.
  - `criar_picking_entrada_destino_manual(...)` (~150 LOC) — ETAPA F: idempotencia via origin exato (search picking; se done = IDEMPOTENT_DONE skip; outro state = IDEMPOTENT_OTHER para investigacao) → create picking → **G023 critico** write company_id em moves apos create (XML-RPC nao herda) → action_confirm + action_assign → G011 re-escrever quantity + lot_name nas MLs → button_validate → **G019/G020** re-le state e raise se != 'done'. Aceita `moves_data` com `lot_dest_name` por produto.
  - `aplicar_peso_volumes_fallback(picking_id, ...)` (~70 LOC) — G018 v2: write `l10n_br_peso_liquido` + `l10n_br_peso_bruto` + `l10n_br_volumes` em stock.picking (writable). Capinado do script 09 L346-413.
- ✅ **19 PYTEST NOVOS VERDES** em `tests/odoo/services/test_stock_picking_service.py` (42 → 61):
  - 2 cobrindo `aplicar_peso_volumes_fallback` (aplica vs noop quando ja setado)
  - 6 cobrindo `criar_picking_inter_company` (basico, company iguais raises, partner_id raises, linhas vazias raises, **D-OPS-3 fix (tracking='none' remove lot_name)**, tracking_por_pid otim)
  - 4 cobrindo `validar_picking_inter_company` (fluxo completo com G018, sem linhas_esperadas, peso_volumes desativado, propaga G019 raise)
  - 7 cobrindo `criar_picking_entrada_destino_manual` (basico CRIADO, moves vazios raises, origin vazio raises, idempotente DONE, idempotente OTHER, G019 state nao done raises, **G023 company_id forcado em moves**)
- ✅ **BASELINE PYTEST ODOO**: 416 → **435 verdes em 14.36s** (+19 v15a).
- ✅ **SMOKE PROD v15a** (read-only — sem write em PROD) validou em 6 cods v14a-ops:
  - Constants ETAPA F importadas corretamente (PICKING_TYPE_ENTRADA_DESTINO_MANUAL={5:19}, LOCATION_ORIGEM_ENTRADA_INDUSTR=26489)
  - Tracking dos 6 cods resolvido em PROD: 102020600/4759598/4829046/4849003/4879046 = `lot`; 103500105 PIMENTA = `none` (esperado v14a-ops!)
  - `criar_picking_inter_company` com mock no WRITE: detectou tracking_none_pids=[35962 (pid de 103500105)]; linha do PIMENTA SEM `lot_name` (D-OPS-3 fix); outros 5 cods preservaram `lot_name='SEMLOTE'`; `criar_transferencia` chamado 1x com linhas normalizadas.
- ✅ **Cross-refs aplicados**:
  - `.claude/skills/operando-picking-odoo/SKILL.md` (description estendida; catalogo de atomos +4 atomos LIVE; Contratos novos secao; Fluxo 2.5.d; Validacao C2/C3/C5/C6 atualizados)
  - `.claude/agents/gestor-estoque-odoo.md` (header status v15a + mencao 3 atomos inter-company com D-OPS-3 fix)
  - `.claude/references/ROUTING_SKILLS.md` (header com extensao v15a)
  - `app/odoo/estoque/CLAUDE.md` (status + tabela §6 skill 5 estendida)
- ✅ **NAO MEXEU** no script 09 (regra Rafael v14a-ops "use scripts existentes apenas") nem no RecebimentoLfOdooService (regra Rafael v14a-fix).
- ✅ **Code-review v15a aplicado** (feature-dev:code-reviewer) — 3 findings IMPORTANT corrigidos antes do commit:
  - **CR-Issue-1 (confidence 85)**: `criar_picking_entrada_destino_manual` chamava `button_validate` SEM context `skip_backorder`. Adicionado `{'context': {'skip_backorder': True, 'picking_ids_not_to_backorder': [picking_id]}}` alinhando pattern dos outros atomos (`validar`, `devolver`).
  - **CR-Issue-2 (confidence 82)**: G011 step em ETAPA F NAO setava `qty_done` (so `quantity`). Adicionado `qty_done` explicito — defesa contra versoes Odoo onde immediate_transfer nao auto-seta. Script L1646-1665 PRECEDENTE em PROD validou sem qty_done mas atomo deve ser MAIS defensivo que o script.
  - **CR-Issue-3 (confidence 80)**: `validar_picking_inter_company` fazia 1 read extra de state apos `validar()` retornar — desnecessario porque `validar()` ja garante state='done' OR raise. Removido read; `state_final = 'done'` hardcoded.
  - Test ajustado (`test_criar_picking_entrada_destino_manual_basico`): expecta `qty_done` no ml_update + `button_validate` com context skip_backorder.
  - **61 pytest verdes** apos fixes (mantido); 435 baseline Odoo (mantido).
- 🟢 **C6.5 destrava v15b** (orchestrator base Skill 8 — C6+C7+C8): pode invocar `criar_picking_inter_company` em F5a, `validar_picking_inter_company` em F5b + `criar_picking_entrada_destino_manual` em ETAPA F sem reimplementar logica de picking.
- 🟢 **D-OPS-3 fix permanente codificado no atomo** — orchestrator v15b NAO precisa mais workaround SEMLOTE; passa `lot_name` natural dos ajustes e o atomo strip se produto for tracking='none'.

---

## 13. GLOSSARIO

| Termo | Significado |
|-------|-------------|
| **F5a/F5b/F5c/F5d/F5e** | Sub-etapas da etapa "Faturamento" no service `inventario_pipeline_service.py` (nome historico) |
| **Etapa A/B/C/D/E/F** | Etapas do script `09_executar_onda1_bulk.py` (nome operacional) — A=transf interna, B=picking, C=invoice, D=SEFAZ, E=entrada FB, F=entrada destino |
| **Pre-flight** | Validacao de cadastro fiscal de produtos da onda antes do bulk (G017 NCM + G035 barcode + G018 weight) |
| **Recovery** | Retomada de bulk parcial via loop com idempotencia + timeout + stagnation detector |
| **Canary** | Execucao de 1 ajuste real PROD apos validacao dry-run, antes do bulk |
| **Bulk** | Execucao em massa (10-700 ajustes) apos canary OK |
| **DEV_*** | Acoes_decididas com fiscal setup customizado (DEV_FB_LF, DEV_LF_FB, DEV_CD_LF, DEV_LF_CD) — exigem `_garantir_fiscal_setup` (G034) |
| **MIGRACAO** | Lote consolidador legado usado em transferencias internas (G031: por produto, nao universal) |
| **Indisponivel** | Location final para saldo nao-disponivel (FB=Indisp/CD=Indisp/LF=Indisp por company) |
| **fase_pipeline** | Coluna em `AjusteEstoqueInventario` que rastreia estado por etapa (F5a_PICKING_OK, F5b_VALIDADO, F5c_LIBERADO, F5d_INVOICE_GERADA, F5e_SEFAZ_OK, F5f_ENTRADA_OK) |
| **acao_decidida** | Direcao do faturamento (TRANSFERIR_*, INDUSTRIALIZACAO_*, PERDA_*, DEV_*) |
| **chave_nfe** | NFe 35 digitos retornada apos SEFAZ-autorizado (campo `chave_nfe` no ajuste) |
| **CIEL IT** | Modulo fiscal de terceiros `l10n_br_ciel_it_account` (cria invoice apartir de picking; SEFAZ via Playwright UI) |
| **G##** | Gotchas codificados em `docs/inventario-2026-05/02-gotchas/G###-*.md` |

---

## 14. PONTEIROS RAPIDOS

| Recurso | Caminho |
|---------|---------|
| **Constituicao** | `app/odoo/estoque/CLAUDE.md` |
| **ROADMAP geral** | `app/odoo/estoque/ROADMAP_SKILLS.md` |
| **Pattern Skill 6 v9 (reuso)** | `app/odoo/estoque/orchestrators/pre_etapa_executor.py` |
| **Service-fonte** | `app/odoo/services/inventario_pipeline_service.py` |
| **Script-fonte macro** | `scripts/inventario_2026_05/09_executar_onda1_bulk.py` |
| **Pre-flight historico** | `scripts/inventario_2026_05/09_executar_onda1_bulk.py:139-211` (`validar_cadastro_fiscal`) |
| **Recovery historico (B→D)** | `scripts/inventario_2026_05/fat_lf_resume.sh` |
| **Recovery historico (E+F)** | `scripts/inventario_2026_05/fat_lf_resume_entrada.sh` |
| **Gotchas** | `docs/inventario-2026-05/02-gotchas/G{004,007,011,016,017,018,023,029,034,035}*.md` |
| **Subagente** | `.claude/agents/gestor-estoque-odoo.md` |
| **Folhas de fluxo** | `app/odoo/estoque/fluxos/` (galho 1.x a criar em C18) |
| **Constants** | `app/odoo/constants/{operacoes_fiscais,locations,picking_types,ids_diversos}.py` |
| **Memorias-chave** | `[[ciel_it_quirks]]`, `[[picking_317346_pendente]]`, `[[inventario_2026_05]]`, `[[skill6_planejar_pre_etapa_pattern]]` (pattern v9), `[[arquitetura_orquestrador_odoo]]` |

---

**FIM DO PLANEJAMENTO v13.** Atualizar §0 (status global), §7 (checkpoints), §9 (pendencias), §10 (decisoes), §12 (trilha) a cada sessao.
