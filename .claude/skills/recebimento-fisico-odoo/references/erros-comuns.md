# Erros Comuns no Recebimento Fisico

## Erros Descobertos e Documentados nesta Implementacao

---

## ERRO 1: "cannot marshal None" no button_validate

### Sintoma
```
xmlrpc.client.Fault: cannot marshal None unless allow_none is enabled
```

### Causa
O `button_validate` do stock.picking retorna `None` em caso de sucesso.
O xmlrpc do Python nao consegue serializar `None` por padrao.

### Solucao
```python
try:
    odoo.execute_kw('stock.picking', 'button_validate', [[picking_id]])
except Exception as e:
    if 'cannot marshal None' in str(e):
        pass  # SUCESSO! Padrao conhecido
    else:
        raise
```

---

## ERRO 2: Usar `odoo.execute()` em vez de `odoo.execute_kw()`

### Sintoma
```
AttributeError: 'OdooConnection' object has no attribute 'execute'
```

### Causa
A classe `OdooConnection` (app/odoo/utils/connection.py) NAO possui metodo `execute()`.

### Codigo ERRADO
```python
# ❌ NAO EXISTE
odoo.execute('stock.picking', 'button_validate', [picking_id])
```

### Codigo CORRETO
```python
# ✅ CORRETO
odoo.execute_kw('stock.picking', 'button_validate', [[picking_id]])
```

### Metodos disponiveis na OdooConnection:
- `execute_kw(model, method, args, kwargs=None)` - GENERICO
- `search(model, domain, limit=None)` - wrapper
- `read(model, ids, fields)` - wrapper
- `write(model, id_ou_ids, values)` - wrapper
- `create(model, values)` - wrapper
- `authenticate()` - autenticacao

---

## ERRO 3: button_validate falha por quality checks pendentes

### Sintoma
```
UserError: You need to pass the quality checks before validating
```

### Causa
Existem quality.check vinculados ao picking com `quality_state='none'`.
O Odoo exige que TODOS os checks estejam com pass ou fail antes de validar.

### Solucao
Processar TODOS os quality checks ANTES de chamar button_validate:
```python
# 1. Processar passfail
for check in checks_passfail:
    if check.resultado == 'pass':
        odoo.execute_kw('quality.check', 'do_pass', [[check.odoo_check_id]])
    else:
        odoo.execute_kw('quality.check', 'do_fail', [[check.odoo_check_id]])

# 2. Processar measure
for check in checks_measure:
    odoo.write('quality.check', check.odoo_check_id, {'measure': check.valor_medido})
    odoo.execute_kw('quality.check', 'do_measure', [[check.odoo_check_id]])

# 3. SO ENTAO validar
odoo.execute_kw('stock.picking', 'button_validate', [[picking_id]])
```

---

## ERRO 4: Lote duplicado (lot_name ja existe)

### Sintoma
```
ValidationError: The lot/serial number LOTE-001 already exists for product X
```
(pode variar, depende da versao do Odoo)

### Causa
O lote ja foi criado em um recebimento anterior. Ao usar `lot_name`, o Odoo
tenta criar um novo stock.lot, mas nome+produto deve ser unico.

### Solucao
Verificar se o lote ja existe ANTES de usar lot_name:
```python
lote_existente = odoo.search('stock.lot', [
    ['name', '=', lote_nome],
    ['product_id', '=', product_id],
])

if lote_existente:
    # Usar lot_id em vez de lot_name
    odoo.write('stock.move.line', line_id, {
        'lot_id': lote_existente[0],
        'quantity': quantidade,
    })
else:
    # Criar via lot_name (Odoo cria automaticamente)
    odoo.write('stock.move.line', line_id, {
        'lot_name': lote_nome,
        'quantity': quantidade,
    })
```

### NOTA:
Na implementacao atual, usamos sempre `lot_name` que cria automaticamente.
Se aparecer erro de duplicata, adicionar a verificacao acima.

---

## ERRO 5: Create stock.move.line falha por falta de campos obrigatorios

### Sintoma
```
ValidationError: Missing required fields: location_id, location_dest_id
```

### Causa
Ao criar stock.move.line adicional (para lotes extras), os campos `location_id`
e `location_dest_id` sao obrigatorios.

### Solucao
Buscar locations do picking:
```python
picking_data = odoo.read('stock.picking', [picking_id], ['location_id', 'location_dest_id'])
location_id = picking_data[0]['location_id'][0]
location_dest_id = picking_data[0]['location_dest_id'][0]

odoo.execute_kw('stock.move.line', 'create', [{
    'picking_id': picking_id,
    'move_id': move_id,
    'product_id': product_id,
    'lot_name': lote_nome,
    'quantity': quantidade,
    'location_id': location_id,           # OBRIGATORIO
    'location_dest_id': location_dest_id,  # OBRIGATORIO
}])
```

---

## ERRO 6: Picking ja foi validado (state != assigned)

### Sintoma
```
UserError: This picking is already done/cancelled
```

### Causa
Outro usuario ou processo ja validou o picking no Odoo.

### Solucao
Verificar state ANTES de qualquer operacao:
```python
picking = odoo.read('stock.picking', [picking_id], ['state', 'name'])
if picking[0]['state'] != 'assigned':
    raise ValueError(
        f"Picking {picking[0]['name']} nao esta pronto "
        f"(state={picking[0]['state']}, esperado=assigned)"
    )
```

---

## ERRO 7: Soma dos lotes != quantidade esperada

### Sintoma
Na API local:
```json
{"error": "Validacao de lotes falhou", "erros_lotes": [...]}
```

### Causa
O operador preencheu lotes cuja soma nao bate com product_uom_qty do stock.move.

### Solucao
Validacao ja implementada no service:
```python
from decimal import Decimal

qtd_esperada = Decimal(str(produto['qtd_esperada']))
soma_lotes = sum(Decimal(str(l['quantidade'])) for l in produto['lotes'])

if abs(soma_lotes - qtd_esperada) >= Decimal('0.001'):
    erros.append(f"Produto {nome}: soma {soma_lotes} != esperado {qtd_esperada}")
```

---

## ERRO 8: Lock anti-duplicata impede processamento

### Sintoma
No log do worker:
```
Lock nao obtido para picking_id=123. Ja em processamento.
```

### Causa
Outro job ja esta processando o mesmo picking.
Lock Redis: `recebimento_lock:{picking_id}` com TTL 30min.

### Solucao
1. Aguardar TTL expirar (30 min)
2. Ou remover lock manualmente:
```python
import redis
r = redis.from_url(os.environ.get('REDIS_URL', 'redis://localhost:6379'))
r.delete(f'recebimento_lock:{picking_id}')
```
3. Ou verificar se o job anterior finalizou com sucesso

---

## ERRO 9: Job RQ timeout (>10 min)

### Sintoma
```
rq.timeouts.JobTimeoutException: Task exceeded maximum timeout
```

### Causa
Picking com muitos produtos/lotes levou mais de 10 min para processar.

### Solucao
O timeout esta configurado em 600s (10 min) no job:
```python
queue.enqueue(
    processar_recebimento_job,
    recebimento_id,
    job_timeout=600,  # 10 minutos
)
```
Se necessario, aumentar para pickings grandes ou otimizar batch de writes.

---

## ERRO 10: Campo `reserved_uom_qty` nao existe em stock.move.line

### Sintoma
```
ValueError: Invalid field 'reserved_uom_qty' on model 'stock.move.line'
```

### Causa
O campo `reserved_uom_qty` NAO existe nesta versao do Odoo para o modelo `stock.move.line`.
Os campos de quantidade disponiveis sao:
- `quantity` — quantidade reservada/atribuida
- `qty_done` — quantidade realizada (feita)
- `product_packaging_qty` — quantidade de embalagem reservada (nao relacionado)

### Codigo ERRADO
```python
# ❌ CAMPO NAO EXISTE
campos = ['id', 'picking_id', 'product_id', 'move_id',
          'lot_id', 'lot_name', 'quantity', 'reserved_uom_qty',  # ERRO
          'product_uom_id', 'location_id', 'location_dest_id']
```

### Codigo CORRETO
```python
# ✅ USAR qty_done
campos = ['id', 'picking_id', 'product_id', 'move_id',
          'lot_id', 'lot_name', 'quantity', 'qty_done',
          'product_uom_id', 'location_id', 'location_dest_id']
```

### Mapeamento Local
A coluna local `reserved_uom_qty` (tabela `picking_recebimento_move_line`)
armazena o valor de `qty_done` do Odoo:
```python
move_line = PickingRecebimentoMoveLine(
    ...
    quantity=ml.get('quantity', 0),
    reserved_uom_qty=ml.get('qty_done', 0),  # Mapeia qty_done → coluna local
    ...
)
```

### Campos Disponiveis (Verificados)
Resultado de `--buscar-campo qty` no modelo `stock.move.line`:
- `product_packaging_qty` (float) — Reserved Packaging Quantity
- `product_packaging_uom_qty` (float) — Packaging Quantity (UoM do Stock Move Line)
- `qty_done` (float) — Qty Done
