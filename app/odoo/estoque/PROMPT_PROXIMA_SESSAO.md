Continue o trabalho do orquestrador-Odoo. Worktree: `/home/rafaelnascimento/projetos/frete_sistema_estoque_odoo` (branch `feat/estoque-odoo`). `main` continua VIVO em paralelo. Verificar se avançou e considerar rebase ANTES de iniciar.

## Setup OBRIGATÓRIO (worktree sem .env)

```bash
cd /home/rafaelnascimento/projetos/frete_sistema_estoque_odoo
source /home/rafaelnascimento/projetos/frete_sistema/.venv/bin/activate
set -a; . <(grep -E '^(DATABASE_URL|ODOO_)' /home/rafaelnascimento/projetos/frete_sistema/.env); set +a
git fetch origin main && git log --oneline HEAD..origin/main  # ver se main avancou
```

## 📋 ESTADO ATUAL — apos v16 (ETAPA A REAL + ETAPA C F5d + G014 + 9 fixes 2 reviewers)

**Sessao v16 (2026-05-25)** entregou em 1 sessao:

1. **`_invoice_helpers.py` NOVO** (~430 LOC) — arquivo separado conforme decisao Rafael "evita inline contaminando logica generica":
   - 3 helpers F5d.5/.6/.7 (G029 payment_provider, G034 fiscal_setup DEV_*, G007 price_zero)
   - Perfil V1 'inventario-inter-company'; outros perfis (venda-cliente, compras-importacao) raise NotImplementedError
   - `FISCAL_SETUP_POR_ACAO_INVENTARIO` local (capinado do service legado L143-159)
   - Auditoria via OperacaoOdooAuditoria.registrar (lazy + try/except)

2. **C10 ETAPA C REAL** (`executar_etapa_c` substitui stub NOT_IMPLEMENTED_v15b):
   - Filtra ajustes `fase_pipeline='F5c_LIBERADO'` com `picking_id_odoo` populado
   - SNAPSHOT meta antes do polling (D5 anti-DetachedInstance em loops 1800s)
   - Polling 1800s/40s (`picking_svc.aguardar_invoice_do_robo`)
   - Para cada invoice resolvida: safe_session_get + marca F5d_INVOICE_GERADA + invoice_id_odoo + external_id_operacao
   - Sub-etapas .5/.6/.7 try/except (D6 — falha individual NAO derruba)
   - Timeout: registra TIMEOUT em auditoria, NAO muda fase (operador pode resume v18)

3. **C10.2 ETAPA A REAL** (substitui guard `NotImplementedError` v15c):
   - Filtra `ACOES_LOTE = {RENOMEAR_LOTE, TRANSFERIR_LOTE}` (escopo DISJUNTO de ACOES_PICKING)
   - Invoca Skill 2 v2 `transferir_quantidade_para_lote_v2` por ajuste (SEQUENCIAL D13)
   - external_id_operacao + auditoria por ajuste
   - Flag DEPRECATED `permitir_etapa_a_noop_real=True` ainda funciona (compat ate v17; emite WARNING)

4. **C10.3 G014 PRE-CHECK** (`_g014_pre_check_lotes_vencidos`):
   - Antes de criar picking, detecta lotes vencidos com saldo livre
   - Calcula `qty_a_migrar = min(demand - livre_validos, livre_vencidos)`
   - Migra via Skill 2 v2 para lote novo `INV-{cod}-{YYYYMMDD}` (idempotente por dia)
   - Atualiza `lote_origem` em memoria do chunk

5. **2 code-reviewers paralelos** (foco SSL/polling + idempotencia/perfis): **9 findings (4 CRIT + 5 HIGH) — TODOS aplicados**:
   - **R1F1** (CRIT 95): validar perfil ANTES do polling (anti-poison session)
   - **R2F1** (CRIT 92): guard `situacao_nf` em `garantir_payment_provider` fallback (anti-invalidar SEFAZ)
   - **R2F2** (CRIT 88): incluir `'enviado'` (mid-SEFAZ) nos guards de `garantir_fiscal_setup`
   - **R1F4** (HIGH 82): substituir `datetime.utcnow()` (banido pelo hook) por `agora_utc_naive`
   - **R2F3** (HIGH 85): guard `situacao_nf` em `corrigir_price_zero_em_invoice` (F5d.6 ANTES de F5d.7)
   - **R2F4** (HIGH 80): `garantir_fiscal_setup` retorna True com `SKIP_GUARD_SITUACAO_NF` em auditoria
   - **R2F5** (HIGH 83): `DEV_FB_LF` sem mapeamento registra `SKIP_NAO_MAPEADO` (nao silencia)
   - **R1F2** (HIGH 88): G014 partial failure marca cod como falha do chunk (anti-action_assign silencioso)
   - **R1F3** (HIGH 85): commit_resilient False apos invoice resolve -> `continue` (anti-cascata sub-etapas)

6. **Pytest**: 472 → **483 verdes em 15.51s** (+11 v16):
   - 5 ETAPA C v16 (dry-run skip/com ajustes/sem picking_id, real-run resolve+sub-etapas, timeout total, perfil invalido FALHA)
   - 4 ETAPA A v16 (real Skill 2 v2, skip ja TRANSF_OK, falha Skill 2, flag DEPRECATED)
   - 4 G014 pre-check (sem vencido, dry-run planeja, real Skill 2 v2, quant sem lote nao vencido)
   - 1 dry-run noop atualizado para v16 status

7. **Smoke dry-run PROD re-validado** em cod 105000007 (4 pickings F5c_LIBERADO):
   - `python -m app.odoo.estoque.orchestrators.faturamento_pipeline --ciclo INVENTARIO_2026_05 --etapas A,B,C --cod-produto 105000007 --pular-pre-flight`
   - ETAPA C dry-run em 766ms detectou pickings [317346, 317516, 317517, 317518]
   - ETAPA combinado A+B+C: status global DRY_RUN_OK em 862ms

8. **Interrupcao Rafael (commit isolado)**: CSV 121 ajustes simples salvos em `scripts/inventario_2026_05/ajustes_simples_pendentes_v16_2026-05-25.csv` (12 POSITIVO + 109 NEGATIVO; 101 FB + 14 CD + 6 LF). Commit `168499bd`. Sem processamento.

**Baseline pytest**: **483 verdes em 15.51s** (472 baseline v15c + 11 v16).

**Documento vivo MACRO (regra inviolavel 0)**:
`app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md` (~1500+ LOC, 14 secoes + trilha v16 detalhada §12)

**Memorias-chave** (LER PRIMEIRO antes de v17):
- `[[skill5_picking_pattern]]` — pattern Skill 5 v3 + v15a (3 atomos) + v15c F1 idempotencia origin
- `[[skill6_planejar_pre_etapa_pattern]]` — pattern orchestrator C3 v9 (template reusado v15b/c/v16)
- `[[sub-skill-c5-pattern]]` — pattern sub-skill C5 V1 'inventario' (v14b)
- `[[teste-real-6-cods-v14a-ops]]` — origem operacional D-OPS-1..5

**Checkpoints concluidos: 10 de 24**
✅ C1 pre-mortem | ✅ C2 minera service | ✅ C3 minera script | ✅ C4 escopo confirmado
✅ C5 sub-skill auditando-cadastro-fiscal-odoo V1 (v14b)
✅ C6.5 Skill 5 estendida com 3 atomos inter-company (v15a)
✅ C6 orchestrator base esqueleto (v15b)
✅ C7 ETAPA B F5a criar pickings (v15b/c)
✅ C8 ETAPA B F5b validar pickings (v15b)
✅ C9 ETAPA B F5c liberar faturamento (v15b)
✅ **C10 ETAPA C F5d aguardar invoices + sub-etapas .5/.6/.7 + ETAPA A real + G014 (v16)**

**Arquivos NOVOS criados em v16**:
- `app/odoo/estoque/scripts/_invoice_helpers.py` (~430 LOC — 3 helpers + perfis)

**Arquivos modificados em v16**:
- `app/odoo/estoque/orchestrators/faturamento_pipeline.py` (ETAPA C real + ETAPA A real + G014 + 9 fixes reviewers)
- `tests/odoo/services/test_faturamento_pipeline_orchestrator.py` (14 testes novos)
- `app/odoo/estoque/CLAUDE.md` (status v16)
- `app/odoo/estoque/ROADMAP_SKILLS.md` (handoff v16)
- `app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md` (§0 + §7 C10 ✅ + §12 trilha v16)

## 🎯 PRIORIDADE v17 — F5e SEFAZ Playwright (IRREVERSIVEL) + ETAPA E RecLF + ETAPA F atomo Skill 5

**Objetivo** (~250-300min): implementar ETAPAS D + E + F no orchestrator. **D e' IRREVERSIVEL (SEFAZ)** — exigir confirmacao explicita + canary obrigatorio.

### Sub-objetivo C11: ETAPA D F5e transmitir SEFAZ (CRITICO IRREVERSIVEL)

Substituir stub `executar_etapa_d` por implementacao real:

1. Filtra ajustes `fase_pipeline='F5d_INVOICE_GERADA'` + `invoice_id_odoo NOT NULL`
2. Reduz para invoices distintas (D8 do service legado — 1 invoice = 1 transmissao)
3. Idempotencia TRIPLA (D8):
   - Por ajuste: skip se sem invoice_id (anomalia)
   - Por invoice no batch: skip se ja transmitida nesta sessao
   - Por persistencia: skip se ja `fase_pipeline='F5e_SEFAZ_OK'`
4. Playwright SEFAZ serial (1 browser), 5-10min/NF:
   - Re-fetch via safe_session_get apos cada NF
   - commit_resilient antes E depois (G016)
   - `HARD_FAIL_CONFIG_ERRORS` (playwright_indisponivel + odoo_password_ausente + odoo_username_ausente) ABORTA batch
5. Marca fase F5e_SEFAZ_OK + chave_nfe + status (D7+D8 do service §7.2)
6. `MED C-1`/`MED C-2` (situacao_nf != 'autorizado' com sucesso=True; persistir cstat+xmotivo)
7. Reuso: `app.recebimento.services.playwright_nfe_transmissao.transmitir_nfe_via_playwright(invoice_id, odoo, logger)` (modulo externo — NAO MEXER)

### Sub-objetivo C12: ETAPA E RecebimentoLf X→FB

1. Filtra `ACOES_ENTRADA_FB = {PERDA_LF_FB, TRANSFERIR_CD_FB, DEV_LF_FB, DEV_CD_LF}` + `fase_pipeline='F5e_SEFAZ_OK'`
2. Agrupa por invoice_id (1 NF = 1 RecebimentoLf)
3. Verifica idempotencia via `RecebimentoLf.odoo_lf_invoice_id` (constraint UK)
4. Invoca `RecebimentoLfOdooService.processar_recebimento(rec_id)` (NAO MEXER — 4562 LOC, 37 etapas)
5. ⚠️ **G-RECLF-1**: bulk ETAPA E NAO viavel sincrono (50-100h em onda 100 invoices). **Decisao paralelismo v17 — AskUserQuestion obrigatoria**.
6. ⚠️ **G-RECLF-9**: Playwright SEFAZ no step_23 sobreposto com F5e — JA MITIGADO pelo etapa-barreira (decisao 10.3) ✓

### Sub-objetivo C13: ETAPA F entrada manual destino (Skill 5 atomo v15a)

1. Filtra `ACOES_ENTRADA_DESTINO_MANUAL = {INDUSTRIALIZACAO_FB_LF}` + `fase_pipeline='F5e_SEFAZ_OK'`
2. Agrupa por invoice_id (1 NF = 1 picking entrada manual)
3. **DELEGA para Skill 5 atomo v15a**: `picking_svc.criar_picking_entrada_destino_manual(...)` (G023 codificado intra-atomo, idempotencia via origin EXATO)
4. Marca fase F5f_ENTRADA_OK

### Tarefas concretas v17

1. **Setup + baseline** (5min):
   - `cd` worktree + venv + DATABASE_URL+ODOO_*
   - `git fetch + verificar main avancou; rebase se necessario`
   - `pytest tests/odoo/ -q --tb=no` baseline **483 verdes** esperado

2. **Ler MUITA documentacao** (regra inviolavel 0, ~30min):
   - `app/odoo/estoque/CLAUDE.md` (constituicao + tabela §6 atualizada v16)
   - `app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md` INTEIRO (especialmente §5 SSL/timeout + §7.2 D1-D9 + §7.4 G-RECLF-1..11 + §10.6 Skill 5 + §12 trilha v16)
   - `app/odoo/estoque/ROADMAP_SKILLS.md` HANDOFF v16
   - Memorias: `[[skill5_picking_pattern]]` (atomo `criar_picking_entrada_destino_manual` v15a) + `[[skill6_planejar_pre_etapa_pattern]]`
   - Source pattern reuso: `app/odoo/services/inventario_pipeline_service.py` L1116-1346 (f5e_transmitir_sefaz)
   - Service externo RecebimentoLfOdoo: `app/recebimento/services/recebimento_lf_odoo_service.py` (4562 LOC — NAO MEXER, so' chamar `processar_recebimento`)
   - Atomo Skill 5 ETAPA F: `app/odoo/estoque/scripts/picking.py:criar_picking_entrada_destino_manual`
   - Orchestrator v16 atual: `app/odoo/estoque/orchestrators/faturamento_pipeline.py`

3. **AskUserQuestion sobre escopo v17** (~5min):
   - Opcao A: C11 + C12 + C13 (sessao longa ~300min)
   - Opcao B: C11 sozinho (so' F5e SEFAZ, mais conservador — primeira NF real)
   - Opcao C: C12 + C13 sem C11 (deixa SEFAZ para v18 — preserva contexto SEFAZ irreversivel)
   - **Decisao paralelismo G-RECLF-1** (10.7 PENDENTE): sincrono (lento) vs paralelo (risco SEFAZ vs picking double-book)

4. **Implementacao** (~200min se opcao A):
   - Editar `app/odoo/estoque/orchestrators/faturamento_pipeline.py`:
     - Implementar `executar_etapa_d` real (substituir stub)
     - Implementar `executar_etapa_e` real (substituir stub — invoca RecLF service)
     - Implementar `executar_etapa_f` real (substituir stub — invoca atomo Skill 5)
   - >=20 pytest novos (Playwright mock + sub-etapas + idempotencia tripla)

5. **Smoke dry-run PROD** (~15min):
   - 1 ajuste F5d_INVOICE_GERADA real (validar polling F5d v16)
   - Dry-run ETAPA D sem `--confirmar-sefaz` retorna BLOQUEADO
   - Dry-run ETAPA E sem `--confirmar` retorna planejamento

6. **Code-review paralelo** (~25min):
   - Dispatch >=3 reviewers paralelos com focos distintos (Playwright SEFAZ + idempotencia + G-RECLF integration)

7. **Cross-refs + commit + PROMPT v18** (~25min):
   - CLAUDE.md estoque + ROADMAP HANDOFF + PLANEJAMENTO §0 + §7 (C11/C12/C13 ✅) + §12 trilha v17
   - Commit consolidado v17
   - Atualizar PROMPT_PROXIMA_SESSAO para v18 (canary REAL PROD 1 ajuste)

## ⚠️ PRE-MORTEM v17 (riscos novos)

| # | Risco | Mitigacao |
|---|-------|-----------|
| **R40** | F5e Playwright crash mid-loop deixa NF transmitida sem chave_nfe no DB local — re-run dobra transmissao | Idempotencia TRIPLA (D8) + commit_resilient antes de cada NF (D9) + re-fetch via safe_session_get |
| **R41** | HARD_FAIL_CONFIG_ERRORS aborta batch — operador precisa intervir manual | Codificar `--ignorar-config-errors=False` (default) + log claro |
| **R42** | Browser session Odoo expira mid-loop — login falha | Recovery via `--resume` v18 retoma do ultimo ajuste sem chave_nfe |
| **R43** | RecebimentoLf duplicado em ETAPA E — race entre threads se paralelizar | Decisao 10.7 v17: lock por invoice_id OU sincrono (lento) |
| **R44** | ETAPA F atomo Skill 5 v15a tem idempotencia origin EXATO — se origin diferir em re-run (ex YYYYMMDD muda), cria duplicata | Validar pattern de origin no teste (v15a pattern testado em smoke v15a 6 cods) |
| **R45** | Etapa F apenas valida `INDUSTRIALIZACAO_FB_LF` em PROD — outras acoes nao foram testadas | Documentar limitacao em SKILL.md + log WARNING se acao_decidida != INDUSTRIALIZACAO_FB_LF |
| **R46** | F5e em invoice ja autorizada externamente (admin Odoo manual) — Playwright pula mas DB local nao marca | Re-fetch state ANTES de transmitir + skip se ja autorizada |
| **R47** | RecLF service externo tem 37 etapas em 7 fases — falha tardia (FASE 6+7) NAO derruba FB | G-RECLF-2 ja' documentado: Skill 8 aceita `transfer_status='erro'` como sucesso parcial |

## LEITURAS OBRIGATÓRIAS (ordem)

1. `app/odoo/estoque/CLAUDE.md` (constituição) — §6 catálogo skills atualizado v16
2. `app/odoo/estoque/ROADMAP_SKILLS.md` — seção HANDOFF v16
3. `app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md` INTEIRO (regra inviolavel 0):
   - §0 cabeçalho (status v16 — 483 verdes, 9 fixes aplicados)
   - §5 SSL/timeout/recovery (G016 + D10/D14 ja em ETAPA C v16)
   - §7.2 D7-D9 (F5e Playwright + idempotencia tripla)
   - §7.4 G-RECLF-1 a G-RECLF-11 (decisao paralelismo + Playwright sobreposicao)
   - §10.6 Skill 5 atomos v15a (ETAPA F via atomo)
   - §12 trilha v16 (esta sessao terminou)
4. Memorias: `[[skill5_picking_pattern]]` (v15a + F1 v15c) + `[[skill6_planejar_pre_etapa_pattern]]`
5. Orchestrator v16 atual: `app/odoo/estoque/orchestrators/faturamento_pipeline.py`
6. Helpers v16 novo: `app/odoo/estoque/scripts/_invoice_helpers.py`
7. Service legado F5e: `app/odoo/services/inventario_pipeline_service.py:1116-1346`
8. RecebimentoLfOdoo: `app/recebimento/services/recebimento_lf_odoo_service.py` (header + docstrings — NAO MEXER no codigo)

## CHECKLIST DA SESSÃO v17

```
[ ] Setup (cd worktree + venv + DATABASE_URL+ODOO_*)
[ ] Verificar main avancou desde HEAD v16
[ ] Pytest baseline: 483 verdes esperado
[ ] Ler memorias [[skill5_picking_pattern]] + [[skill6_planejar_pre_etapa_pattern]]
[ ] Ler PLANEJAMENTO §5 + §7.2 D7-D9 + §7.4 G-RECLF-1..11 + §10.6 + §12 v16
[ ] AskUserQuestion sobre escopo v17 (C11+C12+C13 OU faseado)
[ ] AskUserQuestion decisao 10.7 paralelismo G-RECLF-1 (sincrono vs paralelo)
[ ] Editar faturamento_pipeline.py:
[ ]   - Implementar executar_etapa_d real (F5e SEFAZ Playwright + idempotencia tripla)
[ ]   - Implementar executar_etapa_e real (RecLF service invoke)
[ ]   - Implementar executar_etapa_f real (Skill 5 atomo invoke)
[ ] 20+ pytest novos verdes (Playwright mock + idempotencia + RecLF mock)
[ ] Smoke dry-run PROD: ETAPA D sem confirmar-sefaz bloqueia, ETAPA E planeja
[ ] >=3 code-reviewers paralelos (focos: Playwright/SEFAZ + idempotencia + RecLF integration)
[ ] Atualizar PLANEJAMENTO §0 + §7 (C11/C12/C13 ✅) + §12 trilha v17 + ROADMAP HANDOFF
[ ] Commit consolidado v17
[ ] Atualizar PROMPT_PROXIMA_SESSAO.md para v18 (canary REAL PROD 1 ajuste)
```

## CRONOGRAMA RESTANTE (apos v16)

| Sessão | Foco | Checkpoints | Risco |
|--------|------|-------------|-------|
| v16 (concluida) | ETAPA C F5d + ETAPA A real + G014 + 9 fixes 2 reviewers | C10 + C10.2 + C10.3 | Medio ✅ |
| **v17 (proxima)** | **C11 F5e SEFAZ + C12 ETAPA E RecLF + C13 ETAPA F atomo Skill 5** | C11, C12, C13 | **Alto (SEFAZ irreversivel + paralelismo G-RECLF-1)** |
| v18 | C14 recovery (--resume + stagnation detector) + C15 SKILL.md + C16 pytest baseline + C17 smokes | C14-C17 | Medio |
| v19 | C18 folhas fluxos + C19 cross-refs + C20 Canary REAL PROD (1 ajuste) | C18-C20 | Alto (1a NF real Skill 8) |
| v20+ | C21 bulk REAL PROD + C22 code-review + C23 commit final + arquivar 09_* SUPERADOS | C21-C23 | Alto (volume real) |

**Total restante**: 4-5 sessoes (v17 → v20+).

## REGRAS INVIOLÁVEIS NOVAS v16

75. **(v16 R1F1)** ETAPA C `executar_etapa_c` valida perfil ANTES do polling iniciar. `NotImplementedError` no meio do polling envenenaria session (pickings restantes ficavam F5c_LIBERADO permanentemente). Tentativa de regressao re-introduz armadilha.

76. **(v16 R2F1+F2+F3)** Helpers `_invoice_helpers.py` SEMPRE checam `l10n_br_situacao_nf in ('autorizado', 'excecao_autorizado', 'enviado')` ANTES de chamar `button_draft`. `button_draft` em NF SEFAZ-autorizada/enviada INVALIDA chave fiscal irreversivelmente. Tentativa de remover guard re-introduz catastrofe fiscal.

77. **(v16 R1F4)** `datetime.utcnow()` PROIBIDA — banida pelo hook `ban_datetime_now.py`. Usar `from app.utils.timezone import agora_utc_naive`. Pre-commit bloqueia.

78. **(v16 R1F2)** ETAPA B `_processar_chunk_etapa_b`: cods cujo G014 falhou devem ser EXCLUIDOS do picking (em vez de seguir com lote vencido original que faria `action_assign` falhar silenciosamente). Adicionar a `out_chunk['falhas']` explicitamente.

79. **(v16 R1F3)** ETAPA C: se `_commit_resilient` retorna False apos invoice resolve, `continue` para proximo pid (NAO executa sub-etapas com session sujo). Resume v18 reprocessa.

80. **(v16 CR-C10.2)** ETAPA A `_executar_etapa_a` filtra APENAS `ACOES_LOTE = {RENOMEAR_LOTE, TRANSFERIR_LOTE}` (escopo disjunto de ACOES_PICKING). Marcar ACOES_PICKING como TRANSF_OK era bug v15c (perigoso).

81. **(v16 CR-C10.3)** G014 idempotencia diaria via `nome_lote_destino='INV-{cod}-{YYYYMMDD}'`. Skill 2 v2 internamente faz search ANTES de criar (mesmo nome + mesmo produto = retorna existente). Re-rodar G014 mesmo dia NAO duplica.

82. **(v16 CR-C10.1)** Helpers F5d.5/.6/.7 em arquivo SEPARADO `_invoice_helpers.py` com perfil `'inventario-inter-company'` V1 (outros perfis raise NotImplementedError). Inline na classe orchestrator contaminaria logica generica (Rafael: "venda-cliente NAO tem fallback standard_price").

## NÃO-FAZER (red flags v17)

❌ Começar v17 SEM ler PLANEJAMENTO §12 trilha v16 (entender o que 9 fixes mudaram + ETAPA C/A/G014 real)
❌ Implementar F5e Playwright SEM idempotencia tripla (D8) — duplicacao SEFAZ catastrofica
❌ Modificar RecebimentoLfOdooService (regra v14a-fix — 4562 LOC NAO MEXER)
❌ Implementar ETAPA F inline no orchestrator (viola Fluxo>>Skills — DELEGAR para atomo `criar_picking_entrada_destino_manual` v15a)
❌ Esquecer `--confirmar-sefaz` na CLI da ETAPA D (segunda barreira de seguranca)
❌ Esquecer `db.engine.dispose()` ANTES e APOS ETAPA D (D10 ja codificado em v15c F7 — preservar)
❌ Esquecer SNAPSHOT meta antes do Playwright loop (D5) + `safe_session_get` apos cada NF (D9 + F6 v15c)
❌ Fazer paralelismo ETAPA E sem AskUserQuestion sobre decisao 10.7 (G-RECLF-1 — 50-100h sincrono em onda 100)
❌ Quebrar pytest baseline 483 verdes (esperado >=503 apos v17 com 20+ pytest novos)
❌ Esquecer `--canary-feito-em CICLO` obrigatorio antes de `--bulk` (regra v17 sera codificada)

## REFERÊNCIAS RÁPIDAS

- **Commit v16**: a ser criado nesta sessao
- **Commit v15c**: `ea455fe8`
- **Commit v15b**: `e38ec281`
- **Commit v15a**: `8ecfaaff`+`6c9fffff`
- **Commit CSV ajustes simples (interrupcao Rafael)**: `168499bd`
- **Baseline pytest**: 483 verdes em 15.51s
- **Smoke PROD ultimo**: cod 105000007 ETAPA A,B,C DRY_RUN_OK em 862ms
- **`_invoice_helpers.py` perfis**: V1 'inventario-inter-company' (outros raise)
- **G014 idempotencia**: lote novo `INV-{cod}-{YYYYMMDD}` (Skill 2 v2 search-before-create)
