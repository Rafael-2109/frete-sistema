"""Testa o LADO NOSSO (READ) da SAÍDA do retorno de industrialização (orchestrator C3
`saida_retorno_industrializacao`). A execução das 2 NFs é server-side (server action,
infra-Odoo `provisioning/`) — aqui testamos só planejar (spec/oráculo), validar (NF-2 da
SA vs spec) e medir (baixa PASSIVA pelo ciclo). Constituição SOT §6.3: a Descoberta é o
ORÁCULO; o orchestrator é READ-only (zero escrita Odoo).
"""
from unittest.mock import MagicMock
from app.odoo.estoque.orchestrators.saida_retorno_industrializacao import (
    SaidaRetornoIndustrializacaoExecutor as Saida,
    J847, RETIND, ACC_PASSIVA_LF,
)

CHAVE_REMESSA = '35260661724241000178550010000946041007356795'

DESCOBERTA = {
    'nf1_id': 791437,
    'pa': {'product_id': 27834, 'qtd_faturada': 1.0, 'lote': 60542},
    'produzido_total': 3.0,
    'componentes': [
        {'product_id': 210, 'default_code': '210030010', 'name': 'FRASCO', 'qty': 4.0,
         'price_unit': 22.231, 'subtotal': 88.924},
        {'product_id': 105, 'default_code': '104000007', 'name': 'CORANTE', 'qty': 0.06,
         'price_unit': 6.29, 'subtotal': 0.3774},
    ],
    'total': 89.30,
    'remessa': {'picking_id': 322451, 'picking_name': 'LF/IN/01790', 'votos': 2},
}


def _ex(nf1_read=None, chave='OK'):
    """Executor com odoo + 2 services-átomos mockados (planejar)."""
    odoo = MagicMock()
    descoberta = MagicMock()
    descoberta.descobrir_fonte_nf2.return_value = DESCOBERTA
    escrit = MagicMock()
    escrit.resolver_chave_remessa.return_value = (
        {'status': 'OK', 'chave': CHAVE_REMESSA, 'chaves': [CHAVE_REMESSA], 'n': 1}
        if chave == 'OK' else {'status': 'VAZIO', 'chave': None, 'chaves': [], 'n': 0})
    odoo.read.return_value = nf1_read if nf1_read is not None else [{
        'journal_id': [J847, 'VND PRODUCAO'], 'l10n_br_cstat_nf': '100',
        'invoice_date': '2026-06-14', 'state': 'posted'}]
    ex = Saida(odoo=odoo, escrit_svc=escrit, descoberta_svc=descoberta)
    return ex, odoo, escrit, descoberta


# ── planejar (READ — spec/oráculo) ────────────────────────────────────────────
def test_planejar_monta_spec_via_descoberta_oraculo():
    ex, odoo, escrit, descoberta = _ex()
    spec = ex.planejar(nf1_servico_id=791437, ciclo='RET-IND-4870112-PILOTO')
    descoberta.descobrir_fonte_nf2.assert_called_once_with(791437)
    assert spec['pa_product_id'] == 27834
    assert spec['n_componentes'] == 2
    assert spec['total_ic'] == 89.30
    assert spec['chave_remessa'] == CHAVE_REMESSA
    assert spec['cstat_nf1'] == '100'
    assert spec['ciclo'] == 'RET-IND-4870112-PILOTO'


def test_planejar_detecta_journal_j847():
    ex, _, _, _ = _ex()
    spec = ex.planejar(nf1_servico_id=791437)
    assert spec['journal_id_nf1'] == J847
    assert spec['journal_ok'] is True


def test_planejar_journal_errado_marca_journal_ok_false():
    ex, _, _, _ = _ex(nf1_read=[{'journal_id': [999, 'OUTRO'], 'l10n_br_cstat_nf': False,
                                 'invoice_date': '2026-06-14', 'state': 'draft'}])
    spec = ex.planejar(nf1_servico_id=1)
    assert spec['journal_ok'] is False


def test_planejar_chave_vazia_pre_sa_e_aceitavel():
    """Pré-SA a NF-1 ainda não tem R3 → resolver_chave_remessa VAZIO; planejar não quebra."""
    ex, _, _, _ = _ex(chave='VAZIO')
    spec = ex.planejar(nf1_servico_id=791437)
    assert spec['chave_remessa'] is None
    assert spec['n_componentes'] == 2   # spec segue válido pelo resto


def test_planejar_ciclo_default_derivado_do_pa():
    ex, _, _, _ = _ex()
    spec = ex.planejar(nf1_servico_id=791437)
    assert spec['ciclo'] == 'RET-IND-27834-791437'


# ── validar (READ — NF-2 da SA contra o spec) ─────────────────────────────────
def _dom_get(domain, field):
    for t in domain:
        if isinstance(t, (list, tuple)) and len(t) == 3 and t[0] == field:
            return t[2]
    return None


class FakeOdooValidar:
    """NF-2 da SA com N linhas configuráveis (CFOP/CST/conta) para exercitar validar()."""
    def __init__(self, *, linhas, journal=RETIND, origin='RET-IND-4870112-PILOTO',
                 refs=(1,), untax=89.30):
        self._linhas = linhas
        self._journal = journal
        self._origin = origin
        self._refs = list(refs)
        self._untax = untax
        self.escritas = []

    def read(self, model, ids, fields):
        return [{'journal_id': [self._journal, 'J'], 'invoice_origin': self._origin,
                 'referencia_ids': self._refs, 'state': 'draft', 'amount_untaxed': self._untax}]

    def search_read(self, model, domain, fields=None, **k):
        if model == 'account.move.line':
            return self._linhas
        return []

    def execute_kw(self, model, method, *a, **k):
        self.escritas.append(method)
        return True


def _linha(cfop='5902', cst='50', conta='1150100012', sub=44.65):
    return {'l10n_br_cfop_codigo': cfop, 'l10n_br_icms_cst': cst,
            'account_id': [123, f'{conta} TRANSITORIA FATURAMENTO'], 'price_subtotal': sub}


SPEC_VAL = {'ciclo': 'RET-IND-4870112-PILOTO', 'n_componentes': 2, 'total_ic': 89.30}


def test_validar_ok_quando_nf2_bate_o_spec():
    fake = FakeOdooValidar(linhas=[_linha(), _linha()])
    ex = Saida(odoo=fake)
    res = ex.validar(SPEC_VAL, nf2_id=795441)
    assert res['ok'] is True, res['divergencias']
    assert res['divergencias'] == []
    assert res['cfops'] == ['5902'] and res['csts'] == ['50']
    assert fake.escritas == []   # READ-only


def test_validar_pega_cfop_errado():
    fake = FakeOdooValidar(linhas=[_linha(cfop='5949'), _linha()])
    res = Saida(odoo=fake).validar(SPEC_VAL, nf2_id=1)
    assert res['ok'] is False
    assert any('CFOP' in d for d in res['divergencias'])


def test_validar_pega_conta_errada_e_journal_errado():
    fake = FakeOdooValidar(linhas=[_linha(conta='3101010001')], journal=999)
    res = Saida(odoo=fake).validar(SPEC_VAL, nf2_id=1)
    assert res['ok'] is False
    assert any('conta_linha' in d for d in res['divergencias'])
    assert any('journal' in d for d in res['divergencias'])


def test_validar_pega_n_linhas_e_total_divergente():
    # 1 linha (spec espera 2) + total 44.65 (spec 89.30)
    fake = FakeOdooValidar(linhas=[_linha()], untax=44.65)
    res = Saida(odoo=fake).validar(SPEC_VAL, nf2_id=1)
    assert res['ok'] is False
    assert any('n_linhas' in d for d in res['divergencias'])
    assert any('total' in d for d in res['divergencias'])


def test_validar_pega_r3_ausente():
    fake = FakeOdooValidar(linhas=[_linha(), _linha()], origin=False, refs=())
    res = Saida(odoo=fake).validar(SPEC_VAL, nf2_id=1)
    assert res['ok'] is False
    assert any('invoice_origin' in d for d in res['divergencias'])
    assert any('referencia_ids' in d for d in res['divergencias'])


# ── medir (READ — baixa da PASSIVA pelo ciclo) ────────────────────────────────
class FakeOdooMedir:
    """Modela a baixa da PASSIVA 26667 pela NF-2 do ciclo (query DIRECIONADA por origin)."""
    NF2 = 795441

    def __init__(self):
        self.escritas = []

    def search_read(self, model, domain, fields=None, **k):
        if model == 'account.move' and _dom_get(domain, 'invoice_origin'):
            return [{'id': self.NF2, 'name': 'RETIN/2026/00001'}]
        if model == 'account.move.line':
            acc = _dom_get(domain, 'account_id')
            mids = _dom_get(domain, 'move_id') or []
            if acc == ACC_PASSIVA_LF[0] and self.NF2 in mids:   # 26667: D = baixa
                return [{'debit': 279.23, 'credit': 0.0}]
            return []
        return []

    def execute_kw(self, model, method, *a, **k):
        self.escritas.append(method)
        return True


def test_medir_baixa_passiva_pelo_ciclo():
    spec = {'ciclo': 'RET-IND-4870112-PILOTO', 'total_ic': 279.23}
    fake = FakeOdooMedir()
    res = Saida(odoo=fake).medir(spec, nf2_id=FakeOdooMedir.NF2)
    assert res['baixa_passiva'] == 279.23
    assert res['conta_passiva'] == '5101020001'
    assert res['ok'] is True
    assert {m['tipo'] for m in res['moves_incluidos']} == {'saida'}
    assert fake.escritas == []   # READ-only


def test_medir_query_e_direcionada_por_origin_nunca_conta_inteira():
    """medir nunca varre a conta inteira (timeout) — só moves do ciclo por invoice_origin."""
    capt = {'domains': []}

    class Capt(FakeOdooMedir):
        def search_read(self, model, domain, fields=None, **k):
            capt['domains'].append((model, domain))
            return super().search_read(model, domain, fields, **k)

    Saida(odoo=Capt()).medir({'ciclo': 'C', 'total_ic': 279.23}, nf2_id=Capt.NF2)
    # toda busca de account.move filtra por invoice_origin (direcionada)
    am = [d for m, d in capt['domains'] if m == 'account.move']
    assert am and all(_dom_get(d, 'invoice_origin') is not None for d in am)
