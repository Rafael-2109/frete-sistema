<!-- doc:meta
tipo: scratch
camada: L3
sot_de: —
hub: docs/inventario-2026-05/08-execucoes/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# EXECUCAO — Ajuste positivo CD (2026-05-18 21:06)

**Script**: `scripts/inventario_2026_05/12_ajuste_positivo_cd.py`
**Origem**: planilha `AJUSTE SALDO CD.xlsx` (versao 2, 35 linhas, todos AJUSTE>0)
**Log JSON**: `scripts/inventario_2026_05/auditoria/log_12_ajuste_pos_cd_20260518_210639.json`
**Confirmado**: Rafael (AskUserQuestion 2x — escopo + destrave classifier)

## Resumo

| Metrica | Valor |
|---|---|
| Linhas processadas | 35 |
| Status `EXECUTADO` | 34 (97.1%) |
| Status `FALHA_PRODUCT` | 1 (linha 15) |
| Lotes criados | 1 (`P-15/05` para cod=4510161) |
| Lotes reutilizados | 33 |
| Quants criados (novos) | 6 |
| Quants atualizados | 28 |
| Soma absoluta ajustes | +130.999450 un |
| Tempo execucao | ~24s (media 700 ms/ajuste) |

## Item 15 — `FALHA_PRODUCT` (skip autorizado)

`cod=4320161 lote='051/26' ajuste=+5.0` — `default_code` nao existe no Odoo (nem ativo nem inativo).

Investigacao:
- `4320162` (Azeitona Verde Fatiada) existe mas nao tem lote `051/26` (so `050/26` e `057/26`)
- Cod mais provavel de ser typo: `4520161` (Cogumelo Inteiro Campo Belo) — esse SIM tem lote `051/26` (id=57167) em CD/Estoque

Rafael autorizou skip (24 OK + pular item 15). Re-rodar isolado quando planilha
for corrigida:

```bash
python scripts/inventario_2026_05/12_ajuste_positivo_cd.py --confirmar \
    --apenas-linhas 15
```

## Como executou

Mesmo padrao do script 11 (negativo), mas com criacao de lote/quant quando
nao existem:

1. `default_code` → `product.product.id` (active=True)
2. `(name, product, company=4)` → `stock.lot.id` (cria se nao existe via
   `StockLotService.criar_se_nao_existe`)
3. Filtro `(product, company=4, location=32, lot)` → `stock.quant`
4. Se quant existe: `write({inventory_quantity: qty_atual + ajuste})` +
   `action_apply_inventory`
5. Se quant nao existe: `create({product, company, location, lot,
   inventory_quantity: ajuste})` + `action_apply_inventory`

Gera 1 `stock.move` por quant com origem "Physical Inventory" (auditavel em
Inventory > Reporting > Stock Moves, filtrar location_id=32 + data hoje).

## Reversao

`quant_id` de cada ajuste no log JSON (`resultados[].quant_id`). Reversao via
novo inventory adjustment com sinal oposto. Lote `P-15/05` (cod=4510161,
recem-criado) so pode ser desativado se nenhuma outra movimentacao usar.

## Decisoes operacionais

- Nao toca `ajuste_estoque_inventario` local (regra emergenciais FB)
- Sync das movimentacoes Odoo trara o resultado pelo fluxo normal
- Item 15 cou rejected — Rafael corrige planilha ou ignora
