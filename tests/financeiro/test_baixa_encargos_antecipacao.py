# -*- coding: utf-8 -*-
"""
Testes da baixa de ANTECIPACAO (ex: Sendas/Assai) no template de baixa de titulos.

Cobre o nucleo deterministico (sem Odoo real): montagem do wizard de write-off de
encargos, resolucao da company do journal e o mapa de contas de encargos.
A baixa end-to-end no Odoo NAO e' testavel aqui (exige titulo aberto) — a primeira
execucao real deve ser feita com 1 titulo, conforme o fluxo da tela.
"""
from unittest.mock import MagicMock

from app.financeiro.constants import CONTA_ENCARGOS_POR_COMPANY
from app.financeiro.services.baixa_titulos_service import BaixaTitulosService


def test_conta_encargos_por_company_cobre_as_quatro_empresas():
    # FB, SC, CD, LF (IDs confirmados no Odoo em 2026-06-23, code 3701010002)
    assert CONTA_ENCARGOS_POR_COMPANY == {1: 22768, 3: 24050, 4: 25334, 5: 26618}


def test_company_do_journal_extrai_id():
    conn = MagicMock()
    conn.search_read.return_value = [{'company_id': [1, 'NACOM GOYA - FB']}]
    svc = BaixaTitulosService(connection=conn)
    assert svc._company_do_journal(10) == 1


def test_company_do_journal_sem_journal_retorna_none():
    svc = BaixaTitulosService(connection=MagicMock())
    assert svc._company_do_journal(None) is None


def test_writeoff_encargos_monta_wizard_e_retorna_payment():
    conn = MagicMock()
    # 1) create wizard -> id; 2) action_create_payments -> None; 3) search_read payment
    conn.execute_kw.side_effect = [
        777,
        None,
        [{'id': 999, 'name': 'PSIC/1502/01244', 'move_id': [1, 'x'], 'state': 'posted'}],
    ]
    svc = BaixaTitulosService(connection=conn)

    payment_id, payment_name = svc._criar_pagamento_com_writeoff_encargos(
        titulo_id=5345534,
        partner_id=204476,
        valor_liquido=5410.89,
        journal_id=10,
        conta_encargos_id=22768,
        ref='NF-e: 149407',
        data='2026-08-21',
    )

    assert payment_id == 999
    assert payment_name == 'PSIC/1502/01244'

    # O wizard de registro de pagamento deve ter o write-off na conta de encargos,
    # com a diferenca (saldo-liquido) sendo reconciliada (fecha o titulo).
    # execute_kw('account.payment.register', 'create', [wizard_data], {'context': ctx})
    create_call = conn.execute_kw.call_args_list[0]
    assert create_call.args[0] == 'account.payment.register'
    assert create_call.args[1] == 'create'
    wizard_data = create_call.args[2][0]
    assert wizard_data['amount'] == 5410.89
    assert wizard_data['journal_id'] == 10
    assert wizard_data['writeoff_account_id'] == 22768
    assert wizard_data['payment_difference_handling'] == 'reconcile'
    # contexto (posicional) aponta para o titulo (account.move.line)
    contexto = create_call.args[3]['context']
    assert contexto['active_ids'] == [5345534]
    assert contexto['active_model'] == 'account.move.line'


def test_writeoff_encargos_cannot_marshal_none_e_sucesso():
    """'cannot marshal None' no action_create_payments = sucesso (O6), nao deve propagar."""
    conn = MagicMock()

    def _execute(*args, **kwargs):
        model, method = args[0], args[1]
        if model == 'account.payment.register' and method == 'create':
            return 777
        if model == 'account.payment.register' and method == 'action_create_payments':
            raise Exception('cannot marshal None unless allow_none is enabled')
        if model == 'account.payment' and method == 'search_read':
            return [{'id': 1000, 'name': 'PSIC/1502/01245', 'move_id': [2, 'y'], 'state': 'posted'}]
        return None

    conn.execute_kw.side_effect = _execute
    svc = BaixaTitulosService(connection=conn)

    payment_id, payment_name = svc._criar_pagamento_com_writeoff_encargos(
        titulo_id=1, partner_id=2, valor_liquido=100.0, journal_id=10,
        conta_encargos_id=22768, ref='x', data='2026-08-21',
    )
    assert payment_id == 1000
    assert payment_name == 'PSIC/1502/01245'
