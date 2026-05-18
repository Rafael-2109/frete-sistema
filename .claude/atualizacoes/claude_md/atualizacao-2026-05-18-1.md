# Atualizacao CLAUDE.md — 2026-05-18-1

**Data**: 2026-05-18  **Auditados**: 9/9  **Modificados**: 8

## Resumo
Auditoria dos 9 CLAUDE.md. Mudancas estruturais notaveis: **odoo** ganhou 6
services novos (inventario_pipeline + stock_picking/lot + stock_internal_transfer
+ pre_etapa_estoque + indisponibilizacao_estoque) elevando services 12 -> 18 e
LOC 18.8K -> 22.2K. **agente** ganhou rotas (admin_metrics, artifacts), tools
(artifact_tool, sql_session_context) e workers (artifact_worker) — 72 -> 80
arquivos. **agente/services** subiu 14 -> 17 (artifact_service, metrics_dashboard,
sql_evaluator_falses). Carteira so LOC; CarVia LOC + 1 template; Financeiro
documentou 3 arquivos root + corrigiu contagem remessa_vortx (5 -> 8). Seguranca
e Teams sem mudancas estruturais — apenas datas.

## Estado Atual (apos auditoria)

| Modulo | Arquivos .py | LOC | Templates |
|--------|--------------|------|-----------|
| agente | 80 | ~41.8K | 5 (web) |
| agente/services | 17 | ~10.5K | — |
| carteira | 50 | ~18.4K | 13 + 22 JS |
| carvia | 104 | ~66.1K | 108 |
| financeiro | 80 | ~46.1K | 29 |
| odoo | 44 | ~22.2K | — |
| seguranca | 14 | ~2.0K | 8 |
| teams | 4 | ~2.5K | — |

## Alteracoes por Arquivo

### CLAUDE.md (raiz)
- Data: 13/05/2026 -> 18/05/2026
- Todos os caminhos da tabela "CAMINHOS DO SISTEMA" verificados; todas as
  references citadas (`.claude/`, design/UI, modelos, odoo, ssw) verificadas
  existem. Nenhuma mudanca de conteudo.

### app/agente/CLAUDE.md
- Header: 36.8K LOC / 72 arquivos -> 41.8K / 80 (data 11/05 -> 18/05)
- **routes/** 18 -> 20: adicionados `admin_metrics.py` (Fase A telemetria
  subagent, 10 endpoints) e `artifacts.py` (5 rotas: page/bundle/status +
  API list + by-uuid/url)
- **tools/** 10 -> 12: adicionados `artifact_tool.py` (build_artifact MCP
  Enhanced v1.0) e `sql_session_context.py` (helpers SQL por sessao)
- **workers/** 2 -> 3: adicionado `artifact_worker.py` (build_artifact_job,
  Vite+React+TS+Tailwind, fila `artifacts`)
- **services/** 14 -> 17: adicionados `artifact_service.py`, `metrics_dashboard_service.py`,
  `sql_evaluator_falses_service.py` (ver tambem services/CLAUDE.md)
- **templates/agente/** 3 -> 5: `admin_metrics.html` (Chart.js 3.9.1) e
  `artifact.html` (render bundle em iframe sandboxed)

### app/agente/services/CLAUDE.md
- Header: 8.9K LOC / 14 arquivos -> 10.5K / 17 (data 2026-05-11 -> 2026-05-18)
- Adicionados 3 services na arvore com LOC reais:
  - `artifact_service.py` (491 LOC) — rate limit pipeline MULTI/EXEC + spec
    validation + S3 upload
  - `metrics_dashboard_service.py` (690 LOC) — dashboard Fase A1+A3 (KPIs
    per-agent, anomaly detection)
  - `sql_evaluator_falses_service.py` (387 LOC) — detector de falsos negativos
    no SQL evaluator
- LOC atualizados: pattern_analyzer 2216 -> 2247, session_summarizer 475 -> 480,
  intersession_briefing 571 -> 576

### app/carteira/CLAUDE.md
- Header: 18.1K -> 18.4K LOC (data 11/05 -> 18/05)
- Header "23 JS (22 templates + 1 static)" -> "22 JS (21 templates + 1 static)"
  — arquivo `interface_enhancements.js` no root templates/carteira/ nao existe;
  contagem real e 21 em `js/` (inclui subdirs `utils/` e `workspace/`) + 1 em
  `static/`. Corpo (linha 29) corrigido tambem.
- 50 arquivos / 13 HTML / contagens batem.

### app/carvia/CLAUDE.md
- Header: 64.6K -> 66.1K LOC, 107 -> 108 templates (data 2026-05-11 -> 2026-05-18)
- "107 templates" inline no bloco Estrutura tambem corrigido para 108.
- 104 .py inalterado (29 routes + 41 services em 6 sub-pacotes + 2 root + 4
  workers + 4 utils + 13 models + __init__/forms). Sem novos arquivos
  estruturais desde 11/05 — crescimento foi puramente LOC + 1 template.

### app/financeiro/CLAUDE.md
- Header: 77 / 45.1K -> 80 / 46.1K (data 11/05 -> 18/05)
- Arvore Estrutura ganhou linhas para arquivos root nao documentados antes:
  `forms.py`, `leitor_comprovantes_sicoob.py`, `remover_pagamentos_*.py`.
- Correcao: `services/remessa_vortx/` documentado como "5 services", real
  e 8 (cnab_generator, cnab_parser, conversor_externo, dac_calculator,
  layout_vortx, nosso_numero_service, odoo_injector, validador).

### app/odoo/CLAUDE.md
- Header: 32 / 18.8K -> 44 / 22.2K (data 11/05 -> 18/05)
- **services/** 12 -> 18: adicionados 6 services do inventario 2026-05 e
  primitivos stock:
  - `inventario_pipeline_service.py` — orquestrador F0-F5 ondas LF/FB/CD
  - `stock_picking_service.py` — operacoes stock.picking (criar/validar/cancelar)
  - `stock_lot_service.py` — operacoes stock.lot (criar/buscar com fallback like)
  - `stock_internal_transfer_service.py` — transf internas FB <-> CD
  - `pre_etapa_estoque_service.py` — pre-etapa CD/FB (D007, minimizar NF)
  - `indisponibilizacao_estoque_service.py` — bloqueio temporario de lotes
- utils/config/routes/jobs/docs sem mudanca estrutural — apenas crescimento LOC.

### app/seguranca/CLAUDE.md
- Data: 11/05 -> 18/05 (14 / 1953 LOC / 8 templates corretos)

### app/teams/CLAUDE.md
- Data: 11/05 -> 18/05 (4 / 2487 LOC corretos)

## Observacoes

- **Nenhum caminho inexistente**: todas as references dev (`.claude/`),
  sub-docs CarVia (CONFERENCIA, FINANCEIRO, FLUXOS_CRIACAO, etc.), modulos
  vizinhos (`app/agente_lojas/`, `app/chat/`, `app/hora/`, `app/motos_assai/`,
  `app/devolucao/`, `app/whatsapp/`, `app/fretes/`, `app/relatorios_fiscais/`,
  `app/seguranca/`) verificados.
- **odoo** foi o modulo com maior delta estrutural desde 11/05 — 6 services
  novos relacionados ao Inventario 2026-05 (commits piloto LF + bulk onda 1)
  e a primitives stock para suportar transferencias internas e pre-etapas
  FB/CD documentadas em `docs/inventario-2026-05/00-decisoes/D007*`.
- **agente** ganhou estrutura completa de artifacts (route + tool + worker +
  service + template + page) que ja foi descrita no corpo do CLAUDE.md na
  ultima sessao mas nao tinha sido propagada para a arvore "Estrutura"
  ASCII no topo do arquivo.
- **agente/services** finalmente reflete os 3 services adicionados nas
  ultimas 2 sessoes (artifact + metrics dashboard + sql evaluator falses).
- Nenhum CLAUDE.md de modulo periferico foi tocado (apenas os 9 da
  auditoria). Modulos `app/recebimento`, `app/portal`, `app/pedidos`,
  `app/pallet`, `app/producao`, `app/motochefe` continuam sem CLAUDE.md
  (planejados em `~/.claude/CLAUDE.md`).
