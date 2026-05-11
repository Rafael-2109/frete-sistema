# Historico de Atualizacoes — Tests

> Cada entrada aponta para o relatorio detalhado da execucao de testes.
> Formato: `[Data-N](arquivo.md) — Resumo (max 5 linhas)`

---

## Atualizacoes

- [2026-05-11-1](atualizacao-2026-05-11-1.md) — 946/1019 testes (92.84%), 265.46s. 47 falhas + 19 errors + 7 skipped + 20 nao coletados (`tests/skills/motos_assai/conftest.py` pytest 8.4 deprecation). Falhas: motos_assai (22, fixtures PDF/XLSX ausentes), hora (16 FAILED `modalidade_frete=9` invalido + 1 avaria + 19 ERROR state pollution suite-wide), custeio (6, migrations locais nao aplicadas), carvia (3, mock SSW reincidente + `listar_fretes_divergentes` ausente), agente/sdk (2, race async_event). Sem correlacao D4.
- [2026-05-05-1](atualizacao-2026-05-05-1.md) — 749/766 testes (97.78%), 96.13s. 15 falhas em `tests/hora/test_pedido_workflow.py` (coluna `modalidade_frete` ausente no DB local — migration `hora_21` nao aplicada) + 2 falhas reincidentes em `tests/carvia/test_a3_ctrnc_cte_comp.py` (mock SSW bypass, mesmo bug de 2026-04-27). Sem correlacao D4.
- [2026-04-27-1](atualizacao-2026-04-27-1.md) — 735/737 testes (99.73%), 102.19s. 2 falhas em `tests/carvia/test_a3_ctrnc_cte_comp.py::TestCasoBVerificacao` por patch path incorreto de `resolver_ctrc_ssw` (worker chama SSW real em vez de mock). Sem correlacao D4.
- [2026-04-20-1](atualizacao-2026-04-20-1.md) — 569/569 testes OK (100%), 41.20s. +281 testes desde 2026-04-06. Sem correlacao D4.
- [2026-04-06-1](atualizacao-2026-04-06-1.md) — 288/288 testes OK (100%), 14.68s. Nenhuma falha.

<!-- Template para novas entradas:
- [YYYY-MM-DD-N](atualizacao-YYYY-MM-DD-N.md) — Resumo do que foi feito
-->
