# Manutencao Semanal Consolidada — 2026-06-08

**Data**: 2026-06-08
**Dominios executados**: 7
**Dominios OK**: 6 | **PARCIAL**: 1 | **FAILED**: 0

## Resumo por Dominio

| # | Dominio | Status | Resumo |
|---|---------|--------|--------|
| 1 | CLAUDE.md Audit | OK | 9 auditados, 8 corrigidos (agente 96->104 arq pos-observabilidade Teams; drifts LOC odoo/carvia/financeiro/teams; datas sincronizadas) |
| 2 | References Audit | OK | 41 revisados, 7 corrigidos; bump SDK 0.2.87->0.2.89, 3 skills novas reconciliadas, drift event listeners Separacao. 0 caminhos quebrados |
| 3 | Memorias Cleanup | OK | 160 auditadas, 1 removida, 12 consolidadas, 8 orfaos indexados; MEMORY.md 25.6KB->23.92KB (abaixo do limite de truncamento) |
| 4 | Sentry Triage | OK | 50 issues avaliadas; 1 fix de codigo aplicado (XA, rollback READ-ONLY); 49 fora de escopo (46 infra Odoo CIEL IT) |
| 5 | Test Runner | PARCIAL | 3752 testes, 96.5% sucesso; 137 falhas/errors ambientais/reincidentes (NAO regressao); sem correlacao com D4 |
| 6 | Memory Eval | OK | Health 85/100 (-1); 529 memorias, 781 sessoes, 32 usuarios; cold 12.48%, KG coverage 42.9%; 8 recomendacoes |
| 7 | Agent Intelligence Report | OK | Health 64/100 (era 70), trend declining; regressao de memoria + custo +39% (cluster conciliacao financeira); 13 recomendacoes |

## Metricas

### CLAUDE.md
- Arquivos auditados: 9/9, modificados: 8
- Driver principal: feature observabilidade Teams (F2) — `app/agente` saltou de 96 para 104 arquivos (~48.9K->~53.6K LOC); tree corrigido (Root 6->7 +SUBSISTEMAS.md, routes +admin_teams.py, services +approval_inbox/+skill_effectiveness/+teams_observability)
- Drifts de LOC corrigidos: odoo/estoque ~19.4K->~19.9K, carvia ~67.2K->~67.4K, financeiro ~46.1K->~46.2K, teams ~2.5K->~2.6K
- `app/seguranca/CLAUDE.md` ja consistente (06/06) — nao modificado
- Nenhum caminho inexistente

### References
- Arquivos revisados: 41 (22 P0 + 10 P1 + 9 P2 + scan P3-P4), corrigidos: 7
- Caminhos quebrados: 0
- Correcoes: bump `claude-agent-sdk` 0.2.87->0.2.89 (CLI 2.1.150->2.1.162) propagado em MCP_CAPABILITIES/BEST_PRACTICES/STUDY/AGENT_DESIGN_GUIDE; 3 skills novas (51->54) reconciliadas em ROUTING_SKILLS+INDEX; drift +6 linhas event listeners Separacao em REGRAS_CARTEIRA_SEPARACAO
- Pendencias historicas (inalteradas): product_tmpl_id (FRETE) requer MCP Odoo; revisao trimestral STUDY agendada 2026-07

### Memorias
- Auditadas: 160, removidas: 1 (`render_gunicorn_caddy_split` — redundante com secao WEB-CADDY-SPLIT do CLAUDE.md), consolidadas: 12, atualizadas: 38
- 8 orfaos indexados (skills 7/8 + agente-evolucao shadow + worker_render_filas)
- MEMORY.md: 166 linhas / 23.92KB (reduzido de 25.6KB, abaixo do limite ~24.4KB que causava truncamento no load)
- Estado final: 159 topic files, 159/159 referenciados, 0 orfaos, 0 links quebrados, frontmatter OK em 159/159

### Sentry
- Issues avaliadas: 50, corrigidas (codigo): 1, ignoradas/fora de escopo: 49
- **Fix aplicado**: PYTHON-FLASK-XA (13 eventos, 4 usuarios) — rollback best-effort no `except` de `query_ontology_entities` (tool READ-ONLY), corrige cascata de transacao SQLAlchemy invalida. Arquivo: `app/agente/tools/ontology_query_tool.py`
- PYTHON-FLASK-XN (270 eventos, a #1) — ja corrigido em `main` (commit `2c093f44b`); eventos eram ruido pre-deploy
- Fora de escopo: 46 infra Odoo XML-RPC 502/auth (CIEL IT), 2 scripts ad-hoc Render Shell, 1 ja-resolvido

### Tests
- Total: 3752, passed: 3608, failed: 89, error: 48, skipped: 7, taxa: 96.50%
- **PARCIAL** — falhas quase todas ambientais/reincidentes, NAO regressoes de codigo
- Driver NOVO: coluna `separacao.equipe_vendas` ausente no Postgres local (migration pendente) cascateia ~45 falhas em motos_assai
- Reincidentes: residuo `hora_loja_cnpj_key` (69 hits/35 erros HORA), ARRAY em SQLite (14), fixtures PDF ausentes (6+), residuo custeio TEST_C2_010, carvia `listar_fretes_divergentes` ausente (6 ciclos), doc_audit 3m21s > timeout 60s
- Correlacao com D4: nenhuma (D4 nao tocou os arquivos dos testes que falharam)
- Acoes recomendadas: `flask db upgrade` local, limpeza de residuo de dados, versionar fixtures, isolar suites HORA/motos_assai

### Memory Eval (Producao)
- Health score: 85/100 (-1 vs 86 em 06-01)
- Total memorias: 529, sessoes: 781, cold: 66 (12.48%), stale 60d: 69 (13.04%), usuarios unicos: 32
- Breakdown: eficacia 0.895 (30/30), cold 18.8/20, stale 15.4/20, KG coverage 5.7/15 (ponto fraco — 42.9%, 1590 orfas), correcoes 15/15
- Marco metodologico: `correction_count` deixou de ser zero universal (avg 0.055) — dimensao Correcoes agora legitima
- Recomendacoes: 8 (R1 deletar memorias arquivadas 3x ainda em uso, R2 cluster zero-efficacy do judge, R3 backlog de revisao empresa, R4 poda de orfaos no KG, R5-R8)

### Agent Intelligence Report
- Health score: 64/100 (era 70)
- Sessoes analisadas: 248, friction score: 41
- Recomendacoes: 13, backlog: 13 itens (mergeado do report 2026-06-01)
- Trend: **declining**
- Dois sinais convergem no cluster de conciliacao financeira (Marcus/user_id=18 + user_id=82): (1) regressao de memoria apos 9 semanas perfeitas — 7 memorias com correcao, 1 toxica com 8 correcoes/eficacia 0.0; (2) custo semanal +39% ($402->$557), avg high_cost +25%
- Resolution rate estavel alta (~76%)
- Persistido no banco: sim (report_id=6, HTTP 200)
- 4 recomendacoes critical: remover memoria toxica, soft-cap de custo por sessao, reviver skill `conciliando-transferencias-internas`, especificar skill de pagamento em lote (SICOOB+Desagio)

## Erros e Falhas

Nenhum dominio FAILED. O unico dominio nao-OK foi:

- **D5 (Test Runner) — PARCIAL**: a suite executou integralmente (3752 testes), mas com 89 failed + 48 errors. A analise do agente confirmou que sao falhas ambientais/reincidentes (migration local pendente, residuos de dados de teste, incompatibilidade ARRAY/SQLite, fixtures nao versionadas) e NAO regressoes de codigo introduzidas. Gotcha de procedimento: o comando do manual aborta a ~50% por `--maxfail=5` no `pytest.ini`; o run completo exigiu sobrescrever `addopts`.

## Observacoes do Orquestrador

- **Reconciliacao D4**: o `dominio-4-status.json` registrou `arquivos_modificados: []`, mas o working tree continha um fix real em `app/agente/tools/ontology_query_tool.py` (rollback para a issue XA). O orquestrador inspecionou o diff, confirmou que e o fix legitimo descrito na mensagem final do agente (seguro, READ-ONLY, dentro do escopo permitido) e o incluiu no commit do D4. A discrepancia no status.json decorreu de processos concorrentes editando arquivos durante a sessao.
- **Saude do agente em queda (D7)**: trend declining pela 1a vez em varias semanas, concentrado no fluxo de conciliacao financeira. Recomenda-se priorizar as 4 recomendacoes critical do D7 no proximo ciclo.
- Todas as mudancas de `app/estoque/transferencia_*` do snapshot inicial ja haviam sido commitadas em `6601fc1cf` antes desta manutencao — nenhuma interferencia.
