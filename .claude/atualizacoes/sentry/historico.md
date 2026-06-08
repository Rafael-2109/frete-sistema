# Historico de Atualizacoes — Sentry

> Cada entrada aponta para o relatorio detalhado da atualizacao.
> Formato: `[Data-N](arquivo.md) — Resumo (max 5 linhas)`

---

## Atualizacoes

- [2026-06-08-1](atualizacao-2026-06-08-1.md) — Triagem 50 issues. **0 fixes de codigo** (working tree intacto por esta triagem). 1 bug tecnico real (XN, 270ev — `_criar_itens_da_api` desempacotava 4 valores de `_resolver_preco_tabela` 5-tupla em `backfill_service.py:1476`) JA CORRIGIDO em `main` por `2c093f44b` (2026-06-03 17:30); os 270 eventos rodaram no release `418a717d` (17:06) ANTERIOR ao fix → ruido pre-deploy. XN ja estava `resolved` no Sentry (comentario de rastreio adicionado; guard AST `test_resolver_preco_tabela_arity.py` passa). 49 fora escopo: 46 Odoo XML-RPC 502/auth (infra CIEL IT), 2 scripts ad-hoc `python -c` Render Shell (WK/WJ — campo `sequence_id` inexistente em `account.journal`), 1 ja-resolved (XA — `[ONTOLOGY_QUERY]` transacao invalida; log nao-crash HTTP 200; rollback defensivo ja presente no working tree, NAO desta triagem).
- [2026-06-01-1](atualizacao-2026-06-01-1.md) — Triagem 23 issues. 3 resolved: WB+WD (`OdooConnection.search_count`/`search(offset)` em `inventario/services/movimentacoes_odoo_service.py` — ja-corrigidas no commit `4477faa4d` 27/05, eventos pre-fix) + W4 (1 fix NOVO: import-path `app.carvia.services.cotacao_service` → `...pricing.cotacao_service` no script de skill `cotando_subcontrato_carvia.py`, 3 linhas; latente `listar_opcoes_transportadora` inexistente documentado fora de escopo). 20 fora escopo: 11 Odoo XML-RPC 502/Fault (infra CIEL IT), 5 scripts ad-hoc `__main__`/`<stdin>` (W6/X2/X3/WZ/W9), 1 MEMORY_MCP EG (ja mitigado por rollback defensivo + transiente 3ev/48d), 1 tessdata OCR (WA), 2 log negocio/dado (W7/W5). 1 arquivo modificado.
- [2026-05-25-1](atualizacao-2026-05-25-1.md) — Triagem 1 issue. 1 fix: PYTHON-FLASK-M5 (TEXT_TO_SQL UndefinedColumn em campos com alias `s.qtd_saldo_produto_pedido`/`fp.qtd_faturada`). `SQLDeterministicValidator._check_qualified_fields` agora resolve aliases via novo `_extract_alias_map` parseando `FROM/JOIN tabela [AS] alias`. Fecha lacuna do Check 3 (so cobria tabela unica sem alias). Suite inline 6 casos OK. Backlog zerado (57->0 em 7d, XML-RPC Odoo auto-resolveu).
- [2026-05-18-1](atualizacao-2026-05-18-1.md) — Triagem 57 issues. 0 fixes (todas fora escopo). 50+ Odoo XML-RPC 500 (`odoo.nacomgoya.com.br/xmlrpc/2/common` instavel — infra externa CIEL IT, V5/V6 regressed com 216+172 eventos). 2 scripts ad-hoc Render Shell (VC backfill chassi VARCHAR(30), VD FK violation `assai_pedido_venda` x `assai_separacao`). 1 N+1 real porem refactor (S9 `tabelas.listar_todas_tabelas` template chama `status_cor`+`status_texto`->`status_tabela` queries por linha). 2 Odoo Fault sem eventos em production (P5/P6).
- [2026-05-11-1](atualizacao-2026-05-11-1.md) — Triagem 6 issues. 2 fixes novos: RN (AttributeError `saldo_estoque_pedido` em carteira.obter_estoque_pedido apos migration remover colunas) + RK (TypeError Decimal*float em custeio.listar_definicao no calculo BOM recursivo). 4 fora escopo: RM (env=development), RP (ad-hoc script Render Shell), RJ (gateway OpenClaw indisponivel), 2A (validacao de negocio NF nao encontrada).
- [2026-05-05-1](atualizacao-2026-05-05-1.md) — Triagem 32 issues. 1 fix novo (Q6 guarda is_authenticated em hora/base.html) + 5 ja-fixed em commits 2bbfcf23/b6c17646 (QG/QM/QH/QF/QC backfill TagPlus DetachedInstance + UniqueViolation). 26 fora escopo (3 fatura 543449 Odoo, 9 Odoo XML-RPC, 2 tmp scripts, 5 transientes, 4 Teams/MCP/agente, 3 Playwright).
- [2026-04-27-1](atualizacao-2026-04-27-1.md) — Triagem 20 issues. 2 fixes (PYTHON-FLASK-PF cast Integer->String, PYTHON-FLASK-P3 ja resolvido em f1c04813). 18 fora escopo (4 migrations, 6 Odoo XML-RPC, 3 negocio, 3 shutdown race, 2 perf).
- [2026-04-06-1](atualizacao-2026-04-06-1.md) — Triagem completa. 0 erros, 2 alertas performance (fora escopo).

<!-- Template para novas entradas:
- [YYYY-MM-DD-N](atualizacao-YYYY-MM-DD-N.md) — Resumo do que foi feito
-->
