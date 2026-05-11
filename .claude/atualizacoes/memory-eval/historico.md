# Historico de Atualizacoes — Memory Eval

> Cada entrada aponta para o relatorio detalhado da avaliacao de memorias em producao.
> Formato: `[Data-N](arquivo.md) — Resumo (max 5 linhas)`

---

## Atualizacoes

- [2026-05-11-1](atualizacao-2026-05-11-1.md) — Health 82/100 (-4, primeira queda da serie). 338 memorias (+21), 539 sessoes (+37, pico semanal 41), 23 usuarios. Cold 37 (estavel), **stale 60d 35 (+29, +483%)** — driver da queda. KG coverage 39.05% (-1.05pp, 6o ciclo de queda). Empresa explodiu 136 -> 163 (+27, +19.9%) — todas sem `reviewed_at`. 13 zero-efficacy (+2), padrao `learned/expertise_*` u1 com 5 ocorrencias (em aceleracao). 10 recomendacoes (R3 NOVA: auditar stale 60d, R5 6o ciclo sem revisao empresa).
- [2026-05-05-1](atualizacao-2026-05-05-1.md) — Health 86/100 (+1, NOVO RECORDE). 317 memorias (+20), 502 sessoes, 23 usuarios. Cold 37 (+5), stale 60d 6 (+1). KG coverage 40.1% (-1.3pp). 9 recomendacoes (R1, R2, R4 5o ciclo consecutivo). Eficacia media 0.641 (+4.6%, melhor da serie). Padrao `learned/expertise_*` u1 emergiu como ruido sistematico.
- [2026-04-27-1](atualizacao-2026-04-27-1.md) — Health 85/100 (+1). 297 memorias (+25), 461 sessoes, 22 usuarios. Cold 32 (estavel), stale 60d 5 (+3). KG coverage 41.4% (-2pp). 8 recomendacoes (R1 e R4 repetem 4 ciclos). Crescimento desacelerou de +38% para +9%.
- [2026-04-20-1](atualizacao-2026-04-20-1.md) — Health 84/100. 272 memorias.
- [2026-04-13-1](atualizacao-2026-04-13-1.md) — Health 83/100.
- [2026-04-06-1](atualizacao-2026-04-06-1.md) — Health 81/100. 128 memorias, 14 cold, 2 stale. 7 recomendacoes.

<!-- Template para novas entradas:
- [YYYY-MM-DD-N](atualizacao-YYYY-MM-DD-N.md) — Resumo do que foi feito
-->
