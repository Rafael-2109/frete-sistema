# Fluxo Validado — Transferencias Internas

Codigo testado em producao em 30/03/2026.

## Teste 1: Situacao 1 (criar + conciliar ambos)

**Par**: 32931 (SICOOB, -R$127.501,40) / 17855 (BRADESCO, +R$127.501,40), data 30/09/2025

### Sequencia executada:

```python
from app.odoo.utils.connection import get_odoo_connection
odoo = get_odoo_connection()

# 1. Criar payment is_internal_transfer
payment_id = odoo.execute_kw('account.payment', 'create', [{
    'payment_type': 'outbound',
    'amount': 127501.40,
    'date': '2025-09-30',
    'journal_id': 10,        # SICOOB (pagamento)
    'destination_journal_id': 388,  # BRADESCO (recebimento)
    'is_internal_transfer': True,
    'ref': 'Transf interna - extrato 32931/17855',
}])
# Resultado: payment_id = 40784

# 2. Confirmar
odoo.execute_kw('account.payment', 'action_post', [[payment_id]])
# Odoo gerou automaticamente paired payment 40785 (PBRAD/2025/00249)
# Linhas TRANSITORIA auto-reconciliadas (full_reconcile 62334)

# 3. Buscar linhas PENDENTES
# Payment 40784 move 541985: line 3370239 (PENDENTES, credit=127501.40)
# Payment 40785 move 541986: line 3370241 (PENDENTES, debit=127501.40)

# 4. Conciliar extrato 32931 (SICOOB debito)
odoo.execute_kw('account.move', 'button_draft', [[491381]])  # move do extrato
# Trocar TRANSITORIA → PENDENTES na move.line 3075574
odoo.execute_kw('account.move.line', 'write', [[3075574], {'account_id': 26868}])
odoo.execute_kw('account.move', 'action_post', [[491381]])
odoo.execute_kw('account.move.line', 'reconcile', [[3075574, 3370239]], {})
# full_reconcile 62335

# 5. Conciliar extrato 17855 (BRADESCO credito)
odoo.execute_kw('account.move', 'button_draft', [[421255]])
odoo.execute_kw('account.move.line', 'write', [[2719239], {'account_id': 26868}])
odoo.execute_kw('account.move', 'action_post', [[421255]])
odoo.execute_kw('account.move.line', 'reconcile', [[2719239, 3370241]], {})
# full_reconcile 62336
```

### Verificacao:
- 32931: is_reconciled=True, amount_residual=0
- 17855: is_reconciled=True, amount_residual=0

---

## Teste 2: Situacao 2 (pagamento pendente, recebimento ja conciliado)

**Extrato**: 10050 (GRAFENO, -R$5.203,82), data 08/09/2025

### Sequencia executada:

```python
# 1. Buscar payment existente
# Payment 36963 (PGRA1/2025/05319), outbound, GRAFENO→SICOOB
# Move 503379, line 3134195 (PENDENTES, credit=5203.82, reconciled=False)

# 2. Preparar extrato (6 passos)
odoo.execute_kw('account.move', 'button_draft', [[351156]])  # move extrato

odoo.execute_kw('account.bank.statement.line', 'write',
    [[10050], {'partner_id': 1, 'payment_ref': 'PGRA1/2025/05319'}])

# Re-buscar move lines (IDs podem mudar!)
odoo.execute_kw('account.move.line', 'write',
    [[3370303, 3370304], {'name': 'PGRA1/2025/05319'}])

# account_id ULTIMO!
odoo.execute_kw('account.move.line', 'write',
    [[3370304], {'account_id': 26868}])  # TRANSITORIA → PENDENTES

odoo.execute_kw('account.move', 'action_post', [[351156]])

# 3. Reconciliar
odoo.execute_kw('account.move.line', 'reconcile', [[3370304, 3134195]], {})
# full_reconcile 62337
```

### Verificacao:
- 10050: is_reconciled=True, amount_residual=0

---

## Padroes Confirmados

1. `is_internal_transfer=True` gera 2 payments pareados via `paired_internal_transfer_payment_id`
2. Odoo auto-reconcilia linhas TRANSITORIA entre os 2 moves
3. Linhas PENDENTES (26868) ficam disponiveis para conciliar com extratos
4. Extratos usam TRANSITORIA (22199) — necessario trocar para PENDENTES antes de reconciliar
5. Write na statement_line (partner/ref) pode regenerar move_lines — re-buscar IDs!
6. account_id DEVE ser ULTIMO write antes de action_post
7. partner_id=1 (NACOM GOYA - FB) funciona para transferencias internas
8. "cannot marshal None" em action_post/reconcile = SUCESSO (ignorar)
