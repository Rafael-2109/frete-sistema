# Monitor do Inventario 2026-05

Pipeline reusavel para monitorar o progresso dos ajustes de inventario.

## Scripts

| # | Script | O que faz | Output |
|---|--------|-----------|--------|
| 1 | `1_baixar_estoques.py` | Extrai estoque ATUAL Odoo (stock.quant) em FB/CD/LF | `/tmp/inventario_monitor/estoques.csv` |
| 2 | `2_baixar_movimentacoes.py` | Extrai stock.move.line desde 16/05, exclui apenas recebimento_lf Render puro (overlap com inventario mantido) | `/tmp/inventario_monitor/movimentacoes.csv` |
| 3 | `3_agregar_lote.py` | Le inv fisico + movs, gera saldo teorico por (filial, cod, lote) | `/tmp/inventario_monitor/inv_teorico.csv` |
| 4 | `4_gerar_diffs.py` | Diff inv_teorico vs Odoo atual, filtrando MIGRACAO | `docs/inventario-2026-05/07-relatorios/MONITOR_DIFF_<timestamp>.xlsx` |
| 0 | `0_pipeline.py` | Roda 1, 2, 3, 4 em sequencia | Final do script 4 |

## Uso

### Pipeline completo (recomendado para monitorar)

```bash
source .venv/bin/activate
python scripts/inventario_2026_05/monitor/0_pipeline.py
```

Tempo total: ~3 minutos (depende da quantidade de quants/moves no Odoo).

### Pular passos (usar cache existente)

```bash
# Reusar estoques.csv e movimentacoes.csv do cache, so re-gerar
python scripts/inventario_2026_05/monitor/0_pipeline.py --skip=1,2

# So gerar o Excel final (script 4)
python scripts/inventario_2026_05/monitor/0_pipeline.py --so=4
```

### Rodar individualmente

```bash
python scripts/inventario_2026_05/monitor/1_baixar_estoques.py
python scripts/inventario_2026_05/monitor/2_baixar_movimentacoes.py
python scripts/inventario_2026_05/monitor/3_agregar_lote.py
python scripts/inventario_2026_05/monitor/4_gerar_diffs.py
```

### Parametros

| Flag | Default | Onde |
|------|---------|------|
| `--cache-dir` | `/tmp/inventario_monitor` | 1, 2, 3, 4, 0 |
| `--data-inicio` | `2026-05-16 00:00:00` | 2 |
| `--inv-path` | `/mnt/c/Users/rafael.nascimento/Downloads/INVENTARIO 16-05-26/COMPILADO INV. 16.05.2026.xlsx` | 3 |
| `--output-name` | `MONITOR_DIFF_<timestamp>.xlsx` | 4 |

## Logica de filtragem (script 2)

- Pickings do inventario (`ajuste_estoque_inventario.picking_id_odoo`): SEMPRE INCLUIR
- Pickings do recebimento_lf Render NAO inventario: EXCLUIR
- Pickings em ambas as listas (overlap): INCLUIR como inventario
- Movs sem picking (inventory adjust): INCLUIR
- Outros pickings (vendas, recebimentos comuns): INCLUIR (sao movs reais que afetam estoque)

## Logica de agregacao (script 3)

Para cada stock.move.line:
- Se `location_id` eh stock interno da filial (FB/CD/LF, nao virtual): SUBTRAI qty do (filial, cod, lote)
- Se `location_dest_id` eh stock interno da filial: SOMA qty ao (filial, cod, lote)

`lote` vem de `lot_name` da move_line (normalizado).

`stock interno` = location_name comeca com FB/, CD/, LF/ e nao contem:
'Virtual', 'Parceiros', 'Production', 'Inventory adjustment', 'Cliente',
'Customers', 'Vendors', 'Fornecedor'.

## Logica de diff (script 4)

- Filtra MIGRACAO (variantes: MIGRACAO, MIGRAÇÃO, MIG, etc.) de **ambos** os lados
- Lotes ativos: comparacao inv_teorico vs Odoo atual
- Lotes MIGRACAO: separados em aba propria (auditoria do saldo "fantasma")

`status`:
- `OK`: |diff_qtd| < 0.01
- `DIVERGENTE`: caso contrario

`cobertura`:
- `AMBOS`: lote presente em ambos com qty != 0
- `SO_TEORICO`: existe no teorico mas nao Odoo (precisa criar)
- `SO_ODOO`: existe no Odoo mas nao no teorico (fantasma a tratar)

## Abas do Excel final

1. `README`
2. `1_Resumo_Lote` — totais por filial (n_OK/DIV, qty)
3. `2_Cobertura` — AMBOS / SO_TEORICO / SO_ODOO
4. `3_Resumo_Cod` — totais agregados por (filial, cod)
5. `4_Saldo_MIGRACAO` — saldo acumulado no lote MIGRACAO
6. `5_Diff_Por_Lote` — detalhe (filial, cod, lote, qtd_inicial, entradas, saidas, teorico, Odoo, diff)
7. `6_Diff_Por_Cod` — agregado por (filial, cod)
8. `7_DIV_Lote_TOP` — TOP 2000 divergencias por lote (valor abs)
9. `8_DIV_Cod_TOP` — TOP 500 divergencias por cod
10. `9_MIGRACAO_Detalhe` — detalhe lotes MIGRACAO

## Rotina de monitoramento sugerida

1. Rodar `0_pipeline.py` antes de cada decisao operacional
2. Comparar `1_Resumo_Lote` entre execucoes — n_OK deve crescer
3. Investigar `7_DIV_Lote_TOP` por filial para entender o que falta
4. Atualizar docs (SOT.md, CHECKPOINT*) com base nessa visao consolidada

## Cache

Os CSVs em `/tmp/inventario_monitor/` sao efemeros (perdem em reboot WSL).
Re-rodar `0_pipeline.py` os regenera. Para preservar entre sessoes,
copiar para `~/inventario_monitor_cache/` manualmente.
