"""Testa DescobertaIndustrializacaoService — descoberta READ-only da fonte da NF-2
de retorno de insumos (item 1 da automação industrialização FB↔LF).

Trava as 4 decisões provadas em PROD pelo s69 (NF-1 791437 / lote 60542):
  - genealogia recursiva lote→MO→semis→materiais de terceiros (31092), com RATEIO
    propagado pelos semis (qty × fator / produção_real);
  - exclusão da ÁGUA (type=consu, consumo local — não é material de terceiros);
  - VALOR via SVL do move de ENTRADA em 31092 (= price_unit da remessa, invariante
    5902=5901), NÃO o SVL do consumo (AVCO interno da LF);
  - DESCOBERTA da remessa por voto do picking de entrada em 31092.

Pattern de mock: FakeOdoo despacha search_read/read por modelo (+ campos do domain).
"""
from app.odoo.estoque.scripts.descoberta_industrializacao import (
    DescobertaIndustrializacaoService,
    LOC_TERCEIROS,
)


# ── FakeOdoo: despacha por modelo, inspecionando os campos do domain ──────────
def _dom_get(domain, field):
    """Valor do 1º termo (field, op, value) do domain (ignora '&'/'|')."""
    for t in domain:
        if isinstance(t, (list, tuple)) and len(t) == 3 and t[0] == field:
            return t[2]
    return None


def _dom_has(domain, field):
    return any(isinstance(t, (list, tuple)) and len(t) == 3 and t[0] == field for t in domain)


class FakeOdoo:
    """Odoo mock dirigido por dados — modela a genealogia do shoyu piloto (reduzida):
       PA lote 60542 (1 MO, produz 1) consome: FRASCO(4,terceiros) + SEMI(0,3) + ÁGUA(1,consu)
       SEMI lote 60541 (1 MO, produz 3) consome: CORANTE(0,6,terceiros)
    """
    PA, FRASCO, SEMI, CORANTE, AGUA = 27834, 210, 105022, 104007, 104017
    NF1, PK, LOTE_PA, LOTE_SEMI = 791437, 325346, 60542, 60541
    MO_PA, MO_SEMI = 9001, 9002
    M_FRASCO, M_SEMI, M_AGUA, M_CORANTE = 8001, 8002, 8003, 8101   # consumo
    E_FRASCO, E_CORANTE = 7001, 7002                               # entrada 31092
    PICK_REMESSA = 322451

    def search_read(self, model, domain, fields=None, limit=None, offset=None, order=None):
        if model == 'account.move.line':           # linha 5124 da NF-1
            return [{'product_id': [self.PA, 'PA'], 'quantity': 1.0}]
        if model == 'stock.picking':               # picking da NF-1
            return [{'id': self.PK, 'name': 'LF/SAI/IND/01947'}]
        if model == 'mrp.production':
            lote = _dom_get(domain, 'lot_producing_id')
            if lote == self.LOTE_PA:
                return [{'id': self.MO_PA, 'qty_producing': 1.0, 'product_qty': 1.0}]
            if lote == self.LOTE_SEMI:
                return [{'id': self.MO_SEMI, 'qty_producing': 3.0, 'product_qty': 3.0}]
            return []                              # folha (matéria-prima)
        if model == 'stock.move':
            if _dom_has(domain, 'raw_material_production_id'):   # raws de uma MO
                mo = _dom_get(domain, 'raw_material_production_id')
                if mo == self.MO_PA:
                    return [
                        {'id': self.M_FRASCO, 'product_id': [self.FRASCO, 'FRASCO'],
                         'product_qty': 4.0, 'location_id': [LOC_TERCEIROS, 'Terceiros']},
                        {'id': self.M_SEMI, 'product_id': [self.SEMI, 'SHOYU TRAD'],
                         'product_qty': 0.3, 'location_id': [LOC_TERCEIROS, 'Terceiros']},
                        {'id': self.M_AGUA, 'product_id': [self.AGUA, 'AGUA'],
                         'product_qty': 1.0, 'location_id': [LOC_TERCEIROS, 'Terceiros']},
                    ]
                if mo == self.MO_SEMI:
                    return [{'id': self.M_CORANTE, 'product_id': [self.CORANTE, 'CORANTE'],
                             'product_qty': 0.6, 'location_id': [LOC_TERCEIROS, 'Terceiros']}]
                return []
            if _dom_has(domain, 'location_dest_id'):             # entradas em 31092
                return [
                    {'id': self.E_FRASCO, 'product_id': [self.FRASCO, 'FRASCO'],
                     'picking_id': [self.PICK_REMESSA, 'LF/IN/01790'], 'date': '2026-06-01'},
                    {'id': self.E_CORANTE, 'product_id': [self.CORANTE, 'CORANTE'],
                     'picking_id': [self.PICK_REMESSA, 'LF/IN/01790'], 'date': '2026-06-01'},
                ]
            return []
        if model == 'stock.move.line':
            if _dom_has(domain, 'picking_id'):                   # lote do PA
                return [{'lot_id': [self.LOTE_PA, 'PILOTO-3105']}]
            mv = _dom_get(domain, 'move_id')                     # lote do componente
            return {self.M_SEMI: [{'lot_id': [self.LOTE_SEMI, 'SEMI-LOT']}]}.get(mv, [{'lot_id': False}])
        if model == 'stock.valuation.layer':                     # SVL de ENTRADA
            return [
                {'stock_move_id': [self.E_FRASCO, 'e'], 'unit_cost': 22.231, 'quantity': 4.0, 'value': 88.92},
                {'stock_move_id': [self.E_CORANTE, 'e'], 'unit_cost': 6.29, 'quantity': 0.6, 'value': 3.77},
            ]
        return []

    def read(self, model, ids, fields=None):
        if model == 'product.product':
            cat = {self.FRASCO: 'product', self.SEMI: 'product',
                   self.CORANTE: 'product', self.AGUA: 'consu'}
            cod = {self.FRASCO: '210030010', self.SEMI: '105000022',
                   self.CORANTE: '104000007', self.AGUA: '104000017'}
            return [{'id': i, 'default_code': cod.get(i, str(i)),
                     'name': cod.get(i, str(i)), 'standard_price': 1.0,
                     'type': cat.get(i, 'product')} for i in ids]
        return []


def _comps_by_code(res):
    return {c['default_code']: c for c in res['componentes']}


# ── Testes ────────────────────────────────────────────────────────────────────
def test_genealogia_acha_terceiros_e_exclui_agua():
    """16/16 no piloto; aqui: FRASCO + CORANTE (terceiros), ÁGUA (consu) excluída, SEMI não entra."""
    res = DescobertaIndustrializacaoService(FakeOdoo()).descobrir_fonte_nf2(FakeOdoo.NF1)
    codes = set(_comps_by_code(res))
    assert codes == {'210030010', '104000007'}, f"esperado FRASCO+CORANTE, veio {codes}"
    assert '104000017' not in codes, "ÁGUA (consu) deveria ser excluída"
    assert '105000022' not in codes, "SEMI não é linha de material de terceiros (explode nos filhos)"


def test_rateio_propaga_pelos_semis():
    """CORANTE vem via semi: 0,6 × (0,3/1,0) / 3,0 = 0,06. FRASCO direto: 4 × 1,0/1,0 = 4,0."""
    res = DescobertaIndustrializacaoService(FakeOdoo()).descobrir_fonte_nf2(FakeOdoo.NF1)
    c = _comps_by_code(res)
    assert abs(c['210030010']['qty'] - 4.0) < 1e-9
    assert abs(c['104000007']['qty'] - 0.06) < 1e-9


def test_valor_vem_do_svl_de_entrada_nao_do_consumo():
    """price_unit = unit_cost do SVL de ENTRADA (= remessa), não AVCO de consumo."""
    res = DescobertaIndustrializacaoService(FakeOdoo()).descobrir_fonte_nf2(FakeOdoo.NF1)
    c = _comps_by_code(res)
    assert abs(c['210030010']['price_unit'] - 22.231) < 1e-9
    assert abs(c['210030010']['subtotal'] - 4.0 * 22.231) < 1e-6
    assert abs(res['total'] - (4.0 * 22.231 + 0.06 * 6.29)) < 1e-6


def test_descobre_a_remessa_por_voto_do_picking_de_entrada():
    res = DescobertaIndustrializacaoService(FakeOdoo()).descobrir_fonte_nf2(FakeOdoo.NF1)
    assert res['remessa']['picking_id'] == FakeOdoo.PICK_REMESSA
    assert res['remessa']['votos'] == 2


def test_expoe_pa_lote_e_produzido_para_o_rateio():
    """Contrato p/ a SA: PA, qtd faturada, lote e produção real (denominador do rateio)."""
    res = DescobertaIndustrializacaoService(FakeOdoo()).descobrir_fonte_nf2(FakeOdoo.NF1)
    assert res['pa']['product_id'] == FakeOdoo.PA
    assert res['pa']['qtd_faturada'] == 1.0
    assert res['pa']['lote'] == FakeOdoo.LOTE_PA
    assert res['produzido_total'] == 1.0
