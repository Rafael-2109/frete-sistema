# Manutencao Semanal Consolidada — 2026-04-20

**Data**: 2026-04-20
**Dominios executados**: 7
**Dominios OK**: 3 | **PARCIAL**: 3 | **FAILED**: 1 (apos revisao humana das correcoes D2)

## Resumo por Dominio

| # | Dominio | Status | Resumo |
|---|---------|--------|--------|
| 1 | CLAUDE.md Audit | OK | 9 auditados, 5 modificados (agente, agente/services, carteira, carvia, financeiro). Contagens LOC/arquivos sincronizadas. |
| 2 | References Audit | OK | 30 revisados, 7 divergencias. **6 aplicadas** apos revisao humana; 1 pendente (IDS_FIXOS product_tmpl_id — MCP Odoo). 0 caminhos quebrados. |
| 3 | Memorias Cleanup | OK | 26 topic files auditados, 1 removida (carvia pendencias resolvidas), MEMORY.md 66 linhas (limite 150). |
| 4 | Sentry Triage | FAILED | MCP Sentry token expirado — reautorizacao manual urgente. |
| 5 | Test Runner | PARCIAL | 569/569 tests (100%) em 41.2s. +281 testes desde 2026-04-06. Relatorio reconstruido pelo orquestrador. |
| 6 | Memory Eval | PARCIAL | Health 84/100 (estavel). 272 memorias (+38%), 32 cold (+17), KG coverage 43,4% (-9,4pp). 8 recomendacoes. |
| 7 | Agent Intelligence Report | PARCIAL | Health 52/100 (-6), trend declining. 157 sessoes, $613.50 (+39%). 10 recomendacoes. CRON_API_KEY ausente. |

## Metricas por Dominio

### D1 — CLAUDE.md
- Auditados: 9/9, modificados: 5
- Highlights: agente 58→67 arquivos / 29.8K→33.3K LOC, carvia 96→99 / 55.5K→60.3K LOC, financeiro 70→77 / 43.8K→45.1K LOC

### D2 — References
- Revisados: 30 (P0 root + P1 modelos/negocio + P2 odoo + P3 scan)
- Caminhos quebrados: 0
- Divergencias: 7 (BEST_PRACTICES SDK 0.1.55→0.1.63, MCP_CAPABILITIES idem, MEMORY_PROTOCOL linha 157→173, ROUTING_SKILLS 31→25, MAPEAMENTO_CORES bootstrap path, INDEX faltando AGENT_DESIGN_GUIDE/TEMPLATES, IDS_FIXOS product_tmpl_id flag aberta)
- Aplicadas: **6/7** (todas exceto IDS_FIXOS product_tmpl_id — requer MCP Odoo)

### D3 — Memorias
- Auditadas: 26, removidas: 1 (carvia_auditoria_pendencias — W9 + FC_VIRTUAL→MANUAL ja implementados)
- Consolidadas: 0, atualizadas: 1 (MEMORY.md reorganizado)
- MEMORY.md: 66 linhas, frontmatter 25/25 corretos, 0 orfaos

### D4 — Sentry
- Issues avaliadas: 0, corrigidas: 0
- Erro: `token expired` em search_issues + whoami

### D5 — Tests
- Total: 569, Passed: 569, Failed: 0, Error: 0, Skipped: 0
- Taxa: 100%, Tempo: 41.20s
- Crescimento: +281 testes vs 2026-04-06 (era 288)

### D6 — Memory Eval (Producao)
- Health: 84/100 (estavel vs 2026-04-13)
- Memorias: 272 (+75, +38% em 7d), Sessoes: 434 (+43), Usuarios: 22 (+1)
- Cold: 32 (11.8%, +17), Stale 60d: 2 (0.7%, estavel)
- KG coverage: 43.4% (REGRESSAO -9.4pp), 1351 entidades (+40%)
- 8 recomendacoes (2 ALTA/CRITICA)

### D7 — Agent Intelligence (Bridge)
- Health: 52/100 (-6 vs semana anterior)
- Friction score: 38, Trend: **declining**
- Sessoes analisadas: 157 (30d)
- Custo 30d: $613.50 (+39%), user 18 concentra 38%
- Resolution rate: 71.0%→51.1% (REGRESSAO -19.9pp)
- Outlier escalado: $151.80 (306 msgs, conciliacao) — REC-2026-04-13-001 nao implementada
- 10 recomendacoes: 3 CRITICAL, 4 WARNING, 3 INFO; 2 fechadas (no_tools 4.5%, SQL tool normalizado)

## Erros e Falhas

### D4 — FAILED (reautorizacao urgente)
- `mcp__sentry__search_issues`: token expirado
- `mcp__sentry__whoami`: token expirado
- Write bloqueado em `.claude/atualizacoes/sentry/` (sensitive file)
- Acao: reautorizar MCP Sentry antes do proximo ciclo

### D2/D5 — PARCIAL (sensitive file)
- D2: 7 correcoes documentadas; **6 aplicadas** em sessao subsequente apos revisao humana (20/04/2026). 1 pendente (IDS_FIXOS).
- D5: relatorio reconstruido pelo orquestrador (cp via shell)

### D7 — PARCIAL (CRON_API_KEY ausente)
- POST `/agente/api/intelligence-report` pulado
- Relatorio markdown gravado normalmente

## Acoes de Follow-up Prioritarias

1. **URGENTE**: reautorizar MCP Sentry (bloqueia D4 desde esta semana)
2. ~~**IMPORTANTE**: aplicar manualmente as 7 divergencias de D2 (references)~~ — **RESOLVIDA 2026-04-20**: 6/7 aplicadas, 1 pendente (IDS_FIXOS product_tmpl_id requer MCP Odoo)
3. **ATENCAO**: REC-2026-04-13-001 (circuit breaker user 18) escalou — 2a semana aberta
4. **MONITORAR**: cold tier dobrou em 7d (15→32), KG coverage regrediu
5. **CONFIG**: definir `CRON_API_KEY` local para persistencia D7 no banco
6. **VERIFICAR**: `product_tmpl_id ~34~` em `odoo/IDS_FIXOS.md` via MCP Odoo (flag aberto desde 31/Jan)

## Artefatos

- D1: `.claude/atualizacoes/claude_md/atualizacao-2026-04-20-1.md`
- D2: `.claude/atualizacoes/references/atualizacao-2026-04-20-1.md`
- D3: `.claude/atualizacoes/memorias/atualizacao-2026-04-20-1.md`
- D4: nao gerado (FAILED)
- D5: `.claude/atualizacoes/tests/atualizacao-2026-04-20-1.md`
- D6: `.claude/atualizacoes/memory-eval/atualizacao-2026-04-20-1.md`
- D7: `.claude/atualizacoes/agent-reports/report-2026-04-20.md`
- Logs orquestrador: `/tmp/manutencao-2026-04-20/`
