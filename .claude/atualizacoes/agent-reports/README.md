# Agent Intelligence Reports (D7)

Relatorios semanais de inteligencia do agente web, gerados automaticamente pelo cron de manutencao (Dominio 7).

## O que faz

Consulta o banco de producao (Render Postgres) para extrair:
- **Efetividade de ferramentas**: quais MCP tools sao mais/menos usadas, trends
- **Lacunas de skills**: topicos que usuarios perguntam mas nao ha tool dedicada
- **Pontos de friccao**: mensagens repetidas, sessoes sem tools, abandonos
- **Saude de memorias**: memorias com correcoes frequentes, baixa eficacia
- **Custos**: sessoes mais caras, distribuicao por modelo
- **Tendencias**: comparacao semana a semana

## Bridge Agent SDK <-> Claude Code

Os relatorios servem como canal de comunicacao entre o agente web (producao) e o Claude Code (desenvolvimento):

1. **Cron D7** consulta dados de producao via MCP → gera relatorio
2. **Relatorio markdown** commitado no repo → Claude Code le diretamente
3. **Relatorio JSON** persistido no banco → agente le via intersession_briefing
4. **Recomendacoes** sao prescritivas: indicam arquivos afetados e acoes concretas

## Como ler os relatorios

### Secoes grep-aveis

Cada secao e delimitada por marcadores HTML:
```
<!-- SECTION:TOOL_EFFECTIVENESS -->
...
<!-- /SECTION:TOOL_EFFECTIVENESS -->
```

Secoes disponiveis:
- `TOOL_EFFECTIVENESS` — ranking de ferramentas
- `SKILL_GAPS` — topicos sem tool dedicada
- `FRICTION` — friccao e qualidade de sessoes
- `MEMORY_HEALTH` — memorias problematicas
- `COST_OUTLIERS` — sessoes mais caras
- `TRENDS` — evolucao 4 semanas
- `RECOMMENDATIONS` — recomendacoes acionaveis
- `BACKLOG` — itens acumulados de semanas anteriores

### Frontmatter

```yaml
---
date: 2026-03-28
health_score: 78
friction_score: 23
sessions_analyzed: 45
recommendation_count: 3
trend: improving
---
```

## Backlog

Recomendacoes nao resolvidas acumulam semana a semana:
- `weeks_open` incrementa a cada relatorio
- Itens com 4+ semanas abertos sao auto-escalados para `critical`
- Itens resolvidos (metrica melhorou) sao removidos automaticamente

## Arquivos

| Arquivo | Descricao |
|---------|-----------|
| `report-YYYY-MM-DD.md` | Relatorio semanal |
| `historico.md` | Indice de todos os relatorios |
| `README.md` | Este arquivo |

## Prompt do dominio

`.claude/atualizacoes/dominios/dominio-7-agent-report.md`
