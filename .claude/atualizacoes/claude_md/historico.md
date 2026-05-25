# Historico de Atualizacoes — CLAUDE.md

> Cada entrada aponta para o relatorio detalhado da atualizacao.
> Formato: `[Data-N](arquivo.md) — Resumo (max 5 linhas)`

---

## Atualizacoes

- [2026-05-25-1](atualizacao-2026-05-25-1.md) — 9 auditados, 9 modificados. Mudanca maior: odoo ganhou subpacote `estoque/` (13 arquivos / ~6.7K LOC, scripts atomicos das Skills 1/2/2.4/4/5/6/9 + orchestrators + fluxos) + 2 services novos (stock_mo, transferencia_saldo_codigo) + 2 constants (picking_types, ids_diversos) -> 46 -> 63 arquivos, 23K -> 28.8K LOC. CarVia: feature anexos polimorficos (+1 route anexo, +1 model anexos, +1 service documentos/anexo) -> 104 -> 107 arquivos, 108 -> 109 templates. Carteira: documentado alert_system.py no root (existia mas faltava). Demais: apenas datas + LOC.

- [2026-05-18-1](atualizacao-2026-05-18-1.md) — 9 auditados, 8 modificados. Mudancas estruturais: odoo +6 services inventario 2026-05 (12 -> 18, 18.8K -> 22.2K LOC); agente +2 routes (admin_metrics + artifacts), +2 tools (artifact_tool + sql_session_context), +1 worker (artifact_worker), +2 templates (admin_metrics + artifact) -> 72 -> 80 arquivos; agente/services +3 (artifact + metrics_dashboard + sql_evaluator_falses, 14 -> 17). Financeiro: arvore root corrigida + remessa_vortx (5 -> 8 services). Carteira: JS corrigido (23 -> 22 — interface_enhancements.js nao existe). CarVia: LOC + 1 template (107 -> 108). Datas em todos atualizadas.

- [2026-05-11-1](atualizacao-2026-05-11-1.md) — 9 auditados, 9 modificados. Sem novos arquivos estruturais. Crescimento organico: agente +1.4K LOC (35.4K -> 36.8K), carvia +1.3K (63.3K -> 64.6K). CarVia services: financeiro/ +1 (custo_entrega_autolink), root +1 (cte_complementar_service) -> 41 services total. Carteira: contagem JS corrigida (22 -> 23, inclui interface_enhancements.js no root de templates/carteira/). Datas atualizadas.

- [2026-05-05-1](atualizacao-2026-05-05-1.md) — 9 auditados, 9 modificados (datas). Unica mudanca estrutural: agente/sdk/ +1 arquivo (`shutdown_state.py` — flag atexit suprime Sentry de RuntimeError shutdown no worker Teams). CarVia subiu 600 LOC sem novos arquivos (62.7K -> 63.3K). Demais modulos sem variacao estrutural.

- [2026-04-27-1](atualizacao-2026-04-27-1.md) — 9 auditados, 8 modificados. Agente +4 arquivos (admin_session_store, user_preferences, model_router, session_store_adapter, teams_card_tool). CarVia +3 arquivos (nf_transferencia route+service, importacao_config, rateio_conciliacao_helper, excel_export_helper, papeis_frete). Datas atualizadas.

- [2026-04-20-1](atualizacao-2026-04-20-1.md) — 9 auditados, 8 modificados. Corrigidos contagens/estruturas em agente (+5 sdk, +utils, +workers), carvia (services em 6 sub-pacotes), financeiro (models.py erro chars->linhas). Datas de todos atualizadas.

- [2026-04-06-1](atualizacao-2026-04-06-1.md) — 9 auditados, 7 modificados (contagens LOC/arquivos). Modulos: raiz, agente, carteira, carvia, odoo, teams.

- [2026-03-28-1](atualizacao-2026-03-28-1.md) — Primeira auditoria. 7/9 CLAUDE.md atualizados (LOC + contagens).

<!-- Template para novas entradas:
- [YYYY-MM-DD-N](atualizacao-YYYY-MM-DD-N.md) — Resumo do que foi feito
-->
