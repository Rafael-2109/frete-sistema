# Monitor do Inventario 2026-05

Pipeline reusavel para monitorar o **progresso dos ajustes** do inventario fisico
(contagem de 16/05/2026) nas filiais FB (company 1), CD (4) e LF (5).

Compara o **saldo teorico** (inventario fisico + movimentacoes REAIS de negocio)
contra o **saldo atual no Odoo** (`stock.quant`). A divergencia mostra quanto
ainda falta ajustar: conforme os ajustes avancam, o Odoo se aproxima do teorico
e `diff_qtd -> 0`.

## Conceito central

```
inv_teorico = inventario fisico 16/05
            + movs de negocio (vendas, transferencias, recebimentos normais)
            + recebimentos LF do worker Render
            - (os ajustes do PROPRIO inventario sao DESCARTADOS)

odoo_atual  = saldo stock.quant interno HOJE (snapshot)

diff_qtd    = qtd_teorica - qtd_odoo_atual
```

Os ajustes do inventario sao descartados do teorico porque sao **justamente o
que medimos** — incluir os proprios ajustes mascararia a divergencia.

A separacao "movs reais" vs "ajustes" e feita por **autor da movimentacao**:
o UID 42 (Rafael) e quem executa os ajustes via scripts, entao tudo que ele
move localmente sai do teorico. Movs de outros usuarios (UID != 42) e os
recebimentos LF do worker Render entram no teorico.

## Scripts

| # | Script | O que faz | Output |
|---|--------|-----------|--------|
| 1 | `1_baixar_estoques.py` | `stock.quant` interno (FB/CD/LF), agrega por (filial, cod, lote). Captura snapshot UTC (teto p/ script 2) | `<cache>/estoques.csv` + `<cache>/snapshot_meta.json` |
| 2 | `2_baixar_movimentacoes.py` | `stock.move.line` done entre 16/05 e o snapshot. **Classifica** cada mov em 3 categorias (nao exclui nada) | `<cache>/movimentacoes.csv` |
| 3 | `3_agregar_lote.py` | inv fisico + movs filtradas (so `NAO_RAFAEL` e `RECEBIMENTO_LF_RENDER`; descarta ajustes `RAFAEL_UID42`) -> saldo teorico | `<cache>/inv_teorico.csv` |
| 4 | `4_gerar_diffs.py` | Diff teorico vs Odoo atual, separando MIGRACAO em abas proprias | `docs/inventario-2026-05/07-relatorios/MONITOR_DIFF_<timestamp>.xlsx` |
| 0 | `0_pipeline.py` | Roda 1 -> 2 -> 3 -> 4 em sequencia | Output do script 4 |

`_comum.py` concentra constantes e helpers (companies, normalizadores de
cod/lote, deteccao de location interna, snapshot meta, consulta Render).

## Uso

### Pipeline completo (recomendado)

```bash
source .venv/bin/activate
python scripts/inventario_2026_05/monitor/0_pipeline.py
```

Tempo total: ~1-3 minutos (depende da quantidade de quants/moves no Odoo).

### Pular passos / rodar so um

```bash
# Reusar estoques.csv e movimentacoes.csv do cache, so re-gerar teorico+diff
python scripts/inventario_2026_05/monitor/0_pipeline.py --skip=1,2

# So gerar o Excel final (assume cache ja existente)
python scripts/inventario_2026_05/monitor/0_pipeline.py --so=4
```

### Rodar individualmente

```bash
python scripts/inventario_2026_05/monitor/1_baixar_estoques.py
python scripts/inventario_2026_05/monitor/2_baixar_movimentacoes.py
python scripts/inventario_2026_05/monitor/3_agregar_lote.py
python scripts/inventario_2026_05/monitor/4_gerar_diffs.py
```

## Parametros

| Flag | Default | Script(s) |
|------|---------|-----------|
| `--cache-dir` | `/tmp/inventario_monitor` | 0, 1, 2, 3, 4 |
| `--data-inicio` | `2026-05-16 00:00:00` | 0, 2 |
| `--data-fim` | snapshot UTC do script 1 (`snapshot_meta.json`) | 2 |
| `--inv-path` | `/mnt/c/Users/rafael.nascimento/Downloads/INVENTARIO 16-05-26/COMPILADO INV. 16.05.2026 1.xlsx` | 0, 3 |
| `--apenas` | `NAO_RAFAEL,RECEBIMENTO_LF_RENDER` | 3 |
| `--output-name` | `MONITOR_DIFF_<timestamp>.xlsx` | 4 |
| `--skip` | (vazio) — lista CSV de scripts a pular, ex `1,2` | 0 |
| `--so` | (vazio) — roda APENAS este script, ex `4` | 0 |

> `0_pipeline.py` repassa apenas `--cache-dir`, `--data-inicio` e `--inv-path`.
> Para usar `--data-fim` ou `--apenas` customizados, rode o script individual.

## Variavel de ambiente (script 2)

A classificacao `RECEBIMENTO_LF_RENDER` depende da lista de pickings da tabela
`recebimento_lf` **no Render (producao)**, consultada via psycopg2 usando a env
var `DATABASE_URL_PROD` (External Database URL do Render). Carregada
automaticamente do `.env`.

Se a env nao estiver configurada: a lista vem vazia, nenhuma mov e marcada como
`RECEBIMENTO_LF_RENDER` (essas movs caem em `RAFAEL_UID42` ou `NAO_RAFAEL`
conforme o autor) e o script emite aviso — **nao quebra**.

## Classificacao de movimentacoes (script 2)

Cada `stock.move.line` (state=done) recebe uma categoria, **sem deducao**:

| Categoria | Criterio | Entra no teorico? |
|-----------|----------|-------------------|
| `RECEBIMENTO_LF_RENDER` | `picking_id` na lista `recebimento_lf` do Render | SIM |
| `RAFAEL_UID42` | `create_uid == 42` (e nao Render) | NAO (sao os ajustes) |
| `NAO_RAFAEL` | `create_uid != 42` | SIM |

Prioridade de classificacao: **Render > UID42 > outros**.

### Categoria de negocio (`categoria_negocio`) — para as 3 colunas do script 4

Alem da classificacao acima (que decide o teorico), o script 2 classifica cada mov
em **categoria de negocio**, resolvendo o **parceiro** do picking (`commercial_partner_id`
via `stock.picking` -> `res.partner`) para separar NF entre empresas de compra/venda real:

| Categoria | Criterio |
|-----------|----------|
| `COMPRA_EXT` | ponta fornecedor (`Parceiros/Fornecedores`) + parceiro EXTERNO |
| `VENDA_EXT` | ponta cliente (`Parceiros/Clientes`) + parceiro EXTERNO |
| `INTERCOMPANY` | ponta fornecedor/cliente mas parceiro = empresa do grupo (NF entre empresas — **excluida**) |
| `AJUSTE_TERCEIRO` | ponta de ajuste de inventario E `create_uid != 42` |
| `AJUSTE_PROPRIO` | ponta de ajuste de inventario E `create_uid == 42` (Rafael/scripts) |
| `OUTRO` | transferencia interna, producao, industrializacao, transito, etc. |

- **Inter-company** = `commercial_partner_id` em `res.company.partner_id` (FB=1, SC=33, CD=34, LF=35).
- **Ajuste de inventario** = location virtual em 3 variantes: `Ajuste de Inventario`,
  `Inventory adjustment`, `Ajuste de Estoque` (PT/EN coexistem no CIEL IT).
- Constantes e helpers em `_comum.py` (`is_loc_ajuste/fornecedor/cliente`, `buscar_partner_ids_empresas`).

### Teto temporal (snapshot)

O script 1 grava o horario UTC da extracao de estoque em `snapshot_meta.json`.
O script 2 usa esse horario como **TETO** (`date <= snapshot`) para descartar
movs posteriores a leitura do estoque — evita "diff fantasma" (mov ja contada
no teorico mas ainda nao refletida no quant lido). Override manual: `--data-fim`.

## Agregacao (script 3)

Estado inicial = inventario fisico. Para cada mov **filtrada** (categorias de
`--apenas`):

- `location_id` (origem) e stock interno da filial -> **SUBTRAI** `qty_done`
- `location_dest_id` (destino) e stock interno da filial -> **SOMA** `qty_done`

`lote` vem de `lot_name` normalizado. `stock interno` = `location_name` comeca
com `FB/`, `CD/` ou `LF/` e **nao** contem: `Virtual`, `Parceiros`, `Production`,
`Inventory adjustment`, `Cliente`, `Customers`, `Vendors`, `Fornecedor`.

### Coluna de QUANTIDADE do inventario fisico por aba

Default: `COMPILADO INV. 16.05.2026 1.xlsx` (versao oficial v1). A coluna de
quantidade e detectada automaticamente por aba (ordem = prioridade):

| Aba | Candidatos (ordem) | Coluna na v1 |
|-----|--------------------|--------------|
| FB  | `QUANTIDADE`, `QTD` | `QUANTIDADE` |
| CD  | `FINAL`, `QTD`, `QUANTIDADE` | `FINAL` |
| LF  | `QUANTIDADE/UN`, `QUANTIDADE`, `QTD` | `QUANTIDADE/UN` |

Se nenhuma coluna candidata existir na aba, o script falha com erro claro
listando as colunas disponiveis. Para outra planilha: `--inv-path <arquivo>.xlsx`.

## Diff (script 4)

- **Filtra MIGRACAO** (variantes `MIGRACAO`, `MIGRAÇÃO`, `MIG`, etc.) de **ambos**
  os lados — vai para abas de auditoria proprias, fora do diff ativo.
- Tambem trata `P-15/05` como lote vazio (`LOTES_PROXY_VAZIO` em `_comum.py`).
- `diff_qtd = qtd_teorica - qtd_odoo_atual`
- `status`: `OK` se `|diff_qtd| < 0.01`, senao `DIVERGENTE`
- `cobertura`:
  - `AMBOS`: lote presente nos dois lados com qty != 0
  - `SO_TEORICO`: existe no teorico mas nao no Odoo (precisa criar saldo)
  - `SO_ODOO`: existe no Odoo mas nao no teorico (fantasma / Indisponivel a tratar)

## Abas do Excel final

| Aba | Conteudo |
|-----|----------|
| `Diff_Por_Lote` | Detalhe por (filial, cod, lote): inicial, entradas, saidas, teorico, Odoo, `diff_qtd`, custo, `diff_valor`, **`qtd_comprada`, `qtd_vendida`, `qtd_ajuste_terceiros`**, cobertura, status |
| `Diff_Por_Cod` | Agregado por (filial, cod): n_lotes, teorico, Odoo, diffs, **`qtd_comprada`, `qtd_vendida`, `qtd_ajuste_terceiros`** (soma dos lotes), status (OK se `|diff| < 0.5`) |
| `MIGRACAO_Saldo` | Saldo dos lotes MIGRACAO (teorico vs Odoo) — o "fantasma" acumulado a indisponibilizar |
| `MIGRACAO_Movimentacoes` | Movs com lote MIGRACAO (entrada/saida/saldo, picking, autor) — **so se houver** |

### Colunas de negocio (`qtd_comprada` / `qtd_vendida` / `qtd_ajuste_terceiros`)

Adicionadas em `Diff_Por_Lote` e `Diff_Por_Cod`. Mostram o **impacto no saldo** do lote/produto
no periodo (16/05 -> snapshot), **com sinal** (compra +, venda -, ajuste +/-). Ajudam a explicar `diff_qtd`.

- Impacto de cada mov = `+qty_done` se destino interno, `-qty_done` se origem interna.
- `qtd_comprada` = categoria `COMPRA_EXT` (compra de fornecedor externo; **exclui NF entre empresas**).
- `qtd_vendida` = categoria `VENDA_EXT` (venda a cliente externo; **exclui NF entre empresas**). Tipicamente negativo.
- `qtd_ajuste_terceiros` = categoria `AJUSTE_TERCEIRO` (ajuste de inventario por `create_uid != 42`).
- **Escopo = lotes ATIVOS (nao-MIGRACAO)**, igual ao resto do diff. Movs em lote MIGRACAO entram so na
  aba `MIGRACAO_Movimentacoes`. Por isso `Diff_Por_Cod` = soma exata de `Diff_Por_Lote` por (filial, cod).

Os resumos por filial (`n_OK`/`n_DIV`), por cobertura e do saldo MIGRACAO sao
**impressos no stdout** do script 4 (nao viram aba).

## Rotina de monitoramento sugerida

1. Rodar `0_pipeline.py` antes de cada decisao operacional
2. Comparar `n_OK` / `n_DIV` (stdout) entre execucoes — `n_OK` deve crescer
3. Abrir `Diff_Por_Lote` / `Diff_Por_Cod`, ordenar por `diff_valor` p/ achar o que falta
4. `SO_ODOO` = saldo no Odoo sem contraparte teorica (fantasma / Indisponivel a tratar)
5. `MIGRACAO_Saldo` = saldo consolidado a indisponibilizar nas ondas finais
6. Atualizar docs (SOT.md, CHECKPOINT*) com base nessa visao consolidada

## Cache

`estoques.csv`, `movimentacoes.csv`, `inv_teorico.csv` e `snapshot_meta.json`
ficam em `/tmp/inventario_monitor/` (efemeros — perdem em reboot WSL). Re-rodar
`0_pipeline.py` os regenera. Para preservar entre sessoes, copiar para
`~/inventario_monitor_cache/` manualmente.
