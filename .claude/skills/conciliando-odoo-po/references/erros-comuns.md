# Erros Comuns na Conciliacao PO x DFe

## Erros Descobertos e Corrigidos nesta Implementacao

---

## ERRO 1: Usar `odoo.execute()` em vez de `odoo.execute_kw()`

### Sintoma
```
AttributeError: 'OdooConnection' object has no attribute 'execute'
```

### Causa
A classe `OdooConnection` (app/odoo/utils/connection.py) NAO possui metodo `execute()`.
Existe APENAS `execute_kw()`.

### Codigo ERRADO
```python
# ❌ NAO EXISTE
odoo.execute('purchase.order', 'button_confirm', [po_id])
odoo.execute('purchase.order', 'button_cancel', [po_id])
```

### Codigo CORRETO
```python
# ✅ CORRETO
odoo.execute_kw('purchase.order', 'button_confirm', [po_id])
odoo.execute_kw('purchase.order', 'button_cancel', [po_id])
```

### Metodos disponiveis na OdooConnection:
- `execute_kw(model, method, args, kwargs=None)` - GENERICO
- `search(model, domain, limit=None)` - wrapper
- `read(model, ids, fields)` - wrapper
- `write(model, id_ou_ids, values)` - wrapper
- `create(model, values)` - wrapper
- `authenticate()` - autenticacao

---

## ERRO 2: Criar PO via `create()` esquecendo campos obrigatorios

### Sintoma
```
xmlrpc.client.Fault: Required field(s) missing: payment_term_id, fiscal_position_id
```
ou PO criado com dados incompletos (sem empresa, sem condicao pgto, sem campos fiscais BR).

### Causa
Ao usar `create()`, voce precisa especificar TODOS os campos obrigatorios manualmente.
Campos fiscais brasileiros (l10n_br_*) sao facilmente esquecidos.

### Codigo ERRADO
```python
# ❌ FRAGIL - esquece campos obrigatorios
po_ref = odoo.read('purchase.order', [po_ref_id],
                   ['picking_type_id', 'company_id'])

novo_po_data = {
    'partner_id': fornecedor_id,
    'date_order': data_nf,
    'origin': 'Conciliacao NF ...',
    'state': 'draft',
    'picking_type_id': po_ref[0]['picking_type_id'][0],
    # ⚠️ FALTAM: payment_term_id, fiscal_position_id, currency_id,
    #            l10n_br_*, user_id, incoterm_id, etc.
}
novo_po_id = odoo.create('purchase.order', novo_po_data)
```

### Codigo CORRETO
```python
# ✅ ROBUSTO - copia TODOS os campos automaticamente
novo_po_id = odoo.execute_kw(
    'purchase.order', 'copy', [po_referencia_id],
    {'default': {
        'partner_id': fornecedor_id,
        'date_order': data_nf,
        'origin': 'Conciliacao NF ...',
        'state': 'draft',
        'order_line': False,
    }}
)
```

---

## ERRO 3: Chamar `unlink` com formato errado

### Sintoma
```
xmlrpc.client.Fault: Expected singleton or list of IDs
```

### Causa
O metodo `unlink` espera uma lista de IDs como argumento posicional,
nao IDs individuais em loop.

### Codigo ERRADO
```python
# ❌ Loop desnecessario com formato incorreto
for linha_id in linhas_existentes:
    odoo.execute_kw('purchase.order.line', 'unlink', [[linha_id]])
```

### Codigo CORRETO
```python
# ✅ Uma unica chamada com lista de IDs
odoo.execute_kw('purchase.order.line', 'unlink', [linhas_existentes])
# linhas_existentes = [1, 2, 3, ...]  (lista de IDs)
```

---

## ERRO 4: Linhas do PO de referencia vs linhas individuais

### Sintoma
Linhas do PO Conciliador com CFOP/impostos errados (herdam do PO-1 quando deveriam
herdar do PO-2 ou PO-3).

### Causa
Ao consolidar 3 POs, cada linha deve ser copiada da SUA origem,
nao da linha do PO de referencia.

### Codigo ERRADO
```python
# ❌ Copia TODAS as linhas do PO de referencia
# Resultado: Produto B fica com CFOP do PO-1 em vez do PO-2
for match in matches:
    nova_linha_id = odoo.execute_kw(
        'purchase.order.line', 'copy',
        [linha_do_po_referencia],  # ← ERRADO: sempre a mesma linha
        {'default': {'order_id': po_conciliador_id, ...}}
    )
```

### Codigo CORRETO
```python
# ✅ Copia cada linha da SUA origem individual
for match in matches:
    for aloc in match.alocacoes:
        nova_linha_id = odoo.execute_kw(
            'purchase.order.line', 'copy',
            [aloc.odoo_po_line_id],  # ← CORRETO: linha especifica de cada PO
            {'default': {
                'order_id': po_conciliador_id,
                'product_qty': float(aloc.qtd_alocada),
                'price_unit': preco_nf,
            }}
        )
```

---

## ERRO 5: `order_line: False` pode nao funcionar em todas as versoes

### Sintoma
Apos `copy()`, PO Conciliador tem linhas duplicadas do PO original + linhas novas.

### Causa
Em algumas versoes/customizacoes do Odoo, `order_line: False` no `default` do `copy()`
pode ser ignorado, e as linhas do PO original sao copiadas junto.

### Mitigacao (ja implementada)
```python
# Apos copy(), verificar e remover linhas indesejadas:
linhas_existentes = odoo.search(
    'purchase.order.line',
    [[('order_id', '=', novo_po_id)]]
)
if linhas_existentes:
    odoo.execute_kw('purchase.order.line', 'unlink', [linhas_existentes])
```

---

## ERRO 6: Nao acumular consumo de mesma linha

### Sintoma
Saldo do PO original fica maior que deveria quando 2 itens da NF
consomem da mesma linha de PO.

### Causa
Se 2 itens da NF alocam da mesma `odoo_po_line_id`, cada write()
individual nao considera o consumo do anterior.

### Codigo ERRADO
```python
# ❌ Cada iteracao calcula saldo SEM considerar consumo anterior
for aloc in alocacoes:
    saldo = qtd_po_original - qtd_alocada
    odoo.write(line_id, {'product_qty': saldo})
    # Se 2 alocacoes na mesma linha: segundo calculo ignora primeiro
```

### Codigo CORRETO
```python
# ✅ Acumula consumo total por linha
linhas_processadas = {}  # Cache: {po_line_id: qtd_total_consumida}

for aloc in alocacoes:
    consumo_anterior = linhas_processadas.get(aloc.odoo_po_line_id, Decimal('0'))
    consumo_total = consumo_anterior + qtd_alocada
    linhas_processadas[aloc.odoo_po_line_id] = consumo_total

    saldo = qtd_po_original - qtd_recebida - consumo_total
    odoo.write(line_id, {'product_qty': max(saldo, 0)})
```

---

## ERRO 7: button_confirm pode falhar em PO sem linhas

### Sintoma
```
xmlrpc.client.Fault: Cannot confirm order with empty lines
```

### Causa
Se o PO Conciliador nao tem linhas (ex: todas as `_criar_linha_po_conciliador()`
falharam), nao e possivel confirma-lo.

### Mitigacao
```python
try:
    odoo.execute_kw('purchase.order', 'button_confirm', [po_conciliador_id])
except Exception as e:
    logger.warning(f"Nao foi possivel confirmar PO automaticamente: {e}")
    # NAO falhar a operacao por isso - PO fica em draft
```

---

## ERRO 8: CNPJ formatado vs nao formatado

### Sintoma
Fornecedor nao encontrado no Odoo mesmo com CNPJ correto.

### Causa
O Odoo armazena CNPJ no campo `l10n_br_cnpj` com formatacao: `XX.XXX.XXX/XXXX-XX`
Buscar com CNPJ sem formatacao (`XXXXXXXXXXXXXX`) nao encontra.

### Codigo CORRETO
```python
cnpj_limpo = ''.join(c for c in str(cnpj_fornecedor) if c.isdigit())

def formatar_cnpj(cnpj: str) -> str:
    if len(cnpj) == 14:
        return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:14]}"
    return cnpj

cnpj_formatado = formatar_cnpj(cnpj_limpo)
partner_ids = odoo.search(
    'res.partner',
    [('l10n_br_cnpj', '=', cnpj_formatado)],
    limit=1
)
```

---

## ERRO 9: Decimal vs float em calculos de quantidade

### Sintoma
Quantidades com casas decimais imprecisas (ex: 99.99999999 em vez de 100.0)

### Causa
Usar float para aritmetica monetaria/quantitativa causa imprecisao.

### Codigo CORRETO
```python
from decimal import Decimal

qtd_po = Decimal(str(linha['product_qty'] or 0))
qtd_recebida = Decimal(str(linha['qty_received'] or 0))
qtd_alocada = Decimal(str(aloc.qtd_alocada or 0))

saldo = qtd_po - qtd_recebida - qtd_alocada
nova_qtd = float(saldo) if saldo > 0 else 0  # Converte para float so no final
```

---

## Checklist de Depuracao

Quando uma consolidacao falhar, verificar nesta ordem:

1. **Autenticacao**: `odoo.authenticate()` retornou True?
2. **Fornecedor**: CNPJ formatado encontrado em `res.partner`?
3. **PO de referencia**: `pos_para_consolidar[0]['po_id']` existe no Odoo?
4. **copy() funcionou**: `novo_po_id` nao e None?
5. **Linhas limpas**: PO Conciliador esta sem linhas apos copy()?
6. **Linhas de referencia**: Cada `aloc.odoo_po_line_id` existe e tem `product_id`?
7. **Quantidades**: `product_qty` e `qty_received` sao numeros validos?
8. **Confirmar PO**: PO tem pelo menos 1 linha antes de `button_confirm`?
9. **Vinculo DFe**: Campo `dfe_id` existe no modelo `purchase.order`?

## Logs Uteis

```python
# Ativar logs detalhados:
import logging
logging.getLogger('app.recebimento.services.odoo_po_service').setLevel(logging.DEBUG)

# Logs importantes no fluxo:
# "Iniciando SPLIT/CONSOLIDACAO: validacao X, N POs envolvidos"
# "PO Conciliador PO12345 criado via copy() (baseado em PO 100)"
# "copy() criou N linhas indesejadas, removendo..."
# "Linha criada no PO Conciliador via copy(): produto X, qtd Y, preco Z"
# "Linha 101 ajustada para 100.0"
# "PO Conciliador PO12345 confirmado"
# "SPLIT/CONSOLIDACAO concluida: PO Conciliador PO12345 criado, N linhas, M POs com saldo"
```
