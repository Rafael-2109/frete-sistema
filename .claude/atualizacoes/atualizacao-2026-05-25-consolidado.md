# Manutencao Semanal Consolidada — 2026-05-25

**Data**: 2026-05-25
**Dominios executados**: 7
**Dominios OK**: 6 | **PARCIAL**: 1 | **FAILED**: 0

## Resumo por Dominio

| # | Dominio | Status | Resumo |
|---|---------|--------|--------|
| 1 | CLAUDE.md Audit | OK | 9/9 auditados, 9 modificados. Mudanca maior em `app/odoo/` (+17 arquivos, subpacote `estoque/`) -> 46->63 .py, 23K->28.8K LOC. CarVia +1 feature anexos polimorficos. Carteira: documentado `alert_system.py`. |
| 2 | References Audit | OK | 39 arquivos revisados (20 P0 + 10 P1 + 9 P2), 7 corrigidos. SDK 0.2.82->0.2.87, subagents 15->16, skills 41->48. Listeners/IDs/tolerancias/paths conferem com codigo. 0 caminhos quebrados. |
| 3 | Memorias Cleanup | OK | 86/86 frontmatter OK, 0 orfaos, MEMORY.md 128/150 linhas. Bug estrutural corrigido: 6 arquivos em `memory/memory/` movidos para top-level. 3 correcoes de drift (skills 40->47, SDK 0.2.82->0.2.87). +37 topic files em 7 dias. |
| 4 | Sentry Triage | OK | Backlog producao zerado. Fix `PYTHON-FLASK-M5` (UndefinedColumn alias `s.qtd_saldo_produto_pedido`/`fp.qtd_faturada`) — novo `_extract_alias_map` parseia `FROM/JOIN tabela [AS] alias`. Suite inline 6 casos validada. Issue marcada como resolved. |
| 5 | Test Runner | PARCIAL | 1699 testes, 1611 passed / 33 failed / 48 errors / 7 skipped (94.82%). Reproducao quase identica do baseline 2026-05-18. Sem correlacao com D4. Recomendacao P0: fix collection error (`_try_parse_todos`), state pollution hora, SQLite ARRAY. |
| 6 | Memory Eval | OK | Health 84/100 (+4 vs 80), recupera apos 2 ciclos de queda. Eficacia 0.573->0.656 (+14.5pp). KG coverage retrocede 50.79%->47.53%. Bug latente: memorias `_archived_` continuam em uso. 10 recomendacoes. |
| 7 | Agent Intelligence Report | OK | Health 72, friction 36, 185 sessoes (+15%), resolution rate 76.1% (+11.8pp, REVERTEU declinio). Persistido no banco (report_id=4). Trend: **improving**. 3 itens fechados, 3 novos WARNING, 12 ativos (3 CRITICAL, 6 WARNING, 3 INFO). |

## Metricas

### D1 — CLAUDE.md
- Arquivos auditados: 9/9
- Arquivos modificados: 9
- Maior delta: `app/odoo/CLAUDE.md` (46->63 .py, +17 arquivos novos do subpacote `estoque/`)

### D2 — References
- Arquivos revisados: 39 (20 P0 + 10 P1 + 9 P2)
- Arquivos corrigidos: 7
- Caminhos quebrados: 0
- Drift principal corrigido: SDK 0.2.82->0.2.87 (CLI 2.1.142->2.1.150)

### D3 — Memorias
- Auditadas: 86
- Removidas: 0
- Consolidadas: 0
- Atualizadas: 4 (3 drift + frontmatter)
- MEMORY.md: 128/150 linhas (85% budget)
- Bug estrutural: 6 arquivos em `memory/memory/` movidos para top-level

### D4 — Sentry
- Issues avaliadas: 1
- Issues corrigidas: 1 (`PYTHON-FLASK-M5`)
- Issues ignoradas: 0
- Issues fora-escopo: 0
- Arquivos modificados: `text_to_sql.py` (+~70/−10 linhas)

### D5 — Tests
- Total: 1699
- Passed: 1611
- Failed: 33
- Error: 48
- Skipped: 7
- Taxa de sucesso: 94.82%
- Tempo total: 561.63s (~9min 21s)
- Correlacoes com D4: 0

### D6 — Memory Eval (Producao)
- Health score: 84/100 (+4 vs 80 anterior)
- Total memorias: 425 (+47 vs ciclo anterior)
- Total sessoes: 644 (+52)
- Usuarios unicos: 29 (+4)
- Cold memorias: 44 (10.35%, estabilizou)
- Stale 60d: 59 (+8)
- Eficacia media: 0.656 (+14.5pp — primeira melhora em 3 ciclos)
- Recomendacoes: 10

### D7 — Agent Intelligence Report
- Health score: 72/100
- Friction score: 36
- Sessoes analisadas (30d): 185 (+15%)
- Resolution rate (sem 18/05): 76.1% (+11.8pp — REVERTEU declinio de 3 semanas)
- Custo total (30d): $610.64
- Recomendacoes: 12 (3 CRITICAL, 6 WARNING, 3 INFO)
- Backlog: 12 itens
- Persistido no banco: SIM (report_id=4)
- Trend: **improving**

## Erros e Falhas

### D5 — PARCIAL
Suite executou completa em 561.63s, mas com falhas conhecidas (quase identicas ao baseline 2026-05-18):
- **1 collection error**: `tests/agente_lojas/test_todos_parser.py` — `ImportError: _try_parse_todos` nao existe mais em `app/agente_lojas/sdk/client.py` (modulo ignorado para liberar suite)
- **28 FAILED motos_assai**: 22 fixtures PDF/XLSX ausentes + 6 problemas de logica
- **34 ERROR hora**: `hora_loja_cnpj_key` state pollution em `tests/hora/conftest.py`
- **14 ERROR motos_assai/carregamento_service_crud**: SQLite x ARRAY em `agent_improvement_dialogue.affected_files`
- **2 FAILED custeio**, **2 FAILED agente/sdk** (race async_event), **1 FAILED carvia** (`listar_fretes_divergentes`)

Recomendacao P0 ao orquestrador da proxima semana: fixes triviais (collection error 1 linha + state pollution + SQLite ARRAY) destravam 49 errors.

## Itens CRITICAL Persistentes (D7 backlog)

1. **Circuit breaker** (REC-001, 7 semanas sem acao): topo $50.38 + 2 novos outliers User 38 Alice em manufatura ($13+$12)
2. **Skill gaps embarque/transportadora** (8 semanas): embarque 17 mencoes (+4), transportadora 14 (+3), faturamento 14, novo `journal` 10
3. **conciliando-transferencias-internas SUMIU** (6 semanas): tool deixou de ser usada

## Itens FECHADOS no ciclo

- **Bash trend recuperou UP** (era DOWN ha 3 semanas)
- **Resolution rate -15pp reverteu** (era declining; agora 76.1% +11.8pp)
- **Edit ZERO 7d recuperou** (era critico)

## Itens NOVOS detectados

- **Suite memoria DEGRADADA em 7d** (WARNING)
- **Suite sessions DEGRADADA em 7d** (WARNING)
- **Resolved % caiu 5.2pp** (WARNING — apesar do resolution_rate subir; sao metricas distintas)

## Bugs Latentes Identificados (D6)

- 2 memorias com prefixo `_archived_20260521_174331_*` continuam sendo usadas (u23 e u15, ambas zero-efficacy) — sistema nao filtra arquivadas. R2 URGENTE.
- Zero-efficacy subiu de 8 para 12 (+4 novas no ciclo)
- `low_efficacy_high_use` empresa explodiu 11->29 (~3x) — sinal de fadiga
- KG retrocede: 47 novas memorias entraram, apenas 10 receberam links — pipeline de extracao falhou
- Empresa: 87 sem `reviewed_at` (+10 regressao) — fluxo de revisao quebrado

---

**Logs detalhados em `/tmp/manutencao-2026-05-25/`**
**Relatorios por dominio em `.claude/atualizacoes/{claude_md,references,memorias,sentry,tests,memory-eval,agent-reports}/`**
