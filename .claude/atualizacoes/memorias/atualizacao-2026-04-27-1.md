# Atualizacao Memorias 2026-04-27-1

**Data**: 2026-04-27
**Memorias auditadas**: 29/29 (topic files) + MEMORY.md
**Removidas**: 0 | **Consolidadas**: 0 | **Atualizadas**: 5 topic + MEMORY.md

> **NOTA**: este relatorio foi salvo em `/tmp/manutencao-2026-04-27/dominio-3-relatorio.md` porque o path solicitado `.claude/atualizacoes/memorias/atualizacao-2026-04-27-1.md` foi bloqueado pelo sandbox. O usuario deve copiar manualmente este conteudo para o path correto e atualizar `historico.md` (ver template no fim deste relatorio).

---

## Resumo

Quinta auditoria do sistema de memorias. Sistema permanece saudavel — nenhuma memoria obsoleta, fragmentada ou duplicando CLAUDE.md. Foco da sessao foi corrigir contagens factuais desatualizadas (skills 24->29, scripts SSW 18->22) e reclassificar `type:project` -> `type:feedback|reference` em 3 memorias cujo trabalho ja foi concluido mas cuja regra/heuristica permanece valida permanentemente.

## Acoes Realizadas

### Atualizacoes de contagem (factual)

- **`skills_inventario.md`**: descricao "24 skills" -> "29 skills invocaveis (+ consultando-sql data folder)". Verificado via `ls .claude/skills/` (30 dirs - SKILL_IMPROVEMENT_ROADMAP.md - consultando-sql data folder = 29 invocaveis).
- **`ssw_operacoes.md`**: descricao "18 scripts" -> "22 scripts (18 operacionais + ssw_common.py + agrupar_csvs.py + 2 investigar_903_*.py)". Verificado via `ls .claude/skills/operando-ssw/scripts/*.py`.

### Reclassificacao de type (frontmatter)

Tres memorias estavam marcadas como `type: project` mas documentam regras/heuristicas permanentes — reclassificadas:

- **`app_abort_4xx_gotcha.md`**: `project` -> `feedback`. Gotcha permanente do app (handler global re-raise HTTPException), nao trabalho em andamento.
- **`sdk_0160_subagent_bugs.md`**: `project` -> `reference`. SDK ja avancou para 0.1.66 (verificado em requirements.txt), bugs concretos resolvidos, mas a heuristica "DEV != PROD ao integrar feature SDK nova" + padrao smoketest endpoint permanece valida.
- **`consultando_sql_data_folder.md`**: `project` -> `feedback`. Regra permanente "NAO recriar SKILL.md em consultando-sql", nao trabalho em andamento.

### MEMORY.md

- Skills Inventario entry: "24" -> "29 skills invocaveis (+ consultando-sql data folder)"
- SDK 0.1.60 Subagent Bugs entry: adicionado "(SDK atual 0.1.66)" para sinalizar contexto evolutivo
- SSW Operacoes entry: "18 scripts" -> "22 scripts (18 operacionais + ssw_common + agrupar_csvs + 2 investigacao)"

## Verificacoes Realizadas

- **Frontmatter** (name, description, type): 29/29 corretos.
- **Relevancia**: todas memorias ainda ativas ou uteis como referencia de gotcha permanente.
- **Duplicacao CLAUDE.md**: nenhuma duplicacao detectada (todas as 29 memorias contem informacao especializada nao presente em CLAUDE.md raiz, ~/.claude/CLAUDE.md, app/*/CLAUDE.md).
- **Entradas MEMORY.md -> arquivos**: 29/29 links validos.
- **Arquivos orfaos** (sem entrada em MEMORY.md): 0.
- **Memorias project com datas passadas pendentes**: 0 (apos reclassificacao).
- **Validacoes de paths citados**:
  - `.claude/references/FRAMEWORK_ARISTOTELICO.md` existe (citado em `framework_aristotelico.md`)
  - `.claude/references/MCP_CAPABILITIES_2026.md` existe (citado em `mcp_infrastructure.md`)
  - `.claude/references/BEST_PRACTICES_2026.md` existe (citado em `anthropic_best_practices.md`)
  - `.claude/references/ssw/pops/` contem 45 POPs (citado em `ssw-documentacao.md`)

## Estado Final

- **Total memorias** (topic files): 29 (sem mudanca)
- **MEMORY.md**: 70 linhas (limite: 150) — 47% do budget
- **Entradas orfas**: 0
- **Arquivos sem referencia**: 0
- **Frontmatter correto**: 29/29
- **Distribuicao por tipo**: 12 feedback, 17 reference, 0 project, 0 user puro

## Observacao

Apos esta auditoria, nao ha mais memorias `type: project` no sistema. Isso reflete corretamente o estado atual: todas as memorias persistidas sao ou (a) feedback do usuario / regras de comportamento, ou (b) referencia tecnica para sistemas externos / decisoes arquiteturais. Memorias `type: project` (trabalho em andamento) tendem a ser efemeras e devem ser removidas/reclassificadas quando o trabalho concluir.

---

## Template para historico.md (adicionar manualmente apos `## Atualizacoes`)

```markdown
- [2026-04-27-1](atualizacao-2026-04-27-1.md) — Quinta auditoria. 0 removidas, 0 consolidadas, 5 atualizadas: contagens factuais (skills 24->29, scripts SSW 18->22) + reclassificacao 3 memorias `type:project` -> `feedback|reference` (app_abort_4xx, sdk_0160, consultando_sql_data_folder). 29 memorias, MEMORY.md 70 linhas. 0 memorias `type:project` apos sessao.
```
