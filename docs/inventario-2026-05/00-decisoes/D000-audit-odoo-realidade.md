# D000 — Audit Run: realidade do Odoo

**Data:** 2026-05-17T15:30:44.661418
**Origem:** `scripts/inventario_2026_05/00_audit_odoo_realidade.py`
**Spec:** `docs/superpowers/specs/2026-05-17-ajuste-inventario-nacom-lf-design.md`

## Locations e Picking Types por Company

### FB (`company_id=1`)

**Locations internas:**

- `id=8` — FB/Estoque
- `id=4065` — FB/Estoque/ALMOXARIFADO
- `id=4051` — FB/Estoque/DEVOLUÇÃO
- `id=4052` — FB/Estoque/EXPEDIÇÃO
- `id=4049` — FB/Estoque/PATIO
- `id=20142` — FB/Estoque/REVISÃO
- `id=4022` — FB/Estoque/SALMOURA
- `id=48` — FB/Pós-Produção
- `id=20140` — FB/Pré-Produção
- `id=20134` — FB/Pré-Produção/Linha Almofada 3
- `id=26490` — FB/Pré-Produção/Linha Almofada 7
- `id=4068` — FB/Pré-Produção/Linha Balde
- `id=30718` — FB/Pré-Produção/Linha Industrialização LF
- `id=4067` — FB/Pré-Produção/Linha Manual
- `id=4030` — FB/Pré-Produção/Linha Pouch 1
- `id=4037` — FB/Pré-Produção/Linha Pouch 2
- `id=4033` — FB/Pré-Produção/Linha Pouch 4
- `id=4069` — FB/Pré-Produção/Linha Pouch 5
- `id=4070` — FB/Pré-Produção/Linha Pouch 6
- `id=27457` — FB/Pré-Produção/Linha Retrabalho

**Picking types (incoming):**

- `id=1` — Recebimento (FB)
- `id=52` — Recebimentos Industrialização (FB)
- `id=54` — Recebimentos Entre Filiais (FB)
- `id=6` — Devoluções (FB)

### CD (`company_id=4`)

**Locations internas:**

- `id=20137` — CD/Conferencia
- `id=32` — CD/Estoque
- `id=17434` — CD/Estoque/AVARIA
- `id=17435` — CD/Estoque/BLOCADO
- `id=19497` — CD/Estoque/BLOCADO/P-01
- `id=19498` — CD/Estoque/BLOCADO/P-02
- `id=19499` — CD/Estoque/BLOCADO/P-03
- `id=19500` — CD/Estoque/BLOCADO/P-04
- `id=19501` — CD/Estoque/BLOCADO/P-05
- `id=19502` — CD/Estoque/BLOCADO/P-06
- `id=19503` — CD/Estoque/BLOCADO/P-07
- `id=19504` — CD/Estoque/BLOCADO/P-08
- `id=19505` — CD/Estoque/BLOCADO/P-09
- `id=19506` — CD/Estoque/BLOCADO/P-10
- `id=19507` — CD/Estoque/BLOCADO/P-11
- `id=19508` — CD/Estoque/BLOCADO/P-12
- `id=19509` — CD/Estoque/BLOCADO/P-13
- `id=19510` — CD/Estoque/BLOCADO/P-14
- `id=19511` — CD/Estoque/BLOCADO/P-15
- `id=19512` — CD/Estoque/BLOCADO/P-16

**Picking types (incoming):**

- `id=13` — Recebimento (CD)
- `id=50` — Recebimentos Entre Filiais (CD)
- `id=18` — Devoluções (CD)

### LF (`company_id=5`)

**Locations internas:**

- `id=42` — LF/Estoque
- `id=28831` — LF/Estoque/EXPEDIÇÃO
- `id=28832` — LF/Estoque/MOLHO
- `id=28841` — LF/Estoque/MOLHO/ABAIXO DO MEZANINO
- `id=28838` — LF/Estoque/MOLHO/BLOCADO
- `id=28877` — LF/Estoque/MOLHO/R-1
- `id=29519` — LF/Estoque/MOLHO/R-1/N-1
- `id=30354` — LF/Estoque/MOLHO/R-1/N-1/P-01
- `id=30355` — LF/Estoque/MOLHO/R-1/N-1/P-02
- `id=30356` — LF/Estoque/MOLHO/R-1/N-1/P-03
- `id=30357` — LF/Estoque/MOLHO/R-1/N-1/P-04
- `id=30358` — LF/Estoque/MOLHO/R-1/N-1/P-05
- `id=30359` — LF/Estoque/MOLHO/R-1/N-1/P-06
- `id=30360` — LF/Estoque/MOLHO/R-1/N-1/P-07
- `id=30361` — LF/Estoque/MOLHO/R-1/N-1/P-08
- `id=29520` — LF/Estoque/MOLHO/R-1/N-2
- `id=30362` — LF/Estoque/MOLHO/R-1/N-2/P-01
- `id=30363` — LF/Estoque/MOLHO/R-1/N-2/P-02
- `id=30364` — LF/Estoque/MOLHO/R-1/N-2/P-03
- `id=30365` — LF/Estoque/MOLHO/R-1/N-2/P-04

**Picking types (incoming):**

- `id=19` — Recebimento (LF)
- `id=24` — Devoluções (LF)
- `id=64` — Recebimentos Industrialização (LF)

## NFs de Referência

### NF 94457 (`account.move.id=607443`)

- `name`: 'RPI/2026/00200'
- `move_type`: out_invoice
- `l10n_br_tipo_pedido`: industrializacao
- `fiscal_position_id`: [25, 'REMESSA PARA INDUSTRIALIZAÇÃO']
- `company_id`: [1, 'NACOM GOYA - FB']
- `state`: posted
- Linha sample: `{'id': 3685738, 'product_id': [29649, '[103000014] TOMATE SECO'], 'quantity': 987.5, 'price_unit': 19.50207201139, 'account_id': [26846, '1150100012 FATURAMENTO FISICO FISCAL'], 'tax_ids': [], 'l10n_br_operacao_id': [80, 'Remessa p/ Industrialização'], 'l10n_br_cfop_codigo': '5901'}`

### NF 13075 (`account.move.id=588577`)

- `name`: 'RETNA/2026/04/0008'
- `move_type`: in_invoice
- `l10n_br_tipo_pedido`: False
- `fiscal_position_id`: [97, 'ENTRADA: RETORNO NÃO APLICADO']
- `company_id`: [1, 'NACOM GOYA - FB']
- `state`: posted
- Linha sample: `{'id': 3571277, 'product_id': [27760, '[105000024] ACUCAR CRISTAL'], 'quantity': 1400.0, 'price_unit': 2.7396092369, 'account_id': [26842, '1150100011 RECEBIMENTO FISICO FISCAL'], 'tax_ids': [], 'l10n_br_operacao_id': [838, 'Entrada de retorno de industrialização de material não aplicado'], 'l10n_br_cfop_codigo': '1903'}`

### NF 147772 (`account.move.id=603226`)

- `name`: 'ENTRE/2026/05/0002'
- `move_type`: in_invoice
- `l10n_br_tipo_pedido`: False
- `fiscal_position_id`: [86, 'ENTRADA - RETRABALHO']
- `company_id`: [5, 'LA FAMIGLIA - LF']
- `state`: posted
- Linha sample: `{'id': 3662103, 'product_id': [27832, '[4870146] MOLHO SHOYU - PET 12X150 ML - CAMPO BELO'], 'quantity': 1.0, 'price_unit': 24.9609371094, 'account_id': [26845, '1150100011 RECEBIMENTO FISI'], 'tax_ids': [3358378, 3358379], 'l10n_br_operacao_id': [2916, 'RETRABALHO'], 'l10n_br_cfop_codigo': '1949'}`

### NF 94410 (`account.move.id=606166`)

- `name`: 'ENTTR/2026/05/0100'
- `move_type`: in_invoice
- `l10n_br_tipo_pedido`: False
- `fiscal_position_id`: [50, 'ENTRADA - TRANSFERÊNCIA ENTRE FILIAIS']
- `company_id`: [4, 'NACOM GOYA - CD']
- `state`: posted
- Linha sample: `{'id': 3680261, 'product_id': [29708, '[4310148] AZEITONA VERDE SEM CAROCO - POUCH 30X80 G - CAMPO BELO'], 'quantity': 112.0, 'price_unit': 40.3871275567, 'account_id': [26844, '1150100011 RECEBIMENTO FISICO FISCAL'], 'tax_ids': [3376058], 'l10n_br_operacao_id': [2998, 'Transferência p/ comercialização - CD - CONSERVAS'], 'l10n_br_cfop_codigo': '1152'}`

## Decisões derivadas

Após este audit, atualizar:
- `app/odoo/constants/locations.py` com `COMPANY_LOCATIONS = {1: ..., 4: ..., 5: ...}`
- `app/odoo/constants/operacoes_fiscais.py` com `MATRIZ_INTERCOMPANY` (4 entradas, `fiscal_position_id` por company)
- `.claude/references/odoo/IDS_FIXOS.md` se algum ID divergir

## Itens em aberto

- [ ] Confirmar com Rafael qual `location_id` interno usar quando há múltiplos (escolher principal)
- [ ] Confirmar com Rafael se NFs com estado ≠ `posted` são válidas como referência
- [ ] Confirmar `fiscal_position_id` por company para cada CFOP (FB e LF para 5901/5903/5949; FB e CD para 5152)