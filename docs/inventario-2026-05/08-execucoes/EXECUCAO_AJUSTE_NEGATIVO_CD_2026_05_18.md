# EXECUCAO — Ajuste negativo residual CD (2026-05-18 20:38-20:39)

**Script**: `scripts/inventario_2026_05/11_ajuste_negativo_cd.py`
**Origem**: planilha `AJUSTE SALDO CD.xlsx` (enviada pelo Rafael, 182 linhas)
**Log JSON**: `scripts/inventario_2026_05/auditoria/log_11_ajuste_cd_20260518_203925.json`
**Confirmado**: Rafael (AskUserQuestion, 2026-05-18 ~20:37)

## Resumo

| Metrica | Valor |
|---|---|
| Linhas processadas | 182 |
| Status `EXECUTADO` | 182 (100%) |
| Falhas | 0 |
| Produtos distintos | 68 |
| Lotes distintos | 182 |
| Quant_ids ajustados | range 42872 — 214984 |
| Soma absoluta ajustes | 0.005949 un (~6 milesimos) |
| Tempo total | 42s (28.9s puro Odoo I/O) |
| Tempo medio por ajuste | 158.7 ms |

## Como executou

Padrao identico ao `10_executar_emergenciais_fb.py` (E09/E10), reutilizando
`StockLotService.buscar_por_nome` (com fallback `=like` para o gotcha do
operator `=`):

1. `default_code` → `product.product.id` (active=True)
2. `(name, product, company=4)` → `stock.lot.id`
3. Filtro `(product, company=4, location=32, lot)` → `stock.quant`
4. `nova_qty = round(quantity + ajuste, 6)`
5. Guarda: `nova_qty < 0` ou `nova_qty < reserved_quantity` aborta a linha
6. `stock.quant.write({inventory_quantity: nova_qty})` + `action_apply_inventory`

Gera 1 `stock.move` por quant com origem **"Physical Inventory"**
(auditavel em Inventory > Reporting > Stock Moves, filtrar location_id=32).

## Por que ajuste puro (sem NF)

Todos os ajustes < 0.0001 un (residuos de arredondamento entre fontes externas
e os 6 decimais do Odoo). Em todos os 182 casos, `quantity == |ajuste|`, ou
seja: a operacao zera quants que ja estavam praticamente em zero. NF para
saldos dessa ordem nao se justifica (mesmo principio dos emergenciais FB).

## Validacao previa (DRY-RUN)

Rodada em 2026-05-18 20:34-20:35 antes de pedir confirmacao:
- 182/182 `DRY_RUN_OK` (zero falhas, zero reservas conflitantes)
- Confirmou que todos os quants existem em `location_id=32` (CD/Estoque)
- Log: `auditoria/log_11_ajuste_cd_20260518_203457.json`

## Reversao

Cada `action_apply_inventory` cria `stock.move` reversivel via novo inventory
adjustment com sinal oposto. Os `quant_id` afetados estao no log JSON
(campo `resultados[].quant_id`).

## Nao toca

- `ajuste_estoque_inventario` local (regra emergenciais FB E09/E10)
- Sync das movimentacoes Odoo trara o resultado pelo fluxo normal
