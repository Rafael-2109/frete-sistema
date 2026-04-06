# Manutencao Semanal Consolidada — 2026-04-06

**Data**: 2026-04-06
**Dominios executados**: 7
**Dominios OK**: 4 | **PARCIAL**: 3 | **FAILED**: 0

## Resumo por Dominio

| # | Dominio | Status | Resumo |
|---|---------|--------|--------|
| 1 | CLAUDE.md Audit | PARCIAL | 9/9 auditados, 2 corrigidos (carteira files 65->47, teams LOC+data). Relatorio/historico nao atualizados (permissao). |
| 2 | References Audit | PARCIAL | 30 arquivos revisados, 7 divergencias encontradas (5 novas + 2 reabertas). Correcoes nao aplicadas (permissao). |
| 3 | Memorias Cleanup | OK | 24 memorias auditadas, 5 removidas, 2 consolidadas, 1 corrigida. MEMORY.md em 58 linhas. |
| 4 | Sentry Triage | OK | 2 issues (performance/db_query), 0 erros app. Reducao 42->2 issues vs anterior. |
| 5 | Test Runner | OK | 288/288 testes OK (100%), 16.63s. Zero falhas. |
| 6 | Memory Eval | OK | Health score 81/100. 128 memorias, 360 sessoes, 21 usuarios. 7 recomendacoes. |
| 7 | Agent Intelligence Report | PARCIAL | Health score 45/100 (DECLINING). Resolution rate caiu 89.6%->36.7%. DB persistence pulada. |

## Metricas

### CLAUDE.md (D1)
- Arquivos auditados: 9/9, modificados: 2
- Divergencias corrigidas: carteira (files 65->47), teams (LOC+data atualizados)
- Pendente: ~/.claude/CLAUDE.md stats espelho

### References (D2)
- Arquivos revisados: 30, corrigidos: 0 (permissao negada)
- Divergencias encontradas: 7
  - claude-agent-sdk: 0.1.53 -> 0.1.55 (real)
  - MCP tools count: 35 -> 36 (real)
  - Memory MCP tools: 11 -> 12 (register_improvement adicionada)
  - Postgres plan: inconsistencia BEST_PRACTICES vs INFRAESTRUTURA
  - odoo/PADROES_AVANCADOS.md: usa datetime.utcnow() em exemplo
  - ssw/INDEX.md: referencia FLUXOS_PROCESSO.md inexistente
  - CLI version: 2.1.88 -> 2.1.91

### Memorias (D3)
- Auditadas: 24 (MEMORY.md + 23 topic files)
- Removidas: 5 (memory_audit_quality, capdo_v3_memoria, teams_postsession_fix, plugins_habilitados, sdk_client_migration_qa)
- Consolidadas: 2 -> 1 (mcp_capabilities + mcp_plugins -> mcp_infrastructure)
- Atualizadas: 1 (framework_aristotelico type project->reference)
- Estado final: 18 topic files, MEMORY.md 58 linhas

### Sentry (D4)
- Issues avaliadas: 2, corrigidas: 0, ignoradas: 2
- Ambas classificadas BAIXO (performance/db_query, nao erro)

### Tests (D5)
- Total: 288, passed: 288, failed: 0, taxa: 100%
- Tempo: 16.63s
- Testes mais lentos: test_confirmar_sugestao (5.05s), test_rejeitar_sugestao (4.24s)

### Memory Eval (D6 - Producao)
- Health score: 81/100
- Total memorias: 128, cold: 14, stale 60d: 2
- Sessoes: 360, usuarios unicos: 21
- Recomendacoes: 7

### Agent Intelligence Report (D7)
- Health score: 45/100
- Sessoes analisadas: 194, friction score: alto (21.6% no_tools)
- Recomendacoes: 8 (2 critical, 4 warning, 2 info)
- Trend: declining

**Issues CRITICAL (D7):**
1. Resolution rate colapsou de 89.6% para 36.7% em 3 semanas
2. 21.6% das sessoes (42) usaram zero tools

**Issues WARNING (D7):**
1. Skill gaps: separacao (21x), frete (20x), nota_fiscal (16x)
2. Memory tools trending DOWN hard
3. Render monitoring zerado em 7d
4. Sessoes NF-PO custando USD 13-17 cada (user 69)

## Erros e Falhas

### D1 (PARCIAL)
- Relatorio/historico nao atualizados (permissao negada ao subagente)
- ~/.claude/CLAUDE.md stats espelho desatualizado

### D2 (PARCIAL)
- 7 divergencias identificadas mas nao corrigidas (permissao negada ao subagente)

### D7 (PARCIAL)
- Persistencia no banco pulada (CRON_API_KEY nao definida localmente)
- historico.md nao atualizado (permissao negada)
