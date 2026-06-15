"""Testa EscrituracaoLfService.montar_invoice_entrada_direta — átomo NOVO da Skill 7
para a ENTRADA do retorno de industrialização (FLUXO L3 1.2.4, item 3 da automação).

Monta a NF-2 (insumos 5902→1902) DIRETO como account.move in_invoice, SEM PO
(refuta o caminho A do s66 que ganha tax lines espelho e não baixa a ATIVA).
Trava os 2 invariantes fiscais provados (s62/s67):
  - `l10n_br_calcular_imposto=False` no header (sem tax lines espelho → a baixa do
    no_payment do j1084 atua sobre a ATIVA);
  - `l10n_br_operacao_manual=True` em cada linha (senão o onchange apaga a op 3252 —
    gotcha s24/s62) + `l10n_br_operacao_id` na linha.
+ R3 (refNFe da remessa) com `company_id` (gotcha s67: o modelo referencia exige).
"""
from unittest.mock import MagicMock
from app.odoo.estoque.scripts.escrituracao import EscrituracaoLfService

LINHAS = [
    {'product_id': 210, 'quantity': 4.0, 'price_unit': 22.231},
    {'product_id': 105, 'quantity': 0.06, 'price_unit': 6.29},
]
BASE = dict(journal_id=1084, partner_id=35, company_id=1, invoice_date='2026-06-14',
            linhas=LINHAS, operacao_id=3252, invoice_origin='RET-IND-4870112-PILOTO')


def _svc():
    return EscrituracaoLfService(odoo=MagicMock())


def test_dry_run_monta_payload_sem_criar():
    odoo = MagicMock()
    res = EscrituracaoLfService(odoo=odoo).montar_invoice_entrada_direta(**BASE)  # dry_run default
    assert res['status'] == 'DRY_RUN_OK'
    mv = res['move_vals']
    assert mv['move_type'] == 'in_invoice'
    assert mv['journal_id'] == 1084 and mv['company_id'] == 1 and mv['partner_id'] == 35
    assert mv['invoice_origin'] == 'RET-IND-4870112-PILOTO'
    odoo.execute_kw.assert_not_called()
    odoo.create.assert_not_called()


def test_invariantes_fiscais_no_payload():
    """calcular_imposto=False no header + operacao_manual=True + op na linha (s66/s24)."""
    res = _svc().montar_invoice_entrada_direta(**BASE)
    mv = res['move_vals']
    assert mv['l10n_br_calcular_imposto'] is False
    for _, _, linha in mv['invoice_line_ids']:
        assert linha['l10n_br_operacao_id'] == 3252
        assert linha['l10n_br_operacao_manual'] is True
        assert {'product_id', 'quantity', 'price_unit'} <= set(linha)


def test_dry_run_calcula_total():
    res = _svc().montar_invoice_entrada_direta(**BASE)
    assert abs(res['total'] - (4.0 * 22.231 + 0.06 * 6.29)) < 1e-6
    assert res['n_linhas'] == 2


def test_linhas_vazias_falha_sem_criar():
    odoo = MagicMock()
    res = EscrituracaoLfService(odoo=odoo).montar_invoice_entrada_direta(
        **{**BASE, 'linhas': []})
    assert res['status'] == 'FALHA'
    odoo.execute_kw.assert_not_called()


def test_confirmar_cria_account_move():
    odoo = MagicMock()
    odoo.execute_kw.return_value = 999  # create retorna o id
    res = EscrituracaoLfService(odoo=odoo).montar_invoice_entrada_direta(
        **BASE, dry_run=False)
    assert res['status'] == 'CRIADO'
    assert res['invoice_id'] == 999
    # 1ª chamada execute_kw = create do account.move com o payload
    model, method, args = odoo.execute_kw.call_args_list[0][0][:3]
    assert (model, method) == ('account.move', 'create')
    assert args[0]['l10n_br_calcular_imposto'] is False


def test_r3_refnfe_gravado_com_company_id():
    """Com refnfe_chave: após create, grava referencia_ids incluindo company_id (gotcha s67)."""
    odoo = MagicMock()
    odoo.execute_kw.return_value = 999
    res = EscrituracaoLfService(odoo=odoo).montar_invoice_entrada_direta(
        **BASE, refnfe_chave='35260661724241000178550010000946041007356795', dry_run=False)
    assert res['invoice_id'] == 999
    assert res.get('r3') is True
    # alguma chamada execute_kw fez write de referencia_ids com a chave + company_id
    writes = [c for c in odoo.execute_kw.call_args_list
              if len(c[0]) >= 2 and c[0][1] == 'write']
    assert writes, 'esperado um write de referencia_ids'
    payload = writes[0][0][2][1]  # execute_kw('account.move','write',[[id], values])
    ref = payload['referencia_ids'][0][2]
    assert ref['l10n_br_chave_nf'].endswith('7356795')
    assert ref['company_id'] == 1
