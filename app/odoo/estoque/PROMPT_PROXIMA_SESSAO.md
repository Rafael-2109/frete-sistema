Continue o trabalho do orquestrador-Odoo. Worktree: /home/rafaelnascimento/projetos/frete_sistema_estoque_odoo (branch feat/estoque-odoo). main continua VIVO em paralelo. Verificar se avancou e considerar rebase ANTES de iniciar.

## Setup OBRIGATORIO (worktree sem .env)

    cd /home/rafaelnascimento/projetos/frete_sistema_estoque_odoo
    source /home/rafaelnascimento/projetos/frete_sistema/.venv/bin/activate
    set -a; . <(grep -E '^(DATABASE_URL|ODOO_)' /home/rafaelnascimento/projetos/frete_sistema/.env); set +a
    git fetch origin main && git log --oneline HEAD..origin/main

## ESTADO ATUAL — apos v17 (PIPELINE COMPLETO A-F LIVE)

Sessao v17 (2026-05-25) entregou em 1 sessao:

1. **C11 ETAPA D F5e SEFAZ Playwright** (~370 LOC novas):
   - `executar_etapa_d` substitui stub NOT_IMPLEMENTED_v15b
   - Playwright serial 1 browser via `transmitir_nfe_via_playwright`
   - Idempotencia TRIPLA (D8): por ajuste sem invoice + por invoice no batch + por persistencia F5e_OK
   - HARD_FAIL_CONFIG_ERRORS (D7): playwright_indisponivel + odoo_password_ausente + odoo_username_ausente + tentativas=0 ABORTA batch
   - SNAPSHOT meta (D5) antes do loop
   - commit_resilient (G016) antes do loop + pre-NF + pos-NF
   - safe_session_get (D9 + F6 v15c) apos Playwright
   - D18 2 niveis: dry-run nao bloqueia (planejamento); real-run exige `--confirmar-sefaz`
   - MED C-1: situacao_nf != autorizado mas sucesso=True em erro_msg
   - MED C-2: cstat+xmotivo de ultimo_estado persistido em falha

2. **C12 ETAPA E RecebimentoLf X->FB** (~270 LOC novas):
   - `executar_etapa_e` substitui stub NOT_IMPLEMENTED_v15b
   - SEQUENCIAL (decisao 10.7 v17 — Rafael) invocando service externo
   - Idempotencia G-RECLF-3 via UK `RecebimentoLf.odoo_lf_invoice_id` (migration v17 PROD aplicada)
   - G-RECLF-2: aceita transfer_status='erro' como sucesso parcial (FASE 6+7 pode falhar)
   - D17: ACAO_PARA_CFOP_ENTRADA 5xxx->1xxx (FB so' tem fiscal_position para entrada)
   - status='processando' RETOMA (HIGH-3 fix anti-RecLf orfao)
   - svc instanciado dentro do loop (HIGH-4 anti-estado-vazando)
   - produto_tracking via batch fetch (HIGH-5 anti-D-OPS-5)

3. **C13 ETAPA F atomo Skill 5** (~250 LOC novas):
   - `executar_etapa_f` substitui stub NOT_IMPLEMENTED_v15b
   - DELEGA atomo Skill 5 v15a `criar_picking_entrada_destino_manual` (principio Fluxo>>Skills)
   - V1 STRICT: APENAS INDUSTRIALIZACAO_FB_LF (LF=19 validado PROD pickings 317306, 317316)
   - Origin idempotente `INV-{ciclo}-ENTRADA-{label}-NF{invoice_id}`
   - Lote MIGRAÇÃO/vazio -> INV-{cod}-{YYYYMMDD} (consistente G014 v16)
   - Pre-check invoice.state='posted' + situacao_nf='autorizado' (CRITICAL-4 anti-saldo-fantasma)
   - HOJE dentro do loop (HIGH-6 anti-lote-errado cross-midnight)
   - Auditoria SKIP_AGG_VAZIO (HIGH-7 anti-falha-sistematica silenciosa)

4. **Migration v17** aplicada em PROD:
   - `scripts/migrations/2026_05_25_v17_uk_recebimento_lf_invoice_id.py` (Python verificacao + ALTER)
   - `scripts/migrations/2026_05_25_v17_uk_recebimento_lf_invoice_id.sql` (idempotente IF NOT EXISTS via DO $$ EXCEPTION)
   - UniqueConstraint `uq_recebimento_lf_invoice_id` em `recebimento_lf.odoo_lf_invoice_id`
   - CRITICAL-3 Reviewer 2: anti-RecLf duplicado se service falha mid-process e re-run cria 2o
   - Pre-flight: 0 duplicatas detectadas; UK criada com sucesso

5. **3 code-reviewers paralelos**: 11 findings (4 CRITICAL + 7 HIGH) — TODOS aplicados:
   - **CRITICAL-1** (R1 95): commit POS-Playwright falha NAO conta sucesso. Fix: FALHA_COMMIT_POS_SEFAZ_OK em invoices_falha
   - **CRITICAL-2** (R1 90): guard permissivo D8.3 — 1+ ajuste em F5e_OK = invoice ja transmitida
   - **CRITICAL-3** (R2 95): UK migration v17 PROD aplicada
   - **CRITICAL-4** (R3 92): pre-check situacao_nf='autorizado' em ETAPA F
   - **HIGH-1** (R1 85): WARN estado inconsistente status=EXECUTADO+fase!=F5e_OK
   - **HIGH-2** (R1 82): docstring removeu Raises RuntimeError (return early, nao lanca)
   - **HIGH-3** (R2 88): status='processando' RETOMA via service
   - **HIGH-4** (R2 82): svc instanciado dentro do loop
   - **HIGH-5** (R2 80): produto_tracking via fetch (anti-D-OPS-5)
   - **HIGH-6** (R3 80): HOJE dentro do loop
   - **HIGH-7** (R3 82): auditoria SKIP_AGG_VAZIO

6. **502 pytest verdes** (483 + 19 v17 = 16 base + 3 pos-fixes CRITICAL-1/CRITICAL-4/HIGH-3):
   - 5 ETAPA D (D18 bloqueado/dry-run/real Playwright mock/HARD_FAIL/idempotencia/cstat)
   - 4 ETAPA E (dry-run/sucesso RecLf mock/idempotencia/parcial transfer_erro)
   - 7 ETAPA F (dry-run/sucesso atomo/V1 STRICT/IDEMPOTENT_DONE/IDEMPOTENT_OTHER/posted)
   - 3 pos-fixes (CRITICAL-1 commit pos falha/CRITICAL-4 situacao_nf/HIGH-3 processando retoma)

7. Smoke dry-run PROD em INVENTARIO_2026_05:
   - ETAPA D dry-run cod 104000003: SKIP_NENHUM_AJUSTE (esperado, cod em F5e nao F5d) 746ms
   - ETAPA E dry-run cod 104000003: 1 invoice 629364 PERDA_LF_FB detectada 742ms
   - ETAPA F dry-run cod 210030007: SKIP_NENHUM_AJUSTE (cod ja em F5f_OK) 743ms
   - Pipeline completo A-F cod 105000007: DRY_RUN_OK em 746ms

Baseline pytest: 502 verdes em 14.51s (483 baseline v16 + 19 v17).

Documento vivo MACRO (regra inviolavel 0): app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md (~1700 LOC, 14 secoes + trilha v17 detalhada §12)

Memorias-chave (LER PRIMEIRO antes de v18):
- [[skill5_picking_pattern]] — pattern Skill 5 v3 + v15a (3 atomos) + v15c F1 idempotencia origin
- [[skill6_planejar_pre_etapa_pattern]] — pattern orchestrator C3 v9 (template reusado v15b/c/v16/v17)

Checkpoints concluidos: **13 de 24**
C1 pre-mortem | C2 minera service | C3 minera script | C4 escopo confirmado
C5 sub-skill auditando-cadastro-fiscal-odoo V1 (v14b)
C6.5 Skill 5 estendida com 3 atomos inter-company (v15a)
C6 orchestrator base esqueleto (v15b)
C7 ETAPA B F5a criar pickings (v15b/c)
C8 ETAPA B F5b validar pickings (v15b)
C9 ETAPA B F5c liberar faturamento (v15b)
C10 ETAPA C F5d aguardar invoices + sub-etapas .5/.6/.7 (v16)
**C11 ETAPA D F5e SEFAZ Playwright (v17)**
**C12 ETAPA E RecebimentoLf X->FB (v17)**
**C13 ETAPA F atomo Skill 5 (v17)**

Arquivos NOVOS criados em v17:
- scripts/migrations/2026_05_25_v17_uk_recebimento_lf_invoice_id.py (~75 LOC)
- scripts/migrations/2026_05_25_v17_uk_recebimento_lf_invoice_id.sql (~25 LOC idempotente)

Arquivos modificados em v17:
- app/odoo/estoque/orchestrators/faturamento_pipeline.py (ETAPAS D+E+F real + 11 fixes; ~890 LOC novas total)
- tests/odoo/services/test_faturamento_pipeline_orchestrator.py (19 testes novos v17)
- app/recebimento/models.py (UK em odoo_lf_invoice_id)
- app/odoo/estoque/CLAUDE.md (status v17)
- app/odoo/estoque/ROADMAP_SKILLS.md (handoff v17)
- app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md (§0 + §7 C11/C12/C13 OK + §12 trilha v17)

## PRIORIDADE v18 — Recovery + SKILL.md + smokes finais

Objetivo (~200-250min): preparar Skill 8 para canary REAL PROD em v19. Pipeline A-F ja' funciona; falta o operational layer.

### Sub-objetivo C14: Recovery `--resume` modo CLI

Implementar entry-point `executar_pipeline_resume(ciclo, max_iter, timeout_iter, detector_stagnation, ...)`:

1. Loop ate `max_iter` (default 18 — script `fat_lf_resume.sh`):
   - Conta restantes_por_fase (F5c_LIBERADO + F5d_INVOICE_GERADA + F5e_SEFAZ_OK_sem_F5f)
   - Se 0 -> motivo_parada='TUDO_OK', break
   - Detector stagnation: se rem == prev_rem -> rodar etapa anterior (C separado) + tentar D
   - Idempotencia ja' garantida em ETAPAS D/E/F v17
2. Args CLI: `--ciclo NOME --max-iter N --timeout-por-iter S --detector-stagnation`
3. Output JSON: `iteracoes_executadas`, `restantes_por_fase` (dict), `motivo_parada` (TUDO_OK / STAGNATION / MAX_ITER), `tempo_total_ms`
4. >=3 pytest novos (mock onda + idempotencia + stagnation)

### Sub-objetivo C15: SKILL.md `faturando-odoo`

Criar `.claude/skills/faturando-odoo/SKILL.md` com:

1. Frontmatter description rica (triga: "fature a onda X", "transmita SEFAZ", "resume da onda Y", "rode pipeline faturamento")
2. Contrato obrigatorio (objeto, input, output, pre/pos-condicoes, gotchas-invariante, modos)
3. 5+ receitas (canary 1 ajuste / bulk onda completa / resume / etapa especifica / pre-flight separado)
4. Trade-offs (Playwright SEFAZ irreversivel + Decisao 10.7 sequencial + V1 STRICT ETAPA F)
5. Cross-refs (subagente gestor-estoque-odoo, ROUTING_SKILLS, tool_skill_mapper)

### Sub-objetivo C16: Pytest baseline >=502 mantido

Validar suite completa nao regrediu. Adicionar smoke tests fim-a-fim mocando todas as dependencias externas.

### Sub-objetivo C17: Smokes documentados em /tmp/log_skill8_*.json

5+ smokes em ondas reais com saida JSON salva para analise pos-execucao:
- Onda LF pequena (3-5 cods PERDA_LF_FB) dry-run completo A-F
- Onda mista (PERDA + INDUSTR + DEV) dry-run
- Resume sobre onda parcialmente concluida
- HARD_FAIL_CONFIG mock para validar abort
- Pipeline com ETAPA F V1 STRICT (DEV_FB_LF skip)

### Tarefas concretas v18

1. Setup + baseline (5min):
   - cd worktree + venv + DATABASE_URL+ODOO_*
   - git fetch + verificar main avancou; rebase se necessario
   - pytest tests/odoo/ -q --tb=no baseline 502 verdes esperado

2. Ler MUITA documentacao (regra inviolavel 0, ~20min):
   - app/odoo/estoque/CLAUDE.md (constituicao + tabela §6 atualizada v17)
   - app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md (especialmente §0 + §5.2 recovery + §7 C14-C20 + §12 trilha v17)
   - app/odoo/estoque/ROADMAP_SKILLS.md HANDOFF v17
   - Memorias: [[skill5_picking_pattern]] + [[skill6_planejar_pre_etapa_pattern]]
   - Source pattern recovery: scripts/inventario_2026_05/fat_lf_resume.sh + fat_lf_resume_entrada.sh
   - Orchestrator v17 atual: app/odoo/estoque/orchestrators/faturamento_pipeline.py

3. AskUserQuestion sobre escopo v18 (~5min):
   - Opcao A: C14+C15+C16+C17 (sessao completa ~250min)
   - Opcao B: C14+C15 (recovery + SKILL.md — fundacao critica)
   - Opcao C: C15+C17 (SKILL.md + smokes — operacional sem recovery)

4. Implementacao (~120min se opcao A):
   - C14 recovery em faturamento_pipeline.py (~150 LOC)
   - C15 SKILL.md em .claude/skills/faturando-odoo/SKILL.md (~200 LOC)
   - C16 pytest novos verdes (3-5)
   - C17 smokes documentados

5. Smoke dry-run PROD (~15min):
   - Recovery em ciclo limpo (esperado TUDO_OK em 1 iter)
   - SKILL.md description triga corretamente via tool_skill_mapper

6. Code-review paralelo (~25min):
   - >=2 reviewers paralelos (recovery loop + SKILL.md compliance)

7. Cross-refs + commit + PROMPT v19 (~25min):
   - CLAUDE.md estoque + ROADMAP HANDOFF + PLANEJAMENTO §0 + §7 (C14/C15/C16/C17 OK) + §12 trilha v18
   - Commit consolidado v18
   - Atualizar PROMPT_PROXIMA_SESSAO para v19 (canary REAL PROD 1 ajuste)

## PRE-MORTEM v18 (riscos)

R48: Recovery loop infinito se detector stagnation nao for robusto. Mitigacao: max_iter hard + timeout_iter por iteracao + log estruturado.

R49: SKILL.md description nao triga corretamente. Mitigacao: testar via tool_skill_mapper apos cada edicao + 3+ frases de triga.

R50: Smokes em PROD podem inadvertidamente acionar real-run. Mitigacao: validar dry-run flag em CADA smoke + double-check `--confirmar` ausente.

## LEITURAS OBRIGATORIAS (ordem)

1. app/odoo/estoque/CLAUDE.md (constituicao) — §6 catalogo skills atualizado v17
2. app/odoo/estoque/ROADMAP_SKILLS.md — secao HANDOFF v17
3. app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md (regra inviolavel 0):
   - §0 cabecalho (status v17 — 502 verdes, 11 fixes aplicados)
   - §5.2 Pattern recovery (scripts fat_lf_resume*)
   - §7 C14-C17 (recovery + SKILL.md + pytest baseline + smokes)
   - §12 trilha v17 (esta sessao terminou)
4. Memorias: [[skill5_picking_pattern]] + [[skill6_planejar_pre_etapa_pattern]]
5. Orchestrator v17 atual: app/odoo/estoque/orchestrators/faturamento_pipeline.py
6. Scripts recovery: scripts/inventario_2026_05/fat_lf_resume.sh + fat_lf_resume_entrada.sh
7. SKILL.md template: .claude/skills/operando-picking-odoo/SKILL.md (referencia de qualidade)

## CHECKLIST DA SESSAO v18

[ ] Setup (cd worktree + venv + DATABASE_URL+ODOO_*)
[ ] Verificar main avancou desde HEAD v17
[ ] Pytest baseline: 502 verdes esperado
[ ] Ler memorias [[skill5_picking_pattern]] + [[skill6_planejar_pre_etapa_pattern]]
[ ] Ler PLANEJAMENTO §0 + §5.2 + §7 C14-C17 + §12 v17
[ ] AskUserQuestion sobre escopo v18 (C14+C15+C16+C17 OU faseado)
[ ] Editar faturamento_pipeline.py: implementar executar_pipeline_resume + CLI --resume + --max-iter + --timeout-iter + --detector-stagnation
[ ] Criar .claude/skills/faturando-odoo/SKILL.md (contrato + 5 receitas)
[ ] 3-5 pytest novos verdes (recovery + idempotencia + stagnation)
[ ] Smokes documentados em /tmp/log_skill8_v18_*.json (5+)
[ ] >=2 code-reviewers paralelos (recovery loop + SKILL.md)
[ ] Atualizar PLANEJAMENTO §0 + §7 (C14/C15/C16/C17 OK) + §12 trilha v18 + ROADMAP HANDOFF
[ ] Commit consolidado v18
[ ] Atualizar PROMPT_PROXIMA_SESSAO.md para v19 (canary REAL PROD 1 ajuste)

## CRONOGRAMA RESTANTE (apos v17)

v17 (concluida): ETAPA D F5e SEFAZ + ETAPA E RecLF + ETAPA F atomo Skill 5 | C11+C12+C13 + 11 fixes | Risco Alto OK
v18 (proxima): C14 recovery + C15 SKILL.md + C16 baseline + C17 smokes | Risco Medio
v19: C18 folhas fluxos + C19 cross-refs + C20 Canary REAL PROD (1 ajuste) | Risco Alto (1a NF real Skill 8)
v20+: C21 bulk REAL PROD + C22 code-review + C23 commit final + arquivar 09_* SUPERADOS | Risco Alto (volume real)

Total restante: 3 sessoes (v18 → v20+).

## REGRAS INVIOLAVEIS NOVAS v17

83. (v17 CRITICAL-1) ETAPA D commit POS-Playwright FALHA NUNCA conta como sucesso. Marca `FALHA_COMMIT_POS_SEFAZ_OK` em `invoices_falha` com chave SEFAZ ja autorizada. Operador DEVE checar DB e marcar fase_pipeline=F5e_SEFAZ_OK manualmente. Tentativa de regressao re-introduz dupla-SEFAZ em re-run.

84. (v17 CRITICAL-2) ETAPA D guard D8.3 permissivo: 1+ ajuste em F5e_OK no invoice = invoice JA transmitida (chave SEFAZ unica). NAO retransmite. Tentativa de regressao re-introduz dupla-SEFAZ em crash mid-loop.

85. (v17 CRITICAL-3) `recebimento_lf.odoo_lf_invoice_id` tem UniqueConstraint `uq_recebimento_lf_invoice_id`. Migration v17 aplicada PROD. Tentativa de remover UK re-introduz RecLf duplicado em re-run de service falho.

86. (v17 CRITICAL-4) ETAPA F pre-check `account.move.l10n_br_situacao_nf='autorizado'` (alem de state='posted'). NF cancelada externamente NAO gera picking de entrada. Tentativa de regressao gera saldo fantasma.

87. (v17 HIGH-3) ETAPA E aceita RecLf em `status='processando'` como RETOMAR (service suporta resume via etapa_atual>0). NAO cria RecLf duplicado. Junto com CRITICAL-3 (UK), idempotencia em crash recovery e' garantida.

88. (v17 HIGH-4) `RecebimentoLfOdooService` SEMPRE instanciado DENTRO do loop por invoice (alinha script base — anti-vazamento de estado interno self._recebimento_id entre invoices).

89. (v17 HIGH-5) `RecebimentoLfLote.produto_tracking` lido do Odoo via batch fetch `product.product.tracking` (anti-D-OPS-5 quebra `_step_10_preencher_lotes` do RecLfSvc para produtos `tracking='none'`). Fallback `'lot'`.

90. (v17 HIGH-6) ETAPA F `HOJE = agora_utc_naive().strftime('%Y%m%d')` CALCULADO DENTRO do loop por invoice. Cross-midnight em runs longas geraria lote `INV-{cod}-{D+1}` para ajustes ainda do dia anterior (idempotencia quebrada).

91. (v17 HIGH-7) ETAPA F `agg vazio` registra auditoria por ajuste (`SKIP_AGG_VAZIO`). NAO silenciar falhas sistematicas de `_resolver_pids_em_batch`.

92. (v17 DECISAO 10.7) ETAPA E executa SEQUENCIAL invoice-a-invoice. RecebimentoLfOdoo NAO eh thread-safe (Redis state); G-RECLF-9 (Playwright SEFAZ step_23) ja mitigado pela etapa-barreira; G-RECLF-1 (50-100h em onda 100) aceito por idempotencia perfeita.

93. (v17 V1 STRICT ETAPA F) APENAS `INDUSTRIALIZACAO_FB_LF` (LF=19 validado PROD pickings 317306, 317316). DEV_FB_LF/TRANSFERIR_FB_CD commented out em `ACOES_ENTRADA_DESTINO_MANUAL`. Expansao SO' quando demanda real + IDs descobertos via audit Odoo.

## NAO-FAZER (red flags v18)

X Comecar v18 SEM ler PLANEJAMENTO §12 trilha v17 (entender o que 11 fixes mudaram + ETAPAS D/E/F real)
X Implementar recovery sem max_iter hard (risco loop infinito)
X Modificar RecebimentoLfOdooService (regra v14a-fix — 4562 LOC NAO MEXER)
X Modificar script 09 (regra v14a-ops — usar apenas scripts existentes)
X Esquecer testar SKILL.md description via tool_skill_mapper (triga e' critico)
X Quebrar pytest baseline 502 verdes (esperado >=507 apos v18 com 5+ pytest novos)
X Esquecer --canary-feito-em CICLO obrigatorio antes de --bulk (regra v17 codificada)

## REFERENCIAS RAPIDAS

- Commit v17: a ser criado (faturamento_pipeline.py + tests + migration + docs)
- Commit v16: 63e7c1a6 (feature consolidado + 8 arquivos + 2644/-336)
- Commit v15c: ea455fe8
- Commit v15b: e38ec281
- Commit v15a: 8ecfaaff + 6c9fffff
- Baseline pytest: 502 verdes em 14.51s
- Smoke PROD ultimo: cod 105000007 pipeline A-F dry-run em 746ms
- UK constraint: `recebimento_lf.uq_recebimento_lf_invoice_id` aplicada PROD 2026-05-25
