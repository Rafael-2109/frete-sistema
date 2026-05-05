# Atualizacao CLAUDE.md — 2026-05-05-1

**Data**: 2026-05-05  **Auditados**: 9/9  **Modificados**: 9

## Resumo
Auditoria dos 9 CLAUDE.md. Unica mudanca estrutural: agente/sdk/ ganhou
`shutdown_state.py` (84 LOC, suprime Sentry de RuntimeError em shutdown
Teams worker — atexit). CarVia subiu 600 LOC (62.7K -> 63.3K) sem mudar
arquivos. Demais modulos sem variacao estrutural — apenas datas atualizadas.

## Estado Atual (apos auditoria)

| Modulo | Arquivos | LOC | Templates |
|--------|----------|------|-----------|
| agente | 72 | ~35.4K | 3 (web) |
| agente/services | 14 | ~8.7K | — |
| carteira | 50 | ~18.1K | 13 + 22 JS |
| carvia | 102 | ~63.3K | 103 |
| financeiro | 77 | ~45.1K | — |
| odoo | 32 | ~18.7K | — |
| seguranca | 14 | ~2K | 8 |
| teams | 4 | ~2.5K | — |

## Alteracoes por Arquivo

### CLAUDE.md (raiz)
- Data: 27/04/2026 -> 05/05/2026 (sem mudanca de conteudo — todos os
  caminhos da tabela "CAMINHOS DO SISTEMA" verificados, todas as
  references existem)

### app/agente/CLAUDE.md
- Header: 71/35.3K -> 72/35.4K LOC (data 27/04 -> 05/05)
- sdk/: 16 -> 17 arquivos (adicionado: `shutdown_state.py` — flag global
  atexit que suprime Sentry de `RuntimeError: cannot schedule new futures
  after shutdown` originado de race de SIGTERM no worker Teams; resolve
  PYTHON-FLASK-PP/PN/PM)
- Demais secoes (estrutura, regras R1-R8, hierarquia de timeouts, gotchas,
  pipeline SSE, memoria compartilhada) sem alteracao — todas verificadas
  contra codigo

### app/agente/services/CLAUDE.md
- Data: 2026-04-27 -> 2026-05-05 (14 arquivos / ~8.7K LOC mantidos —
  pattern_analyzer, insights, KG, etc. todos intactos)

### app/carteira/CLAUDE.md
- Data: 27/04 -> 05/05 (contagens 50/18.1K/13/22 corretas)

### app/carvia/CLAUDE.md
- Header: 102/62.7K -> 102/63.3K LOC (data 2026-04-27 -> 2026-05-05)
- 600 LOC adicionados sem novos arquivos (crescimento em arquivos existentes)
- routes/: 29 sub-rotas — confere com lista atual
- services/: 39 services em 6 sub-pacotes + 1 root — confere
- Sub-docs (CONFERENCIA, FINANCEIRO, FLUXOS_CRIACAO, etc.) verificados

### app/financeiro/CLAUDE.md
- Data: 27/04 -> 05/05 (77/45.1K corretos; 28 services root + 6 remessa_vortx;
  10 workers; 4 parsers — todos verificados)

### app/odoo/CLAUDE.md
- Data: 27/04 -> 05/05 (32 arquivos — 13 services + 12 utils + outros —
  e 18.7K LOC corretos)

### app/seguranca/CLAUDE.md
- Data: 27/04 -> 05/05 (14/2K/8 corretos — 5 routes + 5 services + models
  + __init__)

### app/teams/CLAUDE.md
- Data: 27/04 -> 05/05 (4 arquivos / ~2.5K LOC corretos:
  __init__ 5L + models 81L + bot_routes 482L + services 1895L = 2463 LOC)

## Observacoes

- **Nenhum caminho inexistente**: todas as references dev (`.claude/`),
  sub-docs CarVia, modulos vizinhos (`app/agente_lojas/`, `app/chat/`,
  `app/hora/`, `app/devolucao/`) verificados.
- agente/hooks/ continua so com __init__.py + README.md (hooks reais
  em sdk/hooks.py).
- agente/sdk/ ganhou 1 arquivo (`shutdown_state.py`) — outras secoes
  (config/, services/, tools/, utils/, workers/, prompts/) inalteradas.
- CarVia services/ permaneceu identico (39 services em 6 sub-pacotes).
- Financeiro models.py continua sendo o maior do projeto (~2.8K linhas).
- Odoo continua API-only (sem models proprios), maior consumidor por
  outros modulos.
