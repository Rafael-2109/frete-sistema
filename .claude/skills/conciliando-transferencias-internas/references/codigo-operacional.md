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
        # Busca direta falhou — sugerir rastreamento de cadeia (Sit 2b)
        return {
            'error': f'Payment is_internal_transfer nao encontrado para {amount} em {date}',
            'fallback': 'Usar rastrear_cadeia_documental(stmt_pag_id) para busca via cadeia documental',
        }

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

## Situacao 2b: Rastreamento de Cadeia Documental

Quando Situacao 2 falha (payment nao encontrado por valor/data), rastrear a cadeia
documental pelo lado do recebimento para encontrar o payment correto.

**Quando usar**: Debito pendente cujo credito no destino JA foi reconciliado com payment
de valor agregado (consolidado) ou data divergente.

**Cadeia**: `stmt_pag (pendente) → destino (payment_ref) → stmt_rec (reconciliado)
→ move_line PENDENTES → partial_reconcile → payment move_line → payment
→ paired_payment → move_line PENDENTES (nao reconciliada) → reconciliar`

```python
def rastrear_cadeia_documental(stmt_line_id):
    """Rastreia cadeia documental de extrato pendente ate encontrar payment.

    Retorna dict com 'found', 'payment_rec', 'paired_payment', 'pendentes_line_id',
    'date_mismatch', 'amount_mismatch', 'is_partial'. Ou dict com 'error'.
    NAO executa reconciliacao — apenas diagnostica.
    """
    odoo = get_odoo_connection()

    # 1. Info do stmt pendente
    stmt = odoo.execute_kw('account.bank.statement.line', 'search_read',
        [[['id', '=', stmt_line_id]]],
        {'fields': ['id', 'move_id', 'amount', 'date', 'payment_ref',
                    'journal_id', 'is_reconciled'],
         'limit': 1})
    if not stmt or stmt[0]['is_reconciled']:
        return None
    stmt = stmt[0]

    # 2. Extrair journal destino do payment_ref
    dest_journal_id = _extrair_journal_destino(stmt['payment_ref'])
    if not dest_journal_id:
        return {'error': f'Journal destino nao identificado em: {stmt["payment_ref"]}'}

    # 3. Buscar creditos reconciliados no destino (mesmo valor absoluto, mesma data)
    creditos = odoo.execute_kw('account.bank.statement.line', 'search_read', [[
        ['journal_id', '=', dest_journal_id],
        ['date', '=', stmt['date']],
        ['amount', '=', abs(stmt['amount'])],
        ['is_reconciled', '=', True],
    ]], {'fields': ['id', 'move_id'], 'order': 'id asc'})

    if not creditos:
        return {'error': f'Nenhum credito reconciliado de {abs(stmt["amount"])} '
                        f'em {stmt["date"]} no journal {dest_journal_id}'}

    # 4. Para cada credito, rastrear: move_line → partial_reconcile → payment
    for credito in creditos:
        mls = odoo.execute_kw('account.move.line', 'search_read', [[
            ['move_id', '=', credito['move_id'][0]],
            ['reconciled', '=', True],
        ]], {'fields': ['id', 'account_id']})

        for ml in mls:
            partials = odoo.execute_kw('account.partial.reconcile', 'search_read', [[
                '|',
                ['debit_move_id', '=', ml['id']],
                ['credit_move_id', '=', ml['id']],
            ]], {'fields': ['debit_move_id', 'credit_move_id']})

            for p in partials:
                counterpart_id = (p['debit_move_id'][0]
                                  if p['credit_move_id'][0] == ml['id']
                                  else p['credit_move_id'][0])

                cml = odoo.execute_kw('account.move.line', 'search_read',
                    [[['id', '=', counterpart_id]]],
                    {'fields': ['move_id']})[0]

                payment = odoo.execute_kw('account.payment', 'search_read', [[
                    ['move_id', '=', cml['move_id'][0]],
                    ['is_internal_transfer', '=', True],
                ]], {'fields': ['id', 'name', 'date', 'amount',
                               'paired_internal_transfer_payment_id']})

                if not payment:
                    continue
                payment = payment[0]

                paired_id = payment.get('paired_internal_transfer_payment_id')
                if not paired_id:
                    continue
                paired_id = paired_id[0]

                paired = odoo.execute_kw('account.payment', 'search_read',
                    [[['id', '=', paired_id]]],
                    {'fields': ['id', 'name', 'move_id', 'date', 'amount']})[0]

                # Buscar PENDENTES nao reconciliada no paired payment
                pendentes = odoo.execute_kw('account.move.line', 'search_read', [[
                    ['move_id', '=', paired['move_id'][0]],
                    ['account_id', '=', 26868],
                    ['reconciled', '=', False],
                ]], {'fields': ['id', 'debit', 'credit', 'amount_residual']})

                if not pendentes:
                    continue

                return {
                    'found': True,
                    'stmt_line_id': stmt_line_id,
                    'stmt_date': stmt['date'],
                    'stmt_amount': abs(stmt['amount']),
                    'credito_stmt_id': credito['id'],
                    'payment_rec': {
                        'id': payment['id'],
                        'name': payment['name'],
                        'date': payment['date'],
                        'amount': payment['amount'],
                    },
                    'paired_payment': {
                        'id': paired['id'],
                        'name': paired['name'],
                        'date': paired['date'],
                        'amount': paired['amount'],
                    },
                    'pendentes_line_id': pendentes[0]['id'],
                    'pendentes_residual': abs(
                        pendentes[0].get('amount_residual')
                        or pendentes[0]['credit']
                        or pendentes[0]['debit']
                    ),
                    'date_mismatch': paired['date'] != stmt['date'],
                    'amount_mismatch': paired['amount'] != abs(stmt['amount']),
                    'is_partial': paired['amount'] != abs(stmt['amount']),
                }

    return {'error': 'Cadeia documental nao encontrada para nenhum credito'}
```

### Execucao apos diagnostico

Quando `rastrear_cadeia_documental()` retorna `found=True`:

```python
# Se date_mismatch=False e amount_mismatch=False: executar direto
resultado = rastrear_cadeia_documental(stmt_pag_id)
if resultado.get('found'):
    ok = preparar_extrato_e_reconciliar(
        stmt_pag_id,
        resultado['pendentes_line_id'],
        partner_id=1,
        ref=resultado['paired_payment']['name']
    )

# Se date_mismatch=True ou is_partial=True: REPORTAR ao usuario ANTES
# "Payment {name} tem data {date} (extrato: {stmt_date}). Valor payment: {amount}
#  (extrato: {stmt_amount}). Confirma reconciliacao?"
```

**IMPORTANTE**: Se `is_partial=True`, o Odoo cria `account.partial.reconcile` automaticamente.
Valor do extrato (ex: R$14.999,99) sera conciliado parcialmente contra o payment
(ex: R$547.733,45), reduzindo o residual do payment.

---

## Levantamento em Lote

```python
JOURNAL_MAP = {
    'GRAFENO': 883, 'SICOOB': 10, 'BRADESCO': 388,
    'AGIS GARANTIDA': 1046, 'AGIS': 1046,
    'BRADESCO (COPIA)': 1054, 'VORTX GRAFENO': 1068, 'VORTX': 1068,
}

# Mapeamento codigo bancario (extraido do payment_ref) → journal_id
# Usado por rastrear_cadeia_documental() para identificar journal destino
BANCO_JOURNAL_MAP = {
    '756': 10,    # SICOOB
    '237': 388,   # BRADESCO
    '033': 1046,  # AGIS (Santander DTVM)
}

import re

def _extrair_journal_destino(payment_ref):
    """Extrai journal_id de destino a partir do codigo bancario no payment_ref.

    Formato esperado: '...Banco 756 Agencia 4351 Conta 45078-2...'
    Retorna journal_id (int) ou None.
    """
    if not payment_ref:
        return None
    match = re.search(r'[Bb]anco\s+(\d+)', payment_ref)
    if match:
        return BANCO_JOURNAL_MAP.get(match.group(1))
    return None

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

    # Filtrar exclusoes (FAV, Movimentacao) — case-insensitive via .lower()
    lines = [l for l in lines
             if 'fav' not in (l['payment_ref'] or '').lower()
             and 'movimenta' not in (l['payment_ref'] or '').lower()]

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
