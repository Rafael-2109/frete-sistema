# PLANEJAMENTO — Skill 8 `faturando-odoo` (MACRO C3 SEFAZ)

**Criado:** 2026-05-25 v13 | **Audiencia:** Claude Code + agente web (orquestrador-Odoo) | **Sobrevive:** N sessoes

> **PROPOSITO:** documento vivo de planejamento que persiste o ESCOPO + CHECKPOINTS + DECISOES + PROGRESSO da capinagem da Skill 8 (`faturando-odoo`) — a MACRO C3 mais perigosa do roadmap (NF inter-company → robo CIEL IT → SEFAZ irreversivel). Atualizar a CADA sessao que toque esta skill.

> **REGRA INVIOLAVEL 0 (fundadora deste arquivo):** ANTES de qualquer modificacao em codigo da Skill 8, LER este arquivo INTEIRO + atualizar o checkpoint ativo. Sem isso, risco de regressao e perda de contexto entre sessoes e' inaceitavel para SEFAZ irreversivel.

---

## 0. CABECALHO DE ESTADO (atualizar a cada sessao)

| Campo | Valor |
|-------|-------|
| **Status global** | 🟡 PLANEJADO (sessao v13, escopo definido com Rafael) |
| **Sessao atual** | v13 (2026-05-25) — planejamento + estruturacao |
| **Sessoes estimadas** | 6-8 sessoes (v13 → v20+) |
| **Baseline pytest atual** | 393 verdes (tests/odoo/) |
| **Baseline pytest pos-v20 esperado** | ≥420 verdes (+~25-30 testes Skill 8) |
| **Branch** | `feat/estoque-odoo` (worktree `/home/rafaelnascimento/projetos/frete_sistema_estoque_odoo`) |
| **Service-fonte** | `app/odoo/services/inventario_pipeline_service.py` (1.346 LOC) |
| **Script-fonte macro** | `scripts/inventario_2026_05/09_executar_onda1_bulk.py` (~1.850 LOC) |
| **Pattern de reuso** | `app/odoo/estoque/orchestrators/pre_etapa_executor.py` (Skill 6 v9, 907 LOC) |
| **Destino do orchestrator** | `app/odoo/estoque/orchestrators/faturamento_pipeline.py` (a criar) |
| **Decisoes ABERTAS** | 5 (ver §10) |
| **Checkpoints concluidos** | 0 de 23 |
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
| **Pre-flight** | G017 NCM, G035 barcode, G018 weight (validar+corrigir antes do bulk) |
| **Recovery** | Loop com idempotencia por `fase_pipeline` + timeout/iteracao + stagnation detector |
| **SSL/timeout** | G016 commit_with_retry + re-fetch ajuste + TCP keepalive |
| **Auditoria** | `OperacaoOdooAuditoria.registrar` por etapa+ajuste+uuid8 |
| **Paralelizacao** | `ThreadPoolExecutor + Semaphore(max_concurrent=5)` (preservar do service atual) |
| **Modos CLI** | `--pre-flight` / `--etapa A|B|C|D|E|F` / `--canary` / `--bulk` / `--resume` |
| **Folha de fluxo** | `app/odoo/estoque/fluxos/1.1-faturamento-completo.md` + `1.3-transferencia-completa.md` |
| **SKILL.md** | Com 5+ receitas (canary, bulk, resume, pre-flight, recovery manual de NF travada) |
| **Tests** | Pytest `tests/odoo/services/test_faturamento_pipeline_orchestrator.py` (>20 testes) |

### 2.3 Sai do escopo (DELEGADO)

| Categoria | Para onde |
|-----------|-----------|
| **Etapa A** (transferencias internas pre-faturamento) | Skill 2 `transferindo-interno-odoo` ✅ |
| **Picking generico** (cancelar, validar, devolver fora do pipeline) | Skill 5 `operando-picking-odoo` ✅ |
| **Reservas / cirurgia ML orfa** | Skill 2.4 `operando-reservas-odoo` 🟡 |
| **Ajustes positivos puros** (etapa de planejamento) | Skill 6 `planejando-pre-etapa-odoo` 🟡 |
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
│  │  ETAPA F    │  - INDUSTRIALIZACAO_FB_LF: picking entrada manual        │
│  │  entrada    │    location_dest_id=42, picking_type_id=19,               │
│  │  manual     │    company_id=5 FORCADO em moves                          │
│  │  FB→{LF,CD} │  - Marca fase_pipeline='F5f_ENTRADA_OK'                   │
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

## 4. PRE-FLIGHT (obrigatorio antes do bulk)

### 4.1 G017 — NCM cadastro

- **Risco:** `product.l10n_br_ncm_id=False` gera `<NCM>False</NCM>` no XML → SEFAZ cstat=225.
- **Detecao:** query `product.product` com `l10n_br_ncm_id=False` para produtos da onda.
- **Correcao:** cadastrar NCM via `l10n_br_ciel_it_account.ncm` (campo `codigo_ncm`, NAO `code` — quirk CIEL IT).
- **Existe?** SIM — funcao `validar_cadastro_fiscal` em `09_executar_onda1_bulk.py:139-211`.
- **Acao Skill 8:** capinar como sub-modo `--pre-flight` ou sub-skill nova `auditando-cadastro-fiscal-odoo`. **A DECIDIR (§10.5).**

### 4.2 G035 — barcode invalido

- **Risco:** `product.barcode` populado com `default_code` (ex: 9 digitos sem check digit GTIN-13) gera `<cEAN>` invalido → SEFAZ cstat=225.
- **Detecao:** validar GTIN dos produtos da onda (existe `gtin_validator.py`).
- **Correcao:** `odoo.write('product.product', [ids], {'barcode': False})`.
- **Existe?** SIM — `gtin_validator.py` (caminho TBC em C5).
- **Acao Skill 8:** integrar em `--pre-flight`.

### 4.3 G018 — weight=0

- **Risco:** `product.weight=0` bloqueia `action_liberar_faturamento` (F5c) silenciosamente.
- **Detecao:** query `product.product.weight=0` para produtos da onda.
- **Correcao:** **NAO** alterar `product.weight` (CIEL IT hook nao persiste — quirk). Em vez: escrever `stock.picking.l10n_br_peso_liquido` manualmente apos F5b e antes de F5c.
- **Existe?** Workaround em script ad-hoc. NAO documentado em pre-flight isolado.
- **Acao Skill 8:** integrar peso_liquido fix dentro de F5b/F5c (tratado dentro do atomo) + alertar no pre-flight quando produto tem weight=0.

### 4.4 Saida do pre-flight

| Status | Acao operador |
|--------|---------------|
| `PRE_FLIGHT_OK` | bulk pode iniciar |
| `PRE_FLIGHT_NCM_FALTANDO` | cadastrar NCMs antes (lista no relatorio) |
| `PRE_FLIGHT_BARCODE_INVALIDO` | limpar barcode (operador autoriza correcao OU executa via `--auto-corrigir-barcode`) |
| `PRE_FLIGHT_WEIGHT_ZERO` | warning so' (peso_liquido sera setado dentro do atomo) |

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
| Etapas SEQUENCIAIS B→C→D→E→F (nao paralelo entre etapas) | F5d depende de F5c terminar; F5e depende de F5d achar invoice; etc. |
| Paralelismo INTRA-etapa (B com Semaphore=5) | preservar — pattern do service e' performatico |
| Polling F5d sequencial longo | nao paralelizar — Odoo CIEL IT rejeita concorrente |
| F5e SEQUENCIAL (1 browser Playwright) | preservar — Playwright nao concorre |
| Recovery loop fora do orchestrator (script shell?) | DECISAO: capinar como `--resume` modo CLI no proprio entry-point Python |

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
- Modos: `--pre-flight` / `--canary` / `--bulk` / `--resume` / `--consolidar`
- Args: `--ciclo NOME` / `--company-id ID` / `--etapas LISTA` / `--confirmar-sefaz` / `--max-workers N` / `--max-iter N` / `--timeout-iter S` / `--limite N` / `--ajuste-id ID`
- Exit codes: 0 (OK) / 1 (falha negocial) / 2 (uso) / 4 (DRY_RUN_OK)

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
| **C2** | Mineracao detalhada `inventario_pipeline_service.py` | mapa metodos+linhas+helpers, conferir com cabecalho | Doc inline neste arquivo (§7.2) com referencia file:line | v14 | ⬜ | |
| **C3** | Mineracao `09_executar_onda1_bulk.py` (etapas A/B/E/F) | mapa etapas+funcoes+chamadas, conferir | Doc inline (§7.3) com referencia file:line | v14 | ⬜ | |
| **C4** | Confirmar escopo completo (a/b/c) com Rafael | decisoes §10.1, §10.2 fechadas | Rafael confirmou via AskUserQuestion | v13 | ✅ | "estruturar bem, depois rodar casos reais" |
| **C5** | Capinar pre-flight (G017+G035+G018) | sub-modulo `app/odoo/estoque/scripts/pre_flight_faturamento.py` ou integrado no orchestrator | smoke dry-run em onda real (sem write) | v14-v15 | ⬜ | decisao §10.5 |
| **C6** | Capinar orchestrator base (skeleton) | `app/odoo/estoque/orchestrators/faturamento_pipeline.py` com entry-points (vazios), imports, dataclasses, constants | pytest smoke import OK | v15 | ⬜ | |
| **C7** | Capinar F5a (criar pickings) | metodo `_executar_f5a` no orchestrator | 5+ pytest verdes; dry-run em onda real OK | v15 | ⬜ | reusar Skill 5 onde possivel |
| **C8** | Capinar F5b (validar pickings) | metodo `_executar_f5b` + G018 peso_liquido + G011 qty_done | 5+ pytest verdes; dry-run OK | v15-v16 | ⬜ | |
| **C9** | Capinar F5c (liberar faturamento) | metodo `_executar_f5c` + pre-validar state='done' | 3+ pytest verdes; dry-run OK | v16 | ⬜ | |
| **C10** | Capinar F5d (aguardar invoices) + G016 SSL + G007+G034+G029 | metodo `_executar_f5d` com sub-etapas .5/.6/.7 + commit_with_retry | 5+ pytest verdes; dry-run com mock SSL drop OK | v16 | ⬜ | |
| **C11** | Capinar F5e (transmitir SEFAZ) + G016 SSL | metodo `_executar_f5e` Playwright serial + commit_with_retry + idempotencia F5e_SEFAZ_OK | 5+ pytest verdes (mockando Playwright); dry-run sem confirmar-sefaz OK | v16-v17 | ⬜ | |
| **C12** | Capinar etapa E (RecebimentoLf X→FB) | metodo `_executar_etapa_e` + idempotencia odoo_lf_invoice_id | 4+ pytest verdes; dry-run OK | v17 | ⬜ | |
| **C13** | Capinar etapa F (entrada manual FB→{LF,CD}) G023 | metodo `_executar_etapa_f` + company_id forcado em moves | 4+ pytest verdes; dry-run OK | v17 | ⬜ | |
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

### 7.2 Mineracao service-fonte (C2 — preencher em v14)

> Quando este checkpoint for executado, preencher com mapa metodo→linhas, dependencias, side-effects. Modelo:

| Metodo | Linhas | Side-effects | Deps Odoo | Deps DB | Notas |
|--------|--------|--------------|-----------|---------|-------|
| `resolver_location_destino` | 66-107 | (read-only) | constants | - | TBC |
| `__init__` | 109-... | inicializa odoo conn | - | - | TBC |
| `_commit_with_retry` | 165-202 | DB commit + rollback | - | session | G016 |
| `_garantir_payment_provider` | 204-291 | write account.move | account.move | - | G029 |
| `_garantir_fiscal_setup` | 293-... | write account.move + reset_to_draft+post | account.move | - | G034 |
| `_corrigir_price_zero_em_invoice` | 401-... | write account.move.line | account.move.line | - | G007 |
| `_registrar_op` | 523-... | insert auditoria | - | OperacaoOdooAuditoria | - |
| `f5a_criar_pickings` | 581-... | create stock.picking + write moves | stock.picking, stock.move | AjusteEstoqueInventario | paralelo |
| `f5b_validar_pickings` | 774-... | action_assign + qty_done + button_validate | stock.picking, stock.move.line | AjusteEstoqueInventario | paralelo, agrupado |
| `f5c_liberar_faturamento` | 882-... | action_liberar_faturamento | stock.picking | AjusteEstoqueInventario | paralelo |
| `f5d_aguardar_invoices` | 945-... | search account.move + _garantir_* | account.move | AjusteEstoqueInventario | polling longo |
| `f5e_transmitir_sefaz` | 1116-... | Playwright transmit + write account.move | account.move | AjusteEstoqueInventario | serial, irreversivel |

### 7.3 Mineracao script-fonte (C3 — preencher em v14)

> Modelo similar para `09_executar_onda1_bulk.py`. Etapas A/B/E/F.

---

## 8. RISCOS ARQUITETURAIS E MITIGACAO

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
| Confirmar caminho exato do `gtin_validator.py` (G035) | C5 | ⬜ | grep + Read | v14 |
| Confirmar onde fica `validar_cadastro_fiscal` (G017 fonte) | C5 | ⬜ | Read `09_executar_onda1_bulk.py:139-211` | v14 |
| Decidir: pre-flight como sub-skill nova ou entry-point Skill 8? | §10.5 | ⬜ | AskUserQuestion (v14) | v14 |
| Decidir: centralizar journals 847/1002/987 nesta skill ou depois? | §10.4 | ⬜ | AskUserQuestion (v14) | v14 |
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

### 10.3 ⬜ Pattern paralelismo (PENDENTE v14)
- **Opcoes**:
  - (a) Preservar Semaphore=5 do service atual (paraleliza F5a, F5b, F5c por picking_id)
  - (b) Refatorar para pattern Skill 6 v9 (ThreadPoolExecutor por ajuste com app_context+conn proprios)
- **Recomendacao**: (a) — pattern do service e' eficiente, validado em PROD em ondas anteriores. (b) so' se houver evidencia de starvation.

### 10.4 ⬜ Centralizar journals (847/1002/987) (PENDENTE v14)
- **Opcoes**:
  - (a) Sim, nesta skill — criar `app/odoo/constants/journals.py` em C6
  - (b) Nao, adiar para Skill 7 (escriturando) que tambem precisa
  - (c) Nao, deixar inline no orchestrator
- **Recomendacao**: (b) — escopo Skill 8 ja' grande, tarefa ortogonal.

### 10.5 ⬜ Pre-flight como sub-skill ou entry-point (PENDENTE v14)
- **Opcoes**:
  - (a) Sub-skill nova `auditando-cadastro-fiscal-odoo` (orquestrada pelo Skill 8)
  - (b) Entry-point `--pre-flight` no proprio `faturar_pipeline.py`
  - (c) Helper privado dentro do orchestrator (chamado automaticamente antes do bulk)
- **Recomendacao**: (b) — minimiza fragmentacao; suficiente para v1.

### 10.6 ⬜ Refatorar F5a/F5b para reusar Skill 5 (PENDENTE v15)
- **Opcoes**:
  - (a) Sim — F5a vira `picking.criar_picking_inter_company`; F5b vira `picking.validar_picking_com_pre_validacao_state`
  - (b) Nao — manter F5a/F5b especificos do pipeline (sao pesados, com qty_done agrupado)
- **Recomendacao**: (b) — overhead de generalizacao maior que beneficio.

---

## 11. CRONOGRAMA ESTIMADO

| Sessao | Foco | Checkpoints | Risco |
|--------|------|-------------|-------|
| **v13 (esta)** | Planejamento + estruturacao | C1, C4 | Baixo (sem codigo) |
| **v14** | Mineracao + decisoes 10.3/10.4/10.5 + pre-flight C5 | C2, C3, C5 (parcial) | Baixo |
| **v15** | Orchestrator base + F5a + F5b | C6, C7, C8 | Medio (mexe service pattern) |
| **v16** | F5c + F5d (com G016+G007+G034+G029) | C9, C10 | Medio (SSL pattern critico) |
| **v17** | F5e + etapas E/F | C11, C12, C13 | Alto (SEFAZ Playwright, G023) |
| **v18** | Recovery + SKILL.md + tests + smokes | C14, C15, C16, C17 | Medio |
| **v19** | Folhas fluxos + cross-refs + Canary | C18, C19, C20 | Alto (PRIMEIRA NF real) |
| **v20+** | Bulk + code-review + commit final | C21, C22, C23 | Alto (volume real) |

**Total estimado: 8 sessoes**. Pode estender se canary C20 revelar gaps nao previstos.

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
- ⬜ Resto dos checkpoints pendentes para v14+
- 🟡 Documento PLANEJAMENTO_SKILL8_FATURANDO.md criado (esta versao)

### Sessao v14 (futuro)
- [adicionar quando ocorrer]

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
