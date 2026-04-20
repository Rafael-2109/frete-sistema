# Atualizacao CLAUDE.md — 2026-04-20-1

**Data**: 2026-04-20  **Auditados**: 9/9  **Modificados**: 8

## Resumo
Auditoria dos 9 CLAUDE.md. Corrigidas contagens (7 desatualizados), estruturas
(agente ganhou sdk/routes/utils/workers; carvia services reorganizados em sub-pacotes)
e erro de unidade em financeiro/models.py (caracteres vs linhas).

## Alteracoes

### CLAUDE.md (raiz)
- Data: 13/04 -> 20/04

### app/agente/CLAUDE.md
- Header: 58/29.8K -> 67/33.3K LOC (data 15/04 -> 20/04)
- routes/: 15 -> 17 (admin_subagents, subagents)
- sdk/: 9 -> 14 (_sanitization, memory_injection_rules, pricing, session_archive, subagent_reader)
- services/: 13 -> 14 (_utils, improvement_suggester)
- Adicionado utils/ (pii_masker)
- Adicionado workers/ (subagent_validator)
- memory_mcp_tool: 11 ops v2.0 -> 12 ops v2.1

### app/agente/services/CLAUDE.md
- Header: ~8.5K -> ~8.6K LOC (13/04 -> 20/04)

### app/carteira/CLAUDE.md
- Header: 17.6K -> 18.1K LOC (13/04 -> 20/04)
- JS: 22 templates + 1 static (modal-relatorios)

### app/carvia/CLAUDE.md
- Header: 96/55.5K -> 99/60.3K LOC (15/04 -> 20/04)
- routes/: 22 -> 28 sub-rotas
- services/: "26+" -> 46 em 6 sub-pacotes
- workers/: 3 -> 4 (_ssw_helpers)
- Adicionado utils/, documentados 13 modulos no pacote models/

### app/financeiro/CLAUDE.md
- Header: 70/43.8K -> 77/45.1K LOC (30/03 -> 20/04)
- services/: + subpacote remessa_vortx/
- workers/: 8 -> 9 + utils.py
- models.py: "117K LOC" (chars) -> "~2.8K linhas"
- Adicionado models_comprovante, models_correcao_datas

### app/odoo/CLAUDE.md
- Data: 15/04 -> 20/04 (contagens ja corretas)

### app/seguranca/CLAUDE.md
- Data: 30/03 -> 20/04 (contagens ja corretas)

### app/teams/CLAUDE.md
- Data: 13/04 -> 20/04 (contagens ja corretas)

## Observacoes
- app/odoo/jobs/ continua vazio (scheduler em app/scheduler/).
- app/agente/hooks/ so tem __init__ + README; hooks reais em sdk/hooks.py.
- Todos os caminhos verificados; nenhum inexistente.
