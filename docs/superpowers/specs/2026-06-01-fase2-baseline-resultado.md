# Fase 2 — Resultado do baseline (golden set) · Onda D / resolvedores

> 2026-06-01 · GATE Fase 2. Compara os 7 CLIs ANTIGOS (split intacta) vs as funcoes `_cli` do
> modulo `app.resolvedores`, no MESMO banco local. Ferramenta: `/tmp/baseline_resolvedores.py`.
> Termos reais usados: pedido `NP02190`, cliente `MERCADO PONTO CERTO`, transportadora `ACS E...`.

## Veredito: ZERO regressao, exceto a correcao intencional do bug de acento (cidade).

| Entidade | Casos | Chaves topo | `sucesso` | Conjunto de IDs | Conclusao |
|---|---|---|---|---|---|
| Produto | 6 | iguais | iguais | comum=todos · 0 só-antigo · 0 só-novo | **paridade perfeita** (delega `buscar_produtos_hibrido`) |
| Pedido | 2 | iguais | iguais | comum=todos | **paridade perfeita** |
| Grupo | 2 | iguais | iguais | 100/100 · 99/99 | **paridade perfeita** |
| UF | 2 | iguais | iguais | 100/100 | **paridade perfeita** |
| Cliente | 2 | iguais | iguais | 1/1 | **paridade perfeita** |
| Transportadora | 1 | iguais | iguais | 1/1 | **paridade perfeita** |
| Cidade | 6 | iguais (no mesmo estado) | DIFERE de proposito | novo ≥ antigo | **bug accent corrigido** |

### Detalhe da divergencia de cidade (INTENCIONAL — criterio de aceitacao)
- `itanhaem`/`peruibe`/`sao paulo` (carteira/entregas): split antiga retornava `sucesso=False`
  (`cidades_encontradas=[]`, com `erro`+`sugestao`) por accent-sensitivity. O `_cli` novo casa
  `Itanhaém`/`Peruíbe`/`São Paulo` (`sucesso=True`, `cidades_encontradas=[{cidade,uf}]`, `fonte`).
- `sao paulo` [entregas]: ambos achavam; novo encontra 2 variantes vs 1 (accent-insensitive amplia).
- A diferenca de chaves observada (`erro`/`sugestao` vs `fonte`) decorre de o resultado mudar de
  FALHA→SUCESSO; o **contrato de sucesso e o de falha sao identicos em chaves** entre antigo e novo.

### Notas
- Produto: o campo `modo` no JSON pode diferir em casos de não-encontrado (antigo: `texto (fallback)`;
  novo: o modo passado). Nenhum caso do golden set exibiu isso (todos acharam). É metadado informativo.
- `formatar_sugestao_pedido` (branch múltiplos) preserva um bug latente do monolito (`', '.join` de
  dicts) — port idêntico, fora do escopo de zero-regressão. Reportado para decisão do Rafael.

### Pytest da Fase 1
`tests/resolvedores/` — **82 passed**. Funções puras + contrato de borda + comportamento real
(accent provado, AND multi-termo, stemming, dedup ABREVIACOES via `is`).
