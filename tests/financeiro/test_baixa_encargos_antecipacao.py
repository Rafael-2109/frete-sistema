# -*- coding: utf-8 -*-
"""
Testes da baixa de ANTECIPACAO (ex: Sendas/Assai) no template de baixa de titulos.

Cobre o nucleo deterministico (sem Odoo real): montagem do wizard de write-off de
encargos, resolucao da company do journal e o mapa de contas de encargos.
A baixa end-to-end no Odoo NAO e' testavel aqui (exige titulo aberto) — a primeira
execucao real deve ser feita com 1 titulo, conforme o fluxo da tela.
"""
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.financeiro.constants import CONTA_ENCARGOS_POR_COMPANY
from app.financeiro.services.baixa_titulos_service import BaixaTitulosService
from app.financeiro.services.antecipacao_caixinhas import (
    calcular_caixinhas,
    ESTADO_EMBUTIDO,
    ESTADO_NADA_APLICADO,
    ESTADO_ANO_2000,
)


def _make_item(valor_excel=5410.89, saldo_antes=5969.54):
    return SimpleNamespace(
        nf_excel='149407', parcela_excel=1, partner_odoo_id=204476,
        move_odoo_id=806368, move_odoo_name='VND/2026/04554', titulo_odoo_id=5345534,
        saldo_antes=saldo_antes, valor_excel=valor_excel, data_excel='2026-08-21',
        journal_excel='SICOOB',
        payment_odoo_id=None, payment_odoo_name=None,
        payment_desconto_odoo_id=None, payment_desconto_odoo_name=None,
        payment_encargos_odoo_id=None, payment_encargos_odoo_name=None,
    )


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


# ===========================================================================
# RECONCILIADOR — _montar_caixinhas e _baixar_por_caixinhas (modelo de caixinhas)
# ===========================================================================

def test_montar_caixinhas_sem_desconto_contratual_retorna_none():
    svc = BaixaTitulosService(connection=MagicMock())
    item = _make_item()
    svc._buscar_taxa_desconto_cliente = MagicMock(return_value=0.0)
    caixinhas, estado = svc._montar_caixinhas(item, 0)
    assert caixinhas is None and estado is None


def test_montar_caixinhas_com_desconto_classifica_embutido():
    svc = BaixaTitulosService(connection=MagicMock())
    item = _make_item(saldo_antes=5969.54)
    svc._buscar_taxa_desconto_cliente = MagicMock(return_value=0.005)
    svc._buscar_face_nfe = MagicMock(return_value=5999.54)
    svc._tem_linha_2000 = MagicMock(return_value=False)
    caixinhas, estado = svc._montar_caixinhas(item, 558.65)
    assert estado == ESTADO_EMBUTIDO
    assert caixinhas.liquido == 5410.89
    assert caixinhas.desconto == 30.00


def test_baixar_caixinhas_embutido_com_encargos_usa_writeoff():
    svc = BaixaTitulosService(connection=MagicMock())
    item = _make_item(valor_excel=5410.89, saldo_antes=5969.54)
    c = calcular_caixinhas(5999.54, 0.005, 558.65)  # liquido 5410.89
    svc._company_do_journal = MagicMock(return_value=1)   # journal FB -> conta 22768
    svc._criar_pagamento_com_writeoff_encargos = MagicMock(return_value=(999, 'PSIC/1502/01244'))
    svc._criar_pagamento = MagicMock()
    svc._criar_pagamento_especial = MagicMock()

    svc._baixar_por_caixinhas(item, c, ESTADO_EMBUTIDO, journal_id=10, company_id=4)

    svc._criar_pagamento_com_writeoff_encargos.assert_called_once()
    kw = svc._criar_pagamento_com_writeoff_encargos.call_args.kwargs
    assert kw['valor_liquido'] == 5410.89
    assert kw['conta_encargos_id'] == CONTA_ENCARGOS_POR_COMPANY[1]  # 22768 (company do journal)
    svc._criar_pagamento.assert_not_called()         # nao usou pagamento simples
    svc._criar_pagamento_especial.assert_not_called()  # NAO relancou desconto (embutido)
    assert item.payment_odoo_name == 'PSIC/1502/01244'
    assert 'Encargos' in item.payment_encargos_odoo_name


def test_baixar_caixinhas_embutido_sem_encargos_paga_liquido():
    svc = BaixaTitulosService(connection=MagicMock())
    item = _make_item(valor_excel=479.51, saldo_antes=479.51)
    c = calcular_caixinhas(481.92, 0.005, 0)  # titulo 479.51, liquido 479.51
    svc._company_do_journal = MagicMock(return_value=1)
    svc._criar_pagamento = MagicMock(return_value=(1, 'PSIC/x'))
    svc._postar_pagamento = MagicMock()
    svc._buscar_linha_credito = MagicMock(return_value=55)
    svc._reconciliar = MagicMock()
    svc._criar_pagamento_com_writeoff_encargos = MagicMock()

    svc._baixar_por_caixinhas(item, c, ESTADO_EMBUTIDO, journal_id=10, company_id=4)

    svc._criar_pagamento.assert_called_once()
    assert svc._criar_pagamento.call_args.kwargs['valor'] == 479.51
    svc._reconciliar.assert_called_once_with(55, item.titulo_odoo_id)
    svc._criar_pagamento_com_writeoff_encargos.assert_not_called()


def test_baixar_caixinhas_nada_aplicado_lanca_desconto_antes():
    svc = BaixaTitulosService(connection=MagicMock())
    item = _make_item(valor_excel=5410.89, saldo_antes=5999.54)  # saldo = face cheia
    c = calcular_caixinhas(5999.54, 0.005, 558.65)
    svc._company_do_journal = MagicMock(return_value=1)
    svc._criar_pagamento_especial = MagicMock(return_value=(7, 'DESC/x'))
    svc._buscar_linha_credito = MagicMock(return_value=70)
    svc._reconciliar = MagicMock()
    svc._criar_pagamento_com_writeoff_encargos = MagicMock(return_value=(999, 'PSIC/x'))

    svc._baixar_por_caixinhas(item, c, ESTADO_NADA_APLICADO, journal_id=10, company_id=4)

    # lancou o DESCONTO (face -> titulo) e DEPOIS baixou liquido+encargos
    svc._criar_pagamento_especial.assert_called_once()
    assert svc._criar_pagamento_especial.call_args.kwargs['valor'] == 30.00
    svc._criar_pagamento_com_writeoff_encargos.assert_called_once()


def test_baixar_caixinhas_valor_divergente_falha():
    svc = BaixaTitulosService(connection=MagicMock())
    item = _make_item(valor_excel=9999.99, saldo_antes=5969.54)  # VALOR != liquido (5410.89)
    c = calcular_caixinhas(5999.54, 0.005, 558.65)
    svc._company_do_journal = MagicMock(return_value=1)
    with pytest.raises(ValueError, match="diverge do"):
        svc._baixar_por_caixinhas(item, c, ESTADO_EMBUTIDO, journal_id=10, company_id=4)


def test_baixar_caixinhas_ano_2000_falha():
    svc = BaixaTitulosService(connection=MagicMock())
    item = _make_item()
    c = calcular_caixinhas(5999.54, 0.005, 558.65)
    with pytest.raises(ValueError, match="ANO_2000"):
        svc._baixar_por_caixinhas(item, c, ESTADO_ANO_2000, journal_id=10, company_id=4)
