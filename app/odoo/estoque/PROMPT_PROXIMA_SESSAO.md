# PROMPT_PROXIMA_SESSAO — orquestrador-Odoo (worktree feat/estoque-odoo) v14

> Copie tudo entre `---BEGIN---` e `---END---` e cole como prompt inicial da próxima sessão.

---BEGIN---

Continue o trabalho do orquestrador-Odoo. Worktree: `/home/rafaelnascimento/projetos/frete_sistema_estoque_odoo` (branch `feat/estoque-odoo`, **commits ao fim de v13: a937748b (merge v12 main) + 63d817d5 (v13 planejamento Skill 8) + b6e3bb0b (v13 mid: 4 decisoes RESOLVIDAS + mineracao C2 service) + commit deste PROMPT/pre-mortem**). `main` continua VIVO em paralelo (Rafael commita lá — SPED ECD em progresso) — verificar se avançou e considerar rebase ANTES de iniciar.

## Setup OBRIGATÓRIO (worktree sem .env)

```bash
cd /home/rafaelnascimento/projetos/frete_sistema_estoque_odoo
source /home/rafaelnascimento/projetos/frete_sistema/.venv/bin/activate
set -a; . <(grep -E '^(DATABASE_URL|ODOO_)' /home/rafaelnascimento/projetos/frete_sistema/.env); set +a
git fetch origin main && git log --oneline b6e3bb0b..origin/main  # ver se main avancou
```

## 📋 ESTADO ATUAL — Skill 8 `faturando-odoo` PLANEJADA (v13 concluida)

Sessao v13 (2026-05-25) ESTRUTUROU completamente a Skill 8 — MACRO C3 mais perigosa do roadmap (NF inter-company → robo CIEL IT → SEFAZ irreversivel). Pipeline: 6 etapas A→B→C→D→E→F sequenciais (cada etapa = barreira de sincronizacao).

**Documento vivo de planejamento** (REGRA INVIOLAVEL 0 — LER ANTES de qualquer modificacao em codigo Skill 8):
- `app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md` (~900 LOC, 14 secoes + pre-mortem §8.1)

**Checkpoints concluidos v13**: 3 de 24
- ✅ **C1** — Pre-mortem completo (§7.1 — 4 dimensoes x 6 etapas)
- ✅ **C2** — Mineracao detalhada `inventario_pipeline_service.py` (§7.2 — 14 metodos + **9 descobertas-chave D1-D9 padroes a PRESERVAR**)
- ✅ **C4** — Escopo confirmado: pipeline COMPLETO A-F em N sessoes

**6 decisoes RESOLVIDAS v13** (sem decisoes pendentes para v14):

| # | Decisao | Razao Rafael |
|---|---------|--------------|
| **10.1** | Escopo COMPLETO A-F em N sessoes | "estruturar bem, depois rodar casos reais" |
| **10.2** | Estruturar antes; casos reais apos C18 | idem |
| **10.3** | **Paralelismo: ETAPA = BARREIRA** (todos pickings → todas validacoes → todas emissoes; preservar Semaphore=5) | "fazer tudo por etapa; mitiga DetachedInstanceErros + SSL connection timeout" |
| **10.4** | Centralizar journals: ADIAR para Skill 7 escriturando | tarefa ortogonal |
| **10.5** | Pre-flight como **sub-skill nova `auditando-cadastro-fiscal-odoo`** (agnostica com perfis multiplos) | "podem haver faturamentos para cliente cujo pre-flight tera regras DIFERENTES (certificado A1, IE, FCI)" |
| **10.6** | **Refatorar F5a/F5b COMPLETAMENTE para Skill 5** (atomos novos `criar_picking_inter_company` + `validar_picking_inter_company`) | "Se mexe com picking, devera ser atraves da Skill 5; principio de atomicidade; Fluxo >> Skills" |

**Novo checkpoint v15**: **C6.5** (estender Skill 5 com 2 atomos inter-company antes de C7/C8).

**Sub-skill nova prevista v14**: `auditando-cadastro-fiscal-odoo` (perfis: inventario V1 + futuros venda-cliente).

## ⚠️ PRE-MORTEM v13 (LER §8.1 do PLANEJAMENTO — 15 riscos R1-R15 mapeados)

Riscos CRITICOS para v14 — atencao especial:

| # | Risco | O que fazer em v14 |
|---|-------|---------------------|
| **R1** | "Etapa = barreira" pode NAO ser pattern do script (decidido 10.3 ANTES de minerar). | **C3 PRIMEIRO confirmar**: se script faz pipeline por ajuste → re-validar 10.3 com Rafael |
| **R3** | Sub-skill perfis multiplos viola "skills nascem de demanda real" | **C5: implementar V1 INLINE simples; estrutura de perfis SO' quando 2o perfil chegar** |
| **R6** | C3 (1850 LOC) consome 80% contexto v14, sem sobrar para C5 | **DIVIDIR v14 em v14a (so C3) e v14b (so C5) — sessao fresca para cada** |
| **R13** | Eu (agente) releio PLANEJAMENTO mas IGNORO padroes D1-D9. | **Checklist no fim de v14: D1-D9 documentados foram considerados nas decisoes?** |

## LEITURAS OBRIGATORIAS ANTES DE AGIR (ordem)

1. `app/odoo/estoque/CLAUDE.md` (constituicao)
2. `app/odoo/estoque/ROADMAP_SKILLS.md` — secao HANDOFF (procurar "v13 mid-sessao" + "Status global apos v13 mid-sessao")
3. **`app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md` INTEIRO** (regra inviolavel 0):
   - §0 cabecalho estado
   - §1-§6 visao + escopo + decomposicao A-F + pre-flight delegado + SSL/timeout + pattern reuso
   - **§7.2 D1-D9 descobertas-chave** (CRITICO — padroes a PRESERVAR)
   - **§8.1 pre-mortem v13** (15 riscos R1-R15)
   - §10 6 decisoes RESOLVIDAS
   - §11 cronograma + §12 trilha v13
4. `.claude/agents/gestor-estoque-odoo.md` (subagente — invariantes existentes)
5. **Para C3**: `scripts/inventario_2026_05/09_executar_onda1_bulk.py` (1850 LOC — etapas A/B/E/F)
6. **Para C5**: investigar caminho de `gtin_validator.py` (em `app/odoo/utils/` ou `app/recebimento/services/`) + `09_executar_onda1_bulk.py:139-211` (`validar_cadastro_fiscal`)

## FOCO da Sessao v14 — RECOMENDACAO

**OPCAO RECOMENDADA: v14a APENAS (C3 + decisao R1)** — preserva contexto fresco para v14b (C5).

### v14a — Foco: C3 (mineracao script) + revalidar R1

**Objetivo**: confirmar (ou refutar) decisao 10.3 (etapa = barreira) ANTES de codar orchestrator v15.

**Tarefas concretas**:

1. **C3 — Mineracao detalhada `09_executar_onda1_bulk.py`**:
   - Ler integral (1850 LOC)
   - Preencher §7.3 do PLANEJAMENTO com tabela funcoes etapas+linhas+side-effects+deps
   - Identificar **pattern de orchestracao**: pipeline por ajuste (A→B→C→D→E→F sequencial por ajuste) OU etapa = barreira (todos em A, depois todos em B, etc.)?
   - **Criterio de aceite**: §7.3 preenchida + resposta clara sobre pattern + recomendacao sobre R1

2. **Se R1 confirmado (script faz pipeline por ajuste)**:
   - AskUserQuestion para Rafael: re-validar 10.3 ou manter etapa-barreira no orchestrator novo?
   - Atualizar §10.3 com nova razao (se mudar)
   - Atualizar §6.2 e §11 conforme

3. **Atualizar §0 (status) + §12 (trilha v14a) + ROADMAP HANDOFF**

4. **Commit consolidado** `docs(estoque): v14a — C3 mineracao script + decisao R1`

**Tempo estimado**: ~45-60min, ~70k tokens.

### v14b — Foco: C5 (sub-skill auditando-cadastro-fiscal-odoo)

Em SESSAO FRESCA apos v14a. **Aplicar R3** (V1 INLINE simples, sem estrutura de perfis ate demanda real).

**Tarefas concretas**:

1. Localizar `gtin_validator.py` + `validar_cadastro_fiscal` (mineracao incremental do script — partes especificas)
2. Criar `app/odoo/estoque/scripts/cadastro_fiscal_audit.py` (service):
   - Funcao top-level `auditar_cadastro_inventario(produto_ids, auto_corrigir_barcode=False) -> dict`
   - 3 checks: G017 NCM + G035 barcode + G018 weight
   - Modo dry-run (default) + --confirmar (so para G035 auto-corrigir barcode)
   - Output JSON estruturado
3. Criar `.claude/skills/auditando-cadastro-fiscal-odoo/SKILL.md` + CLI wrapper
4. Cross-refs: subagente `gestor-estoque-odoo` (lista skills) + `.claude/references/ROUTING_SKILLS.md` (+1 invocavel) + `tool_skill_mapper.py` + `CLAUDE.md` raiz + `app/odoo/estoque/CLAUDE.md` §6 catalogo (READ ancillary passa de 1 para 2)
5. Pytest >5 verdes em `tests/odoo/services/test_cadastro_fiscal_audit_service.py`
6. Smoke dry-run em onda real (sem write)
7. Atualizar §0 + §4 + §7 (C5 ✅) + §12 + ROADMAP HANDOFF
8. Commit consolidado `feat(estoque): v14b — Skill auditando-cadastro-fiscal-odoo perfil inventario V1`

**Tempo estimado**: ~90-120min, ~150k tokens.

## REGRAS INVIOLAVEIS NOVAS v13 (somar as 34 anteriores)

35. **(v13) PLANEJAMENTO_SKILL8 e' fonte unica de verdade** para Skill 8. LER inteiro ANTES de tocar codigo (regra inviolavel 0 do planejamento).
36. **(v13) 9 descobertas-chave D1-D9** do §7.2 sao padroes a PRESERVAR no orchestrator C3 macro Skill 8 (D1 snapshot antes threads, D2 agrupamento picking, D3 bug L19/L20/L21 fix, D4 G023 linhas_esperadas, D5 SNAPSHOT meta polling longo, D6 sub-etapas F5d.5/.6/.7 em try/except, D7 HARD_FAIL_CONFIG_ERRORS, D8 idempotencia tripla F5e, D9 db.session.get re-fetch + commit_with_retry).
37. **(v13) Etapa = barreira de sincronizacao** (decisao 10.3): orchestrator Skill 8 NAO faz pipeline por ajuste; faz por etapa (todos pickings → todas validacoes → ...). **Se C3 v14 revelar que script NAO faz isso, RE-VALIDAR com Rafael antes de codar.**
38. **(v13) Skill 5 sera estendida** com 2 atomos novos (`criar_picking_inter_company` + `validar_picking_inter_company`) seguindo principio "Fluxo >> Skills". F5a/F5b NUNCA implementados direto no orchestrator Skill 8 — sempre via Skill 5.
39. **(v13) Pre-flight delegado** a sub-skill `auditando-cadastro-fiscal-odoo` (agnostica com perfis). Skill 8 INVOCA via subprocess; NAO implementa pre-flight diretamente.
40. **(v13 pre-mortem)** R3: sub-skill V1 INLINE simples; estrutura de perfis SO' quando 2o perfil chegar (NAO especulativo).
41. **(v13 pre-mortem)** R6+R7: dividir sessoes grandes em sub-sessoes (v14a/v14b; v15a/v15b) quando contexto/escopo passar de ~80k tokens.

## NÃO-FAZER (red flags v14)

- ❌ Comecar v14 SEM ler PLANEJAMENTO §7.2 D1-D9 + §8.1 pre-mortem inteiro
- ❌ Codar orchestrator Skill 8 ANTES de C3 confirmar R1 (etapa-barreira vs pipeline por ajuste)
- ❌ Criar sub-skill `auditando-cadastro-fiscal-odoo` com estrutura de perfis multiplos antes do 2o perfil real existir (R3)
- ❌ Tentar fazer C3 + C5 na mesma sessao (R6 — preserva contexto)
- ❌ Modificar Skill 5 (`picking.py`) em v14 — C6.5 e' so' v15
- ❌ Pular checklist "D1-D9 considerados?" antes do commit
- ❌ Quebrar pytest baseline 393 verdes
- ❌ Esquecer de atualizar §0 + §12 (trilha) + ROADMAP HANDOFF a CADA commit

## CHECKLIST DA SESSAO v14

```
[ ] Setup (cd worktree + venv + DATABASE_URL+ODOO_*)
[ ] Verificar se main avancou desde b6e3bb0b: git fetch origin main && git log --oneline b6e3bb0b..origin/main
[ ] Se avancou: rebase incremental ANTES de iniciar
[ ] Pytest baseline: 393 verdes esperado (rodar `pytest tests/odoo/ -q`)
[ ] Ler ROADMAP HANDOFF v13 mid + PLANEJAMENTO_SKILL8 INTEIRO (especial §7.2 D1-D9 + §8.1 pre-mortem)
[ ] AskUserQuestion: foco v14a (C3 so) | v14b (C5 so, assumindo C3 ja feito) | combinado (ARRISCADO)
[ ] Executar foco escolhido conforme tarefas acima
[ ] Verificar resultado direto no Odoo se houver smoke
[ ] Code-review paralelo (feature-dev:code-reviewer) ao fim
[ ] Atualizar §0 + §7 (checkpoint movido) + §12 (trilha) + ROADMAP HANDOFF v14
[ ] Commit consolidado
[ ] Atualizar este PROMPT_PROXIMA_SESSAO.md para v15
```

## CRONOGRAMA RESTANTE (estimativa REVISADA pos-pre-mortem)

| Sessao | Foco | Checkpoints | Risco |
|--------|------|-------------|-------|
| **v14a** | C3 mineracao script + revalidar R1 | C3 | Baixo |
| **v14b** | C5 sub-skill auditando-cadastro-fiscal-odoo perfil inventario V1 | C5 | Baixo-Medio |
| **v15a** | C6.5 estender Skill 5 com atomos inter-company | C6.5 | Medio (mexe skill madura) |
| **v15b** | C6+C7+C8 orchestrator base + F5a + F5b (chama atomos novos Skill 5) | C6, C7, C8 | Medio |
| **v16** | C9+C10 F5c + F5d (G016+G007+G034+G029) | C9, C10 | Medio (SSL critico) |
| **v17** | C11+C12+C13 F5e + etapas E/F | C11, C12, C13 | Alto (SEFAZ + G023) |
| **v18** | C14+C15+C16+C17 recovery + SKILL.md + tests + smokes | C14-C17 | Medio |
| **v19** | C18+C19+C20 folhas + cross-refs + CANARY | C18-C20 | Alto (PRIMEIRA NF real) |
| **v20+** | C21+C22+C23 bulk + code-review + commit final | C21-C23 | Alto (volume real) |

**Total revisado: 9-11 sessoes** (era 8 inicial; +1 por dividir v14; +1 por dividir v15; +1 buffer de canary).

---END---
