# Atualizacao CLAUDE.md — 2026-04-27-1

**Data**: 2026-04-27  **Auditados**: 9/9  **Modificados**: 8

## Resumo
Auditoria dos 9 CLAUDE.md. Contagens recalculadas: agente cresceu (+4 arquivos
em routes/sdk/tools), carvia ganhou 3 arquivos (rota nf_transferencia, services
nf_transferencia + importacao_config + rateio_conciliacao_helper, utils
excel_export_helper + papeis_frete). Demais modulos sem variacao estrutural.

## Estado Atual (apos auditoria)

| Modulo | Arquivos | LOC | Templates |
|--------|----------|------|-----------|
| agente | 71 | ~35.3K | (web) |
| agente/services | 14 | ~8.7K | — |
| carteira | 50 | ~18.1K | 13 + 22 JS |
| carvia | 102 | ~62.7K | 103 |
| financeiro | 77 | ~45.1K | — |
| odoo | 32 | ~18.7K | — |
| seguranca | 14 | ~2K | 8 |
| teams | 4 | ~2.5K | — |

## Alteracoes por Arquivo

### CLAUDE.md (raiz)
- Sem alteracoes (data ja em 26/04/2026, indice consistente)

### app/agente/CLAUDE.md
- Header: 67/33.3K -> 71/35.3K LOC (data 26/04 -> 27/04)
- routes/: 17 -> 18 arquivos (adicionados: admin_session_store.py,
  user_preferences.py; removido _deprecated.py que nao existe mais)
- sdk/: 14 -> 16 arquivos (adicionados: model_router.py, session_store_adapter.py)
- tools/: 9 -> 10 arquivos (adicionado: teams_card_tool.py)
- Root: documentado SDK_CHANGELOG.md + ROLLBACK_SESSION_STORE.md (auto-merge linter)
- templates/: 2 -> 3 (admin_session_store.html — auto-merge linter)

### app/agente/services/CLAUDE.md
- Header: ~8.6K -> ~8.7K LOC (data 2026-04-20 -> 2026-04-27)

### app/carteira/CLAUDE.md
- Data: 20/04 -> 27/04 (contagens 50 arquivos / 18.1K LOC ja corretas)

### app/carvia/CLAUDE.md
- Header: 99/60.3K -> 102/62.7K LOC (data 2026-04-20 -> 2026-04-27)
- routes/: 28 -> 29 (adicionada nf_transferencia_routes)
- services/: "46 services" -> "39 services" + 1 root (contagem corrigida)
  - documentos/: 8 -> 9 (adicionado nf_transferencia_service.py)
  - financeiro/: 13 -> 14 (rateio_conciliacao_helper.py documentado)
  - parsers/: 6 -> 7 (importacao_config_service.py documentado)
  - pricing/: 7 listados -> 6 reais (corrigida tabela)
- utils/: 2 -> 4 (adicionados excel_export_helper.py, papeis_frete.py)

### app/financeiro/CLAUDE.md
- Data: 20/04 -> 27/04 (contagens 77 arquivos / 45.1K LOC ja corretas)

### app/odoo/CLAUDE.md
- Header: 18.6K -> 18.7K LOC (data 20/04 -> 27/04, arquivos 32 ja correto)

### app/seguranca/CLAUDE.md
- Data: 20/04 -> 27/04 (contagens 14/2K/8 ja corretas)

### app/teams/CLAUDE.md
- Header: ~2.3K -> ~2.5K LOC (data 20/04 -> 27/04, 4 arquivos ja correto)

## Observacoes

- **Nenhum caminho inexistente**: todos os referenciados (sub-docs CarVia,
  references .claude/, modulos, arquivos _deprecated.py removido) verificados.
- app/odoo/jobs/ continua vazio (jobs em app/scheduler/).
- app/agente/hooks/ continua so com __init__.py + README.md (hooks reais
  em sdk/hooks.py).
- Nenhuma migration nova relevante para auditoria estrutural.
- CarVia routes inclui nf_transferencia_routes.py introduzida com R18
  (NF Triangular, 2026-04-20). Documentacao da regra ja existia.
