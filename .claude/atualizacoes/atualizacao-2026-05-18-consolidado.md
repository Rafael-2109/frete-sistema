# Manutencao Semanal Consolidada — 2026-05-18

**Data**: 2026-05-18
**Dominios executados**: 7
**Dominios OK**: 6 | **PARCIAL**: 1 | **FAILED**: 0

## Resumo por Dominio

| # | Dominio | Status | Resumo |
|---|---------|--------|--------|
| 1 | CLAUDE.md Audit | OK | 9/9 auditados, 8 modificados. Odoo +6 services inventario 2026-05; Agente +artifact tool/worker; Financeiro +3 services remessa_vortx |
| 2 | References Audit | OK | 39 revisados, 12 corrigidos. SDK 0.1.80 -> 0.2.82, novo subagent auditor-sped-ecd, 36 -> 41 skills |
| 3 | Memorias Cleanup | OK | 49 topic files OK, 4 atualizadas. MEMORY.md 90/150 linhas. 1 orfao indexado |
| 4 | Sentry Triage | OK | 57 issues avaliadas, 0 corrigidas (86% sao Odoo CIEL IT, infra externa) |
| 5 | Test Runner | PARCIAL | 1326/1414 passed (93.78%), 33 failed + 48 errors. State pollution motos_assai/hora dominante |
| 6 | Memory Eval | OK | Health 80/100 (-2). 378 memorias, 592 sessoes, KG +670 entidades, coverage +11.74pp |
| 7 | Agent Intelligence | OK | Health 67, trend DECLINING. Resolution rate cai 3 semanas. "atualizar baseline" escalado p/ critical |

## Metricas

### CLAUDE.md
- Arquivos auditados: 9/9
- Arquivos modificados: 8 (7 modulos + raiz com refresh de data)
- Mudancas estruturais: odoo 32 -> 44 arquivos, agente 72 -> 80, agente/services 14 -> 17

### References
- Arquivos revisados: 39 (P0-P2 completo, P3-P4 scan rapido)
- Arquivos corrigidos: 12
- Caminhos quebrados: 0
- Drift: SDK + skills SPED ECD + subagent + listener line numbers

### Memorias
- Auditadas: 49
- Removidas: 0
- Consolidadas: 0
- Atualizadas: 4
- MEMORY.md: 90 linhas (60% do budget de 150)

### Sentry
- Issues avaliadas: 57
- Corrigidas: 0
- Fora de escopo: 57 (49 Odoo infra externa, 2 server-side dist-packages, demais nao-simples)

### Tests
- Total: 1414
- Passed: 1326
- Failed: 33
- Error: 48
- Skipped: 7
- Taxa: 93.78%
- Correlacao D4: 0 (Sentry nao modificou arquivos)

### Memory Eval (Producao)
- Health score: 80/100
- Total memorias: 378
- Total sessoes: 592
- Cold: 40 (10.58%)
- Stale 60d: 51 (+45.7%)
- Usuarios ativos: 25
- KG coverage: 50.79% (+11.74pp)
- Recomendacoes: 8

### Agent Intelligence Report
- Health score: 67/100
- Friction score: 34
- Sessoes analisadas: 161
- Recomendacoes: 13 (3 critical, 5 warning, 5 info)
- Backlog: 12 itens (3 critical, incluindo nova escalada "conciliando-transf-internas SUMIU")
- Trend: declining
- Persistido no DB: sim (report_id=3)

## Sinais Cruzados

### Pontos de Atencao
1. **D5 vs D7**: D5 reporta state pollution expandiu (errors +29 vs 05-11); D7 reporta resolution rate em declinio. Ambos sugerem instabilidade em pipelines de teste/agente.
2. **D7 "atualizar baseline" ESCALADO**: 19 repeticoes (+27% em 1 semana) virou item critical. Cron diario obrigatorio em `app/agente/skills/gerando-baseline-conciliacao/`.
3. **D5 reincidencias**: race async_event em agente/sdk e `listar_fretes_divergentes` ausente em carvia persistem desde 2026-05-11.
4. **D6 vs D7 divergencia**: D6 reporta memoria 7a semana SEM correcoes (saudavel); D7 reporta health 67 (queda) — pressao vem de skills/tools, nao de memoria.

### Sinais Positivos
- D4: zero ruido de bugs simples — sistema estavel, ruido externo dominante
- D6: KG cresceu 670 entidades, coverage +11.74pp
- D6: empresa sem reviewed_at caiu de 163 -> 77 (melhora)
- D7: custo total -17.3%, outliers historicos $151/$81 expurgados
- D7: 7 semanas consecutivas SEM correcoes de memoria

## Erros e Falhas

### D5 (PARCIAL)
- 33 testes falhando (motos_assai 28, hora 0, custeio 2, agente/sdk 2, carvia 1)
- 48 errors de state pollution (hora 34, motos_assai 14)
- Causa raiz: fixtures PDF/XLSX ausentes em motos_assai; UniqueViolation hora_loja_cnpj_key em hora

### Falhas Operacionais Durante o Run
- D6 inicialmente reportou FAILED (MCP render nao conectou) mas voltou OK em retry — status final OK com health=80
- D7 inicialmente nao escreveu o markdown (system prompt do agente bloqueou Write de findings) — usuou fallback psql para queries; markdown foi gerado posteriormente

## Recomendacoes Acionaveis (do D7)

### CRITICAL (3)
1. **REC-2026-04-13-001** Circuit breaker — 6 semanas sem acao, novo outlier $50.38. Arquivos: `app/agente/sdk/preset.py`, `app/agente/sdk/hooks/`
2. **REC-2026-04-06-003** Skill gaps (estoque/separacao/embarque/faturamento) — 7 semanas, 41% das sessoes (66/161)
3. **REC-2026-05-05-001** Cron diario "atualizar baseline" obrigatorio (3a semana escalando)

### WARNING (5)
- Custo NF-PO user 69 ($128 acumulado)
- Skill `conciliando-transferencias-internas` SUMIU do top 25
- Suite memoria recuperou parcialmente
- high_cost +3.7pp contagem mas -33% valor (divergente)
- Novo outlier $50.38

### INFO (5)
- Sessao 93ccedf9 sem resumo (2 semanas)
- Remover `Agent:Explore` definitivo (5 semanas)
- Nova tool `mcp__artifact__build_artifact` adocao confirmada
- Skills `lendo-arquivos`/`lendo-documentos` saíram do top 25
- Resolution rate meta 80% — declinio 4 semanas

## Artefatos

- D1: `.claude/atualizacoes/claude_md/atualizacao-2026-05-18-1.md`
- D2: `.claude/atualizacoes/references/atualizacao-2026-05-18-1.md`
- D3: `.claude/atualizacoes/memorias/atualizacao-2026-05-18-1.md`
- D4: `.claude/atualizacoes/sentry/atualizacao-2026-05-18-1.md`
- D5: `.claude/atualizacoes/tests/atualizacao-2026-05-18-1.md`
- D6: `.claude/atualizacoes/memory-eval/atualizacao-2026-05-18-1.md`
- D7: `.claude/atualizacoes/agent-reports/report-2026-05-18.md`
- Logs: `/tmp/manutencao-2026-05-18/`
