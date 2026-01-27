# Modelos Odoo - Recebimento Fisico

## Campos Verificados (Explorados em 23/01/2026)

---

## stock.picking (Recebimento)

| Campo | Tipo | Descricao | Uso |
|-------|------|-----------|-----|
| `id` | integer | ID do registro | Identificacao |
| `name` | char | Nome do picking (IN/00123) | Display |
| `state` | selection | draft, waiting, confirmed, assigned, done, cancel | Controle fluxo |
| `picking_type_code` | char | "incoming" para recebimento | Filtro |
| `partner_id` | many2one (res.partner) | Fornecedor | Filtro/display |
| `origin` | char | Referencia (PO name, NF) | Filtro |
| `purchase_id` | many2one (purchase.order) | PO vinculado | Vinculo |
| `scheduled_date` | datetime | Data prevista | Display |
| `move_ids` | one2many (stock.move) | Movimentos | Produtos |
| `move_line_ids` | one2many (stock.move.line) | Linhas detalhadas | Lotes |
| `company_id` | many2one (res.company) | Empresa | Filtro |
| `picking_type_id` | many2one (stock.picking.type) | Tipo operacao | Contexto |
| `location_id` | many2one (stock.location) | Origem | Obrigatorio em move.line |
| `location_dest_id` | many2one (stock.location) | Destino | Obrigatorio em move.line |

### Filtro para pickings de recebimento pendentes:
```python
domain = [
    ['state', '=', 'assigned'],
    ['picking_type_code', '=', 'incoming'],
    ['company_id', '=', company_id],
]
```

---

## stock.move (Movimentos por Produto)

| Campo | Tipo | Descricao | Uso |
|-------|------|-----------|-----|
| `id` | integer | ID | Identificacao |
| `product_id` | many2one (product.product) | Produto | Identificacao |
| `product_uom_qty` | float | Qtd esperada (demanda) | Validacao soma lotes |
| `quantity` | float | Qtd realizada | Apos validacao |
| `product_uom` | many2one (uom.uom) | Unidade de medida | Display |
| `state` | selection | Estado do move | Contexto |
| `move_line_ids` | one2many | Linhas (lotes) | Preenchimento |
| `picking_id` | many2one | Picking pai | Filtro |

---

## stock.move.line (Linhas - Lotes + Quantidade)

| Campo | Tipo | Descricao | Uso |
|-------|------|-----------|-----|
| `id` | integer | ID | Identificacao |
| `product_id` | many2one | Produto | Obrigatorio |
| `move_id` | many2one (stock.move) | Move pai | Obrigatorio |
| `picking_id` | many2one | Picking pai | Obrigatorio |
| `lot_id` | many2one (stock.lot) | Lote existente | Opcional |
| `lot_name` | char | Nome do lote (cria auto ao validar) | **PRINCIPAL** |
| `quantity` | float | Quantidade reservada/recebida | **PRINCIPAL** |
| `qty_done` | float | Quantidade realizada | **PRINCIPAL** |
| `product_uom_id` | many2one (uom.uom) | UOM | Contexto |

> **ATENCAO:** `reserved_uom_qty` NAO EXISTE nesta versao do Odoo. Usar `quantity` para quantidade reservada e `qty_done` para quantidade realizada.
| `location_id` | many2one (stock.location) | Origem | Obrigatorio em create |
| `location_dest_id` | many2one (stock.location) | Destino | Obrigatorio em create |

### Operacoes:

**Write em move.line existente (1o lote):**
```python
odoo.write('stock.move.line', line_id, {
    'lot_name': 'LOTE-001',
    'quantity': 500.0,
})
```

**Create de move.line adicional (lotes extras):**
```python
odoo.execute_kw('stock.move.line', 'create', [{
    'picking_id': picking_id,
    'move_id': move_id,
    'product_id': product_id,
    'lot_name': 'LOTE-002',
    'quantity': 250.0,
    'location_id': picking['location_id'][0],
    'location_dest_id': picking['location_dest_id'][0],
}])
```

---

## stock.lot (Cadastro de Lotes)

| Campo | Tipo | Descricao | Uso |
|-------|------|-----------|-----|
| `id` | integer | ID | Identificacao |
| `name` | char | Codigo do lote | Unico por produto |
| `product_id` | many2one | Produto | Vinculo |
| `company_id` | many2one | Empresa | Obrigatorio |
| `expiration_date` | datetime | Data validade | Opcional |
| `use_expiration_date` | boolean | Usa validade? | Config |

**IMPORTANTE**: O Odoo cria o stock.lot AUTOMATICAMENTE quando `lot_name` e preenchido
no stock.move.line e o picking e validado. NAO e necessario criar manualmente.

---

## quality.check (Verificacoes de Qualidade)

| Campo | Tipo | Descricao | Uso |
|-------|------|-----------|-----|
| `id` | integer | ID | Identificacao |
| `name` | char | Nome gerado | Display |
| `title` | char | Titulo legivel | Display |
| `picking_id` | many2one | Picking | Filtro |
| `product_id` | many2one | Produto (pode ser False) | Contexto |
| `point_id` | many2one (quality.point) | Template | Referencia |
| `quality_state` | selection | none, pass, fail | Resultado |
| `test_type` | char | "passfail" ou "measure" | Tipo |
| `test_type_id` | many2one | Tipo de teste | Referencia |
| `measure` | float | Valor medido (measure) | Input |
| `norm_unit` | char | Unidade (ex: "%", "mm") | Display |
| `tolerance_min` | float | Tolerancia minima | Validacao |
| `tolerance_max` | float | Tolerancia maxima | Validacao |

### Operacoes:

**Passfail - aprovar:**
```python
odoo.execute_kw('quality.check', 'do_pass', [[check_id]])
```

**Passfail - reprovar:**
```python
odoo.execute_kw('quality.check', 'do_fail', [[check_id]])
```

**Measure - preencher e avaliar:**
```python
odoo.write('quality.check', check_id, {'measure': 12.5})
odoo.execute_kw('quality.check', 'do_measure', [[check_id]])
```

---

## quality.point (Templates de Verificacao)

| Campo | Tipo | Descricao | Uso |
|-------|------|-----------|-----|
| `id` | integer | ID | Identificacao |
| `name` | char | Nome do ponto | Display |
| `test_type` | char | passfail ou measure | Tipo |
| `test_type_id` | many2one | Tipo de teste | Referencia |
| `product_ids` | many2many | Produtos especificos | Filtro |
| `product_category_ids` | many2many | Categorias | Filtro |
| `picking_type_ids` | many2many | Tipos de picking | Filtro |
| `measure_on` | selection | "operation" ou "product" | Config |

---

## product.product (Tracking)

| Campo | Tipo | Descricao | Valores |
|-------|------|-----------|---------|
| `tracking` | selection | Tipo de rastreio | 'none', 'lot', 'serial' |
| `use_expiration_date` | boolean | Produto usa data validade | True/False |

### Estatisticas do Banco (23/01/2026):
- **73.6%** dos produtos tem tracking='lot' (1191 de 1618)
- Produtos com tracking='serial' sao raros
- Produtos com tracking='none' nao precisam de lote

---

## Validacao do Picking (button_validate)

```python
try:
    odoo.execute_kw('stock.picking', 'button_validate', [[picking_id]])
except Exception as e:
    if 'cannot marshal None' in str(e):
        # SUCESSO! Padrao conhecido do Odoo
        # O retorno e None e xmlrpc nao consegue serializar
        pass
    else:
        raise
```

### Pre-requisitos para button_validate funcionar:
1. Picking `state='assigned'`
2. TODOS os stock.move.line com `lot_name` preenchido (se tracking=lot)
3. TODOS os stock.move.line com `quantity` > 0
4. TODOS os quality.check com `quality_state` != 'none' (se existirem)
