<!-- doc:meta
tipo: reference
camada: L3
sot_de: —
hub: docs/inventario-2026-05/00-decisoes/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# D011 — Locais `Indisponivel` por empresa para ajustes de inventário

> **Papel:** D011 — Locais `Indisponivel` por empresa para ajustes de inventário.

## Indice

- [Contexto](#contexto)
- [Estrutura criada (Odoo)](#estrutura-criada-odoo)
  - [Por que ficam fora das regras](#por-que-ficam-fora-das-regras)
- [Regra (INVIOLÁVEL — a partir de 2026-05-19)](#regra-inviolável-a-partir-de-2026-05-19)
  - [Ajuste **negativo** (perda de estoque detectada no inventário)](#ajuste-negativo-perda-de-estoque-detectada-no-inventário)
  - [Ajuste **positivo** (excesso de estoque detectado no inventário)](#ajuste-positivo-excesso-de-estoque-detectado-no-inventário)
  - [Quem se aplica](#quem-se-aplica)
- [Impacto nas decisões anteriores](#impacto-nas-decisões-anteriores)
- [Implementação técnica (template)](#implementação-técnica-template)
- [Como aplicar (operacional)](#como-aplicar-operacional)
- [Referências cruzadas](#referências-cruzadas)

**Data**: 2026-05-19
**Status**: VIGENTE — SOT para qualquer novo script de ajuste de inventário (CD e FB) a partir desta data
**Validado por**: usuário (Rafael) na sessão da tarde 2026-05-19
**Substitui**: parcialmente o uso do `Estoque Virtual/Inventory adjustment` (location_id=28) como contrapartida de ajustes negativos/positivos quando o objetivo é manter trilha contábil dentro da própria filial.

---

## Contexto

Antes desta decisão, ajustes de inventário positivos e negativos eram lançados contra `Estoque Virtual/Inventory adjustment` (`stock.location` id=28, `usage='inventory'`) — o local virtual padrão do Odoo. Isso funciona, mas:

1. **Mistura empresas**: o local virtual id=28 é compartilhado entre as 4 companies (não tem `company_id` rígido) → audit cross-company difícil.
2. **Sem rastreio físico**: o saldo "vai para o limbo" — não há um local **físico-conceitual** onde se possa "ver" o estoque que está aguardando reconciliação.
3. **Lote MIGRAÇÃO disperso**: o lote `MIGRAÇÃO` foi usado de forma ad-hoc (D005) como consolidador, mas vive dentro de `{emp}/Estoque` junto com lotes reais — risco de operador consumir por engano.

A solução: criar um **local físico dedicado por empresa** que:
- Tenha `company_id` próprio (rastreio limpo)
- Fique **FORA da árvore de regras** (não é descendente de `WH/Estoque`)
- Sirva como contraparte das movimentações de inventário

---

## Estrutura criada (Odoo)

4 locais `stock.location`, criados em 2026-05-19, todos com:
- `usage='internal'`
- `active=True`
- `location_id` = `view_location_id` do warehouse da company (raiz `FB`, `SC`, `CD`, `LF`)
- **Importante**: NÃO descendentes de `lot_stock_id` (`{emp}/Estoque`)

| company_id | Nome | Local | Parent (view) |
|------------|------|-------|---------------|
| 1 — NACOM GOYA - FB | `FB/Indisponivel` | **31088** | 7 (FB) |
| 3 — NACOM GOYA - SC | `SC/Indisponivel` | **31089** | 21 (SC) |
| 4 — NACOM GOYA - CD | `CD/Indisponivel` | **31090** | 31 (CD) |
| 5 — LA FAMIGLIA - LF | `LF/Indisponivel` | **31091** | 41 (LF) |

Constante para reuso em scripts (também em `.claude/references/odoo/IDS_FIXOS.md`):

```python
LOCAIS_INDISPONIVEL = {
    1: 31088,  # FB/Indisponivel
    3: 31089,  # SC/Indisponivel
    4: 31090,  # CD/Indisponivel
    5: 31091,  # LF/Indisponivel
}
```

### Por que ficam fora das regras

`stock.rule` busca quants via `child_of(location_src_id)`. Como nenhuma regra existente da Nacom tem `location_src_id` apontando para `FB/`, `CD/`, `LF/`, `SC/` (todas apontam para `{emp}/Estoque` ou descendentes), o saldo em `{emp}/Indisponivel` é **invisível** para:

- Reservas automáticas de venda
- MRP (consumo de matéria-prima e destino de produto acabado)
- Replenishment / MTO
- Rotas push após recebimento

Isso significa que o operador não consegue "pegar" o estoque dali em fluxos automáticos, mesmo com o local ativo. Para uso manual (picking ad-hoc), o local **aparece** no autocomplete (porque `active=True`) — quem mover é quem entendeu o que está fazendo.

---

## Regra (INVIOLÁVEL — a partir de 2026-05-19)

### Ajuste **negativo** (perda de estoque detectada no inventário)

O lote real perde quantidade. A contraparte vai para `Indisponivel` com lote **MIGRACAO** (sem acento, conforme convenção D005):

```
DE:  {emp}/Estoque        | lote = <lote_real>   | qty = abs(diff)
PARA: {emp}/Indisponivel  | lote = MIGRACAO      | qty = abs(diff)
```

- A NF entre empresas (CFOPs 5901/5903/etc.) deixa de ser obrigatória para a perda — o saldo continua na mesma company.
- O **lote MIGRACAO** funciona como concentrador da perda dentro de `Indisponivel`, sem misturar com lotes reais.

### Ajuste **positivo** (excesso de estoque detectado no inventário)

O lote real ganha quantidade. A contraparte sai de `Indisponivel`:

```
DE:  {emp}/Indisponivel   | lote = MIGRACAO     | qty = abs(diff)
PARA: {emp}/Estoque       | lote = <lote_real>  | qty = abs(diff)
```

- Se `Indisponivel/MIGRACAO` não tiver saldo suficiente, o produto não foi previamente acumulado lá — caso especial (não há de onde tirar). Decisão caso a caso.

### Quem se aplica

| Empresa | Aplica D011? | Observação |
|---------|--------------|------------|
| FB (1) | **Sim** | Aplicar a partir desta data |
| CD (4) | **Sim** | Aplicar a partir desta data |
| SC (3) | Local criado mas sem ajustes previstos (fora do escopo desta fase) | — |
| LF (5) | **Não nesta regra** | LF segue D004/D005 (rename FIFO + diferença líquida via NF LF↔FB). `LF/Indisponivel` foi criado por simetria, uso futuro. |

---

## Impacto nas decisões anteriores

| Decisão | Impacto |
|---------|---------|
| **D005** — Lote MIGRACAO consolidador | Continua válida. Diferença: **onde** ele vive. Antes vivia em `{emp}/Estoque` (`stock.lot.location_id` implícito via quants); agora os quants do lote MIGRACAO ficam em `{emp}/Indisponivel`. O lote em si continua sendo o mesmo `stock.lot` (já existente: id=30482 FB MIGRAÇÃO, id=30856 CD MIGRAÇÃO). |
| **D006** — TRANSFERIR vs RENOMEAR | Continua válida. D011 substitui o uso de `Estoque Virtual/Inventory adjustment` como contraparte; renomeações e transferências internas seguem o mesmo padrão. |
| **D010** — Direção por sinal de `diff_qtd` | **Continua válida e se combina com D011**. Para planilhas do pipeline `monitor/`: <br>• `diff_qtd > 0` → `{emp}/Indisponivel → {emp}/Estoque` (lote precisa) <br>• `diff_qtd < 0` → `{emp}/Estoque → {emp}/Indisponivel` (lote tem excesso) <br>Antes era `lote ↔ MIGRACAO` dentro do mesmo `{emp}/Estoque`; agora muda também a localização. |

---

## Implementação técnica (template)

Scripts novos devem usar um picking interno (`stock.picking` com `picking_type_id` de transferência interna do WH) para mover entre `Estoque ↔ Indisponivel`. Validado em 2026-05-19 (picking de teste 317714 CD/Estoque → CD/Conferencia, revertido em 317715).

```python
from app.odoo.constants.locations import LOCAIS_INDISPONIVEL  # adicionar essa constante

def aplicar_ajuste_negativo(company_id, picking_type_id, lote_origem_id, qty_caixas):
    """Move {emp}/Estoque/<lote_real> → {emp}/Indisponivel/MIGRACAO."""
    loc_estoque = LOT_STOCK_POR_COMPANY[company_id]           # 8/22/32/42
    loc_indisp  = LOCAIS_INDISPONIVEL[company_id]             # 31088/31089/31090/31091
    lote_migracao = LOTES_MIGRACAO_POR_COMPANY[company_id]    # 30482 FB / 30856 CD

    picking = odoo.create('stock.picking', {
        'picking_type_id': picking_type_id,
        'location_id': loc_estoque,
        'location_dest_id': loc_indisp,
        'company_id': company_id,
        'origin': 'INV_2026_05_AJUSTE_NEG',
    })
    move = odoo.create('stock.move', {
        'picking_id': picking,
        'product_id': PRODUTO_ID,
        'product_uom_qty': qty_caixas,
        'product_uom': UOM_CAIXAS,
        'location_id': loc_estoque,
        'location_dest_id': loc_indisp,
        'company_id': company_id,
    })
    odoo.call('stock.picking', 'action_confirm', [picking])
    odoo.create('stock.move.line', {
        'move_id': move,
        'picking_id': picking,
        'product_id': PRODUTO_ID,
        'product_uom_id': UOM_CAIXAS,
        'qty_done': qty_caixas,
        'lot_id': lote_origem_id,           # lote real, NÃO MIGRACAO ainda
        'location_id': loc_estoque,
        'location_dest_id': loc_indisp,
        'company_id': company_id,
    })
    odoo.call('stock.picking', 'button_validate', [picking],
              context={'skip_expired': True, 'skip_backorder': True})
    # APÓS validar: renomear o lote dentro do quant destino, OU usar
    # stock.move.line.lot_id_destino se o Odoo CIEL IT expor o campo.
    # Por padrão, o quant em Indisponivel mantém o lote real — o passo de
    # "renomear para MIGRACAO" pode ser feito via StockLotService ou via
    # consolidação de quants no mesmo lote MIGRACAO já existente.
    return picking
```

**Pendente decidir** (caso de implementação real): se a renomeação para MIGRACAO acontece (a) via segundo picking quant_origem=lote_real → quant_dest=lote_MIGRACAO dentro do mesmo Indisponivel, ou (b) via inventory adjustment direto no quant que acabou de chegar. Não cobrir aqui — decidir quando o primeiro script for construído.

---

## Como aplicar (operacional)

1. **Antes de qualquer script novo** que mexa em ajuste de inventário CD/FB pós-D011: ler este documento + `.claude/references/odoo/IDS_FIXOS.md` (seção "Locais Indisponivel").
2. **NÃO** usar mais `Estoque Virtual/Inventory adjustment` (id=28) como contraparte de ajustes do inventário 2026-05 a partir desta data.
3. Scripts antigos (`09_executar_onda1_bulk.py`, etc.) que já rodaram NÃO devem ser reescritos — D011 vale para NOVAS execuções daqui pra frente.
4. Auditoria: para conferir, basta filtrar `stock.move_line` com `location_dest_id IN (31088, 31089, 31090, 31091)` — todos os ajustes pós-D011 passam por lá.

---

## Referências cruzadas

- `.claude/references/odoo/IDS_FIXOS.md` — seção "Locais Indisponivel por Empresa"
- D005 — Lote MIGRACAO consolidador (continua válido)
- D006 — TRANSFERIR vs RENOMEAR
- D010 — Direção MIGRAÇÃO por sinal de `diff_qtd`
- Pickings de validação de visibilidade (2026-05-19): `CD/INT/00013` (id=317714) + `CD/INT/00014` (id=317715, reversão)
