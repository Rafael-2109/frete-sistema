# Manutencao Semanal Consolidada — 2026-05-11

**Data**: 2026-05-11
**Dominios executados**: 7
**Dominios OK**: 6 | **PARCIAL**: 1 | **FAILED**: 0

## Resumo por Dominio

| # | Dominio | Status | Resumo |
|---|---------|--------|--------|
| 1 | CLAUDE.md Audit | OK | 9 CLAUDE.md auditados, todos atualizados. Crescimento organico (agente +1.4K LOC, carvia +1.3K LOC). Carteira JS corrigido 22->23, CarVia services 39->41. |
| 2 | References Audit | OK | 39 references revisados, 6 P0 corrigidos. Refresh SDK 0.1.66->0.1.80, anthropic 0.84.0->0.98.1. Subagents 13->14 (gestor-motos-assai). 0 caminhos quebrados. |
| 3 | Memorias Cleanup | OK | 32 memorias auditadas, 3 atualizadas factualmente. MEMORY.md 73 linhas (49% budget). Skills 29->35 invocaveis. 0 orfaos. |
| 4 | Sentry Triage | OK | 6 issues triadas, 2 fixes aplicados (RN saldo_estoque_pedido + RK Decimal*float). 4 fora de escopo. Ambas marcadas resolved no Sentry. |
| 5 | Test Runner | PARCIAL | 946/1019 passed (92.84%), 47 failed + 19 errors em 6 modulos (motos_assai 22, hora 16 fail + 19 error state-pollution, custeio 6, carvia 3, agente/sdk 2). 20 nao coletados (conftest pytest_plugins deprecated). |
| 6 | Memory Eval | OK | Health 82/100 (-4 vs anterior). 338 memorias (+21), stale 60d explodiu 6->35 (+483%). 10 recomendacoes. |
| 7 | Agent Intelligence Report | OK | Health 73, friction 30, trend improving. 150 sessoes (30d), resolved 30.7%. 13 recs ativas (2 CRITICAL, 6 WARNING, 3 INFO). Persistido no banco (report_id=2). |

## Metricas

### CLAUDE.md
- Arquivos auditados: 9/9, modificados: 9
- Crescimento detectado: agente +1.4K LOC, carvia +1.3K LOC
- Correcoes estruturais: carteira JS (22->23), carvia services (39->41)

### References
- Arquivos revisados: 39 (P0: 20, P1: 10, P2: 9 + scan P3-P4)
- Arquivos corrigidos: 6
- Caminhos quebrados: 0
- Pendencia historica: `odoo/IDS_FIXOS.md:80` (product_tmpl_id 34 — desde 31/Jan/2026)

### Memorias
- Auditadas: 32, removidas: 0, consolidadas: 0, atualizadas: 3
- MEMORY.md: 73 linhas (49% do budget 150)
- Drift detectado: skills (29->35), SDK (0.1.66->0.1.80)

### Sentry
- Issues avaliadas: 6, corrigidas: 2, ignoradas: 1, fora_escopo: 3
- Arquivos modificados: `app/carteira/routes/estoque_api.py`, `app/custeio/routes/custeio_routes.py`
- Issues marcadas resolved: PYTHON-FLASK-RN, PYTHON-FLASK-RK

### Tests
- Total: 1019, passed: 946, failed: 47, error: 19, skipped: 7, nao_coletados: 20
- Taxa: 92.84% (queda de 97.78% em 2026-05-05; +253 testes coletados)
- Tempo: 265.46s
- Correlacoes com D4: 0
- Falhas reincidentes: 2 (carvia mock SSW desde 2026-04-27)
- Errors: 19 ERROR em tests/hora/ aparecem apenas em suite completa (state pollution de fixture loja com CNPJ duplicado) — passam isoladamente

### Memory Eval (Producao)
- Health score: 82/100 (-4 vs anterior, primeira queda apos 5 melhoras)
- Total memorias: 338, sessoes: 539, cold: 37, stale 60d: 35
- Usuarios unicos: 23
- Recomendacoes: 10
- Driver da queda: stale 60d explodiu 6->35 (+483%), KG coverage 39.05% (6o ciclo de queda)

### Agent Intelligence Report
- Health score: 73/100
- Friction score: 30
- Sessoes analisadas: 150 (30d)
- Recomendacoes: 13 (2 CRITICAL, 6 WARNING, 3 INFO)
- Backlog: 11 itens
- Trend: improving
- Persistido no banco: sim (report_id=2)
- Itens fechados: 2 (mcp__render__consultar_logs, cnab400)
- Itens novos: 1 (outlier sessao 93ccedf9, $25.15)

## Erros e Falhas

### D5 — Tests (PARCIAL)

47 falhas + 19 errors em 6 modulos. Acoes recomendadas:

1. **motos_assai (22 falhas)** — Bloquear modulo via `--ignore` ate criar fixtures PDF/XLSX em `tests/motos_assai/fixtures/`
2. **hora FAILED (16 falhas)** — Atualizar fixtures: trocar `modalidade_frete='9'` por `'0'` (CIF) ou `'1'` (FOB)
3. **hora ERROR (19 errors)** — State pollution: `hora_loja_cnpj_key` duplicado em suite completa; usar UUIDs ou rollback explicito por teste
4. **custeio (6 falhas)** — Aplicar migrations locais (`audit_log_custeio`, `custo_frete.ativo`, constraints unique/check)
5. **carvia (3 falhas)** — 2 reincidentes mock SSW desde 2026-04-27 (test_a3_ctrnc_cte_comp.py); 1 metodo ausente em `ConferenciaService.listar_fretes_divergentes`
6. **agente/sdk (2 falhas)** — Race condition em `async_event.is_set()` apos submit/cancel (test_pending_questions.py)
7. **conftest motos_assai** — Mover `pytest_plugins` para `tests/conftest.py` top-level (pytest 8.4 deprecation)
