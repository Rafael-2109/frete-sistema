# Manutencao Semanal Consolidada — 2026-06-15

**Data**: 2026-06-15
**Dominios executados**: 7
**Dominios OK**: 6 | **PARCIAL**: 1 | **FAILED**: 0

## Resumo por Dominio

| # | Dominio | Status | Resumo |
|---|---------|--------|--------|
| 1 | CLAUDE.md Audit | OK | 9 auditados, 8 modificados. Drift estrutural em 4 modulos (agente 104->108, carvia 107->108, financeiro 80->83, odoo 70->72). carteira/raiz so data; seguranca intacto. |
| 2 | References Audit | OK | P0-P2 (43 files) revisados em profundidade + P3-P4 scan rapido. 6 corrigidos (drift SDK 0.2.95->0.2.101, refs de linha de service, paths CidadeAtendida/CadastroSubRota). 0 caminhos quebrados. |
| 3 | Memorias Cleanup | OK | 154 auditadas, 2 stubs removidos (redundantes c/ CLAUDE.md/IDS_FIXOS), ~22 entradas consolidadas em ~11. MEMORY.md 175->149 linhas (sob o teto de 150). Frontmatter 153/153 OK, 0 links quebrados. |
| 4 | Sentry Triage | OK | 50 issues avaliadas. 1 bug real (TypeError float-Decimal carvia) ja corrigido em main (commit 68d1e43b4) = ruido pre-deploy -> marcado resolved. 49 fora de escopo (46 Odoo XML-RPC infra externa, 2 scripts ad-hoc, 1 N+1 perf). 0 arquivos de codigo alterados. |
| 5 | Test Runner | PARCIAL | Suite coletou 4329 testes; processo pytest MORTO a ~15% (676 executados). Dos executados, 100% passou (676 PASSED, 0 FAILED/ERROR/SKIPPED). Cobertura nao representativa — areas de falha cronica (motos_assai/hora/inventario/custeio/carvia) NAO rodaram. Re-rodar com wait ate EXIT_CODE no proximo ciclo. |
| 6 | Memory Eval | OK | Health 87/100 (+2, recorde da serie). 617 memorias, 869 sessoes, 28 usuarios. stale 60d 13%->3.4%. KG coverage caindo (39.7%, 3o ciclo). Empresa 58% nunca revisada (9o ciclo). 7 recomendacoes. |
| 7 | Agent Intelligence Report | OK | Health 58 (era 64), trend DECLINING. 280 sessoes/30d (+12.9%). Custo semanal dobrou ($557->$1038), resolution 75.9->68.1% (maior queda da serie). Memoria nociva u18 persiste. Relatorio persistido (report_id=7, HTTP 200). 13 recomendacoes, 11 backlog. |

## Metricas

### CLAUDE.md
- Arquivos auditados: 9/9, modificados: 8 (so seguranca inalterado)
- Drift corrigido: agente (+4 arquivos), carvia (+1), financeiro (+3), odoo (+2 estoque scripts)

### References
- Arquivos revisados: 43 (P0 24 + P1 10 + P2 9), corrigidos: 6
- Caminhos quebrados: 0
- Destaque: drift de versao SDK 0.2.95->0.2.101 / anthropic 0.98.1->0.109.1 nao propagado em 2026-06-13

### Memorias
- Auditadas: 154, removidas: 2, consolidadas: 22 (->~11 linhas), atualizadas: 1
- MEMORY.md: 175 -> 149 linhas (26.3KB; teto procedimento 150 OK; byte ~24KB nao perseguido por Guideline #2)

### Sentry
- Issues avaliadas: 50, corrigidas (codigo): 0, marcadas resolved: 1, ignoradas/fora de escopo: 49
- Arquivos de codigo modificados: 0 (working tree de codigo intacto)

### Tests
- Coletados: 4329 (+577 vs 2026-06-08) | Executados: 676 | Passed: 676 | Failed: 0 | Error: 0 | Skipped: 0
- Taxa sobre executado: 100% | Cobertura do run: ~15.6% (NAO representativa — processo morto a ~15%)
- Correlacoes D4: 0 (D4 nao alterou codigo)

### Memory Eval (Producao)
- Health score: 87/100 (+2, recorde)
- Total memorias: 617, cold: 102 (16.5%), stale 60d: 21 (3.4%)
- Total sessoes: 869 | Usuarios: 28 | Recomendacoes: 7

### Agent Intelligence Report
- Health score: 58/100 (era 64) | Friction score: 51
- Sessoes analisadas: 280 | Recomendacoes: 13 | Backlog: 11 itens
- Trend: declining (custo dobrou, resolution -7.8pp)
- Persistido no banco: sim (report_id=7)

## Erros e Falhas

### D5 — Test Runner (PARCIAL)
- Run pytest truncado a ~15% (676/4329) — processo background morto no fim do turno antes da conclusao; log sem linha de sumario final nem `EXIT_CODE=`.
- Resultado NAO conclusivo: status dos ~3653 testes restantes (incluindo as areas de falhas cronicas: motos_assai/hora/inventario/custeio/carvia) e DESCONHECIDO.
- Acao recomendada para o proximo ciclo: re-executar a suite completa com wait explicito ate `EXIT_CODE=` aparecer no log antes de encerrar o turno.

### Sinais de atencao (nao-bloqueantes)
- **D7 trend declining**: custo semanal do agente dobrou e resolution rate caiu 7.8pp — revisar recomendacoes criticas do relatorio de inteligencia.
- **D6 KG coverage**: caindo pelo 3o ciclo consecutivo (39.7%); empresa 58% nunca revisada (9o ciclo).
- **D2 carry-forward (advisory)**: `product_tmpl_id=34` requer MCP Odoo (pendente desde 2026-04-20); 5 tabelas reais sem schema JSON gerado.
