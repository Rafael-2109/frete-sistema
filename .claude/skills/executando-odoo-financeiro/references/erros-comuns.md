# Erros Comuns no Odoo Financeiro

Armadilhas encontradas durante a sessao de 22/01/2026 e como evita-las.

## Erro 1: "cannot marshal None"

### Sintoma
```
TypeError: cannot marshal None unless allow_none is enabled
```

### Causa
O Odoo retorna `None` em algumas operacoes, mas o XML-RPC nao consegue serializar `None`.

### Solucao
**IGNORAR ESTE ERRO!** A operacao foi executada com sucesso.

```python
try:
    result = odoo.execute_kw(...)
except Exception as e:
    if "cannot marshal None" not in str(e):
        raise
    # Operacao foi executada com sucesso, apenas o retorno e None
```

### Metodos que frequentemente geram este erro
- `account.payment.register.action_create_payments()`
- `account.move.line.reconcile()`

---

## Erro 2: Buscar NF pelo Campo Errado

### Sintoma
Buscar fatura por numero da NF retorna vazio:
```python
faturas = odoo.search_read(
    'account.move',
    [['name', 'ilike', '140743']],  # NAO FUNCIONA!
    ...
)
# Resultado: []
```

### Causa
O campo `name` do `account.move` contem o nome interno do Odoo (ex: `VND/2025/04382`), nao o numero da NF.

### Solucao
Buscar pelo campo `ref` ou por parceiro:

```python
# CORRETO: Buscar pelo ref
faturas = odoo.search_read(
    'account.move',
    [['ref', 'ilike', '140743']],
    ...
)

# CORRETO: Buscar linhas receivable do parceiro
linhas = odoo.search_read(
    'account.move.line',
    [
        ['partner_id', '=', partner_id],
        ['account_type', '=', 'asset_receivable'],
        ['reconciled', '=', False],
    ],
    ...
)
```

---

## Erro 3: Confundir IDs de Move vs Line

### Sintoma
Passar ID do `account.move` quando precisa do `account.move.line`:

```python
# ERRADO: Passando ID do move (384419)
wizard_context = {
    'active_ids': [384419],  # ID do account.move
}
# Resultado: Erro ou payment criado incorretamente

# CORRETO: Passando ID da linha (2514959)
wizard_context = {
    'active_ids': [2514959],  # ID do account.move.line
}
```

### Regra
- `account.payment.register` espera IDs de `account.move.line`
- `account.move.line.reconcile()` espera IDs de `account.move.line`

---

## Erro 4: Partner ID False no Statement Line

### Sintoma
O `partner_id` do statement line pode ser `False`:

```python
statement_line = odoo.search_read(
    'account.bank.statement.line',
    [['id', '=', 31615]],
    ['partner_id']
)
# Resultado: {'partner_id': False}
```

### Solucao
Buscar o `partner_id` do titulo ou da fatura:

```python
# Buscar pelo titulo
titulo = odoo.search_read(
    'account.move.line',
    [['id', '=', titulo_line_id]],
    ['partner_id']
)
partner_id = titulo[0]['partner_id'][0]
```

---

## Erro 5: Conta de Juros Errada por Empresa

### Sintoma
Payment criado com juros na conta errada, ou erro ao criar.

### Causa
Cada empresa tem sua propria conta de juros:

```python
# ERRADO: Usar conta fixa
conta_juros = 25345  # Funciona so para CD!

# CORRETO: Mapear por empresa
CONTA_JUROS_RECEBIMENTOS_POR_COMPANY = {
    1: 22778,  # NACOM GOYA - FB
    3: 24061,  # NACOM GOYA - SC
    4: 25345,  # NACOM GOYA - CD
    5: 26629,  # LA FAMIGLIA - LF
}
conta_juros = CONTA_JUROS_RECEBIMENTOS_POR_COMPANY[company_id]
```

---

## Erro 6: Extrato em Company Diferente do Titulo

### Sintoma
Extrato esta na company 1 (FB), mas titulo esta na company 4 (CD).

### Exemplo Real
```
Statement Line 31615: Company [1, 'NACOM GOYA - FB']
Titulo 2514959: Company [4, 'NACOM GOYA - CD']
```

### Solucao
O payment deve ser criado na empresa do TITULO (onde esta o receivable), nao na empresa do extrato.

```python
# Buscar empresa do titulo
titulo = odoo.search_read(
    'account.move.line',
    [['id', '=', titulo_line_id]],
    ['company_id']
)
company_id = titulo[0]['company_id'][0]

# Usar conta de juros da empresa CORRETA
conta_juros = CONTA_JUROS_RECEBIMENTOS_POR_COMPANY[company_id]
```

---

## Erro 7: Tentar Reconciliar Linhas Ja Reconciliadas

### Sintoma
Erro ao tentar reconciliar, ou nada acontece.

### Solucao
Sempre verificar `reconciled=False` antes:

```python
linhas = odoo.search_read(
    'account.move.line',
    [
        ['move_id', '=', move_id],
        ['reconciled', '=', False],  # CRITICO!
    ],
    ...
)
```

---

## Erro 8: Usar _criar_pagamento() em Vez de Wizard

### Sintoma
Criar payment com `_criar_pagamento()` mas nao reconciliar automaticamente com titulo.

### Causa
O metodo `_criar_pagamento()` cria payment em draft, precisa:
1. Postar manualmente
2. Buscar linha de credito
3. Reconciliar manualmente com titulo

### Solucao
**SEMPRE usar `_criar_pagamento_com_writeoff_juros()` ou wizard quando houver juros:**

```python
# ERRADO: Cria payment draft, nao reconcilia
payment_id = baixa_service._criar_pagamento(...)
baixa_service._postar_pagamento(payment_id)
# Ainda precisa reconciliar manualmente!

# CORRETO: Wizard faz TUDO automatico
wizard_id = odoo.execute_kw('account.payment.register', 'create', ...)
odoo.execute_kw('account.payment.register', 'action_create_payments', ...)
# Payment ja esta postado e reconciliado com titulo!
```

---

## Erro 9: Esquecer de Reconciliar Extrato

### Sintoma
Payment criado e titulo reconciliado, mas `is_reconciled=False` no statement line.

### Causa
O wizard reconcilia payment <-> titulo, mas NAO reconcilia payment <-> extrato.

### Solucao
Apos criar payment, reconciliar linha PENDENTES com linha TRANSITORIA:

```python
# Linha PENDENTES do payment (debito na conta 26868)
# Linha TRANSITORIA do extrato (credito na conta 22199)
odoo.execute_kw(
    'account.move.line',
    'reconcile',
    [[payment_pendentes_line_id, extrato_transitoria_line_id]],
    {}
)
```

---

## Erro 10: Buscar Payment pelo Valor Errado

### Sintoma
Apos criar payment, busca retorna vazio.

### Causa
Buscar pelo valor do titulo em vez do valor total (com juros):

```python
# ERRADO: Buscar pelo valor do titulo
payments = odoo.search_read(
    'account.payment',
    [['amount', '=', 1316.20]],  # Valor do titulo
    ...
)
# Resultado: []

# CORRETO: Buscar pelo valor TOTAL (com juros)
payments = odoo.search_read(
    'account.payment',
    [['amount', '=', 1342.52]],  # Valor pago (titulo + juros)
    ...
)
```

---

## Checklist de Verificacao

Antes de executar operacoes financeiras:

- [ ] Tenho o ID da `account.move.line` do titulo (nao do `account.move`)
- [ ] Tenho o ID do `res.partner` correto
- [ ] Sei a `company_id` do titulo
- [ ] Tenho a conta de juros correta para a empresa
- [ ] Tenho o ID da linha TRANSITORIA do extrato (nao do statement line)
- [ ] Verifico `reconciled=False` antes de tentar reconciliar
- [ ] Uso try/except para ignorar "cannot marshal None"
