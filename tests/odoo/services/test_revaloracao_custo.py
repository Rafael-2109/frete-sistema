"""Testa RevaloracaoCustoService.revalorar_custo — átomo NOVO (skill revalorando-custo-odoo)
para ajustar o custo (AVCO) de um produto via wizard stock.valuation.layer.revaluation.

Usado pela ENTRADA do retorno de industrialização (FLUXO L3 1.2.4, passo C): sobe o
custo do PA por +Ic com contrapartida fechando a transitória (account_id = a conta que
SOBRA na NF-2 = 1150100011, NÃO o CMV — gotcha s65/s67). A revaloração DILUI no AVCO do
produto inteiro (pool) — esperado; o gate mede pela CONTA, não pelo std (decisão Rafael).

dry-run-first (AP4): dry-run NÃO toca o Odoo (mostra o plano do wizard).
"""
from unittest.mock import MagicMock
from app.odoo.estoque.scripts.revaloracao import RevaloracaoCustoService

BASE = dict(product_id=27834, added_value=279.23, account_id=26842,
            account_journal_id=8, company_id=1, reason='Ic industrializacao PILOTO 4870112')


def test_dry_run_monta_plano_sem_tocar_odoo():
    odoo = MagicMock()
    res = RevaloracaoCustoService(odoo=odoo).revalorar_custo(**BASE)  # dry_run default
    assert res['status'] == 'DRY_RUN_OK'
    p = res['plano']
    assert p['product_id'] == 27834 and p['added_value'] == 279.23
    assert p['account_id'] == 26842 and p['account_journal_id'] == 8
    odoo.execute_kw.assert_not_called()
    odoo.read.assert_not_called()


def test_added_value_zero_falha():
    odoo = MagicMock()
    res = RevaloracaoCustoService(odoo=odoo).revalorar_custo(**{**BASE, 'added_value': 0})
    assert res['status'] == 'FALHA'
    odoo.execute_kw.assert_not_called()


def test_account_id_invalido_falha():
    res = RevaloracaoCustoService(odoo=MagicMock()).revalorar_custo(**{**BASE, 'account_id': 0})
    assert res['status'] == 'FALHA'


def test_confirmar_cria_wizard_e_valida():
    odoo = MagicMock()
    odoo.execute_kw.side_effect = [555, True]  # create -> wid ; action_validate -> True
    res = RevaloracaoCustoService(odoo=odoo).revalorar_custo(
        **BASE, currency_id=12, dry_run=False)
    assert res['status'] == 'REVALORADO'
    assert res['wizard_id'] == 555
    chamadas = [(c[0][0], c[0][1]) for c in odoo.execute_kw.call_args_list]
    assert ('stock.valuation.layer.revaluation', 'create') in chamadas
    assert ('stock.valuation.layer.revaluation', 'action_validate_revaluation') in chamadas
    # payload do create leva account_id da transitória (NÃO CMV — s65/s67)
    create_call = odoo.execute_kw.call_args_list[0]
    assert create_call[0][2][0]['account_id'] == 26842


def test_currency_resolvido_da_empresa_quando_ausente():
    odoo = MagicMock()
    odoo.read.return_value = [{'currency_id': [12, 'BRL']}]
    odoo.execute_kw.side_effect = [555, True]
    res = RevaloracaoCustoService(odoo=odoo).revalorar_custo(**BASE, dry_run=False)
    assert res['status'] == 'REVALORADO'
    odoo.read.assert_called_once()  # leu a moeda da company
    assert odoo.execute_kw.call_args_list[0][0][2][0]['currency_id'] == 12
