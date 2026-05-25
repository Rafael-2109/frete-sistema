# PLANEJAMENTO — Skill 8 `faturando-odoo` (MACRO C3 SEFAZ)

**Criado:** 2026-05-25 v13 | **Audiencia:** Claude Code + agente web (orquestrador-Odoo) | **Sobrevive:** N sessoes

> **PROPOSITO:** documento vivo de planejamento que persiste o ESCOPO + CHECKPOINTS + DECISOES + PROGRESSO da capinagem da Skill 8 (`faturando-odoo`) — a MACRO C3 mais perigosa do roadmap (NF inter-company → robo CIEL IT → SEFAZ irreversivel). Atualizar a CADA sessao que toque esta skill.

> **REGRA INVIOLAVEL 0 (fundadora deste arquivo):** ANTES de qualquer modificacao em codigo da Skill 8, LER este arquivo INTEIRO + atualizar o checkpoint ativo. Sem isso, risco de regressao e perda de contexto entre sessoes e' inaceitavel para SEFAZ irreversivel.

---

## 0. CABECALHO DE ESTADO (atualizar a cada sessao)

| Campo | Valor |
|-------|-------|
| **Status global** | 🟡 PLANEJADO COMPLETO (sessao v13, escopo + 6 decisoes RESOLVIDAS; pre-flight sub-skill + paralelismo por etapa + F5a/F5b via Skill 5) |
| **Sessao atual** | v13 (2026-05-25) — planejamento + estruturacao + decisoes |
| **Sessoes estimadas** | 8-9 sessoes (v13 → v20+) — +1 por estender Skill 5 com atomos inter-company (C6.5) |
| **Baseline pytest atual** | 393 verdes (tests/odoo/) |
| **Baseline pytest pos-v20 esperado** | ≥420 verdes (+~25-30 testes Skill 8) |
| **Branch** | `feat/estoque-odoo` (worktree `/home/rafaelnascimento/projetos/frete_sistema_estoque_odoo`) |
| **Service-fonte** | `app/odoo/services/inventario_pipeline_service.py` (1.346 LOC) |
| **Script-fonte macro** | `scripts/inventario_2026_05/09_executar_onda1_bulk.py` (~1.850 LOC) |
| **Pattern de reuso** | `app/odoo/estoque/orchestrators/pre_etapa_executor.py` (Skill 6 v9, 907 LOC) |
| **Destino do orchestrator** | `app/odoo/estoque/orchestrators/faturamento_pipeline.py` (a criar) |
| **Decisoes ABERTAS** | 0 (TODAS 6 RESOLVIDAS em v13) |
| **Checkpoints concluidos** | 3 de 24 (C1 ✅ pre-mortem + C2 ✅ mineracao service + C4 ✅ escopo; +C6.5 novo) |
| **Skills NOVAS criadas pela Skill 8** | (1) `auditando-cadastro-fiscal-odoo` — sub-skill agnostica para pre-flight; (2) atomos NOVOS na Skill 5 `operando-picking-odoo` — `criar_picking_inter_company` + `validar_picking_inter_company` (C6.5) |
| **Pattern arquitetural FINAL** | **Etapa = barreira de sincronizacao** (todos pickings → todas validacoes → todas emissoes → polling F5d → SEFAZ F5e → E → F). Mitiga DetachedInstanceError + SSL drop. |
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
| Implementacao service | ⬜ | v14 (C5 redefinido) |
| Wrapper CLI | ⬜ | v14 (C5) |
| Testes pytest | ⬜ | v14 (C5) |
| SKILL.md | ⬜ | v14 (C5) |
| Integracao com Skill 8 | ⬜ | v15 (C6 orchestrator base chama sub-skill) |
| Cross-refs (subagente, ROUTING_SKILLS, etc.) | ⬜ | v14 (C5) |

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
| **Etapas SEQUENCIAIS com BARREIRA de sincronizacao** (B→C→D→E→F) | **DECISAO 10.3 (Rafael v13)**: fazer TUDO por etapa — todos os pickings, depois todas as validacoes, depois todas as emissoes. Mitiga DetachedInstanceError + SSL timeout. Cada etapa = barreira de sincronizacao (aguarda 100% completar antes de iniciar a proxima) |
| Paralelismo INTRA-etapa (B com Semaphore=5) | preservar — pattern do service e' performatico e validado em PROD |
| **NAO interleaving de ajustes entre etapas** | NAO rodar B→C→D em pipeline por ajuste (ajuste 1 vai B→C; ajuste 2 vai B→C; ...). Em vez: TODOS em B, depois TODOS em C, etc. Isso e' chave para reduzir SSL drop window. |
| Polling F5d sequencial longo | nao paralelizar — Odoo CIEL IT rejeita concorrente |
| F5e SEQUENCIAL (1 browser Playwright) | preservar — Playwright nao concorre |
| Recovery loop fora do orchestrator (script shell?) | DECISAO: capinar como `--resume` modo CLI no proprio entry-point Python |
| **F5a/F5b refatorados para atomos Skill 5** | **DECISAO 10.6 (Rafael v13)**: principio inviolavel "se mexe com picking, devera ser atraves da Skill 5". F5a vira `criar_picking_inter_company` na Skill 5; F5b vira `validar_picking_inter_company` na Skill 5. Skill 8 ORQUESTRA sequencia. |

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
| **C3** | Mineracao `09_executar_onda1_bulk.py` (etapas A/B/E/F) | mapa etapas+funcoes+chamadas, conferir | Doc inline (§7.3) com referencia file:line | v14 | ⬜ | |
| **C4** | Confirmar escopo completo (a/b/c) com Rafael | decisoes §10.1, §10.2 fechadas | Rafael confirmou via AskUserQuestion | v13 | ✅ | "estruturar bem, depois rodar casos reais" |
| **C5** | **Criar sub-skill `auditando-cadastro-fiscal-odoo` (perfil inventario V1)** | `app/odoo/estoque/scripts/cadastro_fiscal_audit.py` (service) + `.claude/skills/auditando-cadastro-fiscal-odoo/{SKILL.md,scripts/auditar_cadastro.py}` (CLI) + cross-refs (subagente + ROUTING_SKILLS + tool_skill_mapper) | smoke dry-run em onda real OK; >5 pytest verdes; --perfil inventario funcional | v14 | ⬜ | **REDEFINIDO v13 — decisao 10.5 RESOLVIDA (Rafael: pre-flight como sub-skill separada agnostica para reuso futuro em venda-cliente)** |
| **C6** | Capinar orchestrator base (skeleton) | `app/odoo/estoque/orchestrators/faturamento_pipeline.py` com entry-points (vazios), imports, dataclasses, constants | pytest smoke import OK | v15 | ⬜ | |
| **C6.5** | **NOVO v13 — Estender Skill 5 com atomos inter-company** (DECISAO 10.6) | `app/odoo/estoque/scripts/picking.py` ganha `criar_picking_inter_company` + `validar_picking_inter_company`; SKILL.md `operando-picking-odoo` estendida; pytest >5 verdes novos | dry-run PROD OK em 1 picking real; idempotencia validada | v15 | ⬜ | **NOVO checkpoint criado em v13 mid** |
| **C7** | Capinar F5a no orchestrator (chamando atomo Skill 5 estendido) | metodo `_executar_etapa_b_criar` no orchestrator que itera ajustes em paralelo (Semaphore=5) chamando `criar_picking_inter_company` | 5+ pytest verdes; dry-run em onda real OK; barreira de sincronizacao validada | v15 | ⬜ | depende C6.5 |
| **C8** | Capinar F5b no orchestrator (chamando atomo Skill 5 estendido) | metodo `_executar_etapa_b_validar` + chamada `validar_picking_inter_company` | 5+ pytest verdes; dry-run OK; G011 qty_done + G018 peso_liquido validados via Skill 5 | v15-v16 | ⬜ | depende C6.5 |
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

### 7.3 Mineracao script-fonte (C3 — preencher em v14)

> Modelo similar para `09_executar_onda1_bulk.py`. Etapas A/B/E/F.

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

### 10.3 ✅ Pattern paralelismo (RESOLVIDO v13)
- **Decisao**: (a) **Preservar Semaphore=5 do service atual** — paraleliza DENTRO de cada etapa; sequencializa ENTRE etapas (barreira de sincronizacao).
- **Razao Rafael v13 2026-05-25**: "fazer tudo por etapa — todos os pickings, todas as validacoes, todas emissoes de fatura, etc.". Razao concreta: DetachedInstanceError e SSL connection timeout sao agravados por loops longos com state DB compartilhado. Etapas curtas e atomicas reduzem janela de exposicao.
- **Pattern arquitetural** (consolidando):
  - **Por etapa**: F5a (todos pickings em paralelo Semaphore=5) → RETORNA → F5b (todas validacoes em paralelo Semaphore=5) → RETORNA → F5c (...) → RETORNA → F5d (polling longo SEQUENCIAL) → RETORNA → F5e (SEFAZ Playwright SEQUENCIAL 1 browser) → RETORNA → E → F.
  - **Cada etapa eh uma barreira de sincronizacao**: aguarda 100% completar antes de iniciar a proxima.
  - **DentroDaEtapa: Semaphore=5** (paraleliza ate 5 ajustes simultaneamente).
  - **EntreEtapas: serial** (nao ha' interleaving de ajustes entre etapas).
- **Mitigacoes** de DetachedInstanceError + SSL drop:
  - G016 codificado: `_commit_with_retry` antes de cada operacao longa + re-fetch via `db.session.get(AjusteEstoqueInventario, ajuste_id)` apos.
  - Etapas longas (F5d 1800s, F5e Playwright 5-10min/NF) tem re-fetch explicito.
  - TCP keepalive em `config.py:115-118` (ja' configurado).
- **Smoke obrigatorio em pytest**: simular SSL drop mid-etapa via mock + verificar re-fetch correto.

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

### 10.6 ✅ Refatorar F5a/F5b para reusar Skill 5 (RESOLVIDO v13)
- **Decisao**: (c) **REFATORAR COMPLETAMENTE** — F5a vira atomo novo na Skill 5 `criar_picking_inter_company`; F5b vira atomo novo `validar_picking_inter_company`.
- **Razao Rafael v13 2026-05-25**: principio arquitetural inviolavel — "Se mexe com picking, devera ser atraves da Skill 5". "Devemos seguir o principio da atomicidade e funcao especifica". "Fluxo >> Skills (esta registrado, apenas SIGA)".
- **Implicacao arquitetural**:
  - **Skill 5 estendida** com 2 atomos novos para inter-company:
    - `criar_picking_inter_company(args) -> picking_id` (F5a) — encapsula G004 partner_id + G023 company_id forcado em moves + carrier + incoterm
    - `validar_picking_inter_company(picking_id, qty_done_map, peso_liquido_map) -> bool` (F5b) — encapsula G011 qty_done + G018 peso_liquido + G019/G020 idempotencia
  - **F5c `liberar_faturamento`** pode ir tambem para Skill 5 ou ficar na Skill 8 (decidir em v14 — mas inclinacao para Skill 5: e' operacao em picking).
  - **F5d/F5e** permanecem na Skill 8 (operam em `account.move`, nao picking).
- **Atualizacao do cronograma**:
  - v14 inclui PLANEJAR extensao da Skill 5 (especificar 2-3 atomos novos no SKILL.md existente)
  - v15 EXECUTA: primeiro estende Skill 5 (~1 dia), depois implementa orchestrator Skill 8 que usa
  - Possivel +1 sessao se atomos novos exigirem mais cuidado (pytest >5 verdes + dry-run PROD)
- **Risco mitigado**: refatoracao FRESCA (capinando de inventario_pipeline_service.py) reduz risco — nao mexe em codigo legacy de Skill 5, apenas ADICIONA atomos.
- **Cross-refs a atualizar quando criar atomos novos (em v15)**:
  - `app/odoo/estoque/scripts/picking.py` (adicionar 2 funcoes top-level)
  - `.claude/skills/operando-picking-odoo/SKILL.md` (estender contrato com 2 novos atomos)
  - testes pytest em `tests/odoo/services/test_stock_picking_service.py` (adicionar >5 verdes)
  - subagente `gestor-estoque-odoo` (atualizar listagem Skill 5 com novos atomos)
  - VALIDACAO_FINAL_SESSAO.md §17+ (nova entrada documentando extensao)
  - memoria `[[skill5_picking_pattern]]` (atualizar com inter-company)

---

## 11. CRONOGRAMA ESTIMADO

| Sessao | Foco | Checkpoints | Risco |
|--------|------|-------------|-------|
| **v13 (esta)** | Planejamento + estruturacao + decisao 10.5 (pre-flight sub-skill) | C1, C4 | Baixo (sem codigo) |
| **v14** | Mineracao detalhada + decisoes 10.3/10.4/10.6 + **criar sub-skill `auditando-cadastro-fiscal-odoo`** | C2, C3, **C5** | Baixo-Medio (cria service novo) |
| **v15** | **Estender Skill 5 (atomos inter-company)** + Orchestrator base + F5a + F5b (Skill 8 invoca sub-skill C5 no bulk + chama atomos novos Skill 5) | C6, **C6.5**, C7, C8 | Medio-Alto (mexe service + estende skill madura) |
| **v16** | F5c + F5d (com G016+G007+G034+G029) | C9, C10 | Medio (SSL pattern critico) |
| **v17** | F5e + etapas E/F | C11, C12, C13 | Alto (SEFAZ Playwright, G023) |
| **v18** | Recovery + SKILL.md + tests + smokes | C14, C15, C16, C17 | Medio |
| **v19** | Folhas fluxos + cross-refs + Canary | C18, C19, C20 | Alto (PRIMEIRA NF real) |
| **v20+** | Bulk + code-review + commit final | C21, C22, C23 | Alto (volume real) |

**Total estimado: 8 sessoes** (sub-skill C5 fica em v14 sem expandir cronograma). Pode estender se canary C20 revelar gaps nao previstos OU se sub-skill `auditando-cadastro-fiscal-odoo` exigir validacao mais profunda em v14.

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
