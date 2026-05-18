# Historico de Atualizacoes — References

> Cada entrada aponta para o relatorio detalhado da atualizacao.
> Formato: `[Data-N](arquivo.md) — Resumo (max 5 linhas)`

---

## Atualizacoes

- [2026-05-18-1](atualizacao-2026-05-18-1.md) — 39 arquivos revisados em profundidade (20 P0 + 10 P1 + 9 P2). **12 arquivos corrigidos em 17+ alteracoes** (2 sessoes consecutivas), decorrentes do bump SDK 2026-05-16 (`claude-agent-sdk` 0.1.80 -> 0.2.82 cosmetico, CLI 2.1.138 -> 2.1.142), novo subagent `auditor-sped-ecd` (contagem 14 -> 15 totais; 7 -> 8 xhigh) + 4 skills SPED ECD novas (`parseando-sped-ecd`, `auditando-sped-vs-manual`, `auditando-sped-contabil`, `comparando-sped-ground-truth` — contagem 36 -> 41), drift de 7 linhas em listener line numbers de Separacao, picking_type LF (16->19) tambem corrigido no rodape de IDS_FIXOS, header GOTCHAS.md (Marco/2026 -> 18/05/2026), e line ref memory_consolidator.py:49-52 -> :62-65. Atualizados: `BEST_PRACTICES_2026.md`, `MCP_CAPABILITIES_2026.md`, `AGENT_DESIGN_GUIDE.md`, `AGENT_TEMPLATES.md`, `STUDY_PROMPT_ENGINEERING_2026.md`, `ROUTING_SKILLS.md`, `INDEX.md` (+ mapping SPED), `SUBAGENT_RELIABILITY.md`, `MEMORY_PROTOCOL.md`, `modelos/REGRAS_CARTEIRA_SEPARACAO.md`, `odoo/IDS_FIXOS.md` (rodape), `odoo/GOTCHAS.md` (header). Tolerancias (10%/0%), IDs Odoo (FB=1/SC=3/CD=4/LF=5), regras de negocio TODOS conferem com codigo. Zero caminhos quebrados. Pendencias historicas: IDS_FIXOS product_tmpl_id ~34~ (requer MCP Odoo) + revisao trimestral STUDY (gatilho SDK>=0.2.0 atingido — proxima 2026-07).
- [2026-05-11-1](atualizacao-2026-05-11-1.md) — 39 arquivos revisados em profundidade (20 P0 + 10 P1 + 9 P2). 6 arquivos corrigidos em 8 alteracoes, todas decorrentes dos bumps SDK de 2026-05-09 (`claude-agent-sdk` 0.1.66 -> 0.1.80, `anthropic` 0.84.0 -> 0.98.1) e do novo subagent `gestor-motos-assai` (commit `450b4e28`, contagem 13 -> 14). Atualizados: `BEST_PRACTICES_2026.md`, `MCP_CAPABILITIES_2026.md`, `AGENT_DESIGN_GUIDE.md`, `AGENT_TEMPLATES.md`, `STUDY_PROMPT_ENGINEERING_2026.md`, `INDEX.md`. system_prompt v4.3.2 -> v4.3.3. Listeners, tolerancias, IDs Odoo e regras de negocio TODOS conferem com codigo. Zero caminhos quebrados. Pendencia historica permanece: IDS_FIXOS product_tmpl_id ~34~ requer MCP Odoo.
- [2026-05-05-1](atualizacao-2026-05-05-1.md) — 39 arquivos revisados em profundidade (20 P0 + 10 P1 + 9 P2). 3 divergencias factuais corrigidas, todas relacionadas a contagem "12 subagents" agora desatualizada apos introducao do `orientador-loja` (Agente Lojas HORA, commit 40fcbeb9). AGENT_TEMPLATES e AGENT_DESIGN_GUIDE atualizados para refletir 13 subagents (12 Nacom Goya + 1 orientador-loja). SDK 0.1.66, system_prompt v4.3.2, listener line numbers, IDs Odoo e tolerancias TODOS conferem com codigo. Zero caminhos quebrados. Pendencia historica permanece: IDS_FIXOS product_tmpl_id ~34~ requer MCP Odoo.
- [2026-04-27-1](atualizacao-2026-04-27-1.md) — 30 arquivos revisados, 5 divergencias factuais identificadas em P0 (SDK version 0.1.63->0.1.66 em BEST_PRACTICES_2026 e MCP_CAPABILITIES_2026, MEMORY_PROTOCOL.md linha :173->:271, ROUTING_SKILLS.md 25->30 skills HORA, STUDY_PROMPT_ENGINEERING_2026 SDK + system_prompt v4.3.2). Zero caminhos quebrados. Pendencia herdada do 2026-04-20: IDS_FIXOS.md product_tmpl_id ~34~ requer MCP Odoo.
- [2026-04-20-1](atualizacao-2026-04-20-1.md) — Auditoria de references. SDK version drift, paths, exemplos.
- [2026-04-06-1](atualizacao-2026-04-06-1.md) — 30 arquivos revisados, 6 divergencias encontradas (nao corrigidas — permissao). SDK version, caminhos, exemplos.
- [2026-03-28-1](atualizacao-2026-03-28-1.md) — Primeira auditoria. 3 arquivos corrigidos: datetime.utcnow em exemplos Odoo, Sentry status, caminho CSS. Zero caminhos quebrados.

<!-- Template para novas entradas:
- [YYYY-MM-DD-N](atualizacao-YYYY-MM-DD-N.md) — Resumo do que foi feito
-->
