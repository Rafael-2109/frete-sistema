# PROMPT_PROXIMA_SESSAO — orquestrador-Odoo (worktree feat/estoque-odoo) v15a

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

## 📋 ESTADO ATUAL — apos v14b (FIX D-OPS-5 + SUB-SKILL C5 CONCLUIDOS)

**Sessao v14b (2026-05-25)** entregou em 1 sessao:

1. **FIX Skill 2 D-OPS-5** (~30min) — `transferindo-interno-odoo` agora aceita `lot_id_origem=None` para produto `tracking='none'`. Mudancas em `app/odoo/estoque/scripts/transfer.py`:
   - `_listar_quants_origem`: `aceita_tracking_none=True` default (NAO filtra `lot_id != False`)
   - `transferir_para_indisponivel` (Modo C atomico): tipo `Optional[int]` + valida `product.tracking` via 1 read
   - `distribuir_para_indisponivel` (helper): propaga `aceita_tracking_none`
   - Campo novo: `tracking_origem` ('none' quando lot_id_origem=None validado)
   - 9 pytest novos + canary PROD validado (cod 208000043 sem lote 1 un + reversão Skill 1 ×2)

2. **Sub-skill `auditando-cadastro-fiscal-odoo` perfil V1 'inventario'** (C5 ✅, ~90min) — PRE-FLIGHT delegado pela Skill 8 v15+. Cobre **G017+G018+G035+G014+D-OPS-2/3**:
   - Service: `app/odoo/estoque/scripts/cadastro_fiscal_audit.py` (~430 LOC)
   - SKILL.md + CLI: `.claude/skills/auditando-cadastro-fiscal-odoo/`
   - 14 pytest verdes + smoke PROD 6 cods em 987ms (detectou 2 G014 + 1 D-OPS-3)
   - Cross-refs aplicados: ROUTING_SKILLS, tool_skill_mapper, gestor-estoque-odoo, CLAUDE.md estoque
   - 3 CR-fixes aplicados (HIGH-1 double round-trip; HIGH-2 location filter G014; HIGH-3 agora_utc)

**Baseline pytest**: 416 verdes (393 baseline + 9 D-OPS-5 + 14 C5) em 14.46s.

**Documento vivo MACRO** (regra inviolavel 0 — LER ANTES DE TOCAR Skill 8 OU sub-skills):
- `app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md` (~1450 LOC, 14 seções + §7.5 + trilha v14b)

**Memorias-chave** (LER PRIMEIRO):
- `[[skill2_distribuir_indisp_pattern]]` — pattern Skill 2 + fix v14b D-OPS-5
- `[[sub-skill-c5-pattern]]` — pattern sub-skill C5 V1 'inventario' (NOVA v14b)
- `[[teste-real-6-cods-v14a-ops]]` — origem operacional dos D-OPS-1..5

**Checkpoints concluídos**: 5 de 24
- ✅ C1 pre-mortem (§7.1) | ✅ C2 minera service (§7.2 D1-D9) | ✅ C3 minera script (§7.3 D10-D18)
- ✅ C4 escopo confirmado | ✅ **C5 sub-skill auditando-cadastro-fiscal-odoo V1 (v14b)**
- Bonus v14a-fix: RecebimentoLfOdooService §7.4 G-RECLF-1..11 (READ-only NAO MEXER)
- Bonus v14a-ops: teste real 6 cods §7.5 D-OPS-1..5

## 🎯 PRIORIDADE v15a — Estender Skill 5 com 3 átomos inter-company (C6.5)

**Objetivo** (~150-180min): adicionar 3 átomos novos em `app/odoo/estoque/scripts/picking.py` para a Skill 5 `operando-picking-odoo`. **CRITICO**: o atomo `criar_picking_inter_company` deve INCORPORAR o fix D-OPS-3 (tracking='none') — quando ajuste tem produto tracking='none', criar move SEM lot_name (Odoo aceita; nao cria stock.lot). Elimina o bug L965 do script 09 (D-OPS-3 documentado).

### 3 átomos a criar

| Átomo | Objetivo | Codifica gotcha |
|-------|----------|-----------------|
| `criar_picking_inter_company` | Cria stock.picking de FB→{LF,CD} para faturar inventario (ETAPA B v14a D10-D18). Aceita lista de moves (cod, qty, lote, location_origem, location_destino). Detecta tracking='none' e NAO seta lot_name. | G014 (lote vencido fix Skill 2 on-the-fly preservado), G021/G022 (delegacao Skill 2 ETAPA A), D-OPS-3 (tracking='none') |
| `validar_picking_inter_company` | Valida picking (button_validate) com retry G011 (qty_done) + G018 (peso_liquido/volumes via stock.picking.l10n_br_peso_liquido) + invariante G019/G020 (re-le state pos-validate; raise se != 'done'). | G011, G018, G019/G020 |
| `criar_picking_entrada_destino_manual` | ETAPA F G023: cria picking de entrada manual em destino (LF ou CD) consolidando moves do invoice FB→destino. Idempotente via `origin` (busca antes de criar). Usado quando invoice e' INDUSTR FB→{LF,CD}. | G023 (linhas_esperadas), G021/G022 |

### Tarefas concretas

1. **Setup + baseline**:
   - cd worktree + venv + DATABASE_URL+ODOO_*
   - git fetch + verificar main avancou; rebase se necessario
   - `pytest tests/odoo/ -q --tb=no` baseline 416 verdes

2. **Ler MUITA documentacao** (regra inviolavel 0):
   - `app/odoo/estoque/CLAUDE.md` (constituicao)
   - `app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md` INTEIRO (especialmente §3 diagrama A-F + §7.2 D1-D9 + §7.3 D10-D18 + §7.4 G-RECLF-1..11 + §7.5 D-OPS-1..5 + §10.6 EXPANDIDO + §12 trilha v14b)
   - `app/odoo/estoque/ROADMAP_SKILLS.md` HANDOFF v14b
   - **Memorias**: `[[skill5_picking_pattern]]` + `[[sub-skill-c5-pattern]]` + `[[skill2_distribuir_indisp_pattern]]`
   - **Source do gold-script ETAPA B**: `scripts/inventario_2026_05/09_executar_onda1_bulk.py:624-1155` (`etapa_b_pickings`)
   - **Source ETAPA F**: `scripts/inventario_2026_05/09_executar_onda1_bulk.py:1428-1693` (`etapa_f_entrada_destino_manual` + `_f_criar_entrada_destino_para_invoice`)
   - **Service existente Skill 5**: `app/odoo/estoque/scripts/picking.py` (`StockPickingService`) — ja tem `cancelar`, `validar`, `devolver`
   - **Constants ETAPA F**: `scripts/inventario_2026_05/09_executar_onda1_bulk.py:130-146` (PICKING_TYPE_ENTRADA_DESTINO_MANUAL, COMPANY_LABEL_ENTRADA, LOCATION_ORIGEM_ENTRADA_INDUSTR=26489)

3. **Implementacao** (em ordem):
   - **AskUserQuestion** sobre escopo v15a: 3 atomos juntos OU faseado (apenas 1o em v15a + outros em v15b)?
   - Centralizar constants ETAPA F em `app/odoo/constants/picking_types.py` (pendencia §9)
   - Implementar `criar_picking_inter_company` (atomo C2 — mais complexo, codifica D-OPS-3)
   - Implementar `validar_picking_inter_company` (atomo C2 — invariante G019/G020 ja codificada em outro atomo, REUSAR)
   - Implementar `criar_picking_entrada_destino_manual` (atomo C2 — ETAPA F, idempotente origin)
   - Atualizar `picking.py` SKILL.md + CLI wrapper se aplicavel
   - >=15 pytest novos (3 atomos × ~5 cenarios cada — feliz, dry-run, idempotencia, falha, edge case tracking='none')
   - Cross-refs (subagente + ROUTING_SKILLS + tool_skill_mapper + CLAUDE.md estoque)

4. **Smoke dry-run em PROD** com 1 ajuste real (sem --confirmar):
   - Buscar 1 ajuste AjusteEstoqueInventario com fase F5a + status APROVADO
   - Rodar `criar_picking_inter_company --dry-run` (so plano)
   - Validar output: picking_id_planejado + linhas estruturadas + sem D-OPS-3 bug

5. **Code-review paralelo** (feature-dev:code-reviewer) ao fim
6. **Atualizar PLANEJAMENTO §0 + §3 + §7 (C6.5 ✅) + §12 trilha v15a + ROADMAP HANDOFF**
7. **Commit consolidado** + **atualizar PROMPT_PROXIMA_SESSAO para v15b** (orchestrator base Skill 8)

## ⚠️ PRE-MORTEM v15a (riscos novos)

| # | Risco | Mitigacao |
|---|-------|-----------|
| **R17** | Atomo `criar_picking_inter_company` codifica logica de compensatorio do bug L965 (sem querer) | Implementar primeiro a versao CORRETA (sem bug); compensatorio eh decisao de orchestrator (Skill 8 v15b+), nao do atomo |
| **R18** | `criar_picking_entrada_destino_manual` precisa agregar moves por invoice — risco de duplicar move em multi-call | Idempotencia via `origin` (busca antes de criar) + lock por invoice_id no caller |
| **R19** | Constants ETAPA F (`PICKING_TYPE_ENTRADA_DESTINO_MANUAL`, `COMPANY_LABEL_ENTRADA`, `LOCATION_ORIGEM_ENTRADA_INDUSTR=26489`) so existem em 09_executar_onda1_bulk.py — centralizar antes ou junto | Criar `app/odoo/constants/picking_types.py` (ou extender existing) ANTES dos atomos |
| **R20** | tracking='none' fix no atomo `criar_picking_inter_company` deve REUSAR pattern do Skill 2 v14b (validar tracking; raise se anomalia) | Importar/replicar logica `if lot_id is None: prod_read = odoo.read(...); raise se != 'none'` |

## LEITURAS OBRIGATÓRIAS (ordem)

1. `app/odoo/estoque/CLAUDE.md` (constituição) — especialmente §6 catálogo skills + §7 granularidade + §10 fronteiras
2. `app/odoo/estoque/ROADMAP_SKILLS.md` — seção HANDOFF v14b
3. **`app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md` INTEIRO** (regra inviolavel 0):
   - §0 cabeçalho (status v14b)
   - §3 diagrama A-F (ETAPA B + F = onde os atomos vivem)
   - §4.6 status sub-skill C5 (✅ exceto integracao v15b)
   - §6 pattern Skill 6 v9 + §7 lista checkpoints (C6.5 ⬜)
   - §7.2 D1-D9 (service-fonte) + §7.3 D10-D18 (script-fonte ETAPA B) + §7.4 G-RECLF-1..11 (preservar)
   - **§7.5 D-OPS-1..D-OPS-5** (CRITICO — D-OPS-3 codifica no atomo novo)
   - §8.1 pre-mortem 15 riscos + R16/R17/R18/R19/R20 (v14b/v15a)
   - §9 pendências + §10.6 EXPANDIDO 3 atomos
   - §12 trilha v14b (esta sessao)
4. Memory `[[skill5_picking_pattern]]` (pattern atual da Skill 5)
5. Memory `[[sub-skill-c5-pattern]]` (PRE-FLIGHT que v15b orchestrator vai invocar)
6. Memory `[[skill2_distribuir_indisp_pattern]]` (pattern tracking='none' validado)
7. **Para implementacao**:
   - `scripts/inventario_2026_05/09_executar_onda1_bulk.py:624-1155` (ETAPA B — fonte de `criar_picking_inter_company`)
   - `scripts/inventario_2026_05/09_executar_onda1_bulk.py:1428-1693` (ETAPA F — fonte de `criar_picking_entrada_destino_manual`)
   - `scripts/inventario_2026_05/09_executar_onda1_bulk.py:1156-1196` (ETAPA C — fonte de invariante validacao)
   - `app/odoo/estoque/scripts/picking.py` (StockPickingService atual — adicionar 3 atomos)
   - `tests/odoo/services/test_stock_picking_service.py` (extender com 15+ pytest novos)

## CHECKLIST DA SESSÃO v15a

```
[ ] Setup (cd worktree + venv + DATABASE_URL+ODOO_*)
[ ] Verificar main avancou desde HEAD v14b
[ ] Pytest baseline: 416 verdes esperado (pytest tests/odoo/ -q --tb=no)
[ ] Ler memorias [[skill5_picking_pattern]] + [[sub-skill-c5-pattern]] + [[skill2_distribuir_indisp_pattern]]
[ ] Ler PLANEJAMENTO §3 + §7.3 D10-D18 + §7.5 D-OPS-3 + §10.6 EXPANDIDO
[ ] AskUserQuestion sobre escopo v15a (3 atomos juntos OU faseado)
[ ] Centralizar constants ETAPA F em app/odoo/constants/
[ ] Implementar `criar_picking_inter_company` (codifica D-OPS-3 tracking='none')
[ ] Implementar `validar_picking_inter_company` (reusa invariante G019/G020)
[ ] Implementar `criar_picking_entrada_destino_manual` (idempotente origin)
[ ] 15+ pytest novos verdes
[ ] Smoke dry-run em ajuste PROD real
[ ] Code-review paralelo (feature-dev:code-reviewer)
[ ] Atualizar PLANEJAMENTO §0 + §7 + §12 (trilha v15a) + ROADMAP HANDOFF
[ ] Commit consolidado v15a
[ ] Atualizar PROMPT_PROXIMA_SESSAO.md para v15b (orchestrator base Skill 8)
```

## CRONOGRAMA RESTANTE (apos v14b)

| Sessão | Foco | Checkpoints | Risco |
|--------|------|-------------|-------|
| ~~v14b (concluida)~~ | ~~Fix Skill 2 D-OPS-5 + sub-skill C5~~ | ~~C5~~ | ~~Médio~~ ✅ |
| **v15a (proxima)** | C6.5 estender Skill 5 com **3 átomos** inter-company (`criar_picking_inter_company` + `validar_picking_inter_company` + `criar_picking_entrada_destino_manual`) — INCORPORA fix D-OPS-3 | C6.5 | Médio |
| **v15b** | C6+C7+C8 orchestrator base + F5a + F5b (chama átomos novos Skill 5; invoca sub-skill C5 via subprocess; centraliza D17) | C6, C7, C8 | Médio |
| **v16** | C9+C10 F5c + F5d (G016+G007+G034+G029 + D10 dispose + D14 commit_resilient + D11 expire_all) | C9, C10 | Médio (SSL crítico) |
| **v17** | C11+C12+C13 F5e + etapas E/F (G023 + D17 centralizado + D-OPS-2b fix F5e propagação + D-OPS-4 pós-hook ETAPA E) | C11, C12, C13 | Alto (SEFAZ) |
| **v18** | C14+C15+C16+C17 recovery + SKILL.md + tests + smokes | C14-C17 | Médio |
| **v19** | C18+C19+C20 folhas + cross-refs + Canary REAL PROD | C18-C20 | Alto (1ª NF real Skill 8) |
| **v20+** | C21+C22+C23 bulk REAL PROD + code-review + commit final + arquivar 09_* SUPERADOS | C21-C23 | Alto (volume real) |

**Total restante: 7-8 sessoes** (v15a → v20+).

## REGRAS INVIOLÁVEIS NOVAS v14b (somar as 57 anteriores)

58. **(v14b) Fix Skill 2 D-OPS-5 APLICADO** — `_listar_quants_origem` aceita `aceita_tracking_none=True` default; atomo Modo C valida `product.tracking` se `lot_id_origem=None`. Pattern para REUSAR no atomo novo Skill 5 `criar_picking_inter_company` (C6.5 v15a) — INCORPORAR mesma logica (`if lot_id is None: prod_read = odoo.read('product.product', [pid], ['tracking']); raise se != 'none'`).
59. **(v14b) Sub-skill C5 PRONTA — Skill 8 v15b invoca via subprocess** — `auditando-cadastro-fiscal-odoo` esta LIVE. Orchestrator base Skill 8 (C6 v15b) deve chamar via `subprocess.run(['python', '.claude/skills/auditando-cadastro-fiscal-odoo/scripts/auditar_cadastro_inventario.py', '--ciclo', NOME, '--perfil', 'inventario'], capture_output=True)` ANTES de iniciar bulk. Se exit code != 0 OR `pode_faturar=False` no JSON, abortar com mensagem clara.
60. **(v14b) Code-review aplicado: HIGH-1+HIGH-2+HIGH-3 + CRIT-1+CRIT-2** — todos os findings aplicados em `cadastro_fiscal_audit.py` (eliminar double round-trip, filtrar Indisp em G014, usar agora_utc) + `transfer.py` (mensagem erro D-OPS-5 atualizada, comentario keyfn corrigido). Padrao para futuros atomos: SEMPRE invocar code-reviewer ao fim de sessao.

## NÃO-FAZER (red flags v15a)

- ❌ Começar v15a SEM ler memorias [[skill5_picking_pattern]] + [[sub-skill-c5-pattern]] + PLANEJAMENTO §7.3
- ❌ Implementar `criar_picking_inter_company` SEM codificar fix D-OPS-3 (tracking='none' NAO seta lot_name)
- ❌ Implementar `criar_picking_entrada_destino_manual` SEM idempotencia por `origin`
- ❌ Esquecer de centralizar constants ETAPA F em `app/odoo/constants/picking_types.py` (R19)
- ❌ Patchar script 09 (regra Rafael v14a-ops "use scripts existentes apenas")
- ❌ Implementar orchestrator Skill 8 base em v15a (isso é v15b)
- ❌ Esquecer cross-refs (subagente + ROUTING_SKILLS + tool_skill_mapper + CLAUDE.md estoque)
- ❌ Quebrar pytest baseline 416 verdes (esperado >=431 apos v15a com 15+ pytest novos)
- ❌ Esquecer de atualizar §0 + §3 + §7 + §10.6 + §12 + ROADMAP HANDOFF a CADA commit

---END---
