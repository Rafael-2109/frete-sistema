# PROMPT_PROXIMA_SESSAO — orquestrador-Odoo (worktree feat/estoque-odoo) v16

> Copie tudo entre `---BEGIN---` e `---END---` e cole como prompt inicial da próxima sessão.

---BEGIN---

Continue o trabalho do orquestrador-Odoo. Worktree: `/home/rafaelnascimento/projetos/frete_sistema_estoque_odoo` (branch `feat/estoque-odoo`). `main` continua VIVO em paralelo (Rafael commita lá — SPED ECD em progresso). Verificar se avançou e considerar rebase ANTES de iniciar.

## Setup OBRIGATÓRIO (worktree sem .env)

```bash
cd /home/rafaelnascimento/projetos/frete_sistema_estoque_odoo
source /home/rafaelnascimento/projetos/frete_sistema/.venv/bin/activate
set -a; . <(grep -E '^(DATABASE_URL|ODOO_)' /home/rafaelnascimento/projetos/frete_sistema/.env); set +a
git fetch origin main && git log --oneline HEAD..origin/main  # ver se main avancou
```

## 📋 ESTADO ATUAL — apos v15b (ORCHESTRATOR BASE SKILL 8 LIVE)

**Sessao v15b (2026-05-25)** entregou em 1 sessao:

1. **C6 + C7 + C8 + F5c ✅ COMPLETOS — Orchestrator base Skill 8 LIVE**:
   - Criado `app/odoo/estoque/orchestrators/faturamento_pipeline.py` (~1300 LOC)
   - Classe `FaturamentoPipelineExecutor` composioes Skill 5 atomos v15a em pipeline A->B->C->D->E->F
   - ETAPA A: stub `NOOP` (delegado Skill 2 — v16 expandir)
   - ETAPA B: F5a + F5b + F5c invocando atomos Skill 5 v15a (criar+validar+liberar) + G022 sleep 5s + G-ETB-COMPENSATORIO preservando acao_decidida origem
   - ETAPAS C/D/E/F: stubs `NOT_IMPLEMENTED_v15b` com roadmap v16/v17
   - PRE-FLIGHT via sub-skill C5 (subprocess `auditar_cadastro_inventario.py`)
   - CLI: `python -m app.odoo.estoque.orchestrators.faturamento_pipeline --modo bulk|pre-flight --etapas A,B,C,D,E,F --ciclo X ...`
   - +30 pytest novos verdes (baseline 435 → **465 verdes em 14.85s**)
   - Smoke dry-run PROD validado: cod 210639522 INDUSTRIALIZACAO_FB_LF 6000un picking_type=53 partner=35

2. **Code-review paralelo (feature-dev:code-reviewer) — 9 findings**, 7 aplicados:
   - CR-C1 (CRITICAL 92): status filter default `['PROPOSTO','APROVADO']` em `_carregar_ajustes` — exclui CANCELADO/EXECUTADO/FALHA
   - CR-C2 (CRITICAL 85): `_agrupar_por_direcao` por `acao_decidida` (NAO `(co, tipo_op)`) — preserva partner_id correto
   - CR-H1 (HIGH 83): tracker `chunk_executado` global cobre sleep G022 nas transicoes entre grupos
   - CR-H2 (HIGH 80): compensatorio preserva `acao_decidida` do origem (nao hardcode `INDUSTRIALIZACAO_FB_LF`)
   - CR-H4 (HIGH 82): `ETAPAS_ABORT_SE_ANTERIOR_FALHOU=(D,)` bloqueia ETAPA D se B falhou
   - CR-M1 (MEDIUM 85): intersecao acoes vazia retorna `[]` em vez de remover filtro
   - CR-M3 (MEDIUM 78): `BLOQUEADO_*` conta como falha em status agregado
   - 2 TODOs registrados: CR-H3 (ETAPA A real-run untested — v16), CR-M2 (teste hardcoded Odoo IDs — leve)

3. **Cross-refs aplicados (5)**:
   - `app/odoo/estoque/CLAUDE.md` (status global + tabela §6 Skill 8)
   - `app/odoo/estoque/ROADMAP_SKILLS.md` (HANDOFF v15b detalhado)
   - `app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md` (§0 status + §7 C6/C7/C8/C9 ✅ + §12 trilha v15b)
   - `app/odoo/estoque/PROMPT_PROXIMA_SESSAO.md` (este — atualizado para v16)
   - `PROMPT_PROXIMA_SESSAO_v15b_EXECUTED_2026_05_25.md` (arquivo do v15b)

**Baseline pytest**: **465 verdes em 14.85s** (435 baseline v15a + 30 v15b).

**Documento vivo MACRO (regra inviolavel 0 — LER ANTES DE TOCAR Skill 8)**:
`app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md` (~1500+ LOC, 14 seções + trilha v15b detalhada)

**Memorias-chave** (LER PRIMEIRO antes de v16):
- `[[skill5_picking_pattern]]` — pattern Skill 5 v3 + v15a (3 atomos inter-company)
- `[[skill6_planejar_pre_etapa_pattern]]` — pattern orchestrator C3 v9 (template reusado pelo v15b)
- `[[sub-skill-c5-pattern]]` — pattern sub-skill C5 V1 'inventario' (v14b — invocada via subprocess)
- `[[teste-real-6-cods-v14a-ops]]` — origem operacional D-OPS-1..5

**Checkpoints concluídos: 9 de 24**
✅ C1 pre-mortem | ✅ C2 minera service | ✅ C3 minera script | ✅ C4 escopo confirmado
✅ C5 sub-skill auditando-cadastro-fiscal-odoo V1 (v14b)
✅ C6.5 Skill 5 estendida com 3 atomos inter-company (v15a)
✅ C6 orchestrator base esqueleto (v15b)
✅ C7 ETAPA B F5a criar pickings (v15b)
✅ C8 ETAPA B F5b validar pickings (v15b)
✅ C9 ETAPA B F5c liberar faturamento (v15b — escopo expandido)

## 🎯 PRIORIDADE v16 — ETAPA C F5d aguardar invoices + sub-etapas .5/.6/.7

**Objetivo** (~150-200min): implementar ETAPA C (`executar_etapa_c`) no orchestrator, fazendo polling de invoices criadas pelo robo CIEL IT + sub-etapas defensivas (payment_provider, price zero, fiscal setup DEV_*).

### Sub-objetivo C10: ETAPA C F5d aguardar invoices CIEL IT

- Implementar `_executar_etapa_c` (~200 LOC) que faz:
  1. Carrega ajustes com `fase_pipeline='F5c_LIBERADO'` (CR-C1 status filter ja aplicado)
  2. Agrupa por `picking_id_odoo` (1 picking pode gerar 1 invoice via robo CIEL IT)
  3. **`db.engine.dispose()` PROFILATICO ANTES** (D10 — G016 SSL)
  4. **Polling longo** (default 1800s, intervalo 40s) — busca `account.move` por `invoice_origin=picking.name`
  5. **SNAPSHOT meta antes do polling** (D5 — anti-DetachedInstanceError)
  6. Para cada invoice criada: `db.session.get(AjusteEstoqueInventario, meta['id'])` re-fetch (D9)
  7. Sub-etapas defensivas (D6 — falha individual NAO derruba):
     - **F5d.5** `_garantir_payment_provider` (G029): set `payment_provider_id=38` (SEM PAGAMENTO) se vazio
     - **F5d.6** `_corrigir_price_zero_em_invoice` (G007): fallback `standard_price` ou 0.01 em `account.move.line` com price=0
     - **F5d.7** `_garantir_fiscal_setup` (G034 DEV_*): forca `fiscal_position` + `l10n_br_tipo_pedido` correto para DEV_LF_FB/DEV_LF_CD/DEV_CD_LF via reset_to_draft + write + post
  8. Atualiza `fase_pipeline='F5d_INVOICE_GERADA'` + `invoice_id_odoo` em cada ajuste
  9. **`db.engine.dispose()` PROFILATICO APOS** (D10)
  10. Auditoria via `_registrar_auditoria`

### Sub-objetivo C10.1: Helpers F5d.5/.6/.7

Capinar do `inventario_pipeline_service.py` (NAO copiar — extrair pattern):
- `_garantir_payment_provider` (L204-291 service legado) — G029 idempotente; fallback se write em posted falhar
- `_garantir_fiscal_setup` (L293-399) — G034 reset_to_draft+post fallback; guard pre-state autorizado
- `_corrigir_price_zero_em_invoice` (L401-506) — G007 fallback standard_price ou 0.01

### Sub-objetivo C10.2: Helper compartilhado `_commit_helpers.py`

Consolidar 3 padroes (D14 + G-RECLF-4 + G-RECLF-5) em `app/odoo/estoque/scripts/_commit_helpers.py`:
- `_commit_resilient` (script L158-210 — versao MAIS FORTE, ja codificada inline no orchestrator v15b)
- `_safe_update` / `_checkpoint` (RecebimentoLfOdoo)
- `commit_with_retry` (app.utils.database_retry)

Importar no orchestrator + service legado (preservar interfaces publicas).

### Sub-objetivo C10.3: ETAPA A — integrar Skill 2 real (CR-H3 v15b TODO)

- v15b deixou ETAPA A como NOOP stub
- v16: analisar quants no Odoo (READ) -> se `lote_origem` != quant_atual -> invocar `StockInternalTransferService.transferir_quantidade_para_lote_v2` (Skill 2 v2 com guard delta_esperado)
- Pytest cobrir real-run path

### Tarefas concretas v16

1. **Setup + baseline** (5min):
   - `cd` worktree + venv + DATABASE_URL+ODOO_*
   - `git fetch + verificar main avancou; rebase se necessario`
   - `pytest tests/odoo/ -q --tb=no` baseline 465 verdes esperado

2. **Ler MUITA documentacao** (regra inviolavel 0, ~30min):
   - `app/odoo/estoque/CLAUDE.md` (constituicao + tabela §6 atualizada v15b)
   - `app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md` INTEIRO (especialmente §5 SSL/timeout + §7.2 D1-D9 do service + §10.3 paralelismo + §12 trilha v15b)
   - `app/odoo/estoque/ROADMAP_SKILLS.md` HANDOFF v15b
   - Memorias: `[[skill5_picking_pattern]]` + `[[skill6_planejar_pre_etapa_pattern]]` + `[[sub-skill-c5-pattern]]`
   - Source pattern reuso: `app/odoo/services/inventario_pipeline_service.py` L945-1102 (f5d_aguardar_invoices) + L204-506 (helpers F5d.5/.6/.7)
   - Orchestrator v15b atual: `app/odoo/estoque/orchestrators/faturamento_pipeline.py` (~1300 LOC)

3. **Implementacao** (~120min):
   - AskUserQuestion sobre escopo v16: C10 (F5d completo) + C10.2 (commit_helpers) juntos OU C10 sozinho + C10.1+C10.2 em v16-2?
   - Editar `app/odoo/estoque/orchestrators/faturamento_pipeline.py`:
     - Adicionar helpers `_garantir_payment_provider`, `_garantir_fiscal_setup`, `_corrigir_price_zero_em_invoice` (em modulo helpers ou inline na classe?)
     - Implementar `_executar_etapa_c` real (substituir stub)
     - Adicionar `db.engine.dispose()` ANTES e APOS (D10)
     - Expandir `_executar_etapa_a` para integrar Skill 2 real (CR-H3 v15b TODO)
   - Criar `app/odoo/estoque/scripts/_commit_helpers.py` (consolidar 3 padroes)
   - >=15 pytest novos (F5d polling + sub-etapas + commit_helpers)

4. **Smoke dry-run PROD** (~10min):
   - Identificar 1 ajuste com `fase_pipeline='F5c_LIBERADO'` em PROD (12 esperados conforme contagem v15b)
   - Rodar `faturamento_pipeline.py --etapas C --ciclo INVENTARIO_2026_05 --dry-run --pular-pre-flight`
   - Validar: polling planejado + sub-etapas planejadas

5. **Code-review paralelo** (~15min):
   - Dispatch `feature-dev:code-reviewer` com diff completo (F5d + helpers + commit_helpers + tests)

6. **Cross-refs + commit + PROMPT v17** (~20min):
   - CLAUDE.md estoque + ROADMAP HANDOFF + PLANEJAMENTO §0 + §7 (C10 ✅) + §12 trilha v16
   - Commit consolidado v16
   - Atualizar PROMPT_PROXIMA_SESSAO para v17 (F5e SEFAZ Playwright + ETAPA E RecLF + ETAPA F G023)

## ⚠️ PRE-MORTEM v16 (riscos novos)

| #    | Risco | Mitigacao |
|------|-------|-----------|
| R26  | Polling 1800s mockado em pytest pode demorar (timeout) | Reduzir intervalo no test via `--poll-interval=1 --timeout=10` ou mockar `time.sleep` |
| R27  | `_corrigir_price_zero_em_invoice` em invoice multi-line pode quebrar se UMA linha falhar | Implementar try/except POR linha; agregar falhas; retornar count corrigidas (D6) |
| R28  | `_garantir_fiscal_setup` em invoice ja `state='posted'` exige reset_to_draft | Codificar pattern do service legado L293-399 (guard pre-state autorizado bloqueia) |
| R29  | `engine.dispose()` profilatico pode quebrar transacoes pendentes em outras threads | Documentar pre-cond no docstring (mesmo aviso da CR-EDGE-3 v9 Skill 6) |
| R30  | ETAPA A real-run (Skill 2) pode falhar silenciosamente se quant fonte ja consumido | Codificar guard via re-fetch quant antes de invocar Skill 2 |

## LEITURAS OBRIGATÓRIAS (ordem)

1. `app/odoo/estoque/CLAUDE.md` (constituição) — §6 catálogo skills + §7 granularidade + §10 fronteiras
2. `app/odoo/estoque/ROADMAP_SKILLS.md` — seção HANDOFF v15b
3. `app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md` INTEIRO (regra inviolavel 0):
   - §0 cabeçalho (status v15b)
   - §5 SSL/timeout/recovery (G016 + D10/D14)
   - §7.2 D1-D9 mineracao service (F5d L945-1102 + helpers .5/.6/.7)
   - §10.3 paralelismo (etapa-barreira + D10/D11)
   - §12 trilha v15b (esta sessao terminou)
4. Memorias: `[[skill5_picking_pattern]]` (v15a) + `[[skill6_planejar_pre_etapa_pattern]]` (orchestrator C3 v9)
5. Orchestrator v15b atual: `app/odoo/estoque/orchestrators/faturamento_pipeline.py`

Para implementacao:
- `app/odoo/services/inventario_pipeline_service.py` L165-506 (helpers + F5d) — EXTRAIR padroes, NAO copiar
- `app/recebimento/services/recebimento_lf_odoo_service.py` (READ-only — apenas referencia G-RECLF-4 commit_resilient pattern)

## CHECKLIST DA SESSÃO v16

```
[ ] Setup (cd worktree + venv + DATABASE_URL+ODOO_*)
[ ] Verificar main avancou desde HEAD v15b
[ ] Pytest baseline: 465 verdes esperado
[ ] Ler memorias [[skill5_picking_pattern]] + [[skill6_planejar_pre_etapa_pattern]]
[ ] Ler PLANEJAMENTO §5 + §7.2 D1-D9 + §10.3 + §12 v15b
[ ] AskUserQuestion sobre escopo v16 (C10 + C10.1 + C10.2 juntos OU faseado)
[ ] Editar faturamento_pipeline.py:
[ ]   - Adicionar helpers _garantir_payment_provider (G029)
[ ]   - Adicionar helpers _garantir_fiscal_setup (G034 DEV_*)
[ ]   - Adicionar helpers _corrigir_price_zero_em_invoice (G007)
[ ]   - Implementar _executar_etapa_c real (substituir stub)
[ ]   - Adicionar db.engine.dispose() antes/apos C (D10)
[ ]   - Expandir _executar_etapa_a com Skill 2 real (CR-H3 TODO v15b)
[ ] Criar app/odoo/estoque/scripts/_commit_helpers.py (D14 + G-RECLF-4)
[ ] 15+ pytest novos verdes (F5d polling + sub-etapas + commit_helpers)
[ ] Smoke dry-run PROD em ajuste F5c_LIBERADO real
[ ] Code-review paralelo (feature-dev:code-reviewer)
[ ] Atualizar PLANEJAMENTO §0 + §7 (C10 ✅) + §12 trilha v16 + ROADMAP HANDOFF
[ ] Commit consolidado v16
[ ] Atualizar PROMPT_PROXIMA_SESSAO.md para v17 (F5e SEFAZ + ETAPA E + ETAPA F)
```

## CRONOGRAMA RESTANTE (apos v15b)

| Sessão | Foco | Checkpoints | Risco |
|--------|------|-------------|-------|
| v15b (concluida) | C6/C7/C8/F5c orchestrator base + atomos Skill 5 | C6, C7, C8, C9 | Medio ✅ |
| **v16 (proxima)** | **C10 F5d aguardar invoices + sub-etapas .5/.6/.7 + D10 dispose + helpers commit consolidados + ETAPA A real (CR-H3)** | C10 | Medio (SSL critico + sub-etapas idempotentes) |
| v17 | C11 F5e SEFAZ Playwright (IRREVERSIVEL) + C12 ETAPA E RecLF + C13 ETAPA F G023 invocando atomo Skill 5 | C11, C12, C13 | Alto (SEFAZ + paralelismo G-RECLF-1) |
| v18 | C14 recovery (--resume + stagnation detector) + C15 SKILL.md + C16 pytest baseline + C17 smokes | C14-C17 | Medio |
| v19 | C18 folhas fluxos + C19 cross-refs + C20 Canary REAL PROD (1 ajuste) | C18-C20 | Alto (1a NF real Skill 8) |
| v20+ | C21 bulk REAL PROD + C22 code-review + C23 commit final + arquivar 09_* SUPERADOS | C21-C23 | Alto (volume real) |

**Total restante**: 5-6 sessoes (v16 → v20+).

## REGRAS INVIOLÁVEIS NOVAS v15b (somar as 60+ anteriores)

61. **(v15b)** Orchestrator base LIVE — NAO recriar `executar_pipeline_bulk` ou `_processar_chunk_etapa_b`. Para adicionar ETAPA C/D/E/F, EDITAR metodos stubs (`executar_etapa_c/d/e/f`) — substituir `NOT_IMPLEMENTED_v15b` por implementacao real.

62. **(v15b)** `_carregar_ajustes` default `status_filter=['PROPOSTO','APROVADO']` (CR-C1 CRITICAL). Pass `None` apenas em uso admin/auditoria — NUNCA passar para pipeline real.

63. **(v15b)** `_agrupar_por_direcao` agrupa por `acao_decidida` (NAO `(co, tipo_op)`). Tentativa de regressao para `(co, tipo_op)` re-introduz CR-C2 CRITICAL (DEV_LF_FB+DEV_LF_CD no mesmo chunk = picking com partner errado).

64. **(v15b)** Compensatorio G-ETB preserva `acao_decidida` do origem (CR-H2). NAO hardcode `INDUSTRIALIZACAO_FB_LF`.

65. **(v15b)** ETAPA D requer DUAS confirmacoes: `--confirmar` (real run) + `--confirmar-sefaz` (SEFAZ irreversivel). Sem ambas: `BLOQUEADO_SEM_CONFIRMAR_SEFAZ` (CR-H4 + CR-M3 codificados como falha em status agregado).

66. **(v15b)** `executar_pipeline_bulk` bloqueia ETAPA D se ETAPA B falhou (CR-H4). Constante `ETAPAS_ABORT_SE_ANTERIOR_FALHOU=(D,)` no entry-point.

## NÃO-FAZER (red flags v16)

❌ Começar v16 SEM ler memorias `[[skill5_picking_pattern]]` + `[[skill6_planejar_pre_etapa_pattern]]` + PLANEJAMENTO §5 + §7.2 D1-D9
❌ Recriar orchestrator do zero — EDITAR `faturamento_pipeline.py` v15b existente
❌ Esquecer `db.engine.dispose()` ANTES e APOS ETAPA C (D10 — G016 SSL crash em polling 1800s)
❌ Esquecer SNAPSHOT meta antes do polling (D5 — anti-DetachedInstanceError)
❌ Esquecer `db.session.get(AjusteEstoqueInventario, meta['id'])` re-fetch APOS polling (D9)
❌ Falha em sub-etapa F5d.5/.6/.7 derrubar o ajuste — devem ser try/except (D6)
❌ Implementar F5e Playwright em v16 (isso é v17 — preservar contexto)
❌ Quebrar pytest baseline 465 verdes (esperado >=480 apos v16 com 15+ pytest novos)

---END---
