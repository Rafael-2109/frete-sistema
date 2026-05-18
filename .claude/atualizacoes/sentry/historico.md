# Historico de Atualizacoes — Sentry

> Cada entrada aponta para o relatorio detalhado da atualizacao.
> Formato: `[Data-N](arquivo.md) — Resumo (max 5 linhas)`

---

## Atualizacoes

- [2026-05-18-1](atualizacao-2026-05-18-1.md) — Triagem 57 issues. 0 fixes (todas fora escopo). 50+ Odoo XML-RPC 500 (`odoo.nacomgoya.com.br/xmlrpc/2/common` instavel — infra externa CIEL IT, V5/V6 regressed com 216+172 eventos). 2 scripts ad-hoc Render Shell (VC backfill chassi VARCHAR(30), VD FK violation `assai_pedido_venda` x `assai_separacao`). 1 N+1 real porem refactor (S9 `tabelas.listar_todas_tabelas` template chama `status_cor`+`status_texto`->`status_tabela` queries por linha). 2 Odoo Fault sem eventos em production (P5/P6).
- [2026-05-11-1](atualizacao-2026-05-11-1.md) — Triagem 6 issues. 2 fixes novos: RN (AttributeError `saldo_estoque_pedido` em carteira.obter_estoque_pedido apos migration remover colunas) + RK (TypeError Decimal*float em custeio.listar_definicao no calculo BOM recursivo). 4 fora escopo: RM (env=development), RP (ad-hoc script Render Shell), RJ (gateway OpenClaw indisponivel), 2A (validacao de negocio NF nao encontrada).
- [2026-05-05-1](atualizacao-2026-05-05-1.md) — Triagem 32 issues. 1 fix novo (Q6 guarda is_authenticated em hora/base.html) + 5 ja-fixed em commits 2bbfcf23/b6c17646 (QG/QM/QH/QF/QC backfill TagPlus DetachedInstance + UniqueViolation). 26 fora escopo (3 fatura 543449 Odoo, 9 Odoo XML-RPC, 2 tmp scripts, 5 transientes, 4 Teams/MCP/agente, 3 Playwright).
- [2026-04-27-1](atualizacao-2026-04-27-1.md) — Triagem 20 issues. 2 fixes (PYTHON-FLASK-PF cast Integer->String, PYTHON-FLASK-P3 ja resolvido em f1c04813). 18 fora escopo (4 migrations, 6 Odoo XML-RPC, 3 negocio, 3 shutdown race, 2 perf).
- [2026-04-06-1](atualizacao-2026-04-06-1.md) — Triagem completa. 0 erros, 2 alertas performance (fora escopo).

<!-- Template para novas entradas:
- [YYYY-MM-DD-N](atualizacao-YYYY-MM-DD-N.md) — Resumo do que foi feito
-->
