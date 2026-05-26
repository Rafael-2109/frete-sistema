# PROMPT_PROXIMA_SESSAO — orquestrador-Odoo (worktree feat/estoque-odoo) v15b

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

## 📋 ESTADO ATUAL — apos v15a (3 ÁTOMOS INTER-COMPANY SKILL 5 LIVE)

**Sessao v15a (2026-05-25)** entregou em 1 sessao:

1. **C6.5 ✅ COMPLETO — Skill 5 estendida com 3 atomos inter-company**:
   - `criar_picking_inter_company` (codifica **D-OPS-3 fix** tracking='none')
   - `validar_picking_inter_company` (fluxo F5b completo D3 + G018 v2 peso/volumes)
   - `criar_picking_entrada_destino_manual` (ETAPA F G023 + idempotencia origin EXATO)
   - helper publico `aplicar_peso_volumes_fallback` (G018 v2)
   - +19 pytest verdes (42 → 61 stock_picking_service); baseline Odoo 416 → **435 verdes em 14.36s**
   - smoke PROD validou D-OPS-3 detection em 6 cods v14a-ops (103500105 PIMENTA tracking='none' confirmado)

2. **Constants ETAPA F centralizadas** em `app/odoo/constants/picking_types.py`:
   - `ACOES_ENTRADA_DESTINO_MANUAL: FrozenSet[str]`
   - `PICKING_TYPE_ENTRADA_DESTINO_MANUAL: Dict[int, int]` (LF=19; CD/FB pendentes)
   - `COMPANY_LABEL_ENTRADA: Dict[int, str]`
   - `LOCATION_ORIGEM_ENTRADA_INDUSTR = LOCATION_DESTINO_TRANSITO_INDUSTR` (alias semantico)
   - Decisao v15a: em `picking_types.py` (NAO em `operacoes_fiscais.py` — picking ≠ matriz fiscal).

3. **Cross-refs aplicados** (5):
   - `.claude/skills/operando-picking-odoo/SKILL.md` (description estendida; 6 atomos LIVE no catalogo)
   - `.claude/agents/gestor-estoque-odoo.md` (header status v15a)
   - `.claude/references/ROUTING_SKILLS.md` (header extensao)
   - `app/odoo/estoque/CLAUDE.md` (§6 tabela atualizada)
   - `app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md` (§0 + §7 C6.5 ✅ + §12 trilha v15a)

**Baseline pytest**: **435 verdes** em 14.36s (416 baseline + 19 v15a).

**Documento vivo MACRO** (regra inviolavel 0 — LER ANTES DE TOCAR Skill 8):
- `app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md` (~1500 LOC, 14 seções + §7.5 + trilha v15a)

**Memorias-chave** (LER PRIMEIRO):
- `[[skill5_picking_pattern]]` — pattern Skill 5 v3 + v15a (3 atomos inter-company)
- `[[skill2_distribuir_indisp_pattern]]` — pattern Skill 2 v10+v14b D-OPS-5 fix
- `[[sub-skill-c5-pattern]]` — pattern sub-skill C5 V1 'inventario' (v14b)
- `[[teste-real-6-cods-v14a-ops]]` — origem operacional D-OPS-1..5

**Checkpoints concluídos**: 6 de 24
- ✅ C1 pre-mortem (§7.1) | ✅ C2 minera service (§7.2 D1-D9) | ✅ C3 minera script (§7.3 D10-D18)
- ✅ C4 escopo confirmado | ✅ C5 sub-skill auditando-cadastro-fiscal-odoo V1 (v14b)
- ✅ **C6.5 Skill 5 estendida com 3 atomos inter-company (v15a)**
- Bonus v14a-fix: RecebimentoLfOdooService §7.4 G-RECLF-1..11 (READ-only NAO MEXER)
- Bonus v14a-ops: teste real 6 cods §7.5 D-OPS-1..5

## 🎯 PRIORIDADE v15b — Orchestrator BASE Skill 8 + F5a + F5b (C6+C7+C8)

**Objetivo** (~150-200min): criar `app/odoo/estoque/orchestrators/faturamento_pipeline.py` reutilizando pattern Skill 6 v9 (`pre_etapa_executor.py`). Foco em **3 sub-objetivos**:

### Sub-objetivo C6: Orchestrator base (esqueleto)

- Criar `FaturamentoPipelineExecutor` (classe principal)
- Entry-point `executar_onda_faturamento(ciclo, etapas=['A','B','C','D','E','F'], dry_run=True, ...)` 
- Modos CLI: `planejar`, `propor`, `listar-onda`, `aprovar-onda`, `executar-onda` (alinhado a Skill 6)
- Argparser com `--ciclo`, `--apenas-etapa A|B|C|D|E|F`, `--ate-etapa X`, `--confirmar`, `--confirmar-sefaz` (D18)
- **INVARIANTE v15a**: usar `criar_picking_inter_company` + `validar_picking_inter_company` + `criar_picking_entrada_destino_manual` em vez de re-implementar logica de picking inline (Fluxo>>Skills)
- **INVARIANTE 10.3**: etapa = barreira sincronizacao (todos pickings → expire_all+reload → todas validacoes → expire_all+reload → ...)
- **G016 SSL**: `db.engine.dispose()` PROFILATICO antes/apos C+D (D10); `expire_all() + carregar_ajustes()` entre etapas (D11); `_commit_resilient` versao MAIS FORTE (D14 + G-RECLF-4)
- **PRE-FLIGHT C5**: invoca `subprocess.run(['python', '.claude/skills/auditando-cadastro-fiscal-odoo/scripts/auditar_cadastro_inventario.py', '--ciclo', CICLO, '--perfil', 'inventario'], ...)` ANTES de bulk. Se `pode_faturar=False`, aborta.

### Sub-objetivo C7: ETAPA B F5a (criar pickings)

- Metodo `_executar_etapa_b_criar(ajustes_chunk)` no orchestrator
- Itera por grupo (company_origem, tipo_op) → por chunk (max 30 cods/picking)
- Para cada chunk: monta `linhas` (lote_origem dos ajustes — G023) + invoca `picking_svc.criar_picking_inter_company(...)` (atomo Skill 5 v15a)
- **G014 PROTECTION** (script 09 L795-917): lote vencido on-the-fly via Skill 2 `transferir_quantidade_para_lote` (verificar se v1 ou v2 — pendencia §9 — preferir v2)
- **G-ETB-COMPENSATORIO** (script L994-1031): qty_restante > 0 em PERDA_LF_FB → cria novo `AjusteEstoqueInventario('INDUSTRIALIZACAO_FB_LF', status='PROPOSTO', lote_destino='MIGRAÇÃO', erro_msg='[COMPENSATORIO_FALTA_ESTOQUE]')` para ondas futuras
- **G022**: `time.sleep(5)` entre chunks (script L1136-1138)
- `aj.picking_id_odoo = picking_id` + `aj.fase_pipeline = 'F5a_PICKING_CRIADO'` + commit_resilient

### Sub-objetivo C8: ETAPA B F5b (validar pickings)

- Metodo `_executar_etapa_b_validar(ajustes_chunk, picking_id, linhas)` 
- Invoca `picking_svc.validar_picking_inter_company(picking_id, linhas_esperadas=linhas, aplicar_peso_volumes=True)` (atomo Skill 5 v15a)
- **G018 v2 codificado dentro do atomo** — orchestrator NAO precisa chamar `aplicar_peso_volumes_fallback` manualmente
- Apos OK: `aj.fase_pipeline = 'F5b_VALIDADO'` + commit_resilient

### Tarefas concretas v15b

1. **Setup + baseline**:
   - cd worktree + venv + DATABASE_URL+ODOO_*
   - git fetch + verificar main avancou; rebase se necessario
   - `pytest tests/odoo/ -q --tb=no` baseline **435 verdes**

2. **Ler MUITA documentacao** (regra inviolavel 0):
   - `app/odoo/estoque/CLAUDE.md` (constituicao)
   - `app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md` INTEIRO (especialmente §3 + §6 pattern Skill 6 v9 + §7.2 D1-D9 + §7.3 D10-D18 + §10.3/§10.4/§10.6 + §12 trilha v15a)
   - `app/odoo/estoque/ROADMAP_SKILLS.md` HANDOFF v15a
   - **Memorias**: `[[skill5_picking_pattern]]` (v15a) + `[[skill6_planejar_pre_etapa_pattern]]` (pattern v9 orchestrator) + `[[sub-skill-c5-pattern]]`
   - **Source pattern reuso**: `app/odoo/estoque/orchestrators/pre_etapa_executor.py` (907 LOC)
   - **Service-fonte**: `app/odoo/services/inventario_pipeline_service.py` (1346 LOC — F5a/F5b/F5c) — NAO copiar, EXTRAIR padroes
   - **Script-fonte**: `scripts/inventario_2026_05/09_executar_onda1_bulk.py:617-1149` (ETAPA B) — NAO copiar, EXTRAIR padroes

3. **Implementacao** (em ordem):
   - **AskUserQuestion** sobre escopo v15b: C6+C7+C8 juntos OU C6 sozinho + C7+C8 em v15b-2?
   - Criar arquivo `app/odoo/estoque/orchestrators/faturamento_pipeline.py`
   - Implementar `FaturamentoPipelineExecutor.__init__` + argparser + entry-point
   - Implementar `_pre_flight_via_subskill_c5` (subprocess + parse JSON)
   - Implementar `_executar_etapa_a` (delega Skill 2 — DELEGAVEL 100% D15)
   - Implementar `_executar_etapa_b_criar` (C7) + `_executar_etapa_b_validar` (C8)
   - Implementar `_executar_etapa_b_liberar` (F5c — chama `picking_svc.liberar_faturamento` direto)
   - >=10 pytest novos (orchestrator skeleton + invocacao mocada de atomos Skill 5 v15a)
   - Cross-refs (CLAUDE.md + ROADMAP + PLANEJAMENTO §0 + §7 + §12)

4. **Smoke dry-run em PROD** com 1 ajuste real:
   - Buscar 1 `AjusteEstoqueInventario` status APROVADO + acao_decidida em ACOES_PICKING
   - Rodar `faturamento_pipeline.py --ciclo INVENTARIO_2026_05 --apenas-etapa A,B --cod COD --dry-run`
   - Validar: PRE-FLIGHT OK + ETAPA A planejada + ETAPA B planejada (pickings que seriam criados)

5. **Code-review paralelo** (feature-dev:code-reviewer) ao fim
6. **Atualizar PLANEJAMENTO §0 + §3 + §7 (C6/C7/C8 ✅) + §12 trilha v15b + ROADMAP HANDOFF**
7. **Commit consolidado** + **atualizar PROMPT_PROXIMA_SESSAO para v16** (F5c+F5d + G029/G034)

## ⚠️ PRE-MORTEM v15b (riscos novos)

| # | Risco | Mitigacao |
|---|-------|-----------|
| **R21** | Orchestrator base reimplementa logica de picking que ja' esta nos atomos Skill 5 v15a | Auditar diff antes de commit — orchestrator NAO chama `odoo.create('stock.picking')` direto; sempre via atomos Skill 5 |
| **R22** | `subprocess.run` para PRE-FLIGHT C5 pode ter problemas de PATH/ENV em ambiente de teste | Capturar stderr; tratar exit code; usar `sys.executable` em vez de `'python'`; passar env=os.environ.copy() |
| **R23** | `_commit_resilient` (script) vs `_commit_with_retry` (service) vs `_safe_update` (RecebimentoLfOdoo) — 3 versoes, escolher qual? | Decisao v15b: USAR `app.utils.database_retry.commit_with_retry` (G-RECLF-5 — ja existe util compartilhada). Consolidar em `app/odoo/estoque/scripts/_commit_helpers.py` se for ate v16. |
| **R24** | Etapa-barreira macro vs sub-nuance ETAPA B (por picking com sleep 5s) — implementacao errada paralela tudo | Orchestrator implementa loop SERIAL POR CHUNK em ETAPA B (G022); paraleliza DENTRO de 1 chunk via Semaphore=5 (decisao 10.3 macro mantida) |
| **R25** | G-ETB-COMPENSATORIO regra de negocio nao codificada na Skill 5 atomo — DEVE viver no orchestrator | Orchestrator C7 analisa `qty_restante` e cria novo AjusteEstoqueInventario PROPOSTO ANTES de commit chunk |

## LEITURAS OBRIGATÓRIAS (ordem)

1. `app/odoo/estoque/CLAUDE.md` (constituição) — §6 catálogo skills + §7 granularidade + §10 fronteiras
2. `app/odoo/estoque/ROADMAP_SKILLS.md` — seção HANDOFF v15a
3. **`app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md` INTEIRO** (regra inviolavel 0):
   - §0 cabeçalho (status v15a)
   - §3 diagrama A-F
   - §6 pattern Skill 6 v9 + adaptacoes
   - §7.2 D1-D9 (service-fonte) + §7.3 D10-D18 (script-fonte ETAPA B) + §7.5 D-OPS-1..D-OPS-5
   - §8.1 pre-mortem 15+5 riscos + R21-R25 (v15b)
   - §10.3/§10.4/§10.6 (decisoes RESOLVIDAS)
   - §12 trilha v15a (esta sessao terminou)
4. Memory `[[skill5_picking_pattern]]` (3 atomos v15a — INVOCAR via Python)
5. Memory `[[skill6_planejar_pre_etapa_pattern]]` (pattern v9 orchestrator — reusar)
6. Memory `[[sub-skill-c5-pattern]]` (PRE-FLIGHT — subprocess invocacao)
7. **Para implementacao**:
   - `app/odoo/estoque/orchestrators/pre_etapa_executor.py` (TEMPLATE — Skill 6 v9 pattern)
   - `app/odoo/estoque/scripts/picking.py` (atomos Skill 5 v15a — invocar via service)
   - `scripts/inventario_2026_05/09_executar_onda1_bulk.py:617-1149` (ETAPA B fonte — EXTRAIR padroes, NAO copiar)

## CHECKLIST DA SESSÃO v15b

```
[ ] Setup (cd worktree + venv + DATABASE_URL+ODOO_*)
[ ] Verificar main avancou desde HEAD v15a
[ ] Pytest baseline: 435 verdes esperado
[ ] Ler memorias [[skill5_picking_pattern]] + [[skill6_planejar_pre_etapa_pattern]] + [[sub-skill-c5-pattern]]
[ ] Ler PLANEJAMENTO §3 + §6 + §10.3 + §12 v15a
[ ] AskUserQuestion sobre escopo v15b (C6+C7+C8 juntos OU C6 sozinho)
[ ] Criar app/odoo/estoque/orchestrators/faturamento_pipeline.py
[ ] Implementar `_pre_flight_via_subskill_c5` (subprocess + parse JSON)
[ ] Implementar `_executar_etapa_a` (delega Skill 2 D15)
[ ] Implementar `_executar_etapa_b_criar` (C7 — invoca atomo Skill 5 v15a + compensatorio)
[ ] Implementar `_executar_etapa_b_validar` (C8 — invoca atomo Skill 5 v15a)
[ ] Implementar `_executar_etapa_b_liberar` (F5c — picking_svc.liberar_faturamento direto)
[ ] 10+ pytest novos verdes
[ ] Smoke dry-run em ajuste PROD real
[ ] Code-review paralelo (feature-dev:code-reviewer)
[ ] Atualizar PLANEJAMENTO §0 + §7 + §12 (trilha v15b) + ROADMAP HANDOFF
[ ] Commit consolidado v15b
[ ] Atualizar PROMPT_PROXIMA_SESSAO.md para v16 (F5c + F5d + G029/G034)
```

## CRONOGRAMA RESTANTE (apos v15a)

| Sessão | Foco | Checkpoints | Risco |
|--------|------|-------------|-------|
| ~~v14b (concluida)~~ | ~~Fix Skill 2 D-OPS-5 + sub-skill C5~~ | ~~C5~~ | ~~Médio~~ ✅ |
| ~~v15a (concluida)~~ | ~~C6.5 estender Skill 5 com 3 átomos inter-company~~ | ~~C6.5~~ | ~~Médio~~ ✅ |
| **v15b (proxima)** | **C6+C7+C8 orchestrator base + F5a + F5b + F5c** (chama átomos novos Skill 5 v15a; invoca sub-skill C5 via subprocess; centraliza D17 commit_resilient) | C6, C7, C8 | Médio-Alto |
| **v16** | C9+C10 F5d polling + G029/G034 + D10 dispose + D14 commit_resilient | C9, C10 | Médio (SSL crítico) |
| **v17** | C11+C12+C13 F5e SEFAZ + ETAPA E + ETAPA F (G023 — invoca atomo Skill 5 v15a) | C11, C12, C13 | Alto (SEFAZ + paralelismo G-RECLF-1) |
| **v18** | C14+C15+C16+C17 recovery + SKILL.md + tests + smokes | C14-C17 | Médio |
| **v19** | C18+C19+C20 folhas + cross-refs + Canary REAL PROD | C18-C20 | Alto (1ª NF real Skill 8) |
| **v20+** | C21+C22+C23 bulk REAL PROD + code-review + commit final + arquivar 09_* SUPERADOS | C21-C23 | Alto (volume real) |

**Total restante: 6-7 sessoes** (v15b → v20+).

## REGRAS INVIOLÁVEIS NOVAS v15a (somar as 60 anteriores)

61. **(v15a) 3 atomos Skill 5 LIVE** — `criar_picking_inter_company` + `validar_picking_inter_company` + `criar_picking_entrada_destino_manual`. **Orchestrator Skill 8 (v15b) deve invocar EXCLUSIVAMENTE via service** (Python direct call — NAO subprocess CLI; atomos SEM CLI ad-hoc). Pattern: `from app.odoo.estoque.scripts.picking import StockPickingService; svc = StockPickingService(odoo=odoo); r = svc.criar_picking_inter_company(...)`.
62. **(v15a) D-OPS-3 fix permanente codificado no atomo** — orchestrator v15b NAO precisa workaround SEMLOTE (que era hack v14a-ops). Passa `lot_name` natural dos ajustes; atomo strip se produto for tracking='none'.
63. **(v15a) Constants ETAPA F em `app/odoo/constants/picking_types.py`** (NAO em `operacoes_fiscais.py`). Imports: `from app.odoo.constants.picking_types import ACOES_ENTRADA_DESTINO_MANUAL, PICKING_TYPE_ENTRADA_DESTINO_MANUAL, COMPANY_LABEL_ENTRADA, LOCATION_ORIGEM_ENTRADA_INDUSTR`.

## NÃO-FAZER (red flags v15b)

- ❌ Começar v15b SEM ler memorias [[skill5_picking_pattern]] v15a + [[skill6_planejar_pre_etapa_pattern]] + PLANEJAMENTO §6
- ❌ Orchestrator chama `odoo.create('stock.picking')` direto — DEVE chamar `svc.criar_picking_inter_company(...)` (atomo Skill 5 v15a)
- ❌ Esquecer PRE-FLIGHT C5 ANTES de bulk (subprocess `auditar_cadastro_inventario.py --ciclo X --perfil inventario`)
- ❌ Paralelizar ETAPA B inteira (G022 — sleep 5s entre chunks SERIAL; paraleliza DENTRO de 1 chunk via Semaphore=5)
- ❌ Esquecer G016 SSL (`db.engine.dispose()` antes/apos C+D; `expire_all() + carregar_ajustes()` entre etapas)
- ❌ Esquecer G-ETB-COMPENSATORIO (cria AjusteEstoqueInventario PROPOSTO quando qty_restante > 0 em PERDA_LF_FB)
- ❌ Esquecer cross-refs (subagente + ROUTING_SKILLS + tool_skill_mapper + CLAUDE.md estoque + PLANEJAMENTO)
- ❌ Quebrar pytest baseline 435 verdes (esperado >=445 apos v15b com 10+ pytest novos)
- ❌ Implementar F5d/F5e em v15b (isso é v16/v17 — preservar contexto)

---END---
