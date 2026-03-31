# Codigo Operacional — Transferencias Internas

Funcoes Python validadas em producao (30/03/2026). Usar como base para operacoes via XML-RPC.

## Helper: Preparar Extrato e Reconciliar

```python
from app.odoo.utils.connection import get_odoo_connection

odoo = get_odoo_connection()

def preparar_extrato_e_reconciliar(stmt_line_id, payment_pendentes_line_id, partner_id=1, ref=''):
    """Prepara extrato (draft→write→post) e reconcilia com payment."""

    # 1. Buscar move_id do extrato
    sl = odoo.execute_kw('account.bank.statement.line', 'search_read',
        [[['id', '=', stmt_line_id]]],
        {'fields': ['move_id'], 'limit': 1})
    move_id = sl[0]['move_id'][0]

    # 2. Draft
    try:
        odoo.execute_kw('account.move', 'button_draft', [[move_id]])
    except Exception as e:
        if "cannot marshal None" not in str(e): raise

    # 3. Write partner + payment_ref na statement_line
    odoo.execute_kw('account.bank.statement.line', 'write',
        [[stmt_line_id], {'partner_id': partner_id, 'payment_ref': ref}])

    # 4. Re-buscar move_lines (IDs podem ter mudado!)
    lines = odoo.execute_kw('account.move.line', 'search_read',
        [[['move_id', '=', move_id]]],
        {'fields': ['id', 'account_id', 'debit', 'credit']})

    # 5. Write name nas move_lines
    line_ids = [l['id'] for l in lines]
    odoo.execute_kw('account.move.line', 'write', [line_ids, {'name': ref}])

    # 6. Write account_id TRANSITORIA → PENDENTES (ULTIMO!)
    for l in lines:
        if l['account_id'][0] == 22199:  # TRANSITORIA
            odoo.execute_kw('account.move.line', 'write',
                [[l['id']], {'account_id': 26868}])  # PENDENTES
            extrato_pendentes_line_id = l['id']
            break

    # 7. Post
    try:
        odoo.execute_kw('account.move', 'action_post', [[move_id]])
    except Exception as e:
        if "cannot marshal None" not in str(e): raise

    # 8. Reconciliar
    try:
        odoo.execute_kw('account.move.line', 'reconcile',
            [[extrato_pendentes_line_id, payment_pendentes_line_id]], {})
    except Exception as e:
        if "cannot marshal None" not in str(e): raise

    # 9. Verificar
    sl = odoo.execute_kw('account.bank.statement.line', 'search_read',
        [[['id', '=', stmt_line_id]]],
        {'fields': ['is_reconciled', 'amount_residual'], 'limit': 1})
    return sl[0]['is_reconciled']
```

---

## Situacao 1: Criar is_internal_transfer + Conciliar Ambos

```python
def criar_transferencia_interna_e_conciliar(
    stmt_pag_id,      # ID statement_line do PAGAMENTO (amount < 0)
    stmt_rec_id,      # ID statement_line do RECEBIMENTO (amount > 0)
    journal_pag_id,   # journal_id do extrato de pagamento
    journal_rec_id,   # journal_id do extrato de recebimento
    amount,           # valor absoluto
    date,             # data da transferencia (str 'YYYY-MM-DD')
):
    """Situacao 1: cria is_internal_transfer e concilia ambos os extratos."""

    odoo = get_odoo_connection()

    # 1. Criar payment
    vals = {
        'payment_type': 'outbound',
        'amount': amount,
        'date': date,
        'journal_id': journal_pag_id,
        'destination_journal_id': journal_rec_id,
        'is_internal_transfer': True,
        'ref': f'Transf interna - extrato {stmt_pag_id}/{stmt_rec_id}',
    }
    payment_id = odoo.execute_kw('account.payment', 'create', [vals])

    # 2. Confirmar
    try:
        odoo.execute_kw('account.payment', 'action_post', [[payment_id]])
    except Exception as e:
        if "cannot marshal None" not in str(e): raise

    # 3. Buscar payment e paired
    payment = odoo.execute_kw('account.payment', 'search_read',
        [[['id', '=', payment_id]]],
        {'fields': ['move_id', 'paired_internal_transfer_payment_id'], 'limit': 1})[0]

    paired_id = payment['paired_internal_transfer_payment_id'][0]
    paired = odoo.execute_kw('account.payment', 'search_read',
        [[['id', '=', paired_id]]],
        {'fields': ['move_id'], 'limit': 1})[0]

    # 4. Buscar linhas PENDENTES de cada payment
    pag_lines = odoo.execute_kw('account.move.line', 'search_read',
        [[['move_id', '=', payment['move_id'][0]],
          ['account_id', '=', 26868],
          ['reconciled', '=', False]]],
        {'fields': ['id', 'debit', 'credit'], 'limit': 5})

    rec_lines = odoo.execute_kw('account.move.line', 'search_read',
        [[['move_id', '=', paired['move_id'][0]],
          ['account_id', '=', 26868],
          ['reconciled', '=', False]]],
        {'fields': ['id', 'debit', 'credit'], 'limit': 5})

    # Payment outbound no journal_pag: PENDENTES tem credit
    pag_pendentes = next(l for l in pag_lines if l['credit'] > 0)
    # Paired inbound no journal_rec: PENDENTES tem debit
    rec_pendentes = next(l for l in rec_lines if l['debit'] > 0)

    # 5. Conciliar extrato PAGAMENTO
    ref_pag = f'TRANSF-INT/{date}'
    ok_pag = preparar_extrato_e_reconciliar(
        stmt_pag_id, pag_pendentes['id'], partner_id=1, ref=ref_pag)

    # 6. Conciliar extrato RECEBIMENTO
    ok_rec = preparar_extrato_e_reconciliar(
        stmt_rec_id, rec_pendentes['id'], partner_id=1, ref=ref_pag)

    return {
        'payment_id': payment_id,
        'paired_id': paired_id,
        'pag_reconciled': ok_pag,
        'rec_reconciled': ok_rec,
    }
```

---

## Situacao 2: Encontrar Titulo e Conciliar Pagamento

```python
def conciliar_pagamento_transferencia_existente(stmt_pag_id, amount, date, journal_pag_id):
    """Situacao 2: recebimento ja conciliado, encontrar titulo do pagamento e conciliar."""

    odoo = get_odoo_connection()

    # 1. Buscar payment is_internal_transfer correspondente
    payments = odoo.execute_kw('account.payment', 'search_read',
        [[
            ['is_internal_transfer', '=', True],
            ['amount', '=', amount],
            ['date', '=', date],
            ['journal_id', '=', journal_pag_id],
            ['state', '=', 'posted'],
        ]],
        {'fields': ['id', 'name', 'move_id'], 'limit': 5})

    if not payments:
        # Tentar buscar pelo destination_journal_id
        payments = odoo.execute_kw('account.payment', 'search_read',
            [[
                ['is_internal_transfer', '=', True],
                ['amount', '=', amount],
                ['date', '=', date],
                ['state', '=', 'posted'],
            ]],
            {'fields': ['id', 'name', 'move_id', 'journal_id', 'destination_journal_id'],
             'limit': 10})
        payments = [p for p in payments
                    if p['journal_id'][0] == journal_pag_id
                    or p.get('destination_journal_id', [None])[0] == journal_pag_id]

    if not payments:
        return {'error': f'Payment is_internal_transfer nao encontrado para {amount} em {date}'}

    # 2. Buscar linha PENDENTES nao reconciliada
    for payment in payments:
        lines = odoo.execute_kw('account.move.line', 'search_read',
            [[
                ['move_id', '=', payment['move_id'][0]],
                ['account_id', '=', 26868],  # PENDENTES
                ['reconciled', '=', False],
            ]],
            {'fields': ['id', 'debit', 'credit'], 'limit': 5})

        pendentes = [l for l in lines if l['credit'] > 0 or l['debit'] > 0]
        if pendentes:
            target_line = pendentes[0]
            break
    else:
        return {'error': 'Nenhuma linha PENDENTES nao-reconciliada encontrada nos payments'}

    # 3. Conciliar
    ref = payment['name']
    ok = preparar_extrato_e_reconciliar(
        stmt_pag_id, target_line['id'], partner_id=1, ref=ref)

    return {
        'payment_id': payment['id'],
        'payment_name': payment['name'],
        'reconciled': ok,
    }
```

---

## Levantamento em Lote

```python
JOURNAL_MAP = {
    'GRAFENO': 883, 'SICOOB': 10, 'BRADESCO': 388,
    'AGIS GARANTIDA': 1046, 'AGIS': 1046,
    'BRADESCO (COPIA)': 1054, 'VORTX GRAFENO': 1068, 'VORTX': 1068,
}

def levantar_pares_transferencia_interna(data_inicio=None, data_fim=None, valor=None, journal=None):
    """Busca pares de transferencia interna pendentes, com filtros opcionais.

    Args:
        data_inicio: str 'YYYY-MM-DD' — data minima (inclusive)
        data_fim: str 'YYYY-MM-DD' — data maxima (inclusive)
        valor: float — filtrar por valor absoluto especifico
        journal: str ou int — nome do journal (ex: 'GRAFENO') ou ID (ex: 883)
    """

    odoo = get_odoo_connection()

    # Resolver journal por nome se necessario
    journal_id = None
    if journal:
        if isinstance(journal, str) and not journal.isdigit():
            journal_id = JOURNAL_MAP.get(journal.upper())
        else:
            journal_id = int(journal)

    # Montar domain base
    domain = [
        '|',
        ['payment_ref', 'ilike', 'NACOM GOYA'],
        ['payment_ref', 'ilike', '61.724.241'],
        ['is_reconciled', '=', False],
        ['to_check', '=', False],
    ]

    # Aplicar filtros opcionais
    if data_inicio:
        domain.append(['date', '>=', data_inicio])
    if data_fim:
        domain.append(['date', '<=', data_fim])
    if journal_id:
        domain.append(['journal_id', '=', journal_id])

    lines = odoo.execute_kw('account.bank.statement.line', 'search_read',
        [domain],
        {'fields': ['id', 'date', 'amount', 'payment_ref', 'journal_id'],
         'order': 'date asc'})

    # Filtrar exclusoes (FAV, Movimentacao)
    lines = [l for l in lines
             if 'FAV' not in (l['payment_ref'] or '').upper()
             and 'MOVIMENTAÇÃO' not in (l['payment_ref'] or '')
             and 'MOVIMENTACAO' not in (l['payment_ref'] or '').upper()]

    # Separar debitos e creditos
    debitos = [l for l in lines if l['amount'] < 0]
    creditos = [l for l in lines if l['amount'] > 0]

    # Filtrar por valor especifico (se fornecido)
    if valor:
        debitos = [l for l in debitos if abs(l['amount']) == valor]
        creditos = [l for l in creditos if l['amount'] == valor]

    # Matching: valor absoluto exato + data exata + journals diferentes
    pares = []
    creditos_usados = set()

    for d in debitos:
        for c in creditos:
            if c['id'] in creditos_usados:
                continue
            if (abs(d['amount']) == c['amount']
                and d['date'] == c['date']
                and d['journal_id'][0] != c['journal_id'][0]):
                pares.append({
                    'pag_id': d['id'],
                    'pag_journal': d['journal_id'],
                    'rec_id': c['id'],
                    'rec_journal': c['journal_id'],
                    'amount': abs(d['amount']),
                    'date': d['date'],
                })
                creditos_usados.add(c['id'])
                break

    return pares
```
