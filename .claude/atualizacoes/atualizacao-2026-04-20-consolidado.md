# Manutencao Semanal Consolidada — 2026-04-20

**Data**: 2026-04-20
**Dominios executados**: 7
**Dominios OK**: 2 | **PARCIAL**: 4 | **FAILED**: 1

## Resumo por Dominio

| # | Dominio | Status | Resumo |
|---|---------|--------|--------|
| 1 | CLAUDE.md Audit | OK | 9 auditados, 5 modificados. Contagens LOC/arquivos sincronizadas. |
| 2 | References Audit | PARCIAL | ~30 revisados, 7 divergencias factuais identificadas. Correcoes bloqueadas (sensitive file). |
| 3 | Memorias Cleanup | OK | 26 topic files auditados, 1 removida, MEMORY.md 66 linhas. |
| 4 | Sentry Triage | FAILED | MCP token expirado. Precisa reautorizacao. |
| 5 | Test Runner | PARCIAL | 569/569 testes passaram (100%) em 41.2s. Relatorio bloqueado (sensitive file). |
| 6 | Memory Eval | PARCIAL | Health 84/100 (estavel). Historico.md bloqueado. |
| 7 | Agent Intelligence Report | PARCIAL | Health 42/100, trend declining. Persistencia no banco pulada. |

## Metricas principais

- **D1**: 9/9 auditados, 5 modificados (agente +9 arquivos, carvia +3, financeiro +7)
- **D2**: 7 divergencias (SDK 0.1.55->0.1.63, MEMORY_PROTOCOL linha 157->173, ROUTING_SKILLS 31->25, MAPEAMENTO_CORES bootstrap path, INDEX, IDS_FIXOS, etc)
- **D3**: 26 memorias -> 25 (carvia_auditoria_pendencias removida apos confirmar W9 + FC_VIRTUAL implementados)
- **D4**: 0 issues avaliadas (token expirado)
- **D5**: 569 passed / 0 failed / 100% (crescimento +281 testes em 2 semanas)
- **D6**: Health 84, 272 memorias (+38%), 32 cold, KG 43.4% (-9.4pp), 8 recs
- **D7**: Health 42 (-16), 157 sessoes, $613.50 custo 30d (+39%), outlier user 18 $151.80, 10 recs

## Erros e Falhas

### D4 (Sentry) — FAILED — reautorizacao urgente
- MCP Sentry token expirado em search_issues e whoami
- Write em .claude/atualizacoes/sentry/ bloqueado

### D5/D6 parcial — sensitive file
- D5: relatorio 569/569 OK pronto em memoria mas nao gravado
- D6: historico.md pendente de atualizacao manual

### D7 parcial — CRON_API_KEY
- POST /agente/api/intelligence-report pulado (chave ausente localmente)

## Acoes de Follow-up

1. URGENTE: reautorizar MCP Sentry
2. IMPORTANTE: aplicar as 7 divergencias de references
3. ATENCAO: trend D7 declining — outlier user 18 escalou 2 semanas (REC-2026-04-13-001 ignorada)
4. MONITORAR: cold tier dobrou (15->32), KG coverage regrediu
5. CONFIG: definir CRON_API_KEY local para persistencia D7
