<!-- doc:meta
tipo: scratch
camada: L3
sot_de: —
hub: docs/inventario-2026-05/08-execucoes/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# EXECUCAO — Transferencia MIGRACAO -> lotes canonicos FB (2026-05-18 22:59-23:02)

**Script**: `scripts/inventario_2026_05/13_transferencia_migracao_fb.py`
**Origem**: planilha `TRANSF DE MIGRAÇÃO.xlsx` (446 linhas)
**Log JSON**: `scripts/inventario_2026_05/auditoria/log_13_transf_migr_fb_20260518_230252.json`
**Decisao**: Cenario 1 (Rafael, AskUserQuestion) — executar so as linhas com
saldo livre em FB/Estoque (loc=8), sem mexer em Pre-Producao nem cancelar pickings.

## Resumo

| Metrica | Valor |
|---|---|
| Linhas processadas | 446 |
| `EXECUTADO` | **170 (38.1%)** |
| `FALHA_SEM_SALDO` | 238 (53.4%) |
| `FALHA_LOTE_ORIGEM` | 38 (8.5%) |
| Lotes destino criados | 110 |
| Lotes destino reutilizados | 60 |
| **Soma transferida** | **1.553.336 un** |
| Tempo total | 220s (~3.7 min) |
| Media por transferencia | 1.297 ms |

## Diferenca vs DRY-RUN (186 esperado vs 170 real)

16 transferencias passaram no DRY-RUN mas falharam na execucao por **consumo
cumulativo do mesmo produto**: a planilha pediu mais total de cada produto
do que ele tinha em saldo livre. As primeiras transferencias consumiram
saldo, e as ultimas estouraram. Exemplo (cod=301100014):

- Saldo total MIGRACAO no inicio: 37.639 un
- Total pedido em 12 destinos: ~66.000 un
- Apos 7 transferencias consumiu 37.611 → saldo apos = 28 un
- Restantes 5 destinos falharam (`disponivel=-20.232`, ja_consumido > saldo)

## Padrao de execucao

`StockInternalTransferService.transferir_quantidade_para_lote` (D004/D005):
1. Localiza `stock.quant` (product, company=1, location=8, lot=MIGRACAO)
2. Valida saldo livre suficiente (quantity - reserved)
3. Reduz quant origem: `write({inventory_quantity: novo_qty})` +
   `action_apply_inventory`
4. Cria/aumenta quant destino: `write/create({inventory_quantity})` +
   `action_apply_inventory`

Gera **2 stock.moves por transferencia** com origem `Physical Inventory`,
auditavel em Inventory > Reporting > Stock Moves filtrando location_id=8
+ data hoje.

## Pendencias (276 linhas nao executadas)

| Categoria | N | Acao para resolver |
|---|---:|---|
| FALHA_SEM_SALDO — sem fisico (Virtuais nao contam) | 41 | **Impossivel** — produto ja consumido |
| FALHA_SEM_SALDO — saldo em Pre-Producao | 37 | Decisao operacional: mover semi-acabados? |
| FALHA_SEM_SALDO — saldo parcial em Pre-Producao | 48 | Tratar caso a caso |
| FALHA_SEM_SALDO — totalmente reservado | 96 | Cancelar 59 pickings INT antigos (mar-mai/25) |
| FALHA_SEM_SALDO — cumulativo do mesmo cod | 16 | Revisar planilha (mais destino que origem) |
| FALHA_LOTE_ORIGEM | 38 | Produto nao tem lote MIGRACAO — origem deve ser outro lote |

**Total atingivel adicional** (cenarios 2-3): +149 transferencias (319 total)
se ampliar para Pre-Producao + cancelar pickings antigos.

## Pickings INT antigos travando saldo (59 pickings, ~534k un reservadas)

Os mais antigos: `FB/INT/02459` (2025-03-13), `02543`, `02557`, `02738`,
`02808`, `02814`, `02914` (todos mar-abr/2025). Estes pickings em estado
`assigned` ha mais de 1 ano travam reservas que impedem novas
movimentacoes do lote MIGRACAO em FB/Estoque.

## Reversao

Cada transferencia executada esta no log JSON com:
- `quant_origem_id` / `quant_origem_qty_apos`
- `quant_destino_id` / `quant_destino_qty_apos`
- `lot_id_destino` / `lote_destino_criado_agora`

Reversao via novo inventory adjustment com sinal oposto. Lotes destino
criados (110) so podem ser desativados se nenhuma movimentacao usar.

## Nao toca

- `ajuste_estoque_inventario` local (regra emergenciais FB E01-E10)
- Sync das movimentacoes Odoo trara o resultado pelo fluxo normal
