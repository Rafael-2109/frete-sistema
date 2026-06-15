# Historico de Atualizacoes — CLAUDE.md

> Cada entrada aponta para o relatorio detalhado da atualizacao.
> Formato: `[Data-N](arquivo.md) — Resumo (max 5 linhas)`

---

## Atualizacoes

- [2026-06-15-1](atualizacao-2026-06-15-1.md) — 9 auditados, 8 modificados (todos menos `seguranca`). Drift estrutural em 4 modulos desde 08/06: `agente` 104 -> 108 arquivos (~53.5K -> ~56.4K LOC) — Root 7 -> 8 (+`conversa.md`), sdk 24 -> 26 (+`turn_context_registry.py`, +`vincular_teams_fastpath.py`), services 23 -> 25 (+`adhoc_capture_service.py`, +`memory_format.py`), SDK_CHANGELOG ref 0.2.89 -> 0.2.101; `carvia` 107 -> 108 (~67.4K -> ~67.7K), 109 -> 110 templates (+`_pack_controls.html`); `financeiro` 80 -> 83 (~46.2K -> ~46.9K), routes 18 -> 19 + services 27 -> 28 (feature SRM Bank PDF->OFX: +`conversor_extrato_srm.py`, +`extrato_pdf_srm_service.py`); `odoo` 70 -> 72 (~42.5K -> ~43.4K), subpacote `estoque/` 19 -> 21 scripts (~19.9K -> ~20.8K, +`descoberta_industrializacao.py`, +`revaloracao.py`). `teams` doc:meta 06-11 -> 06-14 (body ja 14/06; LOC ~3.7K/5 conferem). `carteira` (50/18516/13) e raiz (SDK 0.2.101/CLI 2.1.177 bate requirements) conferem em conteudo — so data 08/06 -> 15/06. `seguranca` (14/1953/8, doc:meta 06/06) 100% consistente — intocado.

- [2026-06-08-1](atualizacao-2026-06-08-1.md) — 9 auditados, 8 modificados (todos menos seguranca). `agente` 96 -> 104 arquivos (~48.9K -> ~53.6K LOC), feature de observabilidade do canal Teams (F2): tree corrigido — Root 6 -> 7 (+`SUBSISTEMAS.md`), routes 20 -> 21 (+admin_teams.py), sdk 22 -> 23 (+baseline_fastpath.py), tools 14 -> 15 (+resolver_mcp_tool.py), services 20 -> 23 (+approval_inbox, +skill_effectiveness, +teams_observability), templates 5 -> 7 (+admin_teams.html, +memorias.html), secao Services 22/~13.0K -> 23/~13.8K. `agente/services` tree +teams_observability_service.py (346 LOC). Drifts organicos de LOC: `odoo/estoque` ~19.4K -> ~19.9K, `carvia` ~67.2K -> ~67.4K, `financeiro` ~46.1K -> ~46.2K, `teams` ~2.5K -> ~2.6K (services.py 1.997 -> 2.063). Raiz (SDK 0.2.89/CLI 2.1.162 bate requirements) e carteira (50/~18.5K/22 JS) conferem em conteudo. Datas: 7 doc:meta de frontmatter seguiam em 06-03 (bodies ja bumpados) — sincronizados; raiz e carteira tambem -> 08/06. `seguranca` (14/~2K/8 tpl) ja 100% consistente em 06/06 — mantido.

- [2026-06-01-1](atualizacao-2026-06-01-1.md) — 9 auditados, 9 modificados. Mudancas estruturais: `agente` 80 -> 96 arquivos (~41.9K -> ~48.9K LOC) com o flywheel/blueprint A3/A4 agora em main — +2 config (capability_registry, skills_whitelist), +5 sdk (context_enrichment, plan_state, plan_triage, sticky_session, verifiers), +1 tool (ontology_query_tool), +5 workers (background_jobs, eval_runner, plan_verifier, step_judge, triage_shadow); `agente/services` 17 -> 20 (+directive_promotion A4, +eval_gate A3, +ontology_bootstrap). `odoo` 63 -> 70 arquivos (~28.8K -> ~41.9K LOC), subpacote `estoque/` 13 -> 19 (~6.7K -> ~19.4K) com Skills 7/8 (escrituracao + faturamento) + orchestrator inventario_pipeline + util novo classificacao_produto (12 -> 13 utils). Raiz: Claude Agent SDK 0.1.80 -> 0.2.87 (CLI 2.1.138 -> 2.1.150). CarVia +0.3K LOC organico. Carteira/financeiro/seguranca/teams sem variacao estrutural — apenas data 25/05 -> 01/06.

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
