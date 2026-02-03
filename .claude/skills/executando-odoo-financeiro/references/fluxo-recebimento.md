# Fluxo de Recebimento no Odoo

Documentacao completa do fluxo para criar pagamentos e reconciliar extratos.

## Passo 1: Identificar os IDs Necessarios

### 1.1 Buscar Titulo (Linha Receivable Nao Reconciliada)

```python
from app.odoo.utils.connection import get_odoo_connection

odoo = get_odoo_connection()

# Buscar linhas receivable nao reconciliadas de um cliente
linhas = odoo.search_read(
    'account.move.line',
    [
        ['partner_id', '=', partner_id],
        ['account_type', '=', 'asset_receivable'],  # CRITICO: tipo de conta
        ['company_id', '=', company_id],
        ['reconciled', '=', False],  # NAO reconciliadas
    ],
    ['id', 'name', 'ref', 'debit', 'amount_residual', 'move_id', 'date_maturity'],
    limit=20
)

# Resultado esperado:
# Line 2514959: VND/2025/04382 parcela no1
#   Move: [384419, 'NF-e: 140743 Serie: 1']
#   Debito: R$ 1.316,20 | Residual: R$ 1.316,20
```

**IMPORTANTE**: O `titulo_line_id` que voce precisa e o ID da `account.move.line` (ex: 2514959), NAO o ID do `account.move` (ex: 384419).

### 1.2 Buscar Statement Line (Extrato Nao Reconciliado)

```python
statement_lines = odoo.search_read(
    'account.bank.statement.line',
    [['id', '=', statement_line_id]],
    ['id', 'name', 'partner_id', 'amount', 'date', 'is_reconciled', 'move_id'],
    limit=1
)

# Resultado esperado:
# Statement Line 31615: GRA1/2026/00127
#   Valor: R$ 1.342,52 | Data: 2026-01-19
#   Reconciliado: False | Move: [472809, 'GRA1/2026/00127']
```

### 1.3 Buscar Linha Transitoria do Extrato

O statement line gera um `account.move` com linhas. A linha de CREDITO na conta TRANSITORIA (22199) e a que precisamos reconciliar:

```python
move_id = statement_line['move_id'][0]  # Ex: 472809

linhas_extrato = odoo.search_read(
    'account.move.line',
    [['move_id', '=', move_id]],
    ['id', 'name', 'account_id', 'debit', 'credit', 'amount_residual', 'reconciled'],
    limit=10
)

# Resultado esperado:
# 2968184: [22199, '1110100003 TRANSITORIA DE VALORES'] | D=0.00 C=1,342.52
#   Residual: -1,342.52 | Reconciled: False  <-- ESTA E A LINHA DO EXTRATO

extrato_transitoria_line_id = None
for l in linhas_extrato:
    if l['account_id'][0] == 22199:  # Conta TRANSITORIA
        extrato_transitoria_line_id = l['id']
        break
```

## Passo 2: Criar Pagamento

### 2.1 Calcular Juros

```python
valor_extrato = float(statement_line['amount'])  # Ex: 1342.52
saldo_titulo = float(titulo_line['amount_residual'])  # Ex: 1316.20
valor_juros = valor_extrato - saldo_titulo if valor_extrato > saldo_titulo else 0
# valor_juros = 26.32
```

### 2.2 COM Juros: Usar Wizard account.payment.register

**METODO RECOMENDADO** - O wizard faz tudo automaticamente:
- Cria o payment
- Posta o payment
- Reconcilia com o titulo
- Contabiliza juros na conta de receita

```python
# Mapeamento de conta de juros por empresa
CONTA_JUROS_RECEBIMENTOS_POR_COMPANY = {
    1: 22778,  # NACOM GOYA - FB
    3: 24061,  # NACOM GOYA - SC
    4: 25345,  # NACOM GOYA - CD
    5: 26629,  # LA FAMIGLIA - LF
}

conta_juros = CONTA_JUROS_RECEBIMENTOS_POR_COMPANY[company_id]

wizard_context = {
    'active_model': 'account.move.line',
    'active_ids': [titulo_line_id],  # ID da linha receivable
}

wizard_data = {
    'payment_type': 'inbound',          # Recebimento
    'partner_type': 'customer',         # Cliente
    'partner_id': partner_id,           # ID do res.partner
    'amount': valor_extrato,            # Valor TOTAL (principal + juros)
    'journal_id': 883,                  # GRAFENO
    'payment_date': '2026-01-19',       # Data do extrato
    'communication': 'NF-e: 140743 Serie: 1',
    'payment_difference_handling': 'reconcile',  # CRITICO!
    'writeoff_account_id': conta_juros,          # Conta de juros
    'writeoff_label': 'Juros de recebimento em atraso',
}

# Criar wizard
wizard_id = odoo.execute_kw(
    'account.payment.register',
    'create',
    [wizard_data],
    {'context': wizard_context}
)

print(f"Wizard criado: ID={wizard_id}")

# Executar wizard
try:
    result = odoo.execute_kw(
        'account.payment.register',
        'action_create_payments',
        [[wizard_id]],
        {'context': wizard_context}
    )
except Exception as e:
    if "cannot marshal None" not in str(e):
        raise
    # IMPORTANTE: Erro "cannot marshal None" e NORMAL!
    # O Odoo retorna None mas a operacao FOI executada com sucesso.
    result = None
```

### 2.3 Buscar Payment Criado

```python
payments = odoo.execute_kw(
    'account.payment',
    'search_read',
    [[
        ['partner_id', '=', partner_id],
        ['amount', '=', valor_extrato],  # Valor TOTAL
        ['journal_id', '=', 883],
        ['date', '=', '2026-01-19'],
    ]],
    {
        'fields': ['id', 'name', 'move_id', 'state'],
        'limit': 1
    }
)

payment = payments[0]
payment_id = payment['id']
payment_name = payment['name']  # Ex: PGRA1/2026/00063
payment_move_id = payment['move_id'][0]  # Ex: 474858

print(f"Payment criado: {payment_name} (ID={payment_id}, Move={payment_move_id})")
```

## Passo 3: Reconciliar Extrato

Apos criar o payment com wizard, o titulo JA esta reconciliado. Mas o extrato bancario ainda nao.

### 3.1 Buscar Linha PENDENTES do Payment

O payment cria um move com linhas. A linha de DEBITO na conta PENDENTES (26868) e a que precisamos:

```python
linhas_payment = odoo.search_read(
    'account.move.line',
    [
        ['move_id', '=', payment_move_id],
        ['account_id', '=', 26868],  # PENDENTES
    ],
    ['id', 'name', 'debit', 'credit', 'reconciled'],
    limit=5
)

payment_pendentes_line_id = None
for l in linhas_payment:
    if l['debit'] > 0 and not l['reconciled']:
        payment_pendentes_line_id = l['id']
        break

print(f"Linha PENDENTES do payment: {payment_pendentes_line_id}")
```

### 3.2 Reconciliar

```python
# Reconciliar:
# - Linha PENDENTES do payment (debito)
# - Linha TRANSITORIA do extrato (credito)

try:
    odoo.execute_kw(
        'account.move.line',
        'reconcile',
        [[payment_pendentes_line_id, extrato_transitoria_line_id]],
        {}
    )
    print("Reconciliacao realizada!")
except Exception as e:
    if "cannot marshal None" not in str(e):
        raise
    # Erro "cannot marshal None" = SUCESSO!
    print("Reconciliacao realizada (erro None ignorado)")
```

### 3.3 Corrigir Campos do Extrato (OBRIGATORIO)

Apos reconciliar, os 3 campos do extrato ficam incorretos para boletos.
**Sempre** executar:

1. Trocar conta TRANSITORIA → PENDENTES (ANTES de reconciliar, no passo 3.2)
2. Atualizar partner_id da statement line
3. Atualizar rotulo (payment_ref + name)

Ver `.claude/references/odoo/GOTCHAS.md` secao "Extrato Bancario: 3 Campos" para codigo completo.

## Passo 4: Verificar Resultado

```python
# Verificar statement line
sl = odoo.search_read(
    'account.bank.statement.line',
    [['id', '=', statement_line_id]],
    ['id', 'name', 'is_reconciled'],
    limit=1
)

if sl[0]['is_reconciled']:
    print(f"SUCESSO: Statement Line {statement_line_id} agora esta RECONCILIADO!")
else:
    print(f"ERRO: Statement Line {statement_line_id} ainda NAO esta reconciliado!")
```

## Codigo Completo Validado

Script que funcionou na sessao de 22/01/2026:

```python
"""
Script para criar pagamentos no Odoo com juros e vincular aos extratos.
TESTADO E FUNCIONANDO em 22/01/2026.
"""
from app import create_app
from app.odoo.utils.connection import get_odoo_connection

app = create_app()
with app.app_context():
    odoo = get_odoo_connection()

    # Dados para os pagamentos (obtidos previamente)
    pagamentos_a_criar = [
        {
            'titulo_line_id': 2514959,  # account.move.line do titulo
            'partner_id': 204534,        # res.partner
            'valor_titulo': 1316.20,
            'valor_pago': 1342.52,       # Valor do extrato
            'juros': 26.32,
            'journal_id': 883,           # GRAFENO
            'ref': 'NF-e: 140743 Serie: 1 - VND/2025/04382 - Parcela: 1',
            'data': '2026-01-19',
            'company_id': 4,             # NACOM GOYA - CD
            'conta_juros': 25345,        # Conta de juros CD
            'statement_line_id': 31615,
            'extrato_move_line_id': 2968184,  # Linha transitoria do extrato
        },
    ]

    for p in pagamentos_a_criar:
        print(f"Processando: {p['ref']}")

        # 1. Criar wizard
        wizard_context = {
            'active_model': 'account.move.line',
            'active_ids': [p['titulo_line_id']],
        }

        wizard_data = {
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': p['partner_id'],
            'amount': p['valor_pago'],
            'journal_id': p['journal_id'],
            'payment_date': p['data'],
            'communication': p['ref'],
            'payment_difference_handling': 'reconcile',
            'writeoff_account_id': p['conta_juros'],
            'writeoff_label': 'Juros de recebimento em atraso',
        }

        wizard_id = odoo.execute_kw(
            'account.payment.register',
            'create',
            [wizard_data],
            {'context': wizard_context}
        )

        # 2. Executar wizard
        try:
            odoo.execute_kw(
                'account.payment.register',
                'action_create_payments',
                [[wizard_id]],
                {'context': wizard_context}
            )
        except Exception as e:
            if "cannot marshal None" not in str(e):
                raise

        # 3. Buscar payment criado
        payments = odoo.execute_kw(
            'account.payment',
            'search_read',
            [[
                ['partner_id', '=', p['partner_id']],
                ['amount', '=', p['valor_pago']],
                ['journal_id', '=', p['journal_id']],
                ['date', '=', p['data']],
            ]],
            {
                'fields': ['id', 'name', 'move_id', 'state'],
                'limit': 1
            }
        )

        if payments:
            payment = payments[0]
            print(f"  Payment criado: {payment['name']} (ID={payment['id']})")

            # 4. Buscar linha PENDENTES
            linhas = odoo.search_read(
                'account.move.line',
                [
                    ['move_id', '=', payment['move_id'][0]],
                    ['account_id', '=', 26868],
                ],
                ['id', 'debit', 'reconciled'],
                limit=5
            )

            for l in linhas:
                if l['debit'] > 0 and not l['reconciled']:
                    # 5. Reconciliar com extrato
                    try:
                        odoo.execute_kw(
                            'account.move.line',
                            'reconcile',
                            [[l['id'], p['extrato_move_line_id']]],
                            {}
                        )
                    except Exception as e:
                        if "cannot marshal None" not in str(e):
                            raise
                    print(f"  Extrato reconciliado!")
                    break

        # 6. Verificar resultado
        sl = odoo.search_read(
            'account.bank.statement.line',
            [['id', '=', p['statement_line_id']]],
            ['is_reconciled'],
            limit=1
        )
        status = "RECONCILIADO" if sl[0]['is_reconciled'] else "NAO RECONCILIADO"
        print(f"  Statement Line {p['statement_line_id']}: {status}")
```

## Resumo dos IDs Importantes

### Modelos Odoo

| Modelo | Descricao | Exemplo |
|--------|-----------|---------|
| `res.partner` | Cliente/Fornecedor | 204534 (CACAO CONFEITARIA) |
| `account.move` | Lancamento contabil (NF, Payment) | 384419 (NF), 474858 (Payment) |
| `account.move.line` | Linha do lancamento | 2514959 (titulo), 2968184 (extrato) |
| `account.bank.statement.line` | Linha do extrato bancario | 31615 |
| `account.payment` | Payment (alto nivel) | 27431 |
| `account.payment.register` | Wizard de pagamento | Transiente |

### Contas Contabeis

| ID | Codigo | Nome | Tipo |
|----|--------|------|------|
| 26868 | 1110100004 | PENDENTES | Contrapartida payment |
| 22199 | 1110100003 | TRANSITORIA | Contrapartida extrato |
| 24801 | 1120100001 | CLIENTES NACIONAIS | Receivable |
| 22778 | 3702010003 | JUROS RECEBIMENTOS (FB) | Receita |
| 24061 | 3702010003 | JUROS RECEBIMENTOS (SC) | Receita |
| 25345 | 3702010003 | JUROS RECEBIMENTOS (CD) | Receita |
| 26629 | 3702010003 | JUROS RECEBIMENTOS (LF) | Receita |

### Journal

| ID | Codigo | Nome | Empresa |
|----|--------|------|---------|
| 883 | GRAFENO | Banco Grafeno | Todas |
