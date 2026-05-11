# Atualizacao CLAUDE.md — 2026-05-11-1

**Data**: 2026-05-11  **Auditados**: 9/9  **Modificados**: 9

## Resumo
Auditoria dos 9 CLAUDE.md. Mudanca estrutural unica: CarVia ganhou
`cte_complementar_service.py` (root) + `custo_entrega_autolink_service.py`
(financeiro), elevando services 39 -> 41 (financeiro 14 -> 15). Agente
cresceu 1.4K LOC (35.4K -> 36.8K) sem novos arquivos. CarVia cresceu
1.3K LOC (63.3K -> 64.6K). Demais modulos sem variacao estrutural —
apenas datas atualizadas.

## Estado Atual (apos auditoria)

| Modulo | Arquivos | LOC | Templates |
|--------|----------|------|-----------|
| agente | 72 | ~36.8K | 3 (web) |
| agente/services | 14 | ~8.9K | — |
| carteira | 50 | ~18.1K | 13 + 23 JS |
| carvia | 104 | ~64.6K | 107 |
| financeiro | 77 | ~45.1K | 27 |
| odoo | 32 | ~18.8K | — |
| seguranca | 14 | ~2.0K | 8 |
| teams | 4 | ~2.5K | — |

## Alteracoes por Arquivo

### CLAUDE.md (raiz)
- Data: 05/05/2026 -> 11/05/2026 (sem mudanca de conteudo — todos os
  caminhos da tabela "CAMINHOS DO SISTEMA" verificados, todas as
  references existem)

### app/agente/CLAUDE.md
- Header: 35.4K -> 36.8K LOC (data 09/05 -> 11/05)
- 72 arquivos inalterado (2 root + 18 routes + 5 config + 1 hooks +
  1 prompts + 17 sdk + 14 services + 10 tools + 2 utils + 2 workers)
- LOC subiu por crescimento em arquivos existentes
  (commit 8be2eb24 F1+F7+F8: cache miss alert, browser lazy, cost tracker DB)
- Estrutura SDK 17 arquivos confirmada (shutdown_state.py presente)

### app/agente/services/CLAUDE.md
- LOC: ~8.7K -> ~8.9K (8888 total — crescimento em pattern_analyzer +5,
  memory_consolidator +37, session_summarizer +65,
  suggestion_generator +38, tool_skill_mapper +17, intersession_briefing +2)
- 14 arquivos inalterados
- Data: 2026-05-05 -> 2026-05-11

### app/carteira/CLAUDE.md
- Data: 05/05 -> 11/05 (contagens 50/18.1K corretas)
- JS: 22 templates + 1 static = 23 (header ja diz "23 JS")
- 26 routes flat + carteira_simples (4) + programacao_em_lote (5) confirmados
- services: 5 files (4 services + __init__) confirmados
- utils: 4 files (3 utils + __init__) confirmados
- Templates: 13 HTML confirmados

### app/carvia/CLAUDE.md
- Header: 63.3K -> 64.6K LOC (data 2026-05-08 -> 2026-05-11)
- services 39 -> 41 services em 6 sub-pacotes + 2 root:
  - financeiro/ 14 -> 15 (+`custo_entrega_autolink_service.py` —
    auto-link CE por NF/operacao/transp+CNPJ em 3 niveis)
  - root: +`cte_complementar_service.py` (alem de
    `cte_complementar_persistencia.py`) — orquestrador do fluxo unico
    CTe Comp (criar_para_emissao_ssw, mutex por operacao)
- Inline "103 templates" -> "107 templates" (alinhado ao header)
- 104 arquivos inalterado (29 rotas + 41 services + 4 workers +
  4 utils + 13 models + __init__/forms)
- Origem das mudancas: commit 5e44b692 (5 May, "desacopla CE de
  CarviaFrete + unifica criacao de CTe Complementar")

### app/financeiro/CLAUDE.md
- Data: 05/05 -> 11/05 (77/45.1K corretos)
- 18 routes + 27 services root + 5 services remessa_vortx +
  8 workers + utils.py + 3 parsers + __init__/models/etc confirmados

### app/odoo/CLAUDE.md
- Header LOC: 18.7K -> 18.8K (18783 total)
- Data: 05/05 -> 11/05
- 32 arquivos inalterado (12 services + 11 utils + 1 routes_circuit_breaker +
  1 config + 1 routes/sincronizacao_integrada + __init__s)

### app/seguranca/CLAUDE.md
- Data: 05/05 -> 11/05 (14/2K/8 templates corretos —
  5 routes + 5 services + models + __init__ + dashboard + verificar_senha +
  configuracao + vulnerabilidades/listar+detalhe +
  varreduras/listar+detalhe + usuario/perfil_seguranca = 8 templates)

### app/teams/CLAUDE.md
- Data: 05/05 -> 11/05 (4 arquivos / 2463 LOC corretos:
  __init__ 5L + models 81L + bot_routes 482L + services 1895L)

## Observacoes

- **Nenhum caminho inexistente**: todas as references dev (`.claude/`),
  sub-docs CarVia (CONFERENCIA, FINANCEIRO, FLUXOS_CRIACAO, etc.),
  modulos vizinhos (`app/agente_lojas/`, `app/chat/`, `app/hora/`,
  `app/motos_assai/`, `app/devolucao/`) verificados.
- CarVia foi o unico modulo com adicao de arquivo desde 2026-05-05
  (commit 5e44b692 — 5 May noite). agente cresceu LOC sem novos arquivos.
- agente/hooks/ continua so com __init__.py + README.md (hooks reais
  em sdk/hooks.py).
- agente/sdk/ permaneceu com 17 arquivos.
- agente/CLAUDE.md ja havia sido atualizado parcialmente em 09/05
  (data) mas LOC estava desatualizado (35.4K em vez de 36.8K real).
- carvia/CLAUDE.md ja documentava 41 services corretamente — apenas
  o inline "103 templates" do bloco apresentando estrutura estava
  desalinhado com o header "107 templates".
