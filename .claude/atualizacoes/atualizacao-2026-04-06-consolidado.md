# Manutencao Semanal Consolidada — 2026-04-06

**Data**: 2026-04-06
**Dominios executados**: 7
**Dominios OK**: 4 | **PARCIAL**: 3 | **FAILED**: 0

## Resumo por Dominio

| # | Dominio | Status | Resumo |
|---|---------|--------|--------|
| 1 | CLAUDE.md Audit | PARCIAL | 9/9 auditados. 2 CLAUDE.md corrigidos (carteira files 65->47, teams LOC+data). Relatorio pre-existen |
| 2 | References Audit | PARCIAL | 30 arquivos revisados, 7 divergencias encontradas (2 reabertas + 5 novas). Correcoes nao aplicadas p |
| 3 | Memorias Cleanup | OK | 24 memorias auditadas. 5 projetos obsoletos removidos, 2 MCP files consolidados em 1, 1 frontmatter  |
| 4 | Sentry Triage | OK | 2 issues abertas (ambas performance/db_query, nenhum erro). Nenhuma correcao necessaria. Reducao de  |
| 5 | Test Runner | OK | 288/288 testes OK (100%), 16.63s. Nenhuma falha. D4 sem arquivos modificados. |
| 6 | Memory Eval | OK | Health score 81/100. 128 memorias ativas, 14 cold, 2 stale >60d. 360 sessoes, 21 usuarios. 7 recomen |
| 7 | Agent Intelligence Report | PARCIAL | 194 sessoes analisadas (30d). Health score 42/100 (declining). 2 recomendacoes criticas: resolution  |

## Metricas

### CLAUDE.md
- Arquivos auditados: 9, modificados: 2

### References
- Arquivos revisados: 30, corrigidos: 0
- Caminhos quebrados: 1

### Memorias
- Auditadas: 24, removidas: 6, consolidadas: 2
- MEMORY.md linhas: 58

### Sentry
- Issues avaliadas: 2, corrigidas: 0, ignoradas: 2

### Tests
- Total: 288, passed: 288, failed: 0, taxa: 100%

### Memory Eval (Producao)
- Health score: 81/100
- Total memorias: 128, cold: 14, stale 60d: 2
- Recomendacoes: 7

### Agent Intelligence Report
- Health score: 42/100
- Sessoes analisadas: 194, friction score: 67
- Recomendacoes: 10, backlog: 10 itens
- Trend: declining

## Erros e Falhas

### D1 — CLAUDE.md Audit
- Permissao negada para atualizar relatorio atualizacao-2026-04-06-1.md
- Permissao negada para editar historico.md
- Permissao negada para editar ~/.claude/CLAUDE.md stats espelho

### D2 — References Audit
- Permissao de escrita negada - divergencias identificadas mas nao corrigidas

### D7 — Agent Intelligence Report
- CRON_API_KEY nao definida no ambiente local. Persistencia no banco de producao pulada.
